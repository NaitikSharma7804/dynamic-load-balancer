from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8080


@dataclass
class AdminConfig:
    host: str = "127.0.0.1"
    port: int = 9090


@dataclass
class ProxyConfig:
    algorithm: str = "round_robin"
    connect_timeout_s: float = 1.0
    request_timeout_s: float = 5.0
    retry_count: int = 1


@dataclass
class HealthConfig:
    interval_s: float = 2.0
    timeout_s: float = 1.0
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2
    slow_start_s: float = 10.0


@dataclass
class BackendConfig:
    name: str
    host: str
    port: int
    weight: int = 1
    delay_ms: int = 0


@dataclass
class AppConfig:

    server: ServerConfig = field(
        default_factory=ServerConfig
    )

    admin: AdminConfig = field(
        default_factory=AdminConfig
    )

    proxy: ProxyConfig = field(
        default_factory=ProxyConfig
    )

    health: HealthConfig = field(
        default_factory=HealthConfig
    )

    backends: list[BackendConfig] = field(
        default_factory=list
    )


def load_config(
    path: str = "config.yaml",
) -> AppConfig:

    config_path = Path(path)

    if not config_path.exists():

        raise FileNotFoundError(
            f"Configuration file not found: "
            f"{config_path}"
        )

    with config_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = yaml.safe_load(file) or {}

    server_data = data.get(
        "server",
        {},
    )

    admin_data = data.get(
        "admin",
        {},
    )

    proxy_data = data.get(
        "proxy",
        {},
    )

    health_data = data.get(
        "health",
        {},
    )

    backend_data = data.get(
        "backends",
        [],
    )

    server = ServerConfig(
        host=server_data.get(
            "host",
            "127.0.0.1",
        ),
        port=int(
            server_data.get(
                "port",
                8080,
            )
        ),
    )

    admin = AdminConfig(
        host=admin_data.get(
            "host",
            "127.0.0.1",
        ),
        port=int(
            admin_data.get(
                "port",
                9090,
            )
        ),
    )

    proxy = ProxyConfig(
        algorithm=proxy_data.get(
            "algorithm",
            "round_robin",
        ),
        connect_timeout_s=float(
            proxy_data.get(
                "connect_timeout_s",
                1.0,
            )
        ),
        request_timeout_s=float(
            proxy_data.get(
                "request_timeout_s",
                5.0,
            )
        ),
        retry_count=int(
            proxy_data.get(
                "retry_count",
                1,
            )
        ),
    )

    health = HealthConfig(
        interval_s=float(
            health_data.get(
                "interval_s",
                2.0,
            )
        ),
        timeout_s=float(
            health_data.get(
                "timeout_s",
                1.0,
            )
        ),
        unhealthy_threshold=int(
            health_data.get(
                "unhealthy_threshold",
                3,
            )
        ),
        healthy_threshold=int(
            health_data.get(
                "healthy_threshold",
                2,
            )
        ),
        slow_start_s=float(
            health_data.get(
                "slow_start_s",
                10.0,
            )
        ),
    )

    backends = []

    for item in backend_data:

        backends.append(
            BackendConfig(
                name=item["name"],
                host=item.get(
                    "host",
                    "127.0.0.1",
                ),
                port=int(
                    item["port"]
                ),
                weight=int(
                    item.get(
                        "weight",
                        1,
                    )
                ),
                delay_ms=int(
                    item.get(
                        "delay_ms",
                        0,
                    )
                ),
            )
        )

    return AppConfig(
        server=server,
        admin=admin,
        proxy=proxy,
        health=health,
        backends=backends,
    )