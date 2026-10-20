from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from loadbalancer.pool import Backend
from loadbalancer.proxy import ProxyEngine
from loadbalancer.metrics import Metrics
from loadbalancer.health import HealthMonitor


class AddBackendRequest(BaseModel):
    name: str = Field(min_length=1)
    host: str = "127.0.0.1"
    port: int = Field(gt=0, le=65535)
    weight: int = Field(default=1, ge=1)
    delay_ms: int = Field(default=0, ge=0)


class WeightRequest(BaseModel):
    weight: int = Field(ge=1)


class AlgorithmRequest(BaseModel):
    algorithm: str


def build_admin_router(
    pool,
    proxy: ProxyEngine,
    metrics: Metrics,
    health: HealthMonitor,
):
    router = APIRouter(
        prefix="/admin",
        tags=["Admin"],
    )

    @router.get("/backends")
    async def list_backends():
        return {
            "backends": pool.snapshot()
        }

    @router.post("/backends")
    async def add_backend(
        request: AddBackendRequest,
    ):
        if pool.get(request.name):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Backend '{request.name}' "
                    "already exists"
                ),
            )

        backend = Backend(
            name=request.name,
            host=request.host,
            port=request.port,
            weight=request.weight,
            delay_ms=request.delay_ms,
            state="SUSPECT",
        )

        pool.add(backend)
        health.record_event(
            backend.name,
            "BACKEND_ADDED",
            "-",
            "SUSPECT",
        )

        # Non-blocking health check verification if monitor is active
        if hasattr(health, "running") and health.running:
            import asyncio
            asyncio.create_task(health.check_once(backend))

        return {
            "status": "added",
            "backend": backend.snapshot(),
        }

    @router.delete(
        "/backends/{name}"
    )
    async def delete_backend(name: str):
        backend = pool.get(name)

        if backend is None:
            raise HTTPException(
                status_code=404,
                detail="Backend not found",
            )

        if backend.active_connections > 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Backend has active "
                    "connections. Drain it first."
                ),
            )

        old_state = backend.state
        pool.remove(name)
        metrics.remove_backend(name)
        health.record_event(
            name,
            "BACKEND_REMOVED",
            old_state,
            "REMOVED",
        )

        return {
            "status": "removed",
            "name": name,
        }

    @router.put(
        "/backends/{name}/weight"
    )
    async def update_weight(
        name: str,
        request: WeightRequest,
    ):
        backend = pool.get(name)

        if backend is None:
            raise HTTPException(
                status_code=404,
                detail="Backend not found",
            )

        old_weight = backend.weight
        pool.set_weight(
            name,
            request.weight,
        )
        health.record_event(
            name,
            "WEIGHT_CHANGED",
            f"w={old_weight}",
            f"w={request.weight}",
        )

        return {
            "status": "updated",
            "backend": backend.snapshot(),
        }

    @router.post(
        "/backends/{name}/drain"
    )
    async def drain_backend(name: str):
        backend = pool.get(name)

        if backend is None:
            raise HTTPException(
                status_code=404,
                detail="Backend not found",
            )

        pool.drain(name)
        health.record_event(
            name,
            "BACKEND_DRAINED",
            "HEALTHY",
            "DRAINING",
        )

        return {
            "status": "draining",
            "backend": backend.snapshot(),
        }

    @router.post(
        "/backends/{name}/undrain"
    )
    async def undrain_backend(name: str):
        backend = pool.get(name)

        if backend is None:
            raise HTTPException(
                status_code=404,
                detail="Backend not found",
            )

        pool.undrain(name)
        health.record_event(
            name,
            "BACKEND_UNDRAINED",
            "DRAINING",
            "HEALTHY",
        )

        return {
            "status": "active",
            "backend": backend.snapshot(),
        }

    @router.put("/algorithm")
    async def change_algorithm(
        request: AlgorithmRequest,
    ):
        old_algo = proxy.algorithm_name
        try:
            proxy.set_algorithm(
                request.algorithm,
                reset_csv=True,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

        health.record_event(
            "SYSTEM",
            "ALGORITHM_CHANGED",
            old_algo,
            request.algorithm,
        )

        return {
            "status": "updated",
            "algorithm": proxy.algorithm_name,
        }

    @router.get("/algorithm")
    async def get_algorithm():
        return {
            "algorithm": proxy.algorithm_name
        }

    @router.get("/metrics")
    async def get_metrics():
        return metrics.snapshot()

    @router.post("/metrics/reset")
    async def reset_metrics():
        metrics.reset()
        pool.reset_stats()
        if hasattr(proxy, "reset_csv"):
            proxy.reset_csv()
        health.record_event(
            "SYSTEM",
            "METRICS_RESET",
            "-",
            "RESET",
        )
        return {"status": "reset"}

    @router.get("/csv/download")
    async def download_csv():
        import os
        from fastapi.responses import FileResponse
        if hasattr(proxy, "reset_csv") and not os.path.exists(proxy.csv_path):
            proxy.reset_csv()
        csv_path = getattr(proxy, "csv_path", "results/load_test.csv")
        return FileResponse(
            csv_path,
            media_type="text/csv",
            filename="load_test.csv",
        )

    @router.get("/health")
    async def get_health():
        return {
            "events": health.get_events()
        }

    @router.post("/dev/simulate-failure/{name}")
    async def simulate_failure(name: str):
        backend = pool.get(name)
        if backend is None:
            raise HTTPException(status_code=404, detail=f"Backend '{name}' not found")
        old_state = backend.state
        backend.simulated_failure = True
        backend.state = "UNHEALTHY"
        backend.consecutive_failures = health.unhealthy_threshold
        backend.consecutive_successes = 0
        health.record_event(name, "SIMULATED_FAILURE_INJECTED", old_state, "UNHEALTHY")
        return {"status": "failure_simulated", "backend": backend.snapshot()}

    @router.post("/dev/restore/{name}")
    async def dev_restore(name: str):
        backend = pool.get(name)
        if backend is None:
            raise HTTPException(status_code=404, detail=f"Backend '{name}' not found")
        old_state = backend.state
        backend.simulated_failure = False
        backend.consecutive_failures = 0
        backend.consecutive_successes = health.healthy_threshold
        backend.state = "HEALTHY"
        health.record_event(name, "SIMULATED_RECOVERY", old_state, "HEALTHY")
        return {"status": "restored", "backend": backend.snapshot()}

    return router