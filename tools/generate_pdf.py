import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Dynamic Load Balancer & Health Monitor - CN Project Documentation")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 40, 8.5 * inch - 54, 11 * inch - 40)
        
        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 32, footer_text)
        self.drawString(54, 32, "Confidential - Academic Project Report")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 44, 8.5 * inch - 54, 44)
        
        self.restoreState()


def build_pdf(filename="PROJECT_DOCUMENTATION.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0F172A")
    accent_color = colors.HexColor("#0284C7")
    muted_color = colors.HexColor("#475569")
    code_bg = colors.HexColor("#F1F5F9")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=accent_color,
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=accent_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=primary_color,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "BulletDark",
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.8,
        leading=10.5,
        textColor=colors.HexColor("#0369A1"),
        backColor=code_bg,
        spaceBefore=4,
        spaceAfter=6,
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("Dynamic Load Balancer & Health Monitor", title_style))
    story.append(Paragraph("Computer Networks (CN) Project - Technical System Documentation", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=10))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(
        Paragraph(
            "This project is a high-performance <b>Layer 7 HTTP Reverse Proxy and Dynamic Load Balancer</b> implemented "
            "in Python using FastAPI and Uvicorn. It acts as an intelligent traffic gateway that receives incoming client "
            "requests and distributes them evenly across a pool of backend servers, preventing server overload, eliminating "
            "single points of failure through active health checks, and supporting dynamic runtime reconfiguration without proxy restarts.",
            body_style,
        )
    )

    story.append(Paragraph("&bull; <b>Dual-Server Architecture:</b> Concurrently runs the high-throughput Reverse Proxy on port 8080 and the administrative control plane on port 9090.", bullet_style))
    story.append(Paragraph("&bull; <b>Zero-Downtime Operations:</b> Algorithms and backend node pools can be dynamically altered at runtime via REST Admin endpoints.", bullet_style))
    story.append(Paragraph("&bull; <b>Active Fault Tolerance:</b> Background heartbeat prober identifies dead servers, isolations them within 3 strikes, and restores recovered nodes with a 10s slow-start ramp-up.", bullet_style))
    story.append(Paragraph("&bull; <b>Built-in Monitoring & Benchmark Suite:</b> Real-time browser dashboard, asynchronous load generator, and statistical percentile analysis (P50, P95, P99).", bullet_style))

    # 2. Tech Stack Table
    story.append(Spacer(1, 4))
    story.append(Paragraph("2. Technology Stack", h1_style))

    tech_data = [
        [Paragraph("<b>Component</b>", body_style), Paragraph("<b>Technology</b>", body_style), Paragraph("<b>Purpose</b>", body_style)],
        [Paragraph("Language", body_style), Paragraph("Python 3.13", body_style), Paragraph("Asynchronous coroutines (async/await) and event loop.", body_style)],
        [Paragraph("Web Framework", body_style), Paragraph("FastAPI / Starlette", body_style), Paragraph("High-speed ASGI proxy routing and Admin API.", body_style)],
        [Paragraph("ASGI Server", body_style), Paragraph("Uvicorn", body_style), Paragraph("Runs proxy (8080) and admin (9090) concurrently.", body_style)],
        [Paragraph("HTTP Client", body_style), Paragraph("HTTPX", body_style), Paragraph("Non-blocking proxying, streaming, and health checks.", body_style)],
        [Paragraph("Configuration", body_style), Paragraph("PyYAML", body_style), Paragraph("Parses declarative backend parameters (config.yaml).", body_style)],
        [Paragraph("Test Suite", body_style), Paragraph("Pytest + pytest-asyncio", body_style), Paragraph("23 automated unit, failover, and integration tests.", body_style)],
        [Paragraph("Frontend UI", body_style), Paragraph("HTML5 + CSS3 + JS", body_style), Paragraph("Real-time glassmorphism dashboard polling Admin API.", body_style)],
    ]

    tech_table = Table(tech_data, colWidths=[1.3 * inch, 1.8 * inch, 3.9 * inch])
    tech_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(tech_table)

    # 3. Architecture & How it Works
    story.append(Spacer(1, 4))
    story.append(Paragraph("3. System Architecture & Request Lifecycle", h1_style))

    arch_diagram = """   +-------------------------------------------------------------+
   |                  Incoming Client HTTP Traffic               |
   +-------------------------------------------------------------+
                                  |
                                  v
   +-------------------------------------------------------------+
   |          PORT 8080: Dynamic Load Balancer (Proxy)           |
   |  * Intercepts HTTP request (GET, POST, PUT, DELETE...)      |
   |  * Queries active algorithm for best healthy backend        |
   |  * Acquires connection counter; proxies via Async HTTPX     |
   |  * Injects X-Served-By: <backend>; serves /dashboard UI     |
   +-------------------------------------------------------------+
               |                  |                  |
               v                  v                  v
        +--------------+   +--------------+   +--------------+
        |  Backend b1  |   |  Backend b2  |   |  Backend b3  |
        |  Port: 5001  |   |  Port: 5002  |   |  Port: 5003  |
        |  Delay: 50ms |   |  Delay: 100ms|   |  Delay: 200ms|
        |  Weight: 5   |   |  Weight: 3   |   |  Weight: 1   |
        +--------------+   +--------------+   +--------------+
               ^                  ^                  ^
               +------------------+------------------+
                                  | Active Health Probes (/health every 2s)
   +-------------------------------------------------------------+
   |           PORT 9090: Health Monitor & Admin API             |
   |  * Detects failures (3 strikes) -> marks UNHEALTHY          |
   |  * Detects recovery (2 passes)  -> marks HEALTHY            |
   |  * Admin endpoints for live algorithm switching & metrics   |
   +-------------------------------------------------------------+"""
    story.append(Preformatted(arch_diagram, code_style))

    # 4. Algorithms
    story.append(Spacer(1, 4))
    story.append(Paragraph("4. Implemented Load Balancing Algorithms", h1_style))
    story.append(Paragraph("<b>1. Round Robin:</b> Distributes requests in a strict circular rotation across all healthy backends (b1 -> b2 -> b3 -> b1). Simple and deterministic.", bullet_style))
    story.append(Paragraph("<b>2. Smooth Weighted Round Robin (Nginx-style):</b> Distributes requests based on server weights (5:3:1) while smoothly interleaving selections to avoid bursting the heaviest server.", bullet_style))
    story.append(Paragraph("<b>3. Least Connections:</b> Dynamically tracks concurrent active requests per server and routes incoming traffic to the server with the lowest live load.", bullet_style))
    story.append(Paragraph("<b>4. IP Hash:</b> Hashes client IP addresses modulo the healthy backend count to provide session affinity (sticky sessions).", bullet_style))

    # 5. Health Monitoring & Failover
    story.append(Spacer(1, 4))
    story.append(Paragraph("5. Active Health Monitoring & Failover", h1_style))
    story.append(Paragraph("The health monitor runs as a background task concurrently with the proxy:", body_style))
    story.append(Paragraph("&bull; <b>Heartbeat Interval:</b> Pings <code>GET /health</code> on all servers every 2.0s with a 1.0s timeout.", bullet_style))
    story.append(Paragraph("&bull; <b>Fault Isolation:</b> After 3 consecutive failed health probes, the backend is transitioned to <code>UNHEALTHY</code> and excluded from traffic routing immediately.", bullet_style))
    story.append(Paragraph("&bull; <b>Safe Recovery & Slow Start:</b> A recovering backend must pass 2 consecutive checks before rejoining, followed by a 10-second weight ramp-up to prevent thundering herds.", bullet_style))

    # 6. How to Run
    story.append(Spacer(1, 4))
    story.append(Paragraph("6. Step-by-Step Running Instructions", h1_style))

    run_instructions = """# 1. Start all 3 demo backends (Terminal 1):
.\\.venv\\Scripts\\Activate.ps1
python tools/failure_sim.py demo

# 2. Start the Load Balancer & Admin Plane (Terminal 2):
.\\.venv\\Scripts\\Activate.ps1
python -m loadbalancer.main

# 3. Test & Benchmark (Terminal 3):
curl.exe http://127.0.0.1:8080/some/path
python tools/load_gen.py --requests 100 --concurrency 10
python tools/analyze_results.py results/load_test.csv

# 4. Access Live Web Dashboard:
http://127.0.0.1:8080/dashboard

# 5. Run automated test suite:
pytest"""
    story.append(Preformatted(run_instructions, code_style))

    # 7. Presentation Walkthrough
    story.append(Spacer(1, 4))
    story.append(Paragraph("7. Presentation Walkthrough for Teammates & Faculty", h1_style))
    story.append(Paragraph("<b>1. Open Dashboard:</b> Navigate to <code>http://127.0.0.1:8080/dashboard</code> to showcase live node statuses and metrics.", bullet_style))
    story.append(Paragraph("<b>2. Send Load:</b> Run <code>python tools/load_gen.py --requests 100 --concurrency 10</code>. Point out equal request distribution under Round Robin.", bullet_style))
    story.append(Paragraph("<b>3. Switch Algorithm Live:</b> Use the Dashboard dropdown to switch to <code>weighted_rr</code>. Point out that no proxy restart was required.", bullet_style))
    story.append(Paragraph("<b>4. Demonstrate Auto-Failover:</b> Stop backend <code>b2</code>. The health monitor detects the failure, marks it red, and reroutes all traffic to <code>b1</code> and <code>b3</code> with 100% success rate.", bullet_style))
    story.append(Paragraph("<b>5. Prove Performance:</b> Show <code>python tools/analyze_results.py results/load_test.csv</code> displaying P50, P95, and P99 latency figures.", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built: {os.path.abspath(filename)}")


if __name__ == "__main__":
    build_pdf()
