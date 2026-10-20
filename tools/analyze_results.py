import argparse
import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def load_results(path):

    with open(
        path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        return list(
            csv.DictReader(file)
        )


def percentile(values, percentage):

    if not values:
        return 0

    values = sorted(values)

    position = (
        percentage / 100
    ) * (len(values) - 1)

    lower = int(position)
    upper = min(
        lower + 1,
        len(values) - 1,
    )

    fraction = position - lower

    return (
        values[lower]
        + (
            values[upper]
            - values[lower]
        ) * fraction
    )


def analyze(results):

    total = len(results)

    successful = [
        row
        for row in results
        if row["success"].lower() == "true"
    ]

    failed = [
        row
        for row in results
        if row["success"].lower() != "true"
    ]

    latencies = [
        float(row["latency_ms"])
        for row in results
        if row["latency_ms"]
    ]

    successful_latencies = [
        float(row["latency_ms"])
        for row in successful
        if row["latency_ms"]
    ]

    backend_requests = Counter()

    backend_errors = Counter()

    status_codes = Counter()

    for row in results:

        backend = (
            row["served_by"]
            or "UNKNOWN"
        )

        backend_requests[backend] += 1

        status_codes[
            row["status_code"]
        ] += 1

        if row["success"].lower() != "true":

            backend_errors[backend] += 1

    summary = {
        "total": total,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": (
            len(successful) /
            total *
            100
            if total
            else 0
        ),
        "average_latency": (
            statistics.mean(latencies)
            if latencies
            else 0
        ),
        "median_latency": (
            statistics.median(latencies)
            if latencies
            else 0
        ),
        "p50": percentile(
            successful_latencies,
            50,
        ),
        "p95": percentile(
            successful_latencies,
            95,
        ),
        "p99": percentile(
            successful_latencies,
            99,
        ),
        "backend_requests": backend_requests,
        "backend_errors": backend_errors,
        "status_codes": status_codes,
    }

    return summary


def print_report(
    summary,
    input_file,
):

    print()
    print("=" * 65)
    print("DYNAMIC LOAD BALANCER - RESULT ANALYSIS")
    print("=" * 65)

    print(
        f"Input file          : {input_file}"
    )

    print(
        f"Total requests      : {summary['total']}"
    )

    print(
        f"Successful requests : "
        f"{summary['successful']}"
    )

    print(
        f"Failed requests     : "
        f"{summary['failed']}"
    )

    print(
        f"Success rate        : "
        f"{summary['success_rate']:.2f}%"
    )

    print()

    print(
        "Latency:"
    )

    print(
        f"  Average : "
        f"{summary['average_latency']:.2f} ms"
    )

    print(
        f"  Median  : "
        f"{summary['median_latency']:.2f} ms"
    )

    print(
        f"  P50     : "
        f"{summary['p50']:.2f} ms"
    )

    print(
        f"  P95     : "
        f"{summary['p95']:.2f} ms"
    )

    print(
        f"  P99     : "
        f"{summary['p99']:.2f} ms"
    )

    print()

    print(
        "Requests by backend:"
    )

    for backend, count in sorted(
        summary["backend_requests"].items()
    ):

        errors = summary[
            "backend_errors"
        ].get(
            backend,
            0,
        )

        print(
            f"  {backend:<15} "
            f"requests={count:<6} "
            f"errors={errors}"
        )

    print()

    print(
        "HTTP status codes:"
    )

    for status, count in sorted(
        summary["status_codes"].items()
    ):

        print(
            f"  {status}: {count}"
        )

    print("=" * 65)
    print()


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Analyze load-balancer CSV results"
        )
    )

    parser.add_argument(
        "input",
        help="CSV result file",
    )

    args = parser.parse_args()

    path = Path(args.input)

    if not path.exists():

        raise FileNotFoundError(
            f"File not found: {path}"
        )

    results = load_results(path)

    if not results:

        print(
            "CSV file contains no results."
        )

        return

    summary = analyze(results)

    print_report(
        summary,
        path,
    )


if __name__ == "__main__":
    main()