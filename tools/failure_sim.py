import argparse
import subprocess
import sys
import time
from pathlib import Path


PROCESS_MAP = {}


def start_backend(
    name: str,
    port: int,
    delay_ms: int,
):

    if name in PROCESS_MAP:

        process = PROCESS_MAP[name]

        if process.poll() is None:

            print(
                f"{name} is already running."
            )

            return

    command = [
        sys.executable,
        "-m",
        "backend.server",
        "--port",
        str(port),
        "--name",
        name,
        "--delay-ms",
        str(delay_ms),
    ]

    print(
        f"Starting {name} on port {port}..."
    )

    process = subprocess.Popen(
        command
    )

    PROCESS_MAP[name] = process

    print(
        f"{name} started with PID "
        f"{process.pid}"
    )


def stop_backend(name: str):

    process = PROCESS_MAP.get(name)

    if process is None:

        print(
            f"No process tracked for {name}."
        )

        return

    if process.poll() is not None:

        print(
            f"{name} is already stopped."
        )

        return

    print(
        f"Stopping {name}..."
    )

    process.terminate()

    try:

        process.wait(
            timeout=5
        )

    except subprocess.TimeoutExpired:

        print(
            f"{name} did not stop gracefully. "
            f"Force killing..."
        )

        process.kill()

        process.wait()

    print(
        f"{name} stopped."
    )


def show_status():

    print()
    print("=" * 50)
    print("BACKEND PROCESS STATUS")
    print("=" * 50)

    for name, process in PROCESS_MAP.items():

        running = (
            process.poll() is None
        )

        status = (
            "RUNNING"
            if running
            else "STOPPED"
        )

        print(
            f"{name:<10} {status:<10} "
            f"PID={process.pid}"
        )

    print("=" * 50)
    print()


def run_demo():

    backends = [
        ("b1", 5001, 50),
        ("b2", 5002, 100),
        ("b3", 5003, 200),
    ]

    print()
    print(
        "Starting all demo backends..."
    )

    for name, port, delay in backends:

        start_backend(
            name,
            port,
            delay,
        )

    time.sleep(2)

    show_status()

    print(
        "Demo backends are running."
    )

    print(
        "Press Ctrl+C to stop all "
        "managed backends."
    )

    try:

        while True:

            time.sleep(2)

    except KeyboardInterrupt:

        print()
        print(
            "Stopping demo backends..."
        )

        for name, _, _ in backends:

            stop_backend(name)


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Backend failure simulator "
            "for Dynamic Load Balancer"
        )
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    start_parser = subparsers.add_parser(
        "start",
        help="Start a backend",
    )

    start_parser.add_argument(
        "name"
    )

    start_parser.add_argument(
        "port",
        type=int,
    )

    start_parser.add_argument(
        "--delay-ms",
        type=int,
        default=50,
    )

    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop a managed backend",
    )

    stop_parser.add_argument(
        "name"
    )

    subparsers.add_parser(
        "status",
        help="Show backend status",
    )

    subparsers.add_parser(
        "demo",
        help="Start all demo backends",
    )

    args = parser.parse_args()

    if args.command == "start":

        start_backend(
            args.name,
            args.port,
            args.delay_ms,
        )

    elif args.command == "stop":

        stop_backend(
            args.name
        )

    elif args.command == "status":

        show_status()

    elif args.command == "demo":

        run_demo()

    else:

        parser.print_help()


if __name__ == "__main__":
    main()