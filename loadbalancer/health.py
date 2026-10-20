import asyncio
import time
from collections import deque

import httpx


class HealthMonitor:
    def __init__(
        self,
        pool,
        interval=2.0,
        timeout=1.0,
        unhealthy_threshold=3,
        healthy_threshold=2,
    ):
        self.pool = pool
        self.interval = interval
        self.timeout = timeout
        self.unhealthy_threshold = unhealthy_threshold
        self.healthy_threshold = healthy_threshold

        self.running = False
        self._task = None

        self.events = deque(maxlen=100)

    def record_event(
        self,
        backend,
        event,
        previous_state=None,
        current_state=None,
    ):
        backend_name = backend.name if hasattr(backend, "name") else str(backend)
        self.events.append(
            {
                "timestamp": time.time(),
                "backend": backend_name,
                "event": event,
                "previous_state": previous_state,
                "current_state": current_state,
            }
        )

    def _record_event(
        self,
        backend,
        event,
        previous_state=None,
        current_state=None,
    ):
        self.record_event(backend, event, previous_state, current_state)

    async def check_once(self, backend):
        if backend.draining:
            return False

        if getattr(backend, "simulated_failure", False):
            backend.last_check = time.time()
            await self._record_failure(backend, "Simulated failure active")
            return False

        url = f"http://{backend.host}:{backend.port}/health"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

            backend.last_check = time.time()

            if 200 <= response.status_code < 300:
                backend.consecutive_failures = 0
                backend.consecutive_successes += 1

                # Log initial discovery when first checked successfully
                if backend.consecutive_successes == 1 and not any(e["backend"] == backend.name for e in self.events):
                    self.record_event(
                        backend,
                        "INITIAL_HEALTH_CHECK_OK",
                        "UNKNOWN",
                        "HEALTHY",
                    )

                if backend.state == "UNHEALTHY":
                    if backend.consecutive_successes >= self.healthy_threshold:
                        old_state = backend.state
                        backend.state = "HEALTHY"
                        backend.recovery_started = time.time()
                        self.record_event(
                            backend,
                            "BACKEND_RECOVERED",
                            old_state,
                            backend.state,
                        )

                elif backend.state in ("SUSPECT", "RECOVERING"):
                    if backend.consecutive_successes >= self.healthy_threshold:
                        old_state = backend.state
                        backend.state = "HEALTHY"
                        backend.recovery_started = time.time()
                        self.record_event(
                            backend,
                            "BACKEND_RECOVERED",
                            old_state,
                            backend.state,
                        )

                return True

            await self._record_failure(backend, f"HTTP {response.status_code}")
            return False

        except Exception as exc:
            backend.last_check = time.time()
            await self._record_failure(backend, str(exc))
            return False

    async def _record_failure(self, backend, reason):
        backend.consecutive_successes = 0
        backend.consecutive_failures += 1

        if backend.state == "HEALTHY":
            if backend.consecutive_failures >= 1:
                old_state = backend.state
                backend.state = "SUSPECT"
                self.record_event(
                    backend,
                    "HEALTH_CHECK_FAILED",
                    old_state,
                    backend.state,
                )

        elif backend.state == "SUSPECT":
            if backend.consecutive_failures >= self.unhealthy_threshold:
                old_state = backend.state
                backend.state = "UNHEALTHY"
                self.record_event(
                    backend,
                    "BACKEND_MARKED_UNHEALTHY",
                    old_state,
                    backend.state,
                )

        elif backend.state == "RECOVERING":
            old_state = backend.state
            backend.state = "UNHEALTHY"
            self.record_event(
                backend,
                "RECOVERY_FAILED",
                old_state,
                backend.state,
            )

    async def record_passive_failure(self, backend, reason: str):
        """
        Passive failure signal from the reverse proxy engine when an upstream
        request to this backend fails (e.g. connection refused, network timeout).
        """
        if backend.draining:
            return

        backend.consecutive_successes = 0
        backend.consecutive_failures += 1

        if backend.state == "HEALTHY":
            if backend.consecutive_failures >= 1:
                old_state = backend.state
                backend.state = "SUSPECT"
                self.record_event(
                    backend,
                    "PASSIVE_FAILURE_SUSPECT",
                    old_state,
                    backend.state,
                )
        elif backend.state == "SUSPECT":
            if backend.consecutive_failures >= self.unhealthy_threshold:
                old_state = backend.state
                backend.state = "UNHEALTHY"
                self.record_event(
                    backend,
                    "BACKEND_MARKED_UNHEALTHY",
                    old_state,
                    backend.state,
                )
        elif backend.state == "RECOVERING":
            old_state = backend.state
            backend.state = "UNHEALTHY"
            self.record_event(
                backend,
                "RECOVERY_FAILED",
                old_state,
                backend.state,
            )

    async def run(self):
        self.running = True

        while self.running:
            backends = self.pool.all()

            for backend in backends:
                if not self.running:
                    break

                if backend.draining:
                    continue

                await self.check_once(backend)

            await asyncio.sleep(self.interval)

    async def start(self):
        if self.running:
            return

        self.running = True
        self._task = asyncio.create_task(self.run())

    async def stop(self):
        self.running = False
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=3)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None

    def get_events(self):
        return list(self.events)