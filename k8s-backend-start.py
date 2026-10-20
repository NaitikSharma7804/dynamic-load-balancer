
import subprocess
import sys
import time

backends = [
    ("b1", 5001, 50),
    ("b2", 5002, 100),
    ("b3", 5003, 200),
]

processes = []

try:
    for name, port, delay in backends:
        process = subprocess.Popen([
            sys.executable,
            "-m", "backend.server",
            "--port", str(port),
            "--name", name,
            "--delay-ms", str(delay),
        ])
        processes.append(process)

    while True:
        if any(p.poll() is not None for p in processes):
            raise RuntimeError("A backend process exited unexpectedly")
        time.sleep(2)

finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
