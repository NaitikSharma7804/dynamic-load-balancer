import pytest

from loadbalancer.pool import (
    Backend,
    BackendPool,
)

from loadbalancer.health import (
    HealthMonitor,
)


class FakeResponse:

    def __init__(
        self,
        status_code,
    ):
        self.status_code = status_code


class FakeClient:

    def __init__(
        self,
        response=None,
        exception=None,
    ):
        self.response = response
        self.exception = exception

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False

    async def get(self, url):

        if self.exception:
            raise self.exception

        return self.response


@pytest.mark.asyncio
async def test_backend_failure_detection(
    monkeypatch,
):

    pool = BackendPool()

    backend = Backend(
        name="b1",
        host="127.0.0.1",
        port=5001,
    )

    pool.add(backend)

    monitor = HealthMonitor(
        pool=pool,
        interval=1,
        timeout=1,
        unhealthy_threshold=3,
        healthy_threshold=2,
    )

    def fake_client(*args, **kwargs):

        return FakeClient(
            exception=
            ConnectionError(
                "Backend unavailable"
            )
        )

    monkeypatch.setattr(
        "loadbalancer.health.httpx.AsyncClient",
        fake_client,
    )

    await monitor.check_once(
        backend
    )

    assert backend.state == "SUSPECT"

    await monitor.check_once(
        backend
    )

    await monitor.check_once(
        backend
    )

    assert backend.state == "UNHEALTHY"

    events = monitor.get_events()

    assert any(
        event["event"]
        == "BACKEND_MARKED_UNHEALTHY"
        for event in events
    )


@pytest.mark.asyncio
async def test_backend_recovery(
    monkeypatch,
):

    pool = BackendPool()

    backend = Backend(
        name="b1",
        host="127.0.0.1",
        port=5001,
    )

    backend.state = "UNHEALTHY"

    pool.add(backend)

    monitor = HealthMonitor(
        pool=pool,
        interval=1,
        timeout=1,
        unhealthy_threshold=3,
        healthy_threshold=2,
    )

    def fake_client(*args, **kwargs):

        return FakeClient(
            response=
            FakeResponse(200)
        )

    monkeypatch.setattr(
        "loadbalancer.health.httpx.AsyncClient",
        fake_client,
    )

    await monitor.check_once(
        backend
    )

    assert backend.state == "UNHEALTHY"

    await monitor.check_once(
        backend
    )

    assert backend.state == "HEALTHY"

    events = monitor.get_events()

    assert any(
        event["event"]
        == "BACKEND_RECOVERED"
        for event in events
    )


@pytest.mark.asyncio
async def test_health_check_success(
    monkeypatch,
):

    pool = BackendPool()

    backend = Backend(
        name="b1",
        host="127.0.0.1",
        port=5001,
    )

    pool.add(backend)

    monitor = HealthMonitor(
        pool=pool,
        interval=1,
        timeout=1,
        healthy_threshold=2,
    )

    def fake_client(*args, **kwargs):

        return FakeClient(
            response=
            FakeResponse(200)
        )

    monkeypatch.setattr(
        "loadbalancer.health.httpx.AsyncClient",
        fake_client,
    )

    result = await monitor.check_once(
        backend
    )

    assert result is True
    assert backend.consecutive_failures == 0
    assert backend.consecutive_successes == 1