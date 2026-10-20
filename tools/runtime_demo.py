import argparse
import json
import time

import requests


def request_json(
    method,
    url,
    **kwargs,
):

    response = requests.request(
        method,
        url,
        timeout=5,
        **kwargs,
    )

    print()
    print(
        f"{method} {url}"
    )

    print(
        f"Status: {response.status_code}"
    )

    try:

        data = response.json()

        print(
            json.dumps(
                data,
                indent=2,
            )
        )

        return data

    except Exception:

        print(
            response.text
        )

        return None


def show_backends(
    admin_url,
):

    data = request_json(
        "GET",
        f"{admin_url}/admin/backends",
    )

    if not data:
        return

    print()
    print(
        "BACKEND STATUS"
    )
    print(
        "-" * 70
    )

    for backend in data["backends"]:

        print(
            f"{backend['name']:<8}"
            f" {backend['host']}:"
            f"{backend['port']:<6}"
            f" state={backend['state']:<12}"
            f" weight={backend['weight']:<3}"
            f" connections="
            f"{backend['active_connections']}"
        )


def switch_algorithm(
    admin_url,
    algorithm,
):

    return request_json(
        "PUT",
        f"{admin_url}/admin/algorithm",
        json={
            "algorithm": algorithm
        },
    )


def add_backend(
    admin_url,
    name,
    port,
    weight,
):

    return request_json(
        "POST",
        f"{admin_url}/admin/backends",
        json={
            "name": name,
            "host": "127.0.0.1",
            "port": port,
            "weight": weight,
        },
    )


def change_weight(
    admin_url,
    name,
    weight,
):

    return request_json(
        "PUT",
        f"{admin_url}/admin/backends/"
        f"{name}/weight",
        json={
            "weight": weight
        },
    )


def drain(
    admin_url,
    name,
):

    return request_json(
        "POST",
        f"{admin_url}/admin/backends/"
        f"{name}/drain",
    )


def undrain(
    admin_url,
    name,
):

    return request_json(
        "POST",
        f"{admin_url}/admin/backends/"
        f"{name}/undrain",
    )


def send_requests(
    lb_url,
    count=10,
):

    print()
    print(
        f"Sending {count} requests..."
    )

    distribution = {}

    for i in range(count):

        try:

            response = requests.get(
                f"{lb_url}/demo",
                timeout=5,
            )

            data = response.json()

            backend = data.get(
                "backend",
                "UNKNOWN",
            )

            distribution[backend] = (
                distribution.get(
                    backend,
                    0,
                )
                + 1
            )

        except Exception as exc:

            distribution["ERROR"] = (
                distribution.get(
                    "ERROR",
                    0,
                )
                + 1
            )

            print(
                f"Request {i + 1} failed: "
                f"{exc}"
            )

    print()
    print(
        "REQUEST DISTRIBUTION"
    )
    print(
        "-" * 40
    )

    for backend, count_value in (
        distribution.items()
    ):

        print(
            f"{backend:<15} "
            f"{count_value}"
        )

    return distribution


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Runtime demonstration tool "
            "for Dynamic Load Balancer"
        )
    )

    parser.add_argument(
        "--lb",
        default="http://127.0.0.1:8080",
    )

    parser.add_argument(
        "--admin",
        default="http://127.0.0.1:9090",
    )

    parser.add_argument(
        "--algorithm",
        default="round_robin",
        choices=[
            "round_robin",
            "weighted_rr",
            "least_conn",
            "ip_hash",
        ],
    )

    args = parser.parse_args()

    print("=" * 70)
    print(
        "DYNAMIC LOAD BALANCER "
        "RUNTIME DEMONSTRATION"
    )
    print("=" * 70)

    show_backends(
        args.admin
    )

    print()
    print(
        f"Switching algorithm to: "
        f"{args.algorithm}"
    )

    switch_algorithm(
        args.admin,
        args.algorithm,
    )

    time.sleep(1)

    send_requests(
        args.lb,
        count=20,
    )

    print()
    print(
        "Current metrics:"
    )

    request_json(
        "GET",
        f"{args.admin}/admin/metrics",
    )

    print()
    print(
        "Demo completed."
    )


if __name__ == "__main__":
    main()