import asyncio
import csv
import os
import threading
import time
import uuid
from typing import Dict, List, Optional

import httpx
from fastapi import Request, Response

from .metrics import Metrics
from .pool import BackendPool


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

# Sensitive headers that should not be leaked in logs or errors
SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
}

# Safe and idempotent HTTP methods eligible for retry upon transient failure
RETRYABLE_METHODS = {
    "GET",
    "HEAD",
    "PUT",
    "DELETE",
    "OPTIONS",
}

ALGORITHMS = {
    "round_robin",
    "weighted_rr",
    "least_conn",
    "ip_hash",
}


class ProxyEngine:
    """
    Asynchronous Layer-7 HTTP Reverse Proxy Engine for NetPulse.

    Features:
    - Dynamic backend selection via pluggable scheduling strategies
    - Active connection tracking (acquire/release)
    - Connection pooling & configurable timeouts
    - Safe idempotent retry policy (avoids duplicating side-effects)
    - Accurate client request vs upstream attempt metrics
    - Standard RFC hop-by-hop header filtering
    - Precise upstream error mapping:
        * 502 Bad Gateway (connection refused / protocol error)
        * 503 Service Unavailable (no healthy backend available)
        * 504 Gateway Timeout (upstream timeout)
    """

    def __init__(
        self,
        pool: BackendPool,
        metrics: Metrics,
        algorithm: str = "round_robin",
        connect_timeout: float = 1.0,
        request_timeout: float = 5.0,
        retry_count: int = 1,
        health=None,
    ):
        self.pool = pool
        self.metrics = metrics
        self.health = health

        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout
        self.retry_count = retry_count

        self._algorithm = None
        self._strategy = None

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                request_timeout,
                connect=connect_timeout,
            ),
            follow_redirects=False,
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=200),
        )

        # Real-time CSV output tracking
        self._csv_lock = threading.Lock()
        self._csv_counter = 0
        self.csv_path = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "results",
                "load_test.csv",
            )
        )

        self.enable_csv_logging = True
        self.set_algorithm(algorithm, reset_csv=False)

    # ---------------------------------------------------------
    # Algorithm properties
    # ---------------------------------------------------------

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @property
    def algorithm_name(self) -> str:
        """Compatibility property used by admin API and dashboard."""
        return self._algorithm

    # ---------------------------------------------------------
    # Algorithm switching
    # ---------------------------------------------------------

    def set_algorithm(self, algorithm: str, reset_csv: bool = False) -> None:
        algorithm = algorithm.lower().strip()

        if algorithm not in ALGORITHMS:
            raise ValueError(
                f"Unsupported algorithm '{algorithm}'. "
                f"Available: {sorted(ALGORITHMS)}"
            )

        from .algorithms import (
            IPHash,
            LeastConnections,
            RoundRobin,
            SmoothWeightedRoundRobin,
        )

        strategies = {
            "round_robin": RoundRobin,
            "weighted_rr": SmoothWeightedRoundRobin,
            "least_conn": LeastConnections,
            "ip_hash": IPHash,
        }

        self._algorithm = algorithm
        self._strategy = strategies[algorithm]()
        if reset_csv and self.enable_csv_logging:
            self.reset_csv()

    # ---------------------------------------------------------
    # Real-Time CSV Logging & Reset
    # ---------------------------------------------------------

    def reset_csv(self) -> None:
        """Reset results/load_test.csv with fresh CSV header."""
        with self._csv_lock:
            self._csv_counter = 0
            try:
                os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
                with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "request_id",
                        "status_code",
                        "latency_ms",
                        "success",
                        "error",
                        "served_by",
                    ])
                    f.flush()
            except Exception as exc:
                print(f"[!] Warning: failed to reset CSV: {exc}")

    def _log_to_csv(
        self,
        status_code: int,
        latency_ms: float,
        success: bool,
        error: str = "",
        served_by: str = "",
        explicit_req_id: Optional[str] = None,
    ) -> None:
        """Log each processed request to results/load_test.csv in real time."""
        with self._csv_lock:
            if explicit_req_id is not None:
                req_id = explicit_req_id
            else:
                req_id = self._csv_counter
                self._csv_counter += 1

            try:
                os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
                file_exists = os.path.exists(self.csv_path) and os.path.getsize(self.csv_path) > 0
                with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow([
                            "request_id",
                            "status_code",
                            "latency_ms",
                            "success",
                            "error",
                            "served_by",
                        ])
                    writer.writerow([
                        req_id,
                        status_code,
                        round(latency_ms, 3),
                        success,
                        error,
                        served_by,
                    ])
                    f.flush()
            except Exception as exc:
                pass

    # ---------------------------------------------------------
    # Client cleanup
    # ---------------------------------------------------------

    async def close(self) -> None:
        await self.client.aclose()

    # ---------------------------------------------------------
    # Backend selection
    # ---------------------------------------------------------

    def _select_backend(self, request: Request):
        backends = self.pool.healthy()
        if not backends:
            return None

        return self._strategy.select(backends, request=request)

    # ---------------------------------------------------------
    # Request headers builder
    # ---------------------------------------------------------

    def _build_headers(
        self,
        request: Request,
        backend,
    ) -> Dict[str, str]:
        headers = {}

        for key, value in request.headers.items():
            k_lower = key.lower()
            if k_lower in HOP_BY_HOP_HEADERS or k_lower == "host":
                continue
            headers[key] = value

        # Client IP determination
        client_host = (
            request.client.host
            if request.client is not None
            else "127.0.0.1"
        )

        # Standard X-Forwarded headers
        existing_xff = request.headers.get("x-forwarded-for")
        if existing_xff:
            headers["X-Forwarded-For"] = f"{existing_xff}, {client_host}"
        else:
            headers["X-Forwarded-For"] = client_host

        headers["X-Forwarded-Proto"] = request.url.scheme
        headers["X-Forwarded-Host"] = request.headers.get("host", "localhost")

        # Unique tracing Request ID
        headers["X-Request-ID"] = request.headers.get(
            "X-Request-ID",
            str(uuid.uuid4()),
        )

        # Metadata headers for inspection and labs
        headers["X-LB-Algorithm"] = self._algorithm
        headers["X-Target-Backend"] = backend.name

        return headers

    # ---------------------------------------------------------
    # Response headers
    # ---------------------------------------------------------

    @staticmethod
    def _response_headers(
        response: httpx.Response,
    ) -> Dict[str, str]:
        headers = {}
        for key, value in response.headers.items():
            if key.lower() in HOP_BY_HOP_HEADERS:
                continue
            headers[key] = value
        return headers

    # ---------------------------------------------------------
    # Main reverse proxy request forwarding
    # ---------------------------------------------------------

    async def forward(
        self,
        request: Request,
    ) -> Response:
        method = request.method.upper()
        body = await request.body()

        # Retries permitted only for idempotent, safe methods
        attempts = 1
        if method in RETRYABLE_METHODS:
            attempts += self.retry_count

        attempted_backends: List[str] = []
        last_error = None
        overall_start = time.perf_counter()

        # -----------------------------------------------------
        # Upstream Attempt Loop
        # -----------------------------------------------------

        for attempt_idx in range(attempts):
            backend = self._select_backend(request)

            # -------------------------------------------------
            # 503 Service Unavailable: No healthy backend
            # -------------------------------------------------
            if backend is None:
                latency_ms = (time.perf_counter() - overall_start) * 1000
                self.metrics.record_client_request(
                    latency_ms=latency_ms,
                    success=False,
                    status_code=503,
                )
                self._log_to_csv(
                    status_code=503,
                    latency_ms=latency_ms,
                    success=False,
                    error="No healthy backend available",
                    served_by="none",
                    explicit_req_id=request.query_params.get("req"),
                )
                return Response(
                    content='{"detail":"No healthy backend available"}',
                    status_code=503,
                    media_type="application/json",
                )

            # -------------------------------------------------
            # Avoid re-selecting a failed backend during retries
            # -------------------------------------------------
            if backend.name in attempted_backends:
                available = [
                    item
                    for item in self.pool.healthy()
                    if item.name not in attempted_backends
                ]
                if not available:
                    break

                backend = self._strategy.select(available, request=request)
                if backend is None:
                    break

            attempted_backends.append(backend.name)

            backend_url = (
                f"http://{backend.host}:{backend.port}"
                f"{request.url.path}"
            )
            if request.url.query:
                backend_url += f"?{request.url.query}"

            headers = self._build_headers(request, backend)

            # Connection accounting
            await backend.acquire_connection()
            request_start = time.perf_counter()

            try:
                response = await self.client.request(
                    method=method,
                    url=backend_url,
                    content=body,
                    headers=headers,
                )

                latency_ms = (time.perf_counter() - request_start) * 1000
                success = response.status_code < 500

                if not success:
                    backend.errors += 1
                    if self.health is not None:
                        asyncio.create_task(
                            self.health.record_passive_failure(
                                backend, f"HTTP {response.status_code}"
                            )
                        )

                # Record per-backend attempt
                self.metrics.record_backend_attempt(
                    backend=backend.name,
                    latency_ms=latency_ms,
                    success=success,
                    status_code=response.status_code,
                    is_retry=(attempt_idx > 0),
                )

                # Safe retry if 5xx returned and attempts remaining
                if (
                    response.status_code >= 500
                    and method in RETRYABLE_METHODS
                    and len(attempted_backends) < attempts
                ):
                    continue

                # Successful / completed response to client
                overall_latency_ms = (time.perf_counter() - overall_start) * 1000
                self.metrics.record_client_request(
                    latency_ms=overall_latency_ms,
                    success=success,
                    status_code=response.status_code,
                )

                self._log_to_csv(
                    status_code=response.status_code,
                    latency_ms=overall_latency_ms,
                    success=success,
                    error="",
                    served_by=backend.name,
                    explicit_req_id=request.query_params.get("req"),
                )

                result_headers = self._response_headers(response)
                result_headers["X-Served-By"] = backend.name
                result_headers["X-LB-Latency-Ms"] = f"{overall_latency_ms:.2f}"
                result_headers["X-LB-Algorithm"] = self._algorithm

                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=result_headers,
                    media_type=response.headers.get("content-type"),
                )

            # -------------------------------------------------
            # Connection / Timeout / Protocol failures
            # -------------------------------------------------
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
                httpx.RemoteProtocolError,
            ) as exc:
                last_error = exc
                backend.errors += 1

                latency_ms = (time.perf_counter() - request_start) * 1000

                # Passive failure signal to health monitor
                if self.health is not None:
                    asyncio.create_task(
                        self.health.record_passive_failure(backend, str(exc))
                    )

                self.metrics.record_backend_attempt(
                    backend=backend.name,
                    latency_ms=latency_ms,
                    success=False,
                    status_code=None,
                    is_retry=(attempt_idx > 0),
                )

                if method not in RETRYABLE_METHODS:
                    break

            finally:
                await backend.release_connection()

        # -----------------------------------------------------
        # All attempts exhausted -> Return RFC-compliant Error
        # -----------------------------------------------------
        total_latency_ms = (time.perf_counter() - overall_start) * 1000

        # Differentiate 504 Gateway Timeout from 502 Bad Gateway
        if isinstance(
            last_error,
            (
                httpx.TimeoutException,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
            ),
        ):
            status_code = 504
            detail = f"Upstream backend timed out: {type(last_error).__name__}"
        else:
            status_code = 502
            detail = (
                f"Upstream connection failed: {type(last_error).__name__}"
                if last_error is not None
                else "All backend attempts failed"
            )

        self.metrics.record_client_request(
            latency_ms=total_latency_ms,
            success=False,
            status_code=status_code,
        )

        self._log_to_csv(
            status_code=status_code,
            latency_ms=total_latency_ms,
            success=False,
            error=detail,
            served_by=(attempted_backends[-1] if attempted_backends else "none"),
            explicit_req_id=request.query_params.get("req"),
        )

        return Response(
            content=f'{{"detail":"{detail}"}}',
            status_code=status_code,
            media_type="application/json",
        )