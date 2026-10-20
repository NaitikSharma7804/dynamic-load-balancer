# Dynamic Load Balancer & Health Monitoring System
## Computer Networks (CN) Project - Technical Documentation

---

## 1. Executive Summary

This project is a high-performance **Layer 7 HTTP Reverse Proxy and Dynamic Load Balancer** designed and implemented in Python. It distributes incoming web traffic across multiple backend servers using configurable scheduling algorithms, continuously monitors server availability via an active health check mechanism, provides zero-downtime failover, and includes a real-time web monitoring dashboard and benchmarking tools.

### Key Highlights
* **Zero Downtime / Dynamic Reconfiguration**: Change scheduling algorithms (e.g., Round Robin to Least Connections) and add or drain backend servers at runtime via an Admin API without restarting the proxy.
* **4 Load Balancing Algorithms**: Round Robin, Nginx-style Smooth Weighted Round Robin, Least Connections, and IP Hash (session stickiness).
* **Active Health Checking & Failover**: Background polling of backend `/health` endpoints with consecutive failure thresholds, automatic traffic rerouting upon backend death, and gradual slow-start warmup upon recovery.
* **Real-time Glassmorphism Web Dashboard**: Live web UI (served directly by the proxy) displaying backend health states, active connections, request counts, and live metric feeds.
* **Benchmarking & Analysis Suite**: Asynchronous load testing engine (`httpx`), automated failover testing, and statistical performance reporting (P50, P95, P99 latency percentiles, throughput).

---

## 2. Technology Stack & Dependencies

| Category | Technology | Purpose in Project |
| :--- | :--- | :--- |
| **Language** | Python 3.13 | Core programming language |
| **Web Framework** | FastAPI (ASGI) | Powers both the High-Performance Reverse Proxy and the Admin API |
| **ASGI Web Server** | Uvicorn | High-throughput asynchronous HTTP server running both services |
| **Async HTTP Client** | HTTPX | Handles reverse proxy request forwarding, streaming, and background health probes |
| **Configuration** | PyYAML | Parsing and loading declarative settings from `config.yaml` |
| **Testing** | Pytest & pytest-asyncio | Unit testing, concurrency tests, failover tests, and integration tests |
| **Data Analytics** | Matplotlib / Standard CSV | Parsing benchmark metrics and computing statistical distributions |
| **Frontend UI** | HTML5, Modern CSS, Vanilla JS | Lightweight, real-time monitoring dashboard with zero external build step |

---

## 3. System Architecture & How It Works

The system follows a decoupled, non-blocking asynchronous architecture running two coordinated web applications concurrently on Python's event loop (`asyncio.gather`):

```
                        +---------------------------------------------+
                        |                 Client Traffic              |
                        +---------------------------------------------+
                                       |
                                       v
         +-------------------------------------------------------------------+
         |             PORT 8080: Dynamic Load Balancer (Proxy)             |
         |-------------------------------------------------------------------|
         |  1. Intercepts incoming HTTP requests (GET, POST, PUT, DELETE...) |
         |  2. Queries active Selection Strategy for the best healthy server |
         |  3. Tracks active connections & request counters                  |
         |  4. Forwards request via Async HTTPX Client                       |
         |  5. Injects tracking header: X-Served-By: <backend_name>          |
         |  6. Serves Web Monitoring Dashboard at /dashboard                 |
         +-------------------------------------------------------------------+
                                       |
                   +-------------------+-------------------+
                   |                   |                   |
                   v                   v                   v
            +--------------+    +--------------+    +--------------+
            |  Backend b1  |    |  Backend b2  |    |  Backend b3  |
            |  Port: 5001  |    |  Port: 5002  |    |  Port: 5003  |
            |  Delay: 50ms |    |  Delay: 100ms|    |  Delay: 200ms|
            |  Weight: 5   |    |  Weight: 3   |    |  Weight: 1   |
            +--------------+    +--------------+    +--------------+
                   ^                   ^                   ^
                   |                   |                   |
         +-------------------------------------------------------------------+
         |             PORT 9090: Health Monitor & Admin API                 |
         |-------------------------------------------------------------------|
         |  * Health Monitor: Background loop probes /health every 2s        |
         |  * State Machine: Transitions servers HEALTHY <-> UNHEALTHY      |
         |  * Admin Endpoints: /admin/backends, /admin/metrics, etc.         |
         |  * Live Algorithm Switching: Changes routing policy instantly     |
         +-------------------------------------------------------------------+
```

---

## 4. Deep Dive into Core Modules

### 4.1. Reverse Proxy Engine (`loadbalancer/proxy.py`)
* Intercepts wildcard HTTP traffic (`/{path:path}`).
* Calls the configured load balancing algorithm to select a candidate backend.
* If a backend connection fails or times out, the engine automatically tries an alternate healthy backend (up to `retry_count`), preventing request drops.
* Acquires and releases backend connection counters to enable real-time **Least Connections** tracking.
* Appends diagnostic metadata headers: `X-Served-By: b1`.

### 4.2. Scheduling Algorithms (`loadbalancer/algorithms/`)
1. **Round Robin (`round_robin.py`)**:
   Distributes traffic cyclically across healthy backends in circular order: $b_1 \to b_2 \to b_3 \to b_1$.
2. **Smooth Weighted Round Robin (`weighted_rr.py`)**:
   Nginx-inspired smooth weighting algorithm. Unlike simple weighted round robin that sends bursts to the highest-weight server, smooth weighting interleaves servers evenly according to configured weights ($5 : 3 : 1$).
3. **Least Connections (`least_conn.py`)**:
   Dynamically inspects the active connection count of each healthy server and routes the request to the server currently under the least load. Ideal when backends have varying response times.
4. **IP Hash (`ip_hash.py`)**:
   Hashes the client's IP address (`hash(client_ip) % len(backends)`). Ensures requests from the same client consistently reach the same backend (useful for session stickiness).

### 4.3. Backend Pool & State Management (`loadbalancer/pool.py`)
Each backend maintains:
* `state`: `HEALTHY`, `UNHEALTHY`, `SUSPECT`, or `DRAINING`.
* `active_connections`: Managed via `asyncio.Lock` for race-free concurrency.
* `effective_weight`: Scaled automatically during server warmup / draining.
* `consecutive_failures` & `consecutive_successes`: Counters used by the health monitor state machine.

### 4.4. Active Health Monitor (`loadbalancer/health.py`)
* Runs as a background `asyncio` task on a configurable interval (default: 2.0s).
* Probes each backend's `GET /health` endpoint with a 1.0s timeout.
* **Unhealthy Detection**: If a backend fails 3 consecutive health checks (`unhealthy_threshold = 3`), its state changes to `UNHEALTHY`, and the proxy immediately ceases routing traffic to it.
* **Automatic Recovery**: When a failed server comes back online, it must pass 2 consecutive health checks (`healthy_threshold = 2`) before rejoining the healthy pool.
* **Slow Start**: Prevents a newly recovered server from being overwhelmed by giving it a ramp-up period (`slow_start_s = 10`).

### 4.5. Admin API (`loadbalancer/admin.py`)
Provides REST endpoints on port 9090 for live operations:
* `GET /admin/backends`: List all registered backends, states, and active connections.
* `POST /admin/backends`: Add a new backend server at runtime.
* `DELETE /admin/backends/{name}`: Deregister or drain a backend gracefully.
* `PUT /admin/algorithm`: Change algorithm instantly (`round_robin`, `weighted_rr`, `least_conn`, `ip_hash`).
* `GET /admin/metrics`: Fetch real-time aggregate performance metrics.
* `GET /admin/health`: Fetch health probe logs and transition history.

### 4.6. Web Dashboard (`dashboard/index.html`)
* Served at `http://127.0.0.1:8080/dashboard`.
* Automatically queries the Admin API on port 9090 every 1.5 seconds via CORS-enabled asynchronous `fetch()`.
* Visualizes:
  * Backend cluster health indicators (green = healthy, red = down).
  * Real-time request and error distribution.
  * Active connections per node.
  * Dropdown selector to change load balancing algorithm with 1 click.

---

## 5. How to Run the Project (Step-by-Step)

### Terminal 1: Start the Backend Servers
Activate the virtual environment and start all 3 demo servers at once:

```powershell
.\.venv\Scripts\Activate.ps1
python tools/failure_sim.py demo
```
*This starts `b1` on port 5001 (50ms delay), `b2` on port 5002 (100ms delay), and `b3` on port 5003 (200ms delay).*

---

### Terminal 2: Start the Load Balancer & Admin Server
In a new terminal window:

```powershell
.\.venv\Scripts\Activate.ps1
python -m loadbalancer.main
```
*Output confirms:*
* **Proxy Server**: `http://127.0.0.1:8080`
* **Admin API**: `http://127.0.0.1:9090`
* **Web Dashboard**: `http://127.0.0.1:8080/dashboard`

---

### Terminal 3: Test Requests, Benchmark & Demo

#### 1. Send Single Requests
In Windows PowerShell, use `curl.exe` or `irm` (Invoke-RestMethod):
```powershell
curl.exe http://127.0.0.1:8080/some/path
```
*Response shows JSON payload with `backend` name, and HTTP response headers include `X-Served-By`.*

#### 2. Open the Live Web Dashboard
Open your web browser and go to:
👉 **`http://127.0.0.1:8080/dashboard`**

#### 3. Run Load Generator (Stress Test)
Generate 100 concurrent requests across the backends:
```powershell
python tools/load_gen.py --requests 100 --concurrency 10
```
*Output displays real-time throughput, success rate, and P95 latency, and exports detailed logs to `results/load_test.csv`.*

#### 4. Run Automated Algorithm Comparison
Execute an automated benchmark across Round Robin, Smooth Weighted Round Robin, and Least Connections:
```powershell
python tools/compare_algorithms.py --requests 90 --concurrency 9
```
*Exports `results/algorithm_comparison.csv` and generates publication-grade 4-panel comparison plots at `results/algorithm_comparison.png`.*

#### 5. Demonstrate Automated Failure Detection & Failover
Execute an end-to-end fault tolerance lifecycle demonstration:
```powershell
python tools/failure_test.py --backend b1 --port 5001 --auto
```
*Proves state transition `HEALTHY` -> `SUSPECT` -> `UNHEALTHY`, zero dropped requests to client, and verified recovery.*

#### 6. Run Layer-4 TCP Proxy Extension
Test raw Transport Layer stream forwarding:
```powershell
python -m loadbalancer.tcp_proxy --port 8081
curl.exe http://127.0.0.1:8081/test
```

#### 7. Run the Automated Test Suite
Run all 28 unit, failover, and integration tests:
```powershell
pytest -v
```

---

## 6. How to Present This in Your Viva & Demo

### 5-Minute Live Demonstration Script:
1. **Introduction & Architecture (1 min)**:
   * Explain what a Layer 7 Reverse Proxy is: unlike simple Layer 4 TCP routers, Layer 7 inspects HTTP paths, headers, and client IPs to make content-aware routing decisions. Show the L4 TCP proxy (`loadbalancer/tcp_proxy.py`) to demonstrate the difference.
2. **Normal Load Balancing & Dynamic Switching (1 min)**:
   * Open the real-time observatory dashboard at `http://127.0.0.1:8080/dashboard`.
   * Click "🚀 Send 20 Test Requests" under Round Robin.
   * Switch algorithm to Smooth Weighted Round Robin (`weighted_rr`) and show the proportional 5:3:1 allocation live on the bar chart without server restart.
3. **Fault Tolerance & Zero-Downtime Failover (1.5 min)**:
   * Click "Fail" on backend `b2` (or stop port 5002 in terminal).
   * Watch the dashboard health card transition from `HEALTHY` to `SUSPECT` then `UNHEALTHY`.
   * Send 20 requests: observe that 100% of traffic is served by `b1` and `b3` with zero dropped requests.
   * Click "Restore": observe verified recovery and the server returning smoothly to service.
4. **Performance Benchmarking & Network Analysis (1.5 min)**:
   * Run `python tools/compare_algorithms.py` to show comparative throughput and P95 latency percentiles.
   * Open Wireshark on the loopback adapter using the display filters from `docs/wireshark_guide.md` to demonstrate the dual TCP handshakes and `X-Forwarded-For` injection.
   * For the complete 30 viva questions and team ownership division, see `docs/TEAM_VIVA_GUIDE.md`.

