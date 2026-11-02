import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def create_report():
    doc = docx.Document()

    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Palette Constants
    COLOR_NAVY = RGBColor(15, 23, 42)       # #0F172A
    COLOR_SKY = RGBColor(2, 132, 199)       # #0284C7
    COLOR_SLATE = RGBColor(71, 85, 105)     # #475569
    COLOR_DARK = RGBColor(30, 41, 59)       # #1E293B
    HEX_HEADER_BG = "0F172A"
    HEX_ALT_ROW = "F8FAFC"
    HEX_BORDER = "CBD5E1"
    HEX_CALLOUT_BG = "F0F9FF"
    HEX_CALLOUT_BORDER = "0284C7"

    def set_cell_background(cell, hex_color):
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
        tcPr.append(tcMar)

    def add_callout(text, prefix="Aviation CAMO Compliance Note:"):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        set_cell_background(cell, HEX_CALLOUT_BG)
        set_cell_margins(cell, top=160, bottom=160, left=200, right=200)
        
        # Left border only
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:left w:val="single" w:sz="24" w:space="0" w:color="{HEX_CALLOUT_BORDER}"/><w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/></w:tcBorders>')
        tcPr.append(borders)

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        
        run_bold = p.add_run(prefix + " ")
        run_bold.bold = True
        run_bold.font.name = "Arial"
        run_bold.font.size = Pt(10.5)
        run_bold.font.color.rgb = COLOR_SKY

        run_text = p.add_run(text)
        run_text.font.name = "Arial"
        run_text.font.size = Pt(10)
        run_text.font.color.rgb = COLOR_DARK
        
        p_space = doc.add_paragraph()
        p_space.paragraph_format.space_before = Pt(0)
        p_space.paragraph_format.space_after = Pt(4)

    # -------------------------------------------------------------
    # COVER / HEADER TITLE
    # -------------------------------------------------------------
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(10)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run("Aircraft Maintenance Scanner – Digital Maintenance Record System")
    run_title.bold = True
    run_title.font.name = "Arial"
    run_title.font.size = Pt(24)
    run_title.font.color.rgb = COLOR_NAVY

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(16)
    run_sub = sub_p.add_run("Fleet Aircraft QR Identification and Digital Maintenance Tracking System\nAviation MRO Operations & Continuous Airworthiness Management (CAMO) Technical Report")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(12)
    run_sub.font.color.rgb = COLOR_SKY

    # Divider line
    div_p = doc.add_paragraph()
    div_p.paragraph_format.space_before = Pt(0)
    div_p.paragraph_format.space_after = Pt(18)
    run_div = div_p.add_run("_________________________________________________________________________________")
    run_div.font.color.rgb = COLOR_SLATE
    run_div.font.size = Pt(9)

    # Document Meta Table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_data = [
        ("Project Domain:", "Aviation MRO / Airline Operations & Maintenance Digitization"),
        ("Prepared For:", "Bachelor of Business Administration (BBA) in Aviation Management"),
        ("System Architecture:", "Full-Stack Web (Python Flask, SQLite3, HTML5 QR, Cloudflare Tunnel)"),
        ("Publication Date:", "Academic Term 2026 / Production-Ready Technical Specification")
    ]
    for i, (k, v) in enumerate(meta_data):
        row = meta_table.rows[i]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Inches(2.2)
        c1.width = Inches(4.3)
        set_cell_background(c0, "F1F5F9")
        set_cell_background(c1, "FFFFFF")
        set_cell_margins(c0, 60, 60, 100, 100)
        set_cell_margins(c1, 60, 60, 100, 100)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(k)
        r0.bold = True
        r0.font.name = "Arial"
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = COLOR_NAVY

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(v)
        r1.font.name = "Arial"
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = COLOR_DARK

    doc.add_paragraph()

    # Helper function for Section Headings
    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(20)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(16)
        run.font.color.rgb = COLOR_NAVY

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(12.5)
        run.font.color.rgb = COLOR_SKY

    def add_body(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.font.name = "Arial"
        run.font.size = Pt(10.5)
        run.font.color.rgb = COLOR_DARK
        return p

    def add_bullet(bold_prefix, text):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        rb = p.add_run(bold_prefix + " ")
        rb.bold = True
        rb.font.name = "Arial"
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = COLOR_NAVY
        rt = p.add_run(text)
        rt.font.name = "Arial"
        rt.font.size = Pt(10.5)
        rt.font.color.rgb = COLOR_DARK

    # -------------------------------------------------------------
    # 1. EXECUTIVE SUMMARY & PROJECT BACKGROUND
    # -------------------------------------------------------------
    add_h1("1. Executive Summary & Project Background")
    add_body("In modern commercial aviation management, operational efficiency, continuous airworthiness, and zero-compromise flight safety represent the foundation of sustainable airline profitability. Commercial aircraft are multi-million-dollar capital assets comprised of tens of thousands of Line Replaceable Units (LRUs) and life-limited rotable systems—including turbofan engines, multi-wheel landing gear bogies, carbon composite brake packs, and digital avionics transponders. Each component requires stringent inspection schedules, routine servicing, and regulatory audit compliance.")

    add_body("Historically, airline tarmac line-maintenance teams and maintenance, repair, and overhaul (MRO) facilities have relied heavily on physical paper technical logbooks (TechLogs) and decentralized manual document vaults. In contemporary flight operations, this legacy approach presents serious vulnerabilities:")
    
    add_bullet("Costly Ground Delays & AOG Penalties:", "An Aircraft On Ground (AOG) event costs airlines between $10,000 to over $150,000 per hour in lost passenger bookings, airport gate parking surcharges, flight cancellation compensations, and crew re-rostering.")
    add_bullet("Human Transcription Errors:", "Manual recording of part numbers, flight hours, serial numbers, and maintenance disposition codes frequently leads to transcription inconsistencies.")
    add_bullet("Regulatory Audit Non-Compliance:", "Civil aviation authorities (such as DGCA, FAA, EASA, and ICAO) mandate tamper-evident, complete maintenance histories under Continuing Airworthiness Management Organisation (CAMO) regulations.")

    add_body("The Aircraft Maintenance Scanner – Digital Maintenance Record System resolves these operational bottlenecks by establishing an optical, physical-to-digital link for commercial aircraft airframes. By generating unique 2D Quick Response (Master QR) codes exclusively for each aircraft, line technicians and CAMO auditors can scan an aircraft's tail tag using any camera-enabled smartphone or tablet to instantly retrieve complete chronological service logs, view current airworthiness status, and seamlessly record new maintenance activities.")

    add_callout("Under DGCA CAR M (Continuing Airworthiness Requirements) and EASA Part-M regulations, airlines must maintain verified records of all maintenance performed throughout an aircraft's operational lifecycle. This digital system provides immediate audit readiness with persistent relational logging and automated CSV compliance export.")

    # -------------------------------------------------------------
    # 2. KEY PROJECT OBJECTIVES & BUSINESS VALUE
    # -------------------------------------------------------------
    add_h1("2. Core Objectives & Aviation Business Impact")
    
    table_obj = doc.add_table(rows=6, cols=3)
    table_obj.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_obj = ["Strategic Objective", "Operational Implementation", "Aviation Business Metric"]
    
    for c_idx, h in enumerate(headers_obj):
        cell = table_obj.cell(0, c_idx)
        set_cell_background(cell, HEX_HEADER_BG)
        set_cell_margins(cell, 120, 120, 140, 140)
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(255, 255, 255)

    rows_obj_data = [
        ("Turnaround Time (TAT) Optimization", "Line technicians scan Master QR codes on tarmac turnarounds to inspect previous fault entries within seconds.", "Reduces transit line maintenance verification time by over 70%."),
        ("Airframe-Exclusive QR Tracking", "Dedicated QR codes generated exclusively for aircraft airframes, avoiding component-level visual clutter.", "Standardizes inspection workflow across airline fleet bases."),
        ("Persistent Historical Audit Logs", "All historical maintenance records are chronologically preserved in relational storage, ensuring future scans reflect updates.", "Eliminates missing log records; ensures 100% CAMO audit compliance."),
        ("Two-Step Maintenance Workflow", "Prompts 'Which Aircraft?' first before revealing technical maintenance data inputs.", "Eliminates misattribution of maintenance entries between fleet aircraft."),
        ("Global Network Accessibility", "Bound to universal sockets (0.0.0.0) with Cloudflare and localtunnel zero-trust reverse proxy support.", "Enables ground engineers to log maintenance directly from mobile phones on the tarmac.")
    ]

    for r_idx, row_data in enumerate(rows_obj_data, start=1):
        for c_idx, val in enumerate(row_data):
            cell = table_obj.cell(r_idx, c_idx)
            set_cell_background(cell, HEX_ALT_ROW if r_idx % 2 == 1 else "FFFFFF")
            set_cell_margins(cell, 100, 100, 120, 120)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(val)
            r.font.name = "Arial"
            r.font.size = Pt(9.5)
            r.font.color.rgb = COLOR_DARK
            if c_idx == 0:
                r.bold = True
                r.font.color.rgb = COLOR_NAVY

    doc.add_paragraph()

    # -------------------------------------------------------------
    # 3. COMPREHENSIVE TECHNOLOGY STACK BREAKDOWN
    # -------------------------------------------------------------
    add_h1("3. Comprehensive Technology Stack Breakdown")
    add_body("The system is engineered using a robust, modular, and lightweight technology stack designed for high reliability, minimal latency, and zero-configuration deployment across diverse operating environments.")

    add_h2("3.1 Backend Architecture & Server Technologies")
    add_bullet("Python 3.14 Runtime Environment:", "Serves as the high-performance programming runtime. Python provides native cross-platform compatibility across Windows, Linux, and macOS tarmac servers, offering robust string processing, date-time validation, and standard library stability.")
    add_bullet("Flask (WSGI Web Framework):", "Implements an agile Model-View-Controller (MVC) architectural pattern. Flask handles HTTP request dispatching, URL parameter routing (/aircraft/<registration>), session management, flash messaging, and custom error handlers (404/500).")
    add_bullet("SQLite 3 Relational Database Engine:", "Serves as the zero-configuration, ACID-compliant relational data store. Embedded directly within maintenance.db, SQLite eliminates external database server overhead while supporting relational foreign key cascades, PRAGMA checks, and high-concurrency indexed queries.")
    add_bullet("Python qrcode Engine (ISO/IEC 18004 Standard):", "Programmatically generates high-contrast 2D Matrix Barcodes. Configured with Reed-Solomon Error Correction Level M (recovering up to 15% damaged data from tarmac scuffing) and PIL/Pillow bitmap rendering.")
    add_bullet("CSV & Memory IO Streaming (csv, io):", "Enables real-time dynamic generation of audit compliance reports directly to in-memory buffers (io.StringIO) without disk thrashing, streaming audit logs directly to client browsers.")

    add_h2("3.2 Frontend & User Interface Technologies")
    add_bullet("Semantic HTML5:", "Forms the semantic foundation of the user interface, incorporating accessible navigation landmarks, native date-pickers with validation, and responsive viewport meta tags.")
    add_bullet("Vanilla CSS3 (Custom Aviation Design System):", "Designed completely without heavy bloated utility frameworks. Utilizes custom CSS variables (--navy-darkest: #0B132B, --sky-primary: #0284C7, --bg-page: #F8FAFC), CSS Grid layout decks, glassmorphism banners, radar pulse keyframe animations, and print stylesheets.")
    add_bullet("Jinja2 Template Engine:", "Powers server-side template inheritance through base.html. Facilitates dynamic block overriding, conditional airworthiness badge rendering, and chronological record iteration.")
    add_bullet("Html5-QRCode Optical Scanner Engine:", "Integrates HTML5 MediaDevices API and WebRTC camera video streams. Continuously captures video frames, processes image matrices in client-side memory, and decodes 2D barcodes in real time with audio-frequency tone feedback.")
    add_bullet("Vanilla JavaScript (ES6+):", "Handles client-side asynchronous fetch calls to /api/lookup/<reg>, two-step maintenance form visibility toggles, and seamless Cards-to-Table view transitions.")
    add_bullet("Lucide Vector Icons:", "Provides lightweight, retina-ready vector iconography tailored for aviation management (plane, gauge, shield-check, clipboard-list, history).")

    add_h2("3.3 Networking, Global Tunneling & Deployment Infrastructure")
    add_bullet("Universal Socket Binding (0.0.0.0):", "Configured in app.py to bind to all available network interfaces on port 5000, allowing any mobile smartphone or tablet connected to the local Wi-Fi or airport apron hotspot to access the application via local IP (192.168.x.x).")
    add_bullet("Cloudflare Tunnel (cloudflared):", "Establishes an encrypted, zero-trust QUIC / HTTP/2 reverse-proxy tunnel to Cloudflare edge nodes, generating an instant global HTTPS URL (https://*.trycloudflare.com). Enables worldwide mobile testing over 4G/5G networks with zero port forwarding, SSL/TLS certificates, and no password screens.")
    add_bullet("Localtunnel (npx localtunnel):", "Serves as an auxiliary public internet tunnel providing external HTTPS access with IP verification.")
    add_bullet("Pytest Automated Test Framework:", "Executes isolated unit and regression test suites using temporary in-memory database fixtures, verifying route statuses, data preservation, and foreign key integrity.")

    # -------------------------------------------------------------
    # 4. DATABASE ARCHITECTURE & SCHEMA DESIGN
    # -------------------------------------------------------------
    add_h1("4. Database Architecture & Relational Schema Design")
    add_body("The database is structured to enforce strong referential integrity, linking multiple historical maintenance interventions directly to parent aircraft airframes.")

    schema_rows = [
        ("Aircraft", "registration", "TEXT", "PRIMARY KEY — Tail number (e.g., A6-EEO, VT-ISB)"),
        ("Aircraft", "model", "TEXT", "NOT NULL — Aircraft type (e.g., Airbus A380-800)"),
        ("Aircraft", "airline", "TEXT", "NOT NULL — Fleet operator (e.g., Emirates, IndiGo)"),
        ("Aircraft", "msn", "TEXT", "Manufacturer Serial Number (e.g., MSN-0268)"),
        ("Aircraft", "flight_hours", "TEXT", "Total cumulative airframe operational hours"),
        ("Aircraft", "cycles", "TEXT", "Total cumulative takeoff-and-landing cycles"),
        ("Aircraft", "engine_type", "TEXT", "Powerplant specification (e.g., 4x Engine Alliance GP7200)"),
        ("Aircraft", "home_base", "TEXT", "Primary operational base airport (e.g., DXB, DEL)"),
        ("Aircraft", "airworthiness_status", "TEXT", "CAMO status (Airworthy & In Service, Grounded)"),
        ("Aircraft", "qr_code_path", "TEXT", "File path to generated Master Aircraft QR PNG"),
        ("MaintenanceRecords", "record_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT — Unique audit log ID"),
        ("MaintenanceRecords", "aircraft_registration", "TEXT", "FOREIGN KEY REFERENCES Aircraft(registration)"),
        ("MaintenanceRecords", "component_name", "TEXT", "System worked on (Engine, Landing Gear, Brakes, Avionics)"),
        ("MaintenanceRecords", "service_date", "TEXT", "NOT NULL — ISO format date (YYYY-MM-DD)"),
        ("MaintenanceRecords", "maintenance_activity", "TEXT", "NOT NULL — Detailed description of MRO task performed")
    ]

    # Table Schema Summary
    table_schema = doc.add_table(rows=len(schema_rows) + 1, cols=4)
    table_schema.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_schema = ["Table Name", "Column Field", "Data Type", "Constraints & Aviation Description"]
    
    for c_idx, h in enumerate(headers_schema):
        cell = table_schema.cell(0, c_idx)
        set_cell_background(cell, HEX_HEADER_BG)
        set_cell_margins(cell, 120, 120, 140, 140)
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    for r_idx, row_data in enumerate(schema_rows, start=1):
        for c_idx, val in enumerate(row_data):
            cell = table_schema.cell(r_idx, c_idx)
            set_cell_background(cell, HEX_ALT_ROW if r_idx % 2 == 1 else "FFFFFF")
            set_cell_margins(cell, 80, 80, 100, 100)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(val)
            r.font.name = "Arial"
            r.font.size = Pt(9)
            r.font.color.rgb = COLOR_DARK
            if c_idx == 0:
                r.bold = True
                r.font.color.rgb = COLOR_NAVY
            elif c_idx == 1:
                r.font.name = "Courier New"
                r.bold = True

    doc.add_paragraph()

    # -------------------------------------------------------------
    # 5. COMMERCIAL AIRLINE FLEET CATALOGUE
    # -------------------------------------------------------------
    add_h1("5. Commercial Airline Fleet Catalogue & Seed Profile")
    add_body("To reflect authentic commercial flight operations, the system is seeded with five major international airline carriers, complete with realistic aircraft specifications and historical maintenance baseline entries.")

    fleet_table = doc.add_table(rows=6, cols=5)
    fleet_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_fleet = ["Airline", "Tail Reg", "Model", "Operational Base", "Powerplant"]
    
    for c_idx, h in enumerate(headers_fleet):
        cell = fleet_table.cell(0, c_idx)
        set_cell_background(cell, HEX_HEADER_BG)
        set_cell_margins(cell, 120, 120, 140, 140)
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    fleet_rows = [
        ("Emirates", "A6-EEO", "Airbus A380-800", "Dubai International (DXB)", "4x Engine Alliance GP7200"),
        ("IndiGo", "VT-ISB", "Airbus A321neo", "Delhi (DEL) / Mumbai (BOM)", "2x CFM LEAP-1A32 Turbofans"),
        ("SriLankan Airlines", "4R-ALL", "Airbus A330-300", "Colombo Bandaranaike (CMB)", "2x Rolls-Royce Trent 700"),
        ("Singapore Airlines", "9V-SKU", "Airbus A350-900", "Singapore Changi (SIN)", "2x Rolls-Royce Trent XWB-84"),
        ("Air India / AeroFleet", "VT-AER", "Airbus A320neo", "Chennai (MAA) / Bengaluru (BLR)", "2x CFM LEAP-1A26 Turbofans")
    ]

    for r_idx, row_data in enumerate(fleet_rows, start=1):
        for c_idx, val in enumerate(row_data):
            cell = fleet_table.cell(r_idx, c_idx)
            set_cell_background(cell, HEX_ALT_ROW if r_idx % 2 == 1 else "FFFFFF")
            set_cell_margins(cell, 90, 90, 100, 100)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.name = "Arial"
            r.font.size = Pt(9)
            r.font.color.rgb = COLOR_DARK
            if c_idx == 0:
                r.bold = True
                r.font.color.rgb = COLOR_NAVY
            elif c_idx == 1:
                r.font.name = "Courier New"
                r.bold = True
                r.font.color.rgb = COLOR_SKY

    doc.add_paragraph()

    # -------------------------------------------------------------
    # 6. OPERATIONAL USER WORKFLOW & JOURNEY
    # -------------------------------------------------------------
    add_h1("6. Operational User Workflow & Step-by-Step Journey")
    add_body("The application eliminates confusing multi-step procedures through an intuitive, streamlined user journey tailored for line technicians and inspectors.")

    add_h2("Phase 1: Tarmac Optical QR Scanning")
    add_bullet("1. Camera Activation:", "The technician opens the web application and navigates to 'Scan Aircraft QR'. The camera viewport activates using Html5-QRCode.")
    add_bullet("2. Instant Code Decode:", "The camera focuses on the aircraft's Master QR code affixed near the forward boarding door or nose-gear inspection panel.")
    add_bullet("3. Audio & Visual Confirmation:", "A short 880Hz audio tone confirms decode. An asynchronous REST query (/api/lookup/<reg>) verifies the aircraft in SQLite and redirects to /aircraft/<registration> in under 700ms.")

    add_h2("Phase 2: Master Aircraft Profile & Historical Review")
    add_bullet("Airframe Specifications:", "The technician immediately views total flight hours, engine model, serial number, and airworthiness status.")
    add_bullet("Chronological Maintenance Feed:", "Displays all past service entries (newest first), detailing the exact service date, system worked on, faults reported, corrective repair actions, inspector name, and next scheduled inspection date.")

    add_h2("Phase 3: Dynamic Two-Step Maintenance Logging")
    add_bullet("Step 1 — Target Airframe Identification:", "When clicking 'Log Maintenance', the system presents an interactive fleet selection deck. The technician selects the specific aircraft airframe (e.g., SriLankan Airlines 4R-ALL).")
    add_bullet("Step 2 — Maintenance Entry Details:", "Once the aircraft is chosen, the maintenance detail form dynamically unlocks, capturing component worked on (Engine, Landing Gear, Avionics, Brakes), maintenance activity, reported defects, corrective actions, service status, and next inspection date.")
    add_bullet("Instant Database Persistence:", "Upon submission, the record is committed to SQLite and the technician is redirected to the aircraft's master profile, where the new entry appears immediately at the top while preserving all historical records.")

    # -------------------------------------------------------------
    # 7. CONCLUSION & FUTURE AIRLINE MRO ROADMAP
    # -------------------------------------------------------------
    add_h1("7. Conclusion & Future Airline MRO Roadmap")
    add_body("The Aircraft Maintenance Scanner – Digital Maintenance Record System provides an operational, regulation-compliant prototype demonstrating the digital transformation of airline fleet maintenance. By replacing cumbersome manual paper TechLogs with instant optical Master QR codes, airlines can substantially decrease ground turnaround times, mitigate human error, and achieve seamless CAMO audit readiness.")

    add_h2("Future Enhancements Roadmap")
    add_bullet("RFID & NFC Dual-Frequency Integration:", "Pairing optical 2D QR codes with passive ultra-high-frequency (UHF) RFID tags to enable automated walk-past hangar scanning.")
    add_bullet("Predictive AI Maintenance Analytics:", "Integrating machine learning algorithms to analyze historical fault patterns and predict Mean Time Between Failures (MTBF) for high-wear components.")
    add_bullet("Blockchain-Backed Immutable TechLogs:", "Recording signed maintenance releases to private aviation consortium blockchains (Hyperledger / Ethereum) for cryptographic non-repudiation during aircraft lease transitions.")

    # Save Document
    output_path = os.path.join(os.path.dirname(__file__), "Aircraft_Maintenance_Scanner_Project_Report.docx")
    doc.save(output_path)
    print(f"Report generated successfully: {output_path}")

if __name__ == "__main__":
    create_report()
