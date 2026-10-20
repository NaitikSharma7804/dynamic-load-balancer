"""
NetPulse Demo Store - Shared Product Catalogue.

Provides consistent, immutable product data across all backend servers.
Prevents state discrepancies across nodes in the backend pool.
"""

from typing import Dict, List, Optional


PRODUCTS: List[Dict] = [
    {
        "id": "prod-101",
        "name": "NetPulse PulseRoute Pro 10G",
        "category": "routers",
        "category_name": "Routers & Gateways",
        "price": 499.00,
        "stock": 18,
        "rating": 4.9,
        "badge": "Best Seller",
        "description": "Enterprise-grade multi-WAN edge router with dual 10Gbps SFP+ ports, hardware NAT acceleration, and integrated WireGuard VPN server.",
        "specs": {
            "Throughput": "10 Gbps Wire-Speed",
            "Interfaces": "2x 10G SFP+, 8x 1G RJ45",
            "CPU": "Quad-Core ARM Cortex-A72 @ 2.2 GHz",
            "RAM": "4 GB DDR4",
            "Power": "Dual Redundant 60W AC",
        },
        "icon": "router",
    },
    {
        "id": "prod-102",
        "name": "NetPulse Layer-3 CoreSwitch 24P",
        "category": "switches",
        "category_name": "Managed Switches",
        "price": 799.00,
        "stock": 12,
        "rating": 4.8,
        "badge": "Enterprise",
        "description": "High-density Layer-3 managed switch featuring 24 PoE+ Gigabit ports, 4 10G SFP+ uplinks, dynamic OSPF/BGP routing, and 370W PoE budget.",
        "specs": {
            "Switching Capacity": "128 Gbps",
            "PoE Budget": "370W PoE+ (802.3at)",
            "Interfaces": "24x 1G PoE+, 4x 10G SFP+",
            "Forwarding Rate": "95.2 Mpps",
            "Mounting": "1U 19-inch Rackmount",
        },
        "icon": "switch",
    },
    {
        "id": "prod-103",
        "name": "PulseWave Wi-Fi 7 Enterprise AP",
        "category": "wireless",
        "category_name": "Wireless Access",
        "price": 329.00,
        "stock": 25,
        "rating": 4.9,
        "badge": "Wi-Fi 7",
        "description": "Tri-band 802.11be ceiling-mount access point delivering up to 18.6 Gbps aggregate throughput, 320 MHz channels, and 4096-QAM.",
        "specs": {
            "Speed": "18.6 Gbps Tri-Band",
            "Bands": "2.4 GHz, 5 GHz, 6 GHz",
            "Uplink": "1x 10G PoE++ RJ45",
            "Coverage": "2,500 sq ft / 500+ Clients",
            "Antennas": "8x Internal Omnidirectional",
        },
        "icon": "wifi",
    },
    {
        "id": "prod-104",
        "name": "NetPulse SFP+ 10G-SR Optical Transceiver",
        "category": "optical",
        "category_name": "Optical & Cabling",
        "price": 45.00,
        "stock": 150,
        "rating": 4.7,
        "badge": "Pack of 2",
        "description": "10GBASE-SR 850nm multimode optical module with LC duplex connector, supporting up to 300m reach over OM3 fiber optic cable.",
        "specs": {
            "Data Rate": "10.3125 Gbps",
            "Wavelength": "850 nm",
            "Reach": "300m over OM3 MMF",
            "Connector": "LC Duplex",
            "DOM Support": "Digital Optical Monitoring",
        },
        "icon": "fiber",
    },
    {
        "id": "prod-105",
        "name": "NetPulse SecureEdge Next-Gen Firewall",
        "category": "security",
        "category_name": "Security & Firewalls",
        "price": 899.00,
        "stock": 8,
        "rating": 5.0,
        "badge": "High Security",
        "description": "Rackmount Unified Threat Management appliance with deep packet inspection (DPI), zero-trust network access, and 5 Gbps threat prevention throughput.",
        "specs": {
            "Threat Prevention": "5.0 Gbps",
            "Concurrent Sessions": "2,000,000",
            "VPN Throughput": "3.5 Gbps IPsec",
            "Interfaces": "4x 2.5G RJ45, 2x 10G SFP+",
            "Storage": "256 GB M.2 NVMe SSD",
        },
        "icon": "shield",
    },
    {
        "id": "prod-106",
        "name": "Cat6A Shielded 24-Port Patch Panel",
        "category": "accessories",
        "category_name": "Accessories & Racks",
        "price": 89.00,
        "stock": 40,
        "rating": 4.6,
        "badge": "Shielded",
        "description": "1U 19-inch 10Gbps shielded Cat6A keystone patch panel with integrated cable management bar and grounding wire.",
        "specs": {
            "Standard": "ANSI/TIA-568.2-D Cat6A",
            "Ports": "24 Keystone Ports",
            "Shielding": "STP / Fully Shielded",
            "Rack Unit": "1U Standard 19-inch",
            "Material": "Cold-Rolled SPCC Steel",
        },
        "icon": "server",
    },
    {
        "id": "prod-107",
        "name": "NetPulse EdgeMicro 5-Port Switch",
        "category": "switches",
        "category_name": "Managed Switches",
        "price": 69.00,
        "stock": 55,
        "rating": 4.7,
        "badge": "Compact",
        "description": "Fanless desktop 2.5G Multi-Gigabit unmanaged switch with 5x 2.5GBase-T ports for NAS and high-speed workstation clustering.",
        "specs": {
            "Interfaces": "5x 2.5G RJ45 Ports",
            "Switching Capacity": "25 Gbps",
            "Cooling": "Silent Fanless Metal Case",
            "Power": "12V 1.5A DC Adapter",
            "Dimensions": "160 x 110 x 26 mm",
        },
        "icon": "switch",
    },
    {
        "id": "prod-108",
        "name": "PulseMon Network TAP & Packet Sniffer",
        "category": "accessories",
        "category_name": "Accessories & Racks",
        "price": 249.00,
        "stock": 14,
        "rating": 4.8,
        "badge": "Lab Favorite",
        "description": "Passive Gigabit Network Test Access Point (TAP) for zero-latency in-line Wireshark packet capture, network auditing, and traffic analysis.",
        "specs": {
            "Speed": "10/100/1000 Mbps Full-Duplex",
            "Monitor Ports": "2x Dedicated Sniffer Ports",
            "Latency": "Zero Added Jitter (< 10 ns)",
            "Power": "USB-C 5V / Passive Fail-Open",
            "Compatibility": "Wireshark, tcpdump, Snort",
        },
        "icon": "activity",
    },
]


CATEGORIES: List[Dict] = [
    {"id": "all", "name": "All Products", "count": len(PRODUCTS)},
    {"id": "routers", "name": "Routers & Gateways", "count": 1},
    {"id": "switches", "name": "Managed Switches", "count": 2},
    {"id": "wireless", "name": "Wireless Access", "count": 1},
    {"id": "optical", "name": "Optical & Cabling", "count": 1},
    {"id": "security", "name": "Security & Firewalls", "count": 1},
    {"id": "accessories", "name": "Accessories & Lab", "count": 2},
]


def get_all_products(search: Optional[str] = None, category: Optional[str] = None) -> List[Dict]:
    """Retrieve products with optional case-insensitive search and category filtering."""
    results = PRODUCTS

    if category and category.lower() != "all":
        cat_lower = category.lower().strip()
        results = [p for p in results if p["category"].lower() == cat_lower]

    if search:
        s_lower = search.lower().strip()
        results = [
            p for p in results
            if s_lower in p["name"].lower()
            or s_lower in p["description"].lower()
            or s_lower in p["category_name"].lower()
        ]

    return results


def get_product_by_id(product_id: str) -> Optional[Dict]:
    """Retrieve single product by its unique product ID."""
    for p in PRODUCTS:
        if p["id"] == product_id:
            return p
    return None


def get_categories() -> List[Dict]:
    """Retrieve category list with accurate live item counts."""
    counts = {}
    for p in PRODUCTS:
        counts[p["category"]] = counts.get(p["category"], 0) + 1

    cats = [{"id": "all", "name": "All Products", "count": len(PRODUCTS)}]
    for c in CATEGORIES:
        if c["id"] != "all":
            cats.append({
                "id": c["id"],
                "name": c["name"],
                "count": counts.get(c["id"], 0)
            })
    return cats
