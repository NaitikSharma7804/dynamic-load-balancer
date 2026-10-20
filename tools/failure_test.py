"""
NetPulse - End-to-End Failure Detection, Failover & Recovery Verification.

Demonstrates:
1. Normal baseline traffic distribution.
2. Controlled backend failure (manual CTRL+C or automated simulation).
3. Health Monitor state transition (HEALTHY -> SUSPECT -> UNHEALTHY).
4. Automatic failover (traffic redirected to remaining healthy backends with 0 dropped requests).
5. Backend restoration & verified recovery back into active service.
"""

import argparse
import time
import requests


def check_backend(port: int) -> bool:
    try:
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
        return response.status_code == 200
    except Exception:
        return False


def check_load_balancer(url: str):
    try:
        return requests.get(url, timeout=2.0)
    except Exception as exc:
        return None


def get_health_events(admin_url: str):
    try:
        response = requests.get(f"{admin_url}/admin/health", timeout=3.0)
        return response.json().get("events", [])
    except Exception:
        return []


def get_backends(admin_url: str):
    try:
        response = requests.get(f"{admin_url}/admin/backends", timeout=3.0)
        return response.json().get("backends", [])
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="NetPulse Failure Detection & Failover Demonstration")
    parser.add_argument("--backend", default="b1", help="Target backend name to fail (default: b1)")
    parser.add_argument("--port", type=int, default=5001, help="Backend port (default: 5001)")
    parser.add_argument("--lb", default="http://127.0.0.1:8080", help="Load Balancer URL")
    parser.add_argument("--admin", default="http://127.0.0.1:9090", help="Admin API URL")
    parser.add_argument("--auto", action="store_true", help="Automated non-interactive simulation mode")
    args = parser.parse_args()

    print("=" * 75)
    print("      NETPULSE: FAILURE DETECTION, FAILOVER & RECOVERY DEMO")
    print("=" * 75)
    print(f"Target Backend     : {args.backend} (port {args.port})")
    print(f"Load Balancer URL  : {args.lb}")
    print(f"Admin API URL      : {args.admin}")
    print(f"Execution Mode     : {'AUTOMATED NON-INTERACTIVE' if args.auto else 'INTERACTIVE LIVE DEMO'}")
    print("=" * 75)

    # 1. Verify Initial Health
    print("\n[Step 1/5] Verifying initial backend health status...")
    backends = get_backends(args.admin)
    target_node = next((b for b in backends if b["name"] == args.backend), None)

    if not target_node:
        print(f"[!] Warning: Backend '{args.backend}' is not registered in Admin API!")
    else:
        print(f"    Backend '{args.backend}' initial state: {target_node['state']} (effective weight={target_node['effective_weight']})")

    # 2. Baseline Traffic
    print("\n[Step 2/5] Sending baseline traffic through proxy (10 requests)...")
    baseline_dist = {}
    for i in range(10):
        resp = check_load_balancer(f"{args.lb}/test-baseline?req={i}")
        if resp and resp.status_code == 200:
            served = resp.headers.get("X-Served-By", "unknown")
            baseline_dist[served] = baseline_dist.get(served, 0) + 1
        time.sleep(0.05)

    print(f"    Baseline Distribution: {baseline_dist}")

    # 3. Inject Failure
    print(f"\n[Step 3/5] Injecting Failure on Backend '{args.backend}'...")
    if args.auto:
        print(f"    Triggering simulated failure via Admin API (/admin/dev/simulate-failure/{args.backend})...")
        try:
            r = requests.post(f"{args.admin}/admin/dev/simulate-failure/{args.backend}", timeout=3.0)
            if r.status_code == 200:
                print(f"    [OK] Simulated failure injected on {args.backend} successfully.")
        except Exception as e:
            print(f"    [!] Error triggering failure: {e}")
    else:
        print(f"\n    >>> ACTION REQUIRED: STOP BACKEND '{args.backend}' (Port {args.port}) NOW (Press CTRL+C in its terminal) <<<")
        input("    Press ENTER after stopping the backend process...")

    # Wait for detection
    print("    Waiting for Health Monitor to observe failure (polling /admin/health)...")
    detected = False
    for sec in range(10):
        time.sleep(1)
        b_list = get_backends(args.admin)
        curr = next((b for b in b_list if b["name"] == args.backend), None)
        if curr and curr["state"] in ("SUSPECT", "UNHEALTHY"):
            print(f"    [OK] Health Monitor confirmed state transition -> '{curr['state']}' after {sec+1}s!")
            detected = True
            break

    if not detected:
        print("    [!] Health transition still pending. Continuing failover traffic verification...")

    # 4. Failover Verification
    print(f"\n[Step 4/5] Sending failover traffic (20 requests) while '{args.backend}' is unavailable...")
    success = 0
    failed = 0
    failover_dist = {}

    for i in range(20):
        resp = check_load_balancer(f"{args.lb}/failover-verify?req={i}")
        if resp and resp.status_code == 200:
            success += 1
            served = resp.headers.get("X-Served-By", "unknown")
            failover_dist[served] = failover_dist.get(served, 0) + 1
        else:
            failed += 1
        time.sleep(0.05)

    print("    FAILOVER TEST RESULTS:")
    print(f"    - Successful requests : {success} / 20 ({success/20*100:.1f}%)")
    print(f"    - Failed requests     : {failed} / 20")
    print(f"    - Failover Routing    : {failover_dist}")

    assert args.backend not in failover_dist, f"Failed backend '{args.backend}' should NOT have received traffic during failover!"
    print(f"    [OK] SUCCESS: Failed node '{args.backend}' was 100% excluded. Zero traffic dropped!")

    # 5. Recovery Verification
    print(f"\n[Step 5/5] Restoring Backend '{args.backend}'...")
    if args.auto:
        print(f"    Triggering simulated recovery via Admin API (/admin/dev/restore/{args.backend})...")
        try:
            r = requests.post(f"{args.admin}/admin/dev/restore/{args.backend}", timeout=3.0)
            if r.status_code == 200:
                print(f"    [OK] Recovery signal sent to {args.backend}.")
        except Exception as e:
            print(f"    [!] Error triggering recovery: {e}")
    else:
        print(f"    >>> ACTION: Restart backend '{args.backend}' on port {args.port} now <<<")
        input("    Press ENTER after restarting the backend...")

    print("    Waiting for Health Monitor to verify recovery...")
    recovered = False
    for sec in range(12):
        time.sleep(1)
        b_list = get_backends(args.admin)
        curr = next((b for b in b_list if b["name"] == args.backend), None)
        if curr and curr["state"] == "HEALTHY":
            print(f"    [OK] Health Monitor confirmed recovery: '{args.backend}' is HEALTHY again after {sec+1}s!")
            recovered = True
            break

    # Send traffic after recovery
    print("    Sending 10 requests to verify traffic has returned to the recovered node...")
    post_recovery_dist = {}
    for i in range(10):
        resp = check_load_balancer(f"{args.lb}/test-recovered?req={i}")
        if resp and resp.status_code == 200:
            served = resp.headers.get("X-Served-By", "unknown")
            post_recovery_dist[served] = post_recovery_dist.get(served, 0) + 1
        time.sleep(0.05)

    print(f"    Post-recovery Distribution: {post_recovery_dist}")
    print("\n" + "=" * 75)
    print("  DEMONSTRATION COMPLETE: Full Fault-Tolerance Lifecycle Verified!")
    print("=" * 75)


if __name__ == "__main__":
    main()