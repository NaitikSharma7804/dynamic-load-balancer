import argparse
import asyncio
import csv
import statistics
import time
from pathlib import Path

import httpx


async def send_request(
    client: httpx.AsyncClient,
    url: str,
    request_id: int,
):
    start = time.perf_counter()

    try:
        response = await client.get(url)

        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000

        return {
            "request_id": request_id,
            "status_code": response.status_code,
            "latency_ms": round(elapsed_ms, 3),
            "success": response.is_success,
            "error": "",
            "served_by": response.headers.get(
                "X-Served-By",
                "",
            ),
        }

    except Exception as exc:

        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000

        return {
            "request_id": request_id,
            "status_code": 0,
            "latency_ms": round(elapsed_ms, 3),
            "success": False,
            "error": str(exc),
            "served_by": "",
        }


async def worker(
    client: httpx.AsyncClient,
    url: str,
    request_ids,
):

    tasks = [
        send_request(
            client,
            url,
            request_id,
        )
        for request_id in request_ids
    ]

    return await asyncio.gather(*tasks)


async def run_load_test(
    url: str,
    requests: int,
    concurrency: int,
    timeout: float,
):

    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=concurrency,
    )

    timeout_config = httpx.Timeout(timeout)

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout_config,
    ) as client:

        semaphore = asyncio.Semaphore(
            concurrency
        )

        async def limited_request(request_id):

            async with semaphore:

                return await send_request(
                    client,
                    url,
                    request_id,
                )

        start_time = time.perf_counter()

        tasks = [
            asyncio.create_task(
                limited_request(i)
            )
            for i in range(requests)
        ]

        results = await asyncio.gather(
            *tasks
        )

        total_time = (
            time.perf_counter() - start_time
        )

    return results, total_time


def calculate_summary(
    results,
    total_time,
):

    successful = [
        result
        for result in results
        if result["success"]
    ]

    failed = [
        result
        for result in results
        if not result["success"]
    ]

    latencies = [
        result["latency_ms"]
        for result in results
    ]

    successful_latencies = [
        result["latency_ms"]
        for result in successful
    ]

    if latencies:
        average_latency = statistics.mean(
            latencies
        )
    else:
        average_latency = 0

    if successful_latencies:

        sorted_latencies = sorted(
            successful_latencies
        )

        index_95 = int(
            0.95 *
            (len(sorted_latencies) - 1)
        )

        p95 = sorted_latencies[index_95]

    else:
        p95 = 0

    throughput = (
        len(results) / total_time
        if total_time > 0
        else 0
    )

    return {
        "total_requests": len(results),
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "success_rate_percent": (
            len(successful) /
            len(results) * 100
            if results
            else 0
        ),
        "average_latency_ms": average_latency,
        "p95_latency_ms": p95,
        "throughput_rps": throughput,
        "total_time_s": total_time,
    }


def save_csv(
    results,
    output_path,
):

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "request_id",
        "status_code",
        "latency_ms",
        "success",
        "error",
        "served_by",
    ]

    with output.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(results)


def print_summary(summary):

    print()
    print("=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)

    print(
        f"Total requests      : "
        f"{summary['total_requests']}"
    )

    print(
        f"Successful requests : "
        f"{summary['successful_requests']}"
    )

    print(
        f"Failed requests     : "
        f"{summary['failed_requests']}"
    )

    print(
        f"Success rate        : "
        f"{summary['success_rate_percent']:.2f}%"
    )

    print(
        f"Average latency     : "
        f"{summary['average_latency_ms']:.2f} ms"
    )

    print(
        f"P95 latency         : "
        f"{summary['p95_latency_ms']:.2f} ms"
    )

    print(
        f"Throughput          : "
        f"{summary['throughput_rps']:.2f} req/s"
    )

    print(
        f"Total test time     : "
        f"{summary['total_time_s']:.2f} s"
    )

    print("=" * 60)
    print()


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Async load generator for "
            "Dynamic Load Balancer"
        )
    )

    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8080/test",
        help="Load balancer URL",
    )

    parser.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Number of requests",
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Maximum concurrent requests",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=10,
        help="Request timeout in seconds",
    )

    parser.add_argument(
        "--output",
        default="results/load_test.csv",
        help="CSV output file",
    )

    args = parser.parse_args()

    if args.requests <= 0:
        raise ValueError(
            "requests must be greater than zero"
        )

    if args.concurrency <= 0:
        raise ValueError(
            "concurrency must be greater than zero"
        )

    print()
    print("Starting load test...")
    print(
        f"URL         : {args.url}"
    )
    print(
        f"Requests    : {args.requests}"
    )
    print(
        f"Concurrency : {args.concurrency}"
    )
    print()

    results, total_time = asyncio.run(
        run_load_test(
            url=args.url,
            requests=args.requests,
            concurrency=args.concurrency,
            timeout=args.timeout,
        )
    )

    summary = calculate_summary(
        results,
        total_time,
    )

    save_csv(
        results,
        args.output,
    )

    print_summary(summary)

    print(
        f"CSV saved to: {args.output}"
    )


if __name__ == "__main__":
    main()