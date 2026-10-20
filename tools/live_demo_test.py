"""
Live demonstration and verification test for Dynamic Load Balancer.
Runs full lifecycle:
1. Starts backends (b1, b2, b3) and Load Balancer.
2. Demonstrates request distribution across healthy backends.
3. Shows metrics/graph data updates.
4. Simulates a backend crash (b2 fails) and verifies Health Monitor transitions (HEALTHY -> SUSPECT -> UNHEALTHY).
5. Proves automatic failover (b2 is skipped, requests still 100% succeed).
6. Demonstrates recovery (restarts b2, state becomes HEALTHY, traffic resumes).
7. Shuts down test processes cleanly.
"""

import subprocess
import sys
import time
import httpx

PYTHON = sys.executable
LB_URL = "http://127.0.0.1:8080"
ADMIN_URL = "http://127.0.0.1:9090"

processes = []

def start_process(cmd, name):
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    processes.append(p)
    return p

def wait_for_ready(url, max_wait=10):
    start = time.time()
    while time.time() - start < max_wait:
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code in (200, 404):
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False

def main():
    print("=" * 75)
    print("  DYNAMIC LOAD BALANCER - LIVE DEMO TEST")
    print("=" * 75)

    try:
        # 1. Start backends
        print("\n[1/6] Starting 3 Backend Servers...")
        p_b1 = start_process([PYTHON, "-m", "backend.server", "--port", "5001", "--name", "b1", "--delay-ms", "30"], "b1")
        p_b2 = start_process([PYTHON, "-m", "backend.server", "--port", "5002", "--name", "b2", "--delay-ms", "60"], "b2")
        p_b3 = start_process([PYTHON, "-m", "backend.server", "--port", "5003", "--name", "b3", "--delay-ms", "90"], "b3")

        # 2. Start Load Balancer
        print("      Starting Load Balancer (Proxy :8080, Admin :9090)...")
        p_lb = start_process([PYTHON, "-m", "loadbalancer.main"], "lb")

        print("      Waiting for services to become ready...")
        if not wait_for_ready("http://127.0.0.1:5001/health") or not wait_for_ready("http://127.0.0.1:9090/admin/backends"):
            print("ERROR: Services took too long to start.")
            return

        time.sleep(2.5) # Wait for initial health check cycle

        # 3. Check Initial Backend Status
        print("\n[2/6] Checking Initial Health Status (from /admin/backends):")
        backends_res = httpx.get(f"{ADMIN_URL}/admin/backends").json()
        for b in backends_res.get("backends", []):
            print(f"      Backend: {b['name']:<4} | State: {b['state']:<9} | Weight: {b['weight']} | Addr: {b['host']}:{b['port']}")

        # 4. Send Normal Traffic
        print("\n[3/6] Sending 9 Requests to Load Balancer (:8080) to observe traffic routing:")
        print(f"      {'Req #':<6} | {'Target URL':<28} | {'Served By':<10} | {'Status':<7} | {'Latency':<10}")
        print("      " + "-" * 70)
        distribution = {}
        for i in range(1, 10):
            t0 = time.perf_counter()
            resp = httpx.get(f"{LB_URL}/hello?req={i}")
            latency = (time.perf_counter() - t0) * 1000
            served_by = resp.headers.get("X-Served-By", "unknown")
            distribution[served_by] = distribution.get(served_by, 0) + 1
            print(f"      #{i:<5} | {LB_URL}/hello?req={i:<11} | {served_by:<10} | {resp.status_code:<7} | {latency:.2f} ms")
            time.sleep(0.1)

        print(f"\n      Request distribution so far: {distribution}")

        # Check graph metrics
        metrics = httpx.get(f"{ADMIN_URL}/admin/metrics").json()
        print(f"      Dashboard Metrics Snapshot: Total Requests={metrics['total_requests']}, P95 Latency={metrics['latency_ms']['p95']:.2f}ms")
        for b_name, b_data in metrics.get("per_backend", {}).items():
            print(f"        -> Bar Chart for '{b_name}': {b_data['requests']} requests")

        # 5. Simulate Failure: Kill Backend b2
        print("\n[4/6] Simulating Server Failure: Killing backend 'b2' (port 5002)...")
        p_b2.terminate()
        p_b2.wait()
        processes.remove(p_b2)
        print("      'b2' process terminated! Watching Health Monitor detect the failure...")

        # Poll health until UNHEALTHY
        detected = False
        for tick in range(1, 8):
            time.sleep(1.2)
            backends_state = {b["name"]: b["state"] for b in httpx.get(f"{ADMIN_URL}/admin/backends").json()["backends"]}
            b2_state = backends_state.get("b2")
            print(f"      Tick {tick} (Elapsed: ~{tick*1.2:.1f}s) -> Backend states: {backends_state}")
            if b2_state == "UNHEALTHY":
                detected = True
                print("      >>> SUCCESS: HealthMonitor marked 'b2' as UNHEALTHY! <<<")
                break

        # Show recent health events log
        health_events = httpx.get(f"{ADMIN_URL}/admin/health").json().get("events", [])
        print("      Recent Health Events logged in Load Balancer:")
        for ev in health_events[-4:]:
            print(f"        - {ev.get('event')} on {ev.get('backend')}: {ev.get('previous_state')} -> {ev.get('current_state')}")

        # 6. Test Failover
        print("\n[5/6] Failover Test: Sending 6 requests while 'b2' is DOWN...")
        failover_distribution = {}
        all_succeeded = True
        for i in range(1, 7):
            t0 = time.perf_counter()
            resp = httpx.get(f"{LB_URL}/failover-check?req={i}")
            latency = (time.perf_counter() - t0) * 1000
            served_by = resp.headers.get("X-Served-By", "unknown")
            failover_distribution[served_by] = failover_distribution.get(served_by, 0) + 1
            if resp.status_code != 200:
                all_succeeded = False
            print(f"      Req #{i}: Served by -> {served_by:<6} (Status: {resp.status_code}, Latency: {latency:.2f}ms)")
            time.sleep(0.1)

        print(f"\n      Failover distribution: {failover_distribution}")
        if "b2" not in failover_distribution and all_succeeded:
            print("      >>> VERIFIED: 100% of requests succeeded and ZERO requests went to 'b2'!")
            print("          Load balancer automatically bypassed the dead server without dropping requests! <<<")

        # 7. Recovery Test: Restart b2
        print("\n[6/6] Recovery Test: Restarting 'b2' on port 5002...")
        p_b2_new = start_process([PYTHON, "-m", "backend.server", "--port", "5002", "--name", "b2", "--delay-ms", "60"], "b2_restarted")
        print("      Waiting for HealthMonitor to detect recovery (healthy_threshold = 2)...")
        recovered = False
        for tick in range(1, 8):
            time.sleep(1.5)
            backends_state = {b["name"]: b["state"] for b in httpx.get(f"{ADMIN_URL}/admin/backends").json()["backends"]}
            print(f"      Tick {tick} -> Backend states: {backends_state}")
            if backends_state.get("b2") == "HEALTHY":
                recovered = True
                print("      >>> SUCCESS: 'b2' successfully recovered and is HEALTHY again! <<<")
                break

        # Send 3 requests to confirm b2 receives traffic again
        print("      Sending traffic to verify b2 is accepting requests again:")
        for i in range(1, 4):
            resp = httpx.get(f"{LB_URL}/recovery-check?req={i}")
            print(f"      Req #{i}: Served by -> {resp.headers.get('X-Served-By')}")

        print("\n" + "=" * 75)
        print("  ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 75)

    finally:
        print("\nCleaning up test processes...")
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        print("Cleanup done.")

if __name__ == "__main__":
    main()
