import time
from collections import defaultdict, deque
from typing import Dict, List, Optional


class Metrics:
    """
    Performance and traffic metrics collector for NetPulse.

    Tracks client-facing requests, upstream backend attempts, retries,
    latencies (with bounded memory via rolling deque), and HTTP status distributions.
    """

    def __init__(self, max_samples: int = 10000):
        self.start_time = time.perf_counter()
        self.max_samples = max_samples

        self.total_requests = 0
        self.total_errors = 0
        self.total_retries = 0

        # Bounded sliding window for latencies to avoid unbounded memory growth
        self.latencies: deque = deque(maxlen=max_samples)

        # Global HTTP status code distribution
        self.status_codes: Dict[int, int] = defaultdict(int)

        self.backend_stats = defaultdict(
            lambda: {
                "requests": 0,
                "errors": 0,
                "latencies": deque(maxlen=max_samples),
                "status_codes": defaultdict(int),
            }
        )

    # ---------------------------------------------------------
    # Dedicated client request recording (single count per client request)
    # ---------------------------------------------------------

    def record_client_request(
        self,
        latency_ms: float = 0.0,
        success: bool = True,
        status_code: Optional[int] = None,
    ) -> None:
        """
        Record the completion of a client request.
        Guarantees total_requests is incremented exactly once per client request.
        """
        self.total_requests += 1

        if not success:
            self.total_errors += 1

        self.latencies.append(latency_ms)

        if status_code is not None:
            self.status_codes[status_code] += 1

    # ---------------------------------------------------------
    # Upstream backend attempt recording
    # ---------------------------------------------------------

    def record_backend_attempt(
        self,
        backend: str,
        latency_ms: float = 0.0,
        success: bool = True,
        status_code: Optional[int] = None,
        is_retry: bool = False,
    ) -> None:
        """
        Record an upstream attempt sent to a specific backend server.
        """
        if is_retry:
            self.total_retries += 1

        stats = self.backend_stats[backend]
        stats["requests"] += 1
        stats["latencies"].append(latency_ms)

        if not success:
            stats["errors"] += 1

        if status_code is not None:
            stats["status_codes"][status_code] += 1

    def record_retry(self) -> None:
        """Record an upstream retry invocation."""
        self.total_retries += 1

    # ---------------------------------------------------------
    # Backward compatible record method
    # ---------------------------------------------------------

    def record(
        self,
        backend: Optional[str] = None,
        latency_ms: float = 0.0,
        success: bool = True,
        status_code: Optional[int] = None,
    ) -> None:
        """
        Unified recording method for backward compatibility.
        """
        if backend is None:
            self.record_client_request(
                latency_ms=latency_ms,
                success=success,
                status_code=status_code,
            )
        else:
            self.record_backend_attempt(
                backend=backend,
                latency_ms=latency_ms,
                success=success,
                status_code=status_code,
            )

    # ---------------------------------------------------------
    # Percentile calculation
    # ---------------------------------------------------------

    @staticmethod
    def percentile(
        values,
        percentile: float,
    ) -> float:
        if not values:
            return 0.0

        sorted_values = sorted(values)

        index = (percentile / 100.0) * (len(sorted_values) - 1)

        lower = int(index)
        upper = min(lower + 1, len(sorted_values) - 1)
        fraction = index - lower

        return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction

    # ---------------------------------------------------------
    # Average latency
    # ---------------------------------------------------------

    @staticmethod
    def average(values) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    # ---------------------------------------------------------
    # Requests per second
    # ---------------------------------------------------------

    def rps(self) -> float:
        elapsed = time.perf_counter() - self.start_time
        if elapsed <= 0:
            return 0.0
        return self.total_requests / elapsed

    # ---------------------------------------------------------
    # Snapshot
    # ---------------------------------------------------------

    def snapshot(self) -> Dict:
        latency_values = list(self.latencies)

        per_backend = {}

        for name, stats in self.backend_stats.items():
            backend_latencies = list(stats["latencies"])
            requests = stats["requests"]
            errors = stats["errors"]

            per_backend[name] = {
                "requests": requests,
                "errors": errors,
                "error_rate": (errors / requests if requests else 0.0),
                "latency_ms": {
                    "avg": round(self.average(backend_latencies), 2),
                    "p50": round(self.percentile(backend_latencies, 50), 2),
                    "p95": round(self.percentile(backend_latencies, 95), 2),
                    "p99": round(self.percentile(backend_latencies, 99), 2),
                },
                "status_codes": dict(stats["status_codes"]),
            }

        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "total_retries": self.total_retries,
            "error_rate": (
                self.total_errors / self.total_requests if self.total_requests else 0.0
            ),
            "rps": round(self.rps(), 2),
            "latency_ms": {
                "avg": round(self.average(latency_values), 2),
                "p50": round(self.percentile(latency_values, 50), 2),
                "p95": round(self.percentile(latency_values, 95), 2),
                "p99": round(self.percentile(latency_values, 99), 2),
            },
            "status_codes": dict(self.status_codes),
            "per_backend": per_backend,
        }

    def remove_backend(self, backend: str) -> None:
        if backend in self.backend_stats:
            del self.backend_stats[backend]

    def reset(self) -> None:
        self.start_time = time.perf_counter()
        self.total_requests = 0
        self.total_errors = 0
        self.total_retries = 0
        self.latencies.clear()
        self.status_codes.clear()
        self.backend_stats.clear()