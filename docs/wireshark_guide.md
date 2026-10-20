# NetPulse: Computer Networks Lab Packet Analysis & Wireshark Guide

## 1. Overview & Networking Objectives

In Computer Networks, a **Reverse Proxy and Layer-7 Load Balancer** operates at the Application Layer (HTTP) while orchestrating multiple underlying Transport Layer (TCP) connections.

This guide provides step-by-step instructions for inspecting, analyzing, and explaining packet flows using **Wireshark** or **tshark** during your lab evaluation and viva.

```
                    TCP Connection 1                    TCP Connection 2 (or Pool)
 [Client Browser] <=================> [NetPulse Proxy:8080] <=================> [Backend b1:5001]
                                                                        \======> [Backend b2:5002]
                                                                        \======> [Backend b3:5003]
```

---

## 2. Capture Interface Setup

### Windows Environments
1. Open Wireshark as Administrator.
2. Under **Capture**, select **Adapter for loopback traffic capture** (installed via Npcap).
   > *Note:* Do not select your physical Wi-Fi or Ethernet adapter, as local test traffic (`127.0.0.1`) does not traverse physical network hardware.

### Linux / Mininet Environments
```bash
sudo wireshark -i lo -k
# Or via CLI with tshark:
sudo tshark -i lo -f "tcp port 8080 or tcp port 5001 or tcp port 5002 or tcp port 5003"
```

---

## 3. Essential Display Filters

Copy and paste these exact filters into Wireshark's filter bar:

| Goal / Observation | Wireshark Display Filter |
| :--- | :--- |
| **All NetPulse Traffic** | `tcp.port == 8080 || tcp.port in {5001..5003} \|\| tcp.port == 9090` |
| **Client-to-Proxy Only** | `tcp.port == 8080 && http` |
| **Proxy-to-Backend Only** | `tcp.port in {5001..5003} && http` |
| **Periodic Health Checks** | `http.request.uri contains "/health"` |
| **Server Failures & 5xx Errors** | `http.response.code >= 500` |
| **TCP Connection Resets (RST)** | `tcp.flags.reset == 1` |
| **TCP 3-Way Handshakes (SYN)** | `tcp.flags.syn == 1 && tcp.flags.ack == 0` |
| **End-to-End Tracing by Request ID** | `http contains "X-Request-ID"` |

---

## 4. Experiment 1: Normal Traffic Routing (Round Robin)

### Objective
Observe how a single client request triggers two distinct TCP conversations and demonstrates sequential load balancing.

### Steps
1. Start Wireshark on the loopback adapter. Apply filter:
   ```wireshark
   http && (tcp.port == 8080 || tcp.port in {5001..5003})
   ```
2. Start the demo backends and load balancer:
   ```powershell
   python tools/failure_sim.py demo
   python -m loadbalancer.main
   ```
3. Send 3 sequential requests from PowerShell:
   ```powershell
   curl.exe http://127.0.0.1:8080/test
   curl.exe http://127.0.0.1:8080/test
   curl.exe http://127.0.0.1:8080/test
   ```

### What You Will See in Wireshark
1. **Packet 1 & 2 (Client -> Proxy)**:
   - Client initiates connection to port `8080`.
   - Client sends `GET /test HTTP/1.1`.
2. **Packet 3 & 4 (Proxy -> Backend b1:5001)**:
   - Proxy establishes connection to upstream port `5001`.
   - Proxy forwards `GET /test HTTP/1.1` and appends headers:
     - `X-Forwarded-For: 127.0.0.1`
     - `X-Request-ID: <uuid>`
     - `X-LB-Algorithm: round_robin`
3. **Packet 5 & 6 (Backend b1 -> Proxy -> Client)**:
   - Backend `5001` responds with HTTP `200 OK`.
   - Proxy relays response to Client with header:
     - `X-Served-By: b1`
     - `X-LB-Latency-Ms: 51.42`
4. **Subsequent Requests**:
   - Request 2 will be forwarded to port `5002` (`b2`).
   - Request 3 will be forwarded to port `5003` (`b3`).

---

## 5. Experiment 2: Active Health Monitoring Probes

### Objective
Inspect how background health checks operate autonomously from user traffic.

### Steps
1. Apply filter:
   ```wireshark
   http.request.uri == "/health"
   ```
2. Observe periodic packet bursts:
   - Every `2.0` seconds (configured `interval_s` in `config.yaml`), the Load Balancer issues three concurrent HTTP `GET /health` requests to ports `5001`, `5002`, and `5003`.
   - Each backend replies with `200 OK` and a JSON body containing `uptime_s` and server name.

---

## 6. Experiment 3: Backend Failure, TCP RST, and Automatic Failover

### Objective
Capture the exact moment a backend crashes, the TCP teardown, and how the reverse proxy protects the client.

### Steps
1. Apply filter:
   ```wireshark
   tcp.port == 5002 || (tcp.port == 8080 && http)
   ```
2. In Terminal 1, stop backend `b2` (port 5002) with `CTRL+C`.
3. Send a burst of requests to the load balancer:
   ```powershell
   python tools/load_gen.py --requests 20 --concurrency 5
   ```

### Packet Analysis Breakdown
1. **Health Check Probe Failure**:
   - The health monitor sends `GET /health` to port `5002`.
   - Since port 5002 is closed, the operating system kernel immediately replies with a **TCP RST (Reset)** flag or ICMP Port Unreachable.
   - After `unhealthy_threshold` consecutive failures, the health monitor transitions `b2` from `HEALTHY` to `SUSPECT` then `UNHEALTHY`.
2. **Failover Execution**:
   - All 20 client requests to port `8080` receive HTTP `200 OK`.
   - Looking at `X-Served-By` headers in Wireshark, 100% of traffic is served by `b1:5001` and `b3:5003`.
   - Zero client connections are dropped.

---

## 7. Transport Layer (L4) vs Application Layer (L7) Comparison

To demonstrate the difference in your viva:
* **Layer 7 (HTTP Proxy on :8080)**:
  - Terminates the incoming client TCP connection.
  - Parses HTTP request line, headers, and payload.
  - Can make dynamic routing decisions based on URL path, cookies, or client IP (`ip_hash`).
  - Wireshark shows HTTP protocol dissector on both sides.
* **Layer 4 (TCP Proxy on :8081 - `loadbalancer/tcp_proxy.py`)**:
  - Operates purely on raw TCP packets and byte streams.
  - Cannot inspect or modify HTTP headers (`X-Served-By` cannot be added).
  - Much lower CPU overhead, but incapable of content-aware routing or URL rewriting.
