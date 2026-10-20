import asyncio
import httpx
import pytest
from starlette.requests import Request

from loadbalancer.health import HealthMonitor
from loadbalancer.metrics import Metrics
from loadbalancer.pool import Backend, BackendPool
from loadbalancer.proxy import ProxyEngine


def create_dummy_request(method="GET", path="/test", client_host="127.0.0.1"):
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [(b"host", b"localhost:8080"), (b"x-request-id", b"test-req-123")],
        "client": (client_host, 12345),
        "server": ("127.0.0.1", 8080),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


@pytest.mark.asyncio
async def test_503_when_no_backends_available():
    pool = BackendPool()
    metrics = Metrics()
    proxy = ProxyEngine(pool=pool, metrics=metrics)

    request = create_dummy_request()
    response = await proxy.forward(request)

    assert response.status_code == 503
    assert b"No healthy backend available" in response.body
    assert metrics.total_requests == 1
    assert metrics.total_errors == 1
    await proxy.close()


@pytest.mark.asyncio
async def test_502_on_upstream_connection_failure(monkeypatch):
    pool = BackendPool()
    pool.add(Backend(name="dead_backend", host="127.0.0.1", port=5001, weight=1))
    metrics = Metrics()
    proxy = ProxyEngine(pool=pool, metrics=metrics, retry_count=0)

    async def fake_request(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(proxy.client, "request", fake_request)

    request = create_dummy_request()
    response = await proxy.forward(request)

    assert response.status_code == 502
    assert b"Upstream connection failed" in response.body
    assert metrics.total_requests == 1
    assert metrics.total_errors == 1
    await proxy.close()


@pytest.mark.asyncio
async def test_504_on_upstream_timeout(monkeypatch):
    pool = BackendPool()
    pool.add(Backend(name="slow_backend", host="127.0.0.1", port=5001, weight=1))
    metrics = Metrics()
    proxy = ProxyEngine(pool=pool, metrics=metrics, retry_count=0)

    async def fake_request(*args, **kwargs):
        raise httpx.ReadTimeout("Simulated upstream timeout")

    monkeypatch.setattr(proxy.client, "request", fake_request)

    request = create_dummy_request()
    response = await proxy.forward(request)

    assert response.status_code == 504
    assert b"Upstream backend timed out" in response.body
    assert metrics.total_requests == 1
    assert metrics.total_errors == 1
    await proxy.close()


@pytest.mark.asyncio
async def test_metrics_bounded_memory():
    metrics = Metrics(max_samples=5)
    for i in range(20):
        metrics.record_client_request(latency_ms=float(i), success=True, status_code=200)

    assert metrics.total_requests == 20
    assert len(metrics.latencies) == 5
    assert list(metrics.latencies) == [15.0, 16.0, 17.0, 18.0, 19.0]


@pytest.mark.asyncio
async def test_passive_failure_signaling():
    pool = BackendPool()
    backend = Backend(name="b1", host="127.0.0.1", port=5001)
    pool.add(backend)

    monitor = HealthMonitor(pool=pool, unhealthy_threshold=2)
    metrics = Metrics()
    proxy = ProxyEngine(pool=pool, metrics=metrics, health=monitor, retry_count=0)

    # First passive failure moves to SUSPECT
    await monitor.record_passive_failure(backend, "Connection refused")
    assert backend.state == "SUSPECT"

    # Second passive failure moves to UNHEALTHY
    await monitor.record_passive_failure(backend, "Connection refused")
    assert backend.state == "UNHEALTHY"

    assert pool.healthy() == []
    await proxy.close()
