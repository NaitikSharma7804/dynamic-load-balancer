# NetPulse
### Intelligent Network Traffic Management, Adaptive Load Balancing & Fault-Tolerant Monitoring System

[![Tests](https://img.shields.io/badge/pytest-44%20passed-brightgreen.svg)](#6-running-automated-tests)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](#2-technology-stack)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](#2-technology-stack)
[![Demo Store](https://img.shields.io/badge/Demo%20Store-%3A8080%2Fapp-blueviolet.svg)](#b-open-the-netpulse-demo-store)
[![License](https://img.shields.io/badge/course-Computer%20Networks-orange.svg)](#)

NetPulse is an asynchronous **Layer-7 HTTP Reverse Proxy, Dynamic Load Balancer, and Fault-Tolerant Monitoring System** developed in Python. It intelligently schedules incoming HTTP requests across multiple backend servers using four distinct algorithms, monitors server availability in real-time, executes zero-downtime failover upon server death, measures network performance, and presents real-time telemetry through an observatory web dashboard and a user-facing **NetPulse Demo Store**.

---

## 1. Objectives & Computer Networks Principles Demonstrated

NetPulse was engineered for academic rigor and practical demonstration of core Computer Networks concepts:
* **Application Layer (HTTP/1.1)**: HTTP reverse proxying, wildcard request routing (`/{path:path}`), hop-by-hop header stripping (RFC 7230/9110), `X-Forwarded-For` injection, and distributed tracing with `X-Request-ID`.
* **Transport Layer (TCP)**: TCP connection handshakes, connection pooling (`httpx`), active connection density tracking, and raw Layer-4 stream proxying (`loadbalancer/tcp_proxy.py`).
* **Traffic Scheduling Strategies**:
  1. **Round Robin**: Equal circular allocation.
  2. **Smooth Weighted Round Robin**: Nginx-style interleaved proportional distribution (e.g. 5:3:1) avoiding burst clusters.
  3. **Least Connections**: Dynamic dispatch to the backend with minimum active connection density.
  4. **IP Hash**: Deterministic SHA-256 client IP hashing for session stickiness.
* **User-Facing Application (NetPulse Demo Store)**: Enterprise networking equipment e-commerce web application running at `:8080/app`, allowing users to generate real load balanced traffic with live network telemetry.
* **Fault Tolerance & Health State Machine**: Active polling of backend `/health` endpoints and passive failure signaling (`HEALTHY` $\leftrightarrow$ `SUSPECT` $\leftrightarrow$ `UNHEALTHY` $\leftrightarrow$ `RECOVERING` $\leftrightarrow$ `DRAINING`).
* **Observability & Benchmarking**: Real-time Glassmorphism console, bounded circular memory buffers, live CSV streaming to `results/load_test.csv`, and P50/P95/P99 latency percentile analytics.

---

## 2. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Core** | Python 3.10+, FastAPI (ASGI), Uvicorn, Asyncio, HTTPX, PyYAML |
| **Demo Store & UI** | HTML5, Modern Vanilla CSS (Glassmorphic Dark Theme), JavaScript (ES6+), Chart.js |
| **Testing & Evaluation** | Pytest (44 tests), Pytest-Asyncio, HTTPX Load Engine, Matplotlib |
| **Network Packet Inspection** | Wireshark, Npcap Loopback Adapter, tshark, optional Mininet |

---

## 3. Project Structure

```
CN PROJECT/
├── config.yaml                    # Declarative system configuration
├── requirements.txt               # Project dependencies
├── README.md                      # System documentation & runbook
├── loadbalancer/                  # Core Reverse Proxy & Monitoring Package
│   ├── __init__.py
│   ├── main.py                    # Dual ASGI server startup (Proxy :8080 & Admin :9090)
│   ├── proxy.py                   # L7 Asynchronous Reverse Proxy Engine (with real-time CSV logging)
│   ├── pool.py                    # Backend registry & connection locks
│   ├── health.py                  # Active & passive health monitoring service
│   ├── metrics.py                 # Bounded performance metrics collector (P50/P95/P99)
│   ├── admin.py                   # REST Admin API router (with CSV download endpoint)
│   ├── config.py                  # PyYAML configuration schema validator
│   ├── tcp_proxy.py               # L4 TCP stream proxy extension (Port 8081)
│   └── algorithms/                # Scheduling algorithm strategies
│       ├── __init__.py
│       ├── base.py                # Abstract SelectionStrategy interface
│       ├── round_robin.py         # Standard Round Robin
│       ├── weighted_rr.py         # Smooth Weighted Round Robin
│       ├── least_conn.py          # Weighted Least Connections
│       └── ip_hash.py             # SHA-256 IP Hash strategy
├── backend/
│   ├── __init__.py
│   ├── server.py                  # Upstream demo server with configurable delay & fail rate
│   ├── products.py                # Shared immutable networking product catalogue
│   └── orders.py                  # Thread-safe persistent order processing engine
├── app/                           # NetPulse Demo Store (User-Facing Web Application)
│   ├── index.html                 # E-commerce store layout with live network telemetry drawer
│   └── assets/
│       ├── styles.css             # Glassmorphic dark navy/slate theme
│       └── app.js                 # Cart state, simulated checkout & response header interceptor
├── dashboard/
│   └── index.html                 # Real-time Web Monitoring Console & algorithm controls
├── tools/
│   ├── compare_algorithms.py      # Automated benchmark & 4-panel comparison plot generator
│   ├── failure_sim.py             # Backend fleet manager (start, stop, demo)
│   ├── failure_test.py            # End-to-end failure detection & failover verification test
│   ├── load_gen.py                # Concurrent async HTTP load generator
│   ├── analyze_results.py         # Statistical CSV result parser
│   ├── runtime_demo.py            # CLI runtime algorithm switcher & requester
│   └── mininet_topo.py            # Optional Linux Mininet topology with delay/loss
├── tests/
│   ├── test_algorithms.py         # Unit tests for all 4 scheduling algorithms
│   ├── test_demo_store.py         # Unit & integration tests for Demo Store & proxy routing
│   ├── test_health.py             # Active probe & recovery tests
│   ├── test_failover.py           # Backend exclusion and draining tests
│   ├── test_integration.py        # Admin REST API integration tests
│   └── test_proxy_errors.py       # 502/503/504 errors, bounded memory & passive failures
├── results/                       # Benchmarks, load_test.csv, orders.json, and plots
└── docs/
    ├── TEAM_VIVA_GUIDE.md         # Team ownership breakdown, 30 viva Q&As, demo script
    └── wireshark_guide.md         # Step-by-step packet capture and filter guide
```

---

## 4. Quick Start & Execution Guide (Windows PowerShell)

### Step 1: Environment Setup
Ensure Python 3.10+ is installed:
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### Step 2: Launch Demo Backend Fleet (Terminal 1)
Starts 3 independent backend servers:
* `b1` on port `5001` (Weight: 5, Delay: 50ms)
* `b2` on port `5002` (Weight: 3, Delay: 100ms)
* `b3` on port `5003` (Weight: 1, Delay: 200ms)
```powershell
python tools/failure_sim.py demo
```

### Step 3: Launch NetPulse Load Balancer & Admin API (Terminal 2)
```powershell
python -m loadbalancer.main
```
* **NetPulse Demo Store**: `http://127.0.0.1:8080/app`
* **Web Monitoring Dashboard**: `http://127.0.0.1:8080/dashboard`
* **Admin REST API**: `http://127.0.0.1:9090`
* **Live CSV Log**: `results/load_test.csv` (updated live on every request)

---

## 5. Live Demonstration & Verification Workflows

### A. Open the NetPulse Demo Store
Navigate to **`http://127.0.0.1:8080/app`** in your browser:
* Browse enterprise networking hardware (10G Routers, L3 Switches, Wi-Fi 7 APs, SFP+ Optics).
* Filter by category or search in real time.
* Add items to the cart and click **"Proceed to Simulated Checkout"**.
* Transmit order: fires a real `POST /api/orders` through the reverse proxy to a backend node.
* Open the **"Live Network Activity"** drawer: observe actual response headers (`X-Served-By`, `X-LB-Latency-Ms`, `X-Request-ID`) proving live load balanced distribution.

### B. Open the Web Observatory Dashboard
Navigate to **`http://127.0.0.1:8080/dashboard`** in your browser:
* View live overview cards: Total Requests, RPS Throughput, Error Rate, Avg/P95/P99 latency, Healthy Node count.
* Inspect the 4 real-time Chart.js graphs (Request Distribution, Latency Trend, Throughput, HTTP Status Codes).
* Switch algorithms on the fly using the quick pills (`Round Robin`, `Weighted RR`, `Least Conn`, `IP Hash`).
* Click **"Send 20 Requests"** or generate traffic from the Demo Store to watch charts and backend counters update in real time.
* Click **"📥 Download load_test.csv"** to inspect the live streamed request records.

### C. Automated Scheduling Algorithm Comparison
Execute an automated, identical concurrent load test across Round Robin, Smooth Weighted Round Robin, and Least Connections:
```powershell
python tools/compare_algorithms.py --requests 90 --concurrency 9
```
* Results exported to: `results/algorithm_comparison.csv`
* Publication-quality 4-panel graph saved to: `results/algorithm_comparison.png`

### D. Automated Failure Detection & Failover Test
Run the end-to-end fault tolerance lifecycle verification:
```powershell
python tools/failure_test.py --backend b1 --port 5001 --auto
```
This automated test:
1. Validates initial healthy state.
2. Sends baseline traffic.
3. Injects failure on `b1`.
4. Polls until Health Monitor confirms `HEALTHY` $\to$ `SUSPECT` $\to$ `UNHEALTHY`.
5. Sends 20 failover requests, verifying 100% success and 0 dropped requests.
6. Restores `b1` and verifies recovery back into service.

### E. Layer-4 TCP Proxy Extension (Optional Terminal)
Demonstrates raw Transport Layer stream forwarding:
```powershell
python -m loadbalancer.tcp_proxy --port 8081
# Send raw request:
curl.exe http://127.0.0.1:8081/test
```

---

## 6. Running Automated Tests

Run the complete test suite (**44 comprehensive unit and integration tests**):
```powershell
pytest -v
```

All 44 tests pass with 0 failures:
* `tests/test_algorithms.py` (5 tests): Round Robin, Smooth WRR, Least Connections, IP Hash, Unhealthy node exclusion.
* `tests/test_demo_store.py` (16 tests): Product catalogue schema, search filtering, category filtering, ID lookup, live count metadata, cart/order validation, unique order ID generation, persistent logging, backend API endpoints, and proxy `/app` route.
* `tests/test_failover.py` (5 tests): Dynamic failover, draining state, weighted failover, all-backends-down.
* `tests/test_health.py` (3 tests): Health check probe detection, consecutive thresholds, recovery detection.
* `tests/test_integration.py` (10 tests): Admin REST API endpoints, CORS origin compliance, runtime weight changes, node addition/removal.
* `tests/test_proxy_errors.py` (5 tests): 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout, bounded memory buffers, passive failure detection.

---

## 7. Computer Networks Wireshark Packet Analysis

To analyze packets during your viva:
1. Open Wireshark and select **Adapter for loopback traffic capture**.
2. Apply display filter:
   ```wireshark
   tcp.port == 8080 || tcp.port in {5001..5003}
   ```
3. Read the complete step-by-step guide in **[`docs/wireshark_guide.md`](file:///c:/Users/naiti/OneDrive/Desktop/CN%20PROJECT/docs/wireshark_guide.md)**.

---

## 8. Team of Four: Technical Ownership & Viva Guide

For complete module ownership, architecture sequence diagrams, 5-minute demonstration script, and **30 viva questions with detailed technical answers**, read **[`docs/TEAM_VIVA_GUIDE.md`](file:///c:/Users/naiti/OneDrive/Desktop/CN%20PROJECT/docs/TEAM_VIVA_GUIDE.md)**:
* **Member 1**: Load Balancing Engine (Proxy, Routing, 4 Algorithms, Idempotent Retries, RFC Headers)
* **Member 2**: Health Monitoring & Fault Tolerance (Active/Passive Probes, FSM Transitions, Failover, Draining)
* **Member 3**: Demo Store & Observatory Dashboard (E-Commerce Web App, Real-Time Network Activity, Chart.js, Admin Endpoints, CORS Security)
* **Member 4**: Metrics, Performance & Network Analysis (Bounded Metrics Engine, Real-Time CSV Streaming, Comparative Benchmarks, Wireshark, L4 TCP Proxy)
