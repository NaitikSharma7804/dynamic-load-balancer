"""
NetPulse - Optional Mininet Network Topology for Computer Networks Experiments.

Topology Architecture:
                 +--------------+
                 | Switch (s1)  |
                 +--------------+
                  /     |      \
                 /      |       \
               h1      h2        h3, h4, h5
           (Client)   (Proxy)    (Backends b1, b2, b3)

Demonstrates:
- Emulated network link delays (e.g. 10ms, 50ms)
- Emulated packet loss (e.g. 2% loss)
- Router/Switch packet forwarding with Mininet

Usage (Linux with Mininet installed):
    sudo python3 tools/mininet_topo.py
"""

import sys

try:
    from mininet.net import Mininet  # type: ignore
    from mininet.node import Controller, RemoteController, OVSKernelSwitch  # type: ignore
    from mininet.cli import CLI  # type: ignore
    from mininet.log import setLogLevel, info  # type: ignore
    from mininet.link import TCLink  # type: ignore
except ImportError:
    print("[!] Mininet is only supported on Linux environments with OpenFlow / Mininet installed.")
    print("    This script is provided as an optional lab extension for Linux networking labs.")
    sys.exit(0)


def run_netpulse_topology():
    net = Mininet(controller=Controller, switch=OVSKernelSwitch, link=TCLink)

    info("*** Adding Controller\n")
    net.addController("c0")

    info("*** Adding Switch\n")
    s1 = net.addSwitch("s1")

    info("*** Adding Hosts\n")
    client = net.addHost("h1", ip="10.0.0.1/24")
    proxy = net.addHost("h2", ip="10.0.0.2/24")
    b1 = net.addHost("h3", ip="10.0.0.3/24")
    b2 = net.addHost("h4", ip="10.0.0.4/24")
    b3 = net.addHost("h5", ip="10.0.0.5/24")

    info("*** Creating Links with Network Constraints (Delay & Loss)\n")
    # Client to switch: low latency
    net.addLink(client, s1, delay="2ms")
    # Proxy to switch: low latency
    net.addLink(proxy, s1, delay="2ms")

    # Backend links with custom delay characteristics
    net.addLink(b1, s1, delay="10ms", loss=0)    # Fast backend
    net.addLink(b2, s1, delay="50ms", loss=1)    # Medium backend with 1% packet loss
    net.addLink(b3, s1, delay="100ms", loss=2)   # High delay backend with 2% packet loss

    info("*** Starting Network\n")
    net.start()

    info("*** Testing Network Connectivity\n")
    net.pingAll()

    info("*** Network Ready!\n")
    info("To launch NetPulse in Mininet:\n")
    info("  1. In h3: python3 -m backend.server --port 5001 --name b1 &\n")
    info("  2. In h4: python3 -m backend.server --port 5002 --name b2 &\n")
    info("  3. In h5: python3 -m backend.server --port 5003 --name b3 &\n")
    info("  4. In h2: python3 -m loadbalancer.main &\n")
    info("  5. In h1: curl http://10.0.0.2:8080/test\n")

    CLI(net)

    info("*** Stopping Network\n")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run_netpulse_topology()
