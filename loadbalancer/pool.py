import asyncio
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Backend:
    name: str
    host: str
    port: int
    weight: int = 1
    delay_ms: int = 0

    state: str = "HEALTHY"

    active_connections: int = 0
    requests: int = 0
    errors: int = 0

    consecutive_failures: int = 0
    consecutive_successes: int = 0

    last_check: Optional[float] = None
    recovery_started: Optional[float] = None

    draining: bool = False
    simulated_failure: bool = False

    _connection_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock,
        repr=False,
        compare=False,
    )

    @property
    def effective_weight(self):
        if self.draining:
            return 0

        if self.state != "HEALTHY":
            return 0

        return max(
            0,
            self.weight,
        )

    async def acquire_connection(self):
        async with self._connection_lock:
            self.active_connections += 1
            self.requests += 1

    async def release_connection(self):
        async with self._connection_lock:
            if self.active_connections > 0:
                self.active_connections -= 1

    def snapshot(self):
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "weight": self.weight,
            "delay_ms": self.delay_ms,
            "state": self.state,
            "active_connections": self.active_connections,
            "requests": self.requests,
            "errors": self.errors,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_check": self.last_check,
            "recovery_started": self.recovery_started,
            "draining": self.draining,
            "effective_weight": self.effective_weight,
        }


class BackendPool:
    def __init__(self):
        self._backends = {}

    def all(self):
        return list(self._backends.values())

    def healthy(self):
        return [
            backend
            for backend in self.all()
            if backend.state == "HEALTHY"
            and not backend.draining
            and backend.effective_weight > 0
        ]

    def get(self, name):
        return self._backends.get(name)

    def add(self, backend):
        if backend.name in self._backends:
            raise ValueError(
                f"Backend '{backend.name}' already exists"
            )

        self._backends[backend.name] = backend

    def remove(self, name):
        if name not in self._backends:
            raise KeyError(
                f"Backend '{name}' not found"
            )

        del self._backends[name]

    def set_weight(self, name, weight):
        backend = self.get(name)
        if backend is None:
            raise KeyError(
                f"Backend '{name}' not found"
            )

        backend.weight = weight

    def drain(self, name):
        backend = self.get(name)
        if backend is None:
            raise KeyError(
                f"Backend '{name}' not found"
            )

        backend.draining = True
        backend.state = "DRAINING"

    def undrain(self, name):
        backend = self.get(name)
        if backend is None:
            raise KeyError(
                f"Backend '{name}' not found"
            )

        backend.draining = False
        backend.consecutive_failures = 0
        backend.state = "HEALTHY"

    def healthy_count(self):
        return len(self.healthy())

    def reset_stats(self):
        for backend in self.all():
            backend.requests = 0
            backend.errors = 0

    def snapshot(self):
        return [
            backend.snapshot()
            for backend in self.all()
        ]