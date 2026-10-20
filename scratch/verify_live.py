import urllib.request
import json

try:
    req = urllib.request.Request("http://127.0.0.1:8080/app")
    with urllib.request.urlopen(req) as resp:
        print(f"GET /app: Status {resp.status}, Content Length {len(resp.read())}")
except Exception as e:
    print(f"GET /app failed: {e}")

try:
    req = urllib.request.Request("http://127.0.0.1:8080/api/products")
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode('utf-8')
        headers = dict(resp.headers)
        print(f"GET /api/products: Status {resp.status}")
        print(f"Headers: X-Served-By={resp.headers.get('X-Served-By')}, X-LB-Algorithm={resp.headers.get('X-LB-Algorithm')}, X-LB-Latency-Ms={resp.headers.get('X-LB-Latency-Ms')}")
        print(f"Body preview: {body[:150]}")
except Exception as e:
    print(f"GET /api/products failed: {e}")
