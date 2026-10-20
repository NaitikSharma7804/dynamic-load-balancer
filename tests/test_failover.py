import pytest

from loadbalancer.pool import (
    Backend,
    BackendPool,
)

from loadbalancer.algorithms.round_robin import (
    RoundRobin,
)

from loadbalancer.algorithms.weighted_rr import (
    SmoothWeightedRoundRobin,
)


def build_pool():

    pool = BackendPool()

    pool.add(
        Backend(
            name="b1",
            host="127.0.0.1",
            port=5001,
            weight=5,
        )
    )

    pool.add(
        Backend(
            name="b2",
            host="127.0.0.1",
            port=5002,
            weight=3,
        )
    )

    pool.add(
        Backend(
            name="b3",
            host="127.0.0.1",
            port=5003,
            weight=1,
        )
    )

    return pool


def test_failover_after_backend_failure():

    pool = build_pool()

    failed_backend = pool.get("b1")

    failed_backend.state = "UNHEALTHY"

    healthy = pool.healthy()

    names = [
        backend.name
        for backend in healthy
    ]

    assert "b1" not in names

    assert "b2" in names
    assert "b3" in names


def test_round_robin_failover():

    pool = build_pool()

    pool.get(
        "b2"
    ).state = "UNHEALTHY"

    algorithm = RoundRobin()

    selected = []

    for _ in range(30):

        backend = algorithm.select(
            pool.healthy()
        )

        selected.append(
            backend.name
        )

    assert "b2" not in selected

    assert "b1" in selected
    assert "b3" in selected


def test_weighted_failover():

    pool = build_pool()

    pool.get(
        "b1"
    ).state = "UNHEALTHY"

    algorithm = SmoothWeightedRoundRobin()

    selected = []

    for _ in range(100):

        backend = algorithm.select(
            pool.healthy()
        )

        selected.append(
            backend.name
        )

    assert "b1" not in selected

    assert "b2" in selected
    assert "b3" in selected


@pytest.mark.asyncio
async def test_draining_backend():

    pool = build_pool()

    backend = pool.get("b1")

    pool.drain("b1")

    assert backend.draining is True
    assert backend.state == "DRAINING"
    assert backend.effective_weight == 0

    healthy_names = [
        backend.name
        for backend in pool.healthy()
    ]

    assert "b1" not in healthy_names


def test_all_backends_down():

    pool = build_pool()

    for backend in pool.all():

        backend.state = "UNHEALTHY"

    assert pool.healthy_count() == 0
    assert pool.healthy() == []