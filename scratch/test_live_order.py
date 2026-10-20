import urllib.request
import json

payload = {
    "customer_name": "Viva Evaluator Demo",
    "email": "examiner@university.edu",
    "address": "Faculty of Engineering & Computer Science",
    "items": [
        {"product_id": "prod-101", "quantity": 1},
        {"product_id": "prod-103", "quantity": 2}
    ],
    "payment_method": "Simulated Lab Transaction"
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    "http://127.0.0.1:8080/api/orders",
    data=data,
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as resp:
        res_body = json.loads(resp.read().decode('utf-8'))
        print("ORDER TEST SUCCESS!")
        print(f"Status Code: {resp.status}")
        print(f"Serving Backend Header: {resp.headers.get('X-Served-By')}")
        print(f"Order ID: {res_body.get('order', {}).get('order_id')}")
        print(f"Total: ${res_body.get('order', {}).get('summary', {}).get('total')}")
        print(f"Backend in Body: {res_body.get('backend')}")
except Exception as e:
    print(f"ORDER TEST FAILED: {e}")
