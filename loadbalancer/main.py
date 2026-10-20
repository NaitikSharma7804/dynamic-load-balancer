import asyncio
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from loadbalancer.admin import build_admin_router
from loadbalancer.config import load_config
from loadbalancer.health import HealthMonitor
from loadbalancer.metrics import Metrics
from loadbalancer.pool import Backend, BackendPool
from loadbalancer.proxy import ProxyEngine


def create_components(config_path="config.yaml"):

    config = load_config(config_path)

    pool = BackendPool()

    for backend_config in config.backends:

        backend = Backend(
            name=backend_config.name,
            host=backend_config.host,
            port=backend_config.port,
            weight=backend_config.weight,
            delay_ms=backend_config.delay_ms,
        )

        pool.add(backend)

    metrics = Metrics()

    proxy = ProxyEngine(
        pool=pool,
        metrics=metrics,
        algorithm=config.proxy.algorithm,
        connect_timeout=config.proxy.connect_timeout_s,
        request_timeout=config.proxy.request_timeout_s,
        retry_count=config.proxy.retry_count,
    )

    health = HealthMonitor(
        pool=pool,
        interval=config.health.interval_s,
        timeout=config.health.timeout_s,
        unhealthy_threshold=config.health.unhealthy_threshold,
        healthy_threshold=config.health.healthy_threshold,
    )

    proxy.health = health

    return (
        config,
        pool,
        metrics,
        proxy,
        health,
    )


def create_proxy_app(
    config,
    pool,
    metrics,
    proxy,
    health,
):

    @asynccontextmanager
    async def lifespan(app: FastAPI):

        print("=" * 70)
        print("Dynamic Load Balancer + Health Monitor")
        print("=" * 70)

        print(
            f"Load Balancer : "
            f"http://{config.server.host}:"
            f"{config.server.port}"
        )

        print(
            f"Admin API    : "
            f"http://{config.admin.host}:"
            f"{config.admin.port}"
        )

        print(
            f"Algorithm    : "
            f"{proxy.algorithm_name}"
        )

        print("=" * 70)
        print("Configured backends:")

        for backend in pool.all():

            print(
                f"  {backend.name} -> "
                f"{backend.host}:{backend.port} "
                f"(weight={backend.weight})"
            )

        print("=" * 70)

        await health.start()

        yield

        await health.stop()
        await proxy.close()

    app = FastAPI(
        title="NetPulse Dynamic Load Balancer",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:8080",
            "http://localhost:8080",
            "http://127.0.0.1:9090",
            "http://localhost:9090",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    app.state.config = config
    app.state.pool = pool
    app.state.metrics = metrics
    app.state.proxy = proxy
    app.state.health = health

    dashboard_path = os.path.abspath(
        os.path.join(
            os.path.dirname(
                os.path.dirname(__file__)
            ),
            "dashboard",
        )
    )

    if os.path.isdir(dashboard_path):

        app.mount(
            "/dashboard/static",
            StaticFiles(
                directory=dashboard_path
            ),
            name="dashboard-static",
        )

    @app.get("/dashboard")
    async def dashboard():

        index_path = os.path.join(
            dashboard_path,
            "index.html",
        )

        if not os.path.exists(index_path):

            return JSONResponse(
                status_code=404,
                content={
                    "error": "Dashboard not found"
                },
            )

        return FileResponse(index_path)

    # ---------------------------------------------------------------
    # NetPulse Demo Store frontend (/app)
    # ---------------------------------------------------------------
    app_path = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "app",
        )
    )

    if os.path.isdir(app_path):
        assets_path = os.path.join(app_path, "assets")
        if os.path.isdir(assets_path):
            app.mount(
                "/app/assets",
                StaticFiles(directory=assets_path),
                name="app-assets",
            )

    @app.get("/app")
    async def demo_store():
        index_path = os.path.join(app_path, "index.html")
        if not os.path.exists(index_path):
            return JSONResponse(
                status_code=404,
                content={"error": "NetPulse Demo Store not found"},
            )
        return FileResponse(index_path)

    @app.get("/__lb_info")
    async def lb_info():

        return {
            "service": "Dynamic Load Balancer",
            "algorithm": proxy.algorithm_name,
            "healthy_backends": pool.healthy_count(),
        }

    @app.get("/")
    async def root():

        return {
            "service": "NetPulse Dynamic Load Balancer",
            "demo_store": "/app",
            "dashboard": "/dashboard",
            "health": "/__lb_info",
        }

    @app.api_route(
        "/{path:path}",
        methods=[
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
        ],
    )
    async def proxy_request(
        request: Request,
        path: str,
    ):

        return await proxy.forward(request)

    return app


def create_admin_app(
    config,
    pool,
    metrics,
    proxy,
    health,
):

    app = FastAPI(
        title="Load Balancer Admin API",
        version="1.0.0",
    )

    # --------------------------------------------------
    # CORS CONFIGURATION
    # --------------------------------------------------
    # The dashboard runs on port 8080 while the
    # Admin API runs on port 9090.
    #
    # Because these are different origins, the browser
    # requires CORS permission.
    # --------------------------------------------------

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:8080",
            "http://localhost:8080",
            "http://127.0.0.1:9090",
            "http://localhost:9090",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    router = build_admin_router(
        pool=pool,
        proxy=proxy,
        metrics=metrics,
        health=health,
    )

    app.include_router(router)

    @app.get("/health")
    async def admin_health_alias():
        return {
            "events": health.get_events()
        }

    @app.get("/")
    async def admin_root():

        return {
            "service": "Load Balancer Admin API",
            "endpoints": [
                "/admin/backends",
                "/admin/metrics",
                "/admin/health",
                "/admin/algorithm",
            ],
        }

    return app


def main():

    (
        config,
        pool,
        metrics,
        proxy,
        health,
    ) = create_components()

    proxy_app = create_proxy_app(
        config,
        pool,
        metrics,
        proxy,
        health,
    )

    admin_app = create_admin_app(
        config,
        pool,
        metrics,
        proxy,
        health,
    )

    proxy_config = uvicorn.Config(
        proxy_app,
        host=config.server.host,
        port=config.server.port,
        log_level="info",
    )

    admin_config = uvicorn.Config(
        admin_app,
        host=config.admin.host,
        port=config.admin.port,
        log_level="info",
    )

    proxy_server = uvicorn.Server(
        proxy_config
    )

    admin_server = uvicorn.Server(
        admin_config
    )

    async def run_servers():

        await asyncio.gather(
            proxy_server.serve(),
            admin_server.serve(),
        )

    asyncio.run(
        run_servers()
    )


if __name__ == "__main__":
    main()