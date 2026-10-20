"""
NetPulse - Automated Algorithm Comparison & Benchmarking Engine.

Performs identical, reproducible workloads across:
1. Round Robin
2. Smooth Weighted Round Robin
3. Least Connections
(and optionally IP Hash)

Records:
- Throughput (RPS)
- Latency percentiles (Avg, P50, P95, P99)
- Error rate and status counts
- Per-backend traffic distribution

Exports:
- results/algorithm_comparison.csv
- results/algorithm_comparison.png (4-panel publication-grade comparison chart)
"""

import argparse
import asyncio
import csv
import json
import os
import statistics
import time
from pathlib import Path
from typing import Dict, List, Tuple

import httpx
import matplotlib.pyplot as plt


async def send_single_request(
    client: httpx.AsyncClient,
    url: str,
    request_id: int,
) -> Dict:
    start = time.perf_counter()
    try:
        response = await client.get(url)
        elapsed_ms = (time.perf_counter() - start) * 1000
        served_by = response.headers.get("X-Served-By", "unknown")

        return {
            "request_id": request_id,
            "status_code": response.status_code,
            "latency_ms": round(elapsed_ms, 2),
            "success": response.is_success,
            "served_by": served_by,
            "error": "",
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "request_id": request_id,
            "status_code": 0,
            "latency_ms": round(elapsed_ms, 2),
            "success": False,
            "served_by": "none",
            "error": str(exc),
        }


async def benchmark_algorithm(
    lb_url: str,
    admin_url: str,
    algorithm: str,
    requests_count: int,
    concurrency: int,
    timeout: float = 5.0,
) -> Dict:
    print(f"\n[+] Preparing Benchmark for Algorithm: '{algorithm}'...")

    # 1. Switch algorithm via Admin API
    async with httpx.AsyncClient(timeout=5.0) as admin_client:
        switch_res = await admin_client.put(
            f"{admin_url}/admin/algorithm",
            json={"algorithm": algorithm},
        )
        if switch_res.status_code != 200:
            raise RuntimeError(f"Failed to switch algorithm to {algorithm}: {switch_res.text}")

        # 2. Reset metrics
        reset_res = await admin_client.post(f"{admin_url}/admin/metrics/reset")
        if reset_res.status_code != 200:
            raise RuntimeError(f"Failed to reset metrics: {reset_res.text}")

    await asyncio.sleep(0.5)

    # 3. Execute concurrent load
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    timeout_config = httpx.Timeout(timeout)
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(limits=limits, timeout=timeout_config) as client:
        async def bounded_request(req_id: int):
            async with semaphore:
                return await send_single_request(client, f"{lb_url}/benchmark?req={req_id}", req_id)

        start_time = time.perf_counter()
        tasks = [asyncio.create_task(bounded_request(i)) for i in range(requests_count)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

    # 4. Statistical calculations
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    latencies = [r["latency_ms"] for r in results]

    avg_lat = statistics.mean(latencies) if latencies else 0.0
    sorted_lats = sorted(latencies) if latencies else [0.0]

    def calc_percentile(data, pct):
        if not data:
            return 0.0
        idx = int((pct / 100.0) * (len(data) - 1))
        return data[idx]

    p50 = calc_percentile(sorted_lats, 50)
    p95 = calc_percentile(sorted_lats, 95)
    p99 = calc_percentile(sorted_lats, 99)
    throughput = len(results) / total_time if total_time > 0 else 0.0
    err_rate = (len(failed) / len(results) * 100.0) if results else 0.0

    backend_dist = {}
    for r in results:
        b = r["served_by"]
        backend_dist[b] = backend_dist.get(b, 0) + 1

    return {
        "algorithm": algorithm,
        "requests": len(results),
        "concurrency": concurrency,
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "error_rate_pct": round(err_rate, 2),
        "avg_latency_ms": round(avg_lat, 2),
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "p99_latency_ms": round(p99, 2),
        "throughput_rps": round(throughput, 2),
        "duration_s": round(total_time, 2),
        "backend_distribution": backend_dist,
    }


def save_csv_results(comparison_data: List[Dict], output_file: str):
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "algorithm",
        "requests",
        "concurrency",
        "successful_requests",
        "failed_requests",
        "error_rate_pct",
        "avg_latency_ms",
        "p50_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "throughput_rps",
        "duration_s",
        "backend_distribution",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in comparison_data:
            # Serialize dict field for clean CSV storage
            clean_row = dict(row)
            clean_row["backend_distribution"] = json.dumps(clean_row["backend_distribution"])
            writer.writerow(clean_row)

    print(f"\n[OK] Results exported successfully to: {path.resolve()}")


def generate_comparison_charts(comparison_data: List[Dict], output_image: str):
    path = Path(output_image)
    path.parent.mkdir(parents=True, exist_ok=True)

    algorithms = [d["algorithm"] for d in comparison_data]
    throughputs = [d["throughput_rps"] for d in comparison_data]
    p95_lats = [d["p95_latency_ms"] for d in comparison_data]
    avg_lats = [d["avg_latency_ms"] for d in comparison_data]
    error_rates = [d["error_rate_pct"] for d in comparison_data]

    # Style configuration
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("NetPulse - Load Balancing Scheduling Algorithms Comparison", fontsize=16, fontweight="bold")

    colors = ["#2563eb", "#06b6d4", "#10b981", "#f59e0b"]

    # 1. Throughput (RPS)
    ax1 = axes[0, 0]
    bars1 = ax1.bar(algorithms, throughputs, color=colors[:len(algorithms)], width=0.5)
    ax1.set_title("1. Throughput (Requests / Second)", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Throughput (RPS)")
    ax1.set_ylim(0, max(throughputs) * 1.25 if throughputs else 10)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + (max(throughputs)*0.02 if throughputs else 0.5), f"{yval:.1f}", ha="center", va="bottom", fontweight="bold")

    # 2. Latencies (Avg vs P95)
    ax2 = axes[0, 1]
    import numpy as np
    x = np.arange(len(algorithms))
    width = 0.35
    ax2.bar(x - width/2, avg_lats, width, label="Avg Latency", color="#3b82f6")
    ax2.bar(x + width/2, p95_lats, width, label="P95 Latency", color="#f59e0b")
    ax2.set_title("2. Response Latency Comparison (ms)", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Latency (ms)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(algorithms)
    ax2.legend()

    # 3. Error Rates
    ax3 = axes[1, 0]
    bars3 = ax3.bar(algorithms, error_rates, color="#ef4444", width=0.5)
    ax3.set_title("3. Error Rate (%)", fontsize=12, fontweight="bold")
    ax3.set_ylabel("Error Rate (%)")
    ax3.set_ylim(0, max(max(error_rates, default=0) * 1.5, 5))
    for bar in bars3:
        yval = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 0.1, f"{yval:.2f}%", ha="center", va="bottom", fontweight="bold")

    # 4. Backend Distribution (Grouped Bar Chart)
    ax4 = axes[1, 1]
    all_backends = sorted(list({b for d in comparison_data for b in d["backend_distribution"].keys() if b != "none"}))
    if not all_backends:
        all_backends = ["b1", "b2", "b3"]

    sub_width = 0.8 / len(all_backends)
    for idx, b_name in enumerate(all_backends):
        counts = [d["backend_distribution"].get(b_name, 0) for d in comparison_data]
        ax4.bar(x - 0.4 + idx * sub_width + sub_width/2, counts, sub_width, label=f"Backend {b_name}")

    ax4.set_title("4. Request Allocation Distribution by Backend", fontsize=12, fontweight="bold")
    ax4.set_ylabel("Requests Served")
    ax4.set_xticks(x)
    ax4.set_xticklabels(algorithms)
    ax4.legend()

    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()
    print(f"[OK] Comparison charts saved successfully to: {path.resolve()}")


def print_summary_table(comparison_data: List[Dict]):
    print("\n" + "=" * 90)
    print("                    NETPULSE ALGORITHM COMPARISON BENCHMARK SUMMARY")
    print("=" * 90)
    print(f"{'Algorithm':<16} | {'Reqs':<5} | {'Throughput':<12} | {'Avg Lat':<10} | {'P95 Lat':<10} | {'Err Rate':<8} | {'Distribution'}")
    print("-" * 90)
    for d in comparison_data:
        dist_str = ", ".join([f"{k}:{v}" for k, v in sorted(d["backend_distribution"].items())])
        print(
            f"{d['algorithm']:<16} | {d['requests']:<5} | {d['throughput_rps']:>7.2f} req/s | "
            f"{d['avg_latency_ms']:>7.2f} ms | {d['p95_latency_ms']:>7.2f} ms | {d['error_rate_pct']:>6.2f}% | {dist_str}"
        )
    print("=" * 90 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="NetPulse Algorithm Comparison Engine")
    parser.add_argument("--lb", default="http://127.0.0.1:8080", help="Load Balancer URL")
    parser.add_argument("--admin", default="http://127.0.0.1:9090", help="Admin API URL")
    parser.add_argument("--requests", type=int, default=100, help="Number of requests per algorithm")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent workers")
    parser.add_argument("--output", default="results/algorithm_comparison.csv", help="CSV output path")
    parser.add_argument("--graph", default="results/algorithm_comparison.png", help="PNG chart output path")
    args = parser.parse_args()

    # Algorithms to evaluate
    algorithms = ["round_robin", "weighted_rr", "least_conn"]

    print("=" * 70)
    print("  NETPULSE - REPEATABLE LOAD BALANCING ALGORITHM COMPARISON")
    print("=" * 70)
    print(f"Target LB URL       : {args.lb}")
    print(f"Admin API URL       : {args.admin}")
    print(f"Requests / Algorithm: {args.requests}")
    print(f"Concurrency Level   : {args.concurrency}")
    print("=" * 70)

    comparison_results = []
    for algo in algorithms:
        res = await benchmark_algorithm(
            lb_url=args.lb,
            admin_url=args.admin,
            algorithm=algo,
            requests_count=args.requests,
            concurrency=args.concurrency,
        )
        comparison_results.append(res)

    print_summary_table(comparison_results)
    save_csv_results(comparison_results, args.output)
    generate_comparison_charts(comparison_results, args.graph)


if __name__ == "__main__":
    asyncio.run(main())
