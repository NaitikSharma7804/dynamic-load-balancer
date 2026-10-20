import pytest

from fastapi.testclient import TestClient

from loadbalancer.main import create_components
from loadbalancer.main import create_admin_app


@pytest.fixture
def admin_client():

    (
        config,
        pool,
        metrics,
        proxy,
        health,
    ) = create_components()

    app = create_admin_app(
        config=config,
        pool=pool,
        metrics=metrics,
        proxy=proxy,
        health=health,
    )

    with TestClient(app) as client:
        yield client


def test_get_algorithm(admin_client):

    response = admin_client.get(
        "/admin/algorithm"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["algorithm"] == "round_robin"


def test_switch_algorithm(admin_client):

    algorithms = [
        "round_robin",
        "weighted_rr",
        "least_conn",
        "ip_hash",
    ]

    for algorithm in algorithms:

        response = admin_client.put(
            "/admin/algorithm",
            json={
                "algorithm": algorithm
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["algorithm"]
            == algorithm
        )


def test_invalid_algorithm(admin_client):

    response = admin_client.put(
        "/admin/algorithm",
        json={
            "algorithm": "invalid_algorithm"
        },
    )

    assert response.status_code == 400


def test_list_backends(admin_client):

    response = admin_client.get(
        "/admin/backends"
    )

    assert response.status_code == 200

    data = response.json()

    assert "backends" in data
    assert len(data["backends"]) == 3


def test_add_backend(admin_client):

    response = admin_client.post(
        "/admin/backends",
        json={
            "name": "b4",
            "host": "127.0.0.1",
            "port": 5004,
            "weight": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "added"
    assert data["backend"]["name"] == "b4"


def test_duplicate_backend(admin_client):

    first = admin_client.post(
        "/admin/backends",
        json={
            "name": "b4",
            "host": "127.0.0.1",
            "port": 5004,
            "weight": 2,
        },
    )

    assert first.status_code == 200

    second = admin_client.post(
        "/admin/backends",
        json={
            "name": "b4",
            "host": "127.0.0.1",
            "port": 5004,
            "weight": 2,
        },
    )

    assert second.status_code == 409


def test_change_weight(admin_client):

    response = admin_client.put(
        "/admin/backends/b1/weight",
        json={
            "weight": 10
        },
    )

    assert response.status_code == 200

    backend = response.json()["backend"]

    assert backend["name"] == "b1"
    assert backend["weight"] == 10


def test_drain_backend(admin_client):

    response = admin_client.post(
        "/admin/backends/b1/drain"
    )

    assert response.status_code == 200

    backend = response.json()["backend"]

    assert backend["draining"] is True
    assert backend["state"] == "DRAINING"


def test_undrain_backend(admin_client):

    admin_client.post(
        "/admin/backends/b1/drain"
    )

    response = admin_client.post(
        "/admin/backends/b1/undrain"
    )

    assert response.status_code == 200

    backend = response.json()["backend"]

    assert backend["draining"] is False
    assert backend["state"] == "HEALTHY"


def test_remove_backend(admin_client):

    add_response = admin_client.post(
        "/admin/backends",
        json={
            "name": "temporary",
            "host": "127.0.0.1",
            "port": 5999,
            "weight": 1,
        },
    )

    assert add_response.status_code == 200

    delete_response = admin_client.delete(
        "/admin/backends/temporary"
    )

    assert delete_response.status_code == 200

    list_response = admin_client.get(
        "/admin/backends"
    )

    names = [
        backend["name"]
        for backend in
        list_response.json()["backends"]
    ]

    assert "temporary" not in names