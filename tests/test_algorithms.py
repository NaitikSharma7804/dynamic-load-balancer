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

from loadbalancer.algorithms.least_conn import (
    LeastConnections,
)

from loadbalancer.algorithms.ip_hash import (
    IPHash,
)


def create_pool():

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


def test_round_robin():

    pool = create_pool()

    algorithm = RoundRobin()

    selected = []

    for _ in range(9):

        backend = algorithm.select(
            pool.healthy()
        )

        selected.append(
            backend.name
        )

    assert selected == [
        "b1",
        "b2",
        "b3",
        "b1",
        "b2",
        "b3",
        "b1",
        "b2",
        "b3",
    ]


def test_weighted_round_robin():

    pool = create_pool()

    algorithm = SmoothWeightedRoundRobin()

    counts = {
        "b1": 0,
        "b2": 0,
        "b3": 0,
    }

    for _ in range(900):

        backend = algorithm.select(
            pool.healthy()
        )

        counts[
            backend.name
        ] += 1

    assert counts["b1"] > counts["b2"]
    assert counts["b2"] > counts["b3"]

    assert (
        abs(
            counts["b1"] / 900
            - 5 / 9
        ) < 0.05
    )

    assert (
        abs(
            counts["b2"] / 900
            - 3 / 9
        ) < 0.05
    )

    assert (
        abs(
            counts["b3"] / 900
            - 1 / 9
        ) < 0.05
    )


@pytest.mark.asyncio
async def test_least_connections():

    pool = create_pool()

    backends = pool.healthy()

    await backends[0].acquire_connection()
    await backends[0].acquire_connection()

    await backends[1].acquire_connection()

    algorithm = LeastConnections()

    selected = algorithm.select(
        pool.healthy()
    )

    assert selected.name == "b3"

    await backends[0].release_connection()
    await backends[0].release_connection()

    await backends[1].release_connection()


def test_ip_hash():

    pool = create_pool()

    algorithm = IPHash()

    request_a = {
        "client_ip": "192.168.1.10"
    }

    request_b = {
        "client_ip": "192.168.1.10"
    }

    backend_a = algorithm.select(
        pool.healthy(),
        request_a,
    )

    backend_b = algorithm.select(
        pool.healthy(),
        request_b,
    )

    assert backend_a.name == backend_b.name


def test_unhealthy_backend_is_not_selected():

    pool = create_pool()

    backend = pool.get("b2")

    backend.state = "UNHEALTHY"

    algorithm = RoundRobin()

    selected = []

    for _ in range(20):

        selected.append(
            algorithm.select(
                pool.healthy()
            ).name
        )

    assert "b2" not in selected