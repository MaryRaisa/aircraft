import os
import csv
import io
import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, Response, abort
)
from database import (
    get_db_connection, init_db, seed_sample_data, generate_qr_code, DB_PATH
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "aviation-digital-maintenance-scanner-2026")

# Auto-initialize database and fleet on startup
with app.app_context():
    init_db()
    seed_sample_data()

def parse_date(date_str):
    """Validates YYYY-MM-DD date format."""
    try:
        return datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None

# ==================== 1. DASHBOARD ====================
@app.route("/")
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all aircraft in fleet
    cursor.execute("SELECT * FROM Aircraft ORDER BY airline ASC, registration ASC;")
    fleet = [dict(a) for a in cursor.fetchall()]

    # Attach maintenance stats to each aircraft
    for plane in fleet:
        reg = plane["registration"]
        cursor.execute("SELECT COUNT(*) FROM MaintenanceRecords WHERE aircraft_registration = ?;", (reg,))
        plane["record_count"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT * FROM MaintenanceRecords 
            WHERE aircraft_registration = ? 
            ORDER BY service_date DESC, record_id DESC 
            LIMIT 1;
        """, (reg,))
        latest = cursor.fetchone()
        plane["latest_record"] = dict(latest) if latest else None

    # Overall system metrics
    cursor.execute("SELECT COUNT(*) FROM Aircraft;")
    total_aircraft = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM MaintenanceRecords;")
    total_records = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM MaintenanceRecords WHERE service_status LIKE '%Pending%';")
    pending_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM MaintenanceRecords WHERE service_status LIKE '%Completed%';")
    completed_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM MaintenanceRecords WHERE service_status LIKE '%Further%';")
    further_req_count = cursor.fetchone()[0]

    # Recent maintenance logs across entire fleet (last 6)
    cursor.execute("""
        SELECT m.*, a.model, a.airline 
        FROM MaintenanceRecords m
        JOIN Aircraft a ON m.aircraft_registration = a.registration
        ORDER BY m.service_date DESC, m.record_id DESC
        LIMIT 6;
    """)
    recent_logs = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return render_template(
        "dashboard.html",
        fleet=fleet,
        total_aircraft=total_aircraft,
        total_records=total_records,
        pending_count=pending_count,
        completed_count=completed_count,
        further_req_count=further_req_count,
        recent_logs=recent_logs
    )

# ==================== 2. AIRCRAFT FLEET ====================
@app.route("/fleet")
def fleet_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Aircraft ORDER BY airline ASC, registration ASC;")
    fleet = [dict(a) for a in cursor.fetchall()]

    for plane in fleet:
        reg = plane["registration"]
        cursor.execute("SELECT COUNT(*) FROM MaintenanceRecords WHERE aircraft_registration = ?;", (reg,))
        plane["record_count"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT * FROM MaintenanceRecords 
            WHERE aircraft_registration = ? 
            ORDER BY service_date DESC, record_id DESC 
            LIMIT 1;
        """, (reg,))
        latest = cursor.fetchone()
        plane["latest_record"] = dict(latest) if latest else None

    conn.close()
    return render_template("fleet.html", fleet=fleet)

@app.route("/aircraft/new", methods=["GET", "POST"])
def aircraft_create():
    if request.method == "POST":
        registration = request.form.get("registration", "").strip().upper()
        model = request.form.get("model", "").strip()
        airline = request.form.get("airline", "").strip()
        msn = request.form.get("msn", "").strip()
        flight_hours = request.form.get("flight_hours", "").strip()
        cycles = request.form.get("cycles", "").strip()
        engine_type = request.form.get("engine_type", "").strip()
        home_base = request.form.get("home_base", "").strip()
        airworthiness_status = request.form.get("airworthiness_status", "Airworthy & In Service").strip()

        errors = []
        if not registration:
            errors.append("Aircraft registration (e.g. VT-AER) is required.")
        elif len(registration) < 3 or len(registration) > 12:
            errors.append("Registration must be between 3 and 12 characters.")

        if not model:
            errors.append("Aircraft model (e.g. Airbus A380, Boeing 777) is required.")
        if not airline:
            errors.append("Airline / operator name is required.")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT registration FROM Aircraft WHERE registration = ?;", (registration,))
        if cursor.fetchone():
            errors.append(f"Aircraft registration '{registration}' already exists in fleet records.")

        if errors:
            conn.close()
            for err in errors:
                flash(err, "danger")
            return render_template("aircraft_form.html", form_data=request.form)

        # Generate unique Master QR Code for this new aircraft
        qr_path = generate_qr_code(registration)

        cursor.execute("""
            INSERT INTO Aircraft (
                registration, model, airline, msn, flight_hours, cycles,
                engine_type, home_base, airworthiness_status, qr_code_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            registration, model, airline, msn, flight_hours, cycles,
            engine_type, home_base, airworthiness_status, qr_path
        ))
        conn.commit()
        conn.close()

        flash(f"New aircraft {airline} {model} ({registration}) registered successfully with unique Master QR Code.", "success")
        return redirect(url_for("aircraft_master_view", registration=registration))

    return render_template("aircraft_form.html", form_data={})

# ==================== 3. AIRCRAFT MASTER VIEW & SCAN TARGET ====================
@app.route("/aircraft")
@app.route("/aircraft/<registration>")
def aircraft_master_view(registration=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if not registration:
        # Default to first aircraft in fleet
        cursor.execute("SELECT registration FROM Aircraft ORDER BY airline ASC LIMIT 1;")
        row = cursor.fetchone()
        reg = row[0] if row else "VT-AER"
    else:
        reg = registration.strip().upper()

    cursor.execute("SELECT * FROM Aircraft WHERE registration = ?;", (reg,))
    aircraft_row = cursor.fetchone()

    if not aircraft_row:
        # Try fallback or 404
        cursor.execute("SELECT * FROM Aircraft LIMIT 1;")
        aircraft_row = cursor.fetchone()
        if not aircraft_row:
            conn.close()
            flash(f"Aircraft registration '{reg}' not found in fleet records.", "danger")
            return render_template("404.html", message=f"Aircraft '{reg}' does not exist in the database."), 404

    aircraft_info = dict(aircraft_row)

    # Ensure QR code exists on disk
    qr_full_path = os.path.join(os.path.dirname(__file__), "static", aircraft_info["qr_code_path"])
    if not os.path.exists(qr_full_path):
        aircraft_info["qr_code_path"] = generate_qr_code(aircraft_info["registration"])

    # Fetch ALL historical maintenance records for this specific aircraft (Chronological, newest first)
    cursor.execute("""
        SELECT * FROM MaintenanceRecords 
        WHERE aircraft_registration = ? 
        ORDER BY service_date DESC, record_id DESC;
    """, (aircraft_info["registration"],))
    records = [dict(r) for r in cursor.fetchall()]

    conn.close()

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    default_next = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    return render_template(
        "aircraft_detail.html",
        aircraft=aircraft_info,
        records=records,
        today_str=today_str,
        default_next=default_next
    )

# ==================== 4. ADD NEW MAINTENANCE RECORD (ASKS FOR AIRCRAFT FIRST) ====================
@app.route("/maintenance/new", methods=["GET", "POST"])
def maintenance_create():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        aircraft_reg = request.form.get("aircraft_registration", "").strip().upper()
        component_name = request.form.get("component_name", "").strip()
        custom_component = request.form.get("custom_component", "").strip()
        if component_name == "Other" and custom_component:
            component_name = custom_component

        service_date = request.form.get("service_date", "").strip()
        maintenance_activity = request.form.get("maintenance_activity", "").strip()
        fault_reported = request.form.get("fault_reported", "").strip()
        action_taken = request.form.get("action_taken", "").strip()
        technician = request.form.get("technician", "").strip()
        service_status = request.form.get("service_status", "").strip()
        next_inspection_date = request.form.get("next_inspection_date", "").strip() or None
        notes = request.form.get("notes", "").strip()

        errors = []
        if not aircraft_reg:
            errors.append("Aircraft selection is required. Please specify which aircraft this log applies to.")
        else:
            cursor.execute("SELECT * FROM Aircraft WHERE registration = ?;", (aircraft_reg,))
            plane = cursor.fetchone()
            if not plane:
                errors.append(f"Aircraft '{aircraft_reg}' does not exist in fleet database.")

        if not component_name:
            errors.append("Aircraft component or system name is required (e.g. Engine, Landing Gear, Avionics).")

        if not service_date:
            errors.append("Service date is required.")
        elif not parse_date(service_date):
            errors.append("Invalid service date format (YYYY-MM-DD required).")

        if not maintenance_activity:
            errors.append("Maintenance activity description is required.")
        if not technician:
            errors.append("Technician or inspector name is required.")
        if not service_status:
            errors.append("Service status is required.")

        if next_inspection_date and not parse_date(next_inspection_date):
            errors.append("Invalid next inspection date format (YYYY-MM-DD required).")

        if errors:
            cursor.execute("SELECT * FROM Aircraft ORDER BY airline ASC, registration ASC;")
            fleet = [dict(a) for a in cursor.fetchall()]
            conn.close()
            for err in errors:
                flash(err, "danger")
            return render_template(
                "maintenance_form.html",
                fleet=fleet,
                selected_aircraft=aircraft_reg,
                form_data=request.form
            )

        # Generate a short component ID code
        comp_code = "SYS-" + component_name[:3].upper()

        # Insert new maintenance record attached to this specific aircraft
        cursor.execute("""
            INSERT INTO MaintenanceRecords (
                aircraft_registration, component_id, component_name, service_date,
                maintenance_activity, fault_reported, action_taken, technician,
                service_status, next_inspection_date, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            aircraft_reg, comp_code, component_name, service_date,
            maintenance_activity, fault_reported, action_taken, technician,
            service_status, next_inspection_date, notes
        ))
        conn.commit()
        conn.close()

        flash(f"New maintenance record successfully saved for {aircraft_reg} ({component_name}). Aircraft digital log updated.", "success")
        return redirect(url_for("aircraft_master_view", registration=aircraft_reg))

    # GET request: First asks "Which aircraft?"
    preselected_aircraft = request.args.get("aircraft", "").strip().upper()
    if not preselected_aircraft:
        preselected_aircraft = request.args.get("registration", "").strip().upper()

    cursor.execute("SELECT * FROM Aircraft ORDER BY airline ASC, registration ASC;")
    fleet = [dict(a) for a in cursor.fetchall()]
    conn.close()

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    default_next = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    return render_template(
        "maintenance_form.html",
        fleet=fleet,
        selected_aircraft=preselected_aircraft,
        form_data={
            "service_date": today_str,
            "next_inspection_date": default_next,
            "service_status": "Completed — sample record"
        }
    )

# ==================== 5. CAMERA & QR SCANNER ====================
@app.route("/scan")
def scanner():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Aircraft ORDER BY airline ASC, registration ASC;")
    fleet = [dict(a) for a in cursor.fetchall()]
    conn.close()
    return render_template("scanner.html", fleet=fleet)

@app.route("/api/lookup/<identifier>")
def api_lookup(identifier):
    """
    JSON API called by the optical QR scanner and manual search fallback.
    Decodes the scanned QR data (which is the aircraft registration or aircraft URL)
    and redirects directly to that Aircraft's Digital Profile & Maintenance Logs.
    """
    raw_id = identifier.strip()
    if "/" in raw_id:
        raw_id = raw_id.rstrip("/").split("/")[-1]
    cid = raw_id.upper()

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Match aircraft registration directly
    cursor.execute("SELECT * FROM Aircraft WHERE registration = ?;", (cid,))
    aircraft_row = cursor.fetchone()

    # 2. Match airline or model keywords if searched manually
    if not aircraft_row:
        cursor.execute("""
            SELECT * FROM Aircraft 
            WHERE airline LIKE ? OR model LIKE ? 
            ORDER BY airline ASC LIMIT 1;
        """, (f"%{cid}%", f"%{cid}%"))
        aircraft_row = cursor.fetchone()

    if aircraft_row:
        plane = dict(aircraft_row)
        reg = plane["registration"]

        # Fetch latest maintenance record
        cursor.execute("""
            SELECT * FROM MaintenanceRecords 
            WHERE aircraft_registration = ? 
            ORDER BY service_date DESC, record_id DESC 
            LIMIT 1;
        """, (reg,))
        latest = cursor.fetchone()
        latest_status = latest["service_status"] if latest else plane["airworthiness_status"]

        conn.close()
        return jsonify({
            "success": True,
            "component_id": reg,
            "component_name": f"{plane['airline']} {plane['model']} ({reg})",
            "latest_status": latest_status,
            "redirect_url": url_for("aircraft_master_view", registration=reg)
        })

    conn.close()
    return jsonify({
        "success": False,
        "message": f"Aircraft registration '{cid}' was not found in airline fleet records."
    }), 404

# ==================== 6. PRINT AIRCRAFT QR TAG ====================
@app.route("/aircraft/<registration>/print-tag")
def print_aircraft_tag(registration="VT-AER"):
    reg = registration.strip().upper()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Aircraft WHERE registration = ?;", (reg,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT * FROM Aircraft LIMIT 1;")
        row = cursor.fetchone()

    aircraft_info = dict(row)

    # Fetch recent maintenance logs for printout
    cursor.execute("""
        SELECT * FROM MaintenanceRecords 
        WHERE aircraft_registration = ? 
        ORDER BY service_date DESC, record_id DESC 
        LIMIT 8;
    """, (aircraft_info["registration"],))
    records = [dict(r) for r in cursor.fetchall()]

    conn.close()

    # Ensure QR exists
    generate_qr_code(aircraft_info["registration"])

    return render_template(
        "print_aircraft_tag.html",
        aircraft=aircraft_info,
        records=records
    )

# ==================== 7. ALL RECORDS & CSV AUDIT EXPORT ====================
@app.route("/records")
def all_records():
    aircraft_filter = request.args.get("aircraft", "").strip().upper()
    status_filter = request.args.get("status", "all").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Aircraft ORDER BY airline ASC, registration ASC;")
    fleet = [dict(a) for a in cursor.fetchall()]

    query = """
        SELECT m.*, a.model, a.airline 
        FROM MaintenanceRecords m
        JOIN Aircraft a ON m.aircraft_registration = a.registration
        WHERE 1=1
    """
    params = []

    if aircraft_filter:
        query += " AND m.aircraft_registration = ?"
        params.append(aircraft_filter)

    if status_filter and status_filter != "all":
        query += " AND m.service_status = ?"
        params.append(status_filter)

    query += " ORDER BY m.service_date DESC, m.record_id DESC;"

    cursor.execute(query, params)
    records = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return render_template(
        "records.html",
        records=records,
        fleet=fleet,
        aircraft_filter=aircraft_filter,
        status_filter=status_filter
    )

@app.route("/records/export.csv")
def export_csv():
    aircraft_filter = request.args.get("aircraft", "").strip().upper()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT m.record_id, m.aircraft_registration, a.airline, a.model,
               m.component_name, m.service_date, m.maintenance_activity,
               m.fault_reported, m.action_taken, m.technician,
               m.service_status, m.next_inspection_date, m.notes
        FROM MaintenanceRecords m
        JOIN Aircraft a ON m.aircraft_registration = a.registration
        WHERE 1=1
    """
    params = []
    if aircraft_filter:
        query += " AND m.aircraft_registration = ?"
        params.append(aircraft_filter)

    query += " ORDER BY m.service_date DESC, m.record_id DESC;"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Record ID", "Aircraft Registration", "Airline", "Aircraft Model",
        "Component / System", "Service Date", "Maintenance Activity",
        "Fault Reported", "Action Taken", "Technician",
        "Service Status", "Next Inspection Date", "Notes"
    ])

    for r in rows:
        writer.writerow(list(r))

    filename = f"aircraft_maintenance_audit_{aircraft_filter or 'fleet'}.csv"
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

# Legacy routes redirected gracefully
@app.route("/components")
@app.route("/components/new")
@app.route("/qr-sheet")
def legacy_redirect():
    return redirect(url_for("fleet_list"))

@app.route("/component/<cid>")
def legacy_component_redirect(cid):
    return redirect(url_for("fleet_list"))

@app.route("/component/<cid>/print-label")
def legacy_label_redirect(cid):
    return redirect(url_for("fleet_list"))

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(error):
    return render_template("404.html", message="Requested aircraft or digital maintenance record was not found."), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Aircraft Maintenance Scanner on http://0.0.0.0:{port}")
    print(f"  - Local Computer:  http://127.0.0.1:{port} or http://localhost:{port}")
    print(f"  - Mobile / Wi-Fi:  http://192.168.31.49:{port}")
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
