import os
import sqlite3
import datetime
import qrcode

DB_PATH = os.environ.get("AIRCRAFT_DB_PATH", os.path.join(os.path.dirname(__file__), "maintenance.db"))
QR_FOLDER = os.path.join(os.path.dirname(__file__), "static", "qr_codes")

def get_db_connection(db_path=None):
    """Returns an active SQLite connection with Row factory and foreign keys enabled."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def generate_qr_code(identifier, qr_folder=None):
    """
    Generates a high-contrast QR code for the given aircraft registration.
    QR codes are exclusively generated for aircraft.
    """
    target_folder = qr_folder or QR_FOLDER
    os.makedirs(target_folder, exist_ok=True)
    clean_name = identifier.strip().replace("/", "_").replace(":", "_").upper()
    filename = f"{clean_name}.png"
    filepath = os.path.join(target_folder, filename)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(identifier.strip().upper())
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0B132B", back_color="white")
    img.save(filepath)

    return f"qr_codes/{filename}"

def init_db(db_path=None):
    """Initializes the database schema for Aircraft and MaintenanceRecords."""
    os.makedirs(QR_FOLDER, exist_ok=True)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Aircraft Fleet Table (QR codes are strictly for Aircraft)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Aircraft (
        registration TEXT PRIMARY KEY,
        model TEXT NOT NULL,
        airline TEXT NOT NULL,
        msn TEXT,
        flight_hours TEXT,
        cycles TEXT,
        engine_type TEXT,
        home_base TEXT,
        airworthiness_status TEXT DEFAULT 'Airworthy & In Service',
        qr_code_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Components Table (Optional legacy catalogue)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Components (
        component_id TEXT PRIMARY KEY,
        component_name TEXT NOT NULL,
        aircraft_registration TEXT DEFAULT 'VT-AER',
        qr_code_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Check foreign keys of MaintenanceRecords
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='MaintenanceRecords';")
    if cursor.fetchone():
        cursor.execute("PRAGMA foreign_key_list(MaintenanceRecords);")
        fks = cursor.fetchall()
        needs_migration = any(fk['table'] == 'Components' for fk in fks)
        if needs_migration:
            cursor.execute("ALTER TABLE MaintenanceRecords RENAME TO MaintenanceRecords_old;")
            cursor.execute("""
            CREATE TABLE MaintenanceRecords (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                aircraft_registration TEXT NOT NULL DEFAULT 'VT-AER',
                component_id TEXT DEFAULT 'SYS',
                component_name TEXT NOT NULL,
                service_date TEXT NOT NULL,
                maintenance_activity TEXT NOT NULL,
                fault_reported TEXT,
                action_taken TEXT,
                technician TEXT NOT NULL,
                service_status TEXT NOT NULL,
                next_inspection_date TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (aircraft_registration) REFERENCES Aircraft (registration) ON DELETE CASCADE
            );
            """)
            try:
                cursor.execute("""
                INSERT INTO MaintenanceRecords (
                    record_id, aircraft_registration, component_id, component_name,
                    service_date, maintenance_activity, fault_reported, action_taken,
                    technician, service_status, next_inspection_date, notes, created_at
                )
                SELECT 
                    record_id,
                    COALESCE(aircraft_registration, 'VT-AER'),
                    component_id,
                    COALESCE(component_name, component_id),
                    service_date, maintenance_activity, fault_reported, action_taken,
                    technician, service_status, next_inspection_date, notes, created_at
                FROM MaintenanceRecords_old;
                """)
            except Exception:
                pass
            cursor.execute("DROP TABLE MaintenanceRecords_old;")
    else:
        cursor.execute("""
        CREATE TABLE MaintenanceRecords (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            aircraft_registration TEXT NOT NULL DEFAULT 'VT-AER',
            component_id TEXT DEFAULT 'SYS',
            component_name TEXT NOT NULL,
            service_date TEXT NOT NULL,
            maintenance_activity TEXT NOT NULL,
            fault_reported TEXT,
            action_taken TEXT,
            technician TEXT NOT NULL,
            service_status TEXT NOT NULL,
            next_inspection_date TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (aircraft_registration) REFERENCES Aircraft (registration) ON DELETE CASCADE
        );
        """)

    # Indexes for fast lookup and sorting
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_maint_aircraft_reg ON MaintenanceRecords(aircraft_registration);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_maint_service_date ON MaintenanceRecords(service_date);")

    conn.commit()
    conn.close()

def seed_sample_data(db_path=None, force=False):
    """
    Seeds the dedicated aircraft (Air India / AeroFleet VT-AER)
    and its comprehensive historical maintenance entries.
    QR codes are generated exclusively for aircraft.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Aircraft;")
    aircraft_count = cursor.fetchone()[0]

    if aircraft_count >= 1 and not force:
        conn.close()
        return

    if force:
        cursor.execute("DELETE FROM MaintenanceRecords;")
        cursor.execute("DELETE FROM Aircraft;")

    # Master Fleet Data (Single Aircraft: VT-AER)
    sample_fleet = [
        {
            "registration": "VT-AER",
            "model": "Airbus A320neo",
            "airline": "Air India / AeroFleet",
            "msn": "MSN-9421",
            "flight_hours": "3,420 hrs",
            "cycles": "2,150 cycles",
            "engine_type": "2x CFM LEAP-1A26 Turbofans",
            "home_base": "Chennai (MAA) / Bengaluru (BLR)",
            "airworthiness_status": "Airworthy & In Service"
        }
    ]

    # Insert / Update Aircraft with exclusive QR code
    for plane in sample_fleet:
        qr_path = generate_qr_code(plane["registration"])
        cursor.execute("""
            INSERT OR REPLACE INTO Aircraft (
                registration, model, airline, msn, flight_hours, cycles,
                engine_type, home_base, airworthiness_status, qr_code_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            plane["registration"], plane["model"], plane["airline"], plane["msn"],
            plane["flight_hours"], plane["cycles"], plane["engine_type"],
            plane["home_base"], plane["airworthiness_status"], qr_path
        ))

    # Historical Maintenance Logs for VT-AER Subsystems
    fleet_maintenance_records = [
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Aircraft Engine (CFM LEAP-1A26)",
            "service_date": "2026-10-28",
            "maintenance_activity": "Engine Hot Section Boroscope Inspection",
            "fault_reported": "Routine 500-flight-hour hot section interval check",
            "action_taken": "Boroscopic camera inspection performed on high-pressure turbine blades; no thermal stress cracks detected. Blade clearance verified within OEM limits.",
            "technician": "Eng. Tariq Al-Nuaimi (B1 Licensed)",
            "service_status": "Completed — sample record",
            "next_inspection_date": "2026-11-28",
            "notes": "Engine running at 100% rated thrust. Oil consumption standard at 0.18 qt/hr."
        },
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Main Landing Gear System",
            "service_date": "2026-10-25",
            "maintenance_activity": "Landing Gear Retraction & Hydraulic Seal Servicing",
            "fault_reported": "Minor hydraulic seepage trace noted around left main gear actuator",
            "action_taken": "Replaced O-ring packing seals and pressure-tested hydraulic return line to 3,000 PSI. Cycle tests completed successfully.",
            "technician": "Technician Rashid Z.",
            "service_status": "Completed — sample record",
            "next_inspection_date": "2026-11-25",
            "notes": "Gear retraction sequence timed at 8.2 seconds, well within Airbus AMM specifications."
        },
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Aircraft Brake System (Carbon Discs)",
            "service_date": "2026-10-22",
            "maintenance_activity": "Brake Wear Pin Measurement & Anti-Skid Calibration",
            "fault_reported": "Pilot report: Slight left yaw tendency during high-speed rollout",
            "action_taken": "Wear pins measured at 6.8mm (minimum limit 2.5mm). Anti-skid transducer recalibrated and brake hydraulic lines bled.",
            "technician": "Technician Rohan Verma",
            "service_status": "Completed — sample record",
            "next_inspection_date": "2026-11-22",
            "notes": "Carbon heat pack wear within allowable limits. Taxi brake check signed off."
        },
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Aircraft Tyre Assembly (Nose Gear)",
            "service_date": "2026-10-18",
            "maintenance_activity": "Nose Wheel Tyre Replacement & Pressure Servicing",
            "fault_reported": "Tread groove depth approaching minimum wear indicator limit",
            "action_taken": "Dual nose gear wheel assemblies replaced with fresh Michelin Air X radial tyres. Torqued to 180 ft-lbs and inflated to 165 PSI nitrogen.",
            "technician": "Technician Amit Sharma",
            "service_status": "Completed — sample record",
            "next_inspection_date": "2026-11-18",
            "notes": "Tyre serials: MCH-89211 and MCH-89212. Balancing verified."
        },
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Aircraft Battery (Main 24V)",
            "service_date": "2026-10-15",
            "maintenance_activity": "Battery Condition & Terminal Voltage Check",
            "fault_reported": "Battery voltage slightly below expected level during cold startup",
            "action_taken": "Battery test and charging-system check completed; charger float voltage verified.",
            "technician": "Technician B. Patel",
            "service_status": "Completed — sample record",
            "next_inspection_date": "2026-11-15",
            "notes": "Cell voltage reading 24.2V; full battery bench test passed."
        },
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Avionics & TCAS Transponder",
            "service_date": "2026-09-30",
            "maintenance_activity": "90-Day Periodic Mode-S & TCAS II Functional Ramp Test",
            "fault_reported": "Mandatory DGCA 90-day periodic inspection",
            "action_taken": "IFR 6000 ramp test set connected. Frequency accuracy, sensitivity, and antenna power measured and compliant with ICAO Annex 10.",
            "technician": "Technician V. Pillai",
            "service_status": "Completed — sample record",
            "next_inspection_date": "2026-12-30",
            "notes": "Altitude encoder matched within 20 ft tolerance."
        },
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Auxiliary Power Unit (APU)",
            "service_date": "2026-09-25",
            "maintenance_activity": "APU Generator Load Test & Fuel Feed Line Inspection",
            "fault_reported": "Slight EGT variation during ground transit electrical startup",
            "action_taken": "Fuel nozzle manifold cleaned and spray pattern checked. Generator load test at 90kVA verified with ground electrical cart.",
            "technician": "Eng. K. Dissanayake",
            "service_status": "Completed — sample record",
            "next_inspection_date": "2026-11-25",
            "notes": "APU EGT stabilized at 540°C under full air-conditioning load."
        },
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Flight Controls (Wing Flap Actuators)",
            "service_date": "2026-09-18",
            "maintenance_activity": "Trailing Edge Flap Track Mechanism Lubrication",
            "fault_reported": "Flap asymmetry alert sensor flagged transient advisory during approach",
            "action_taken": "Cleaned tracks 1 through 4. Lubricated drive screw mechanisms with AeroShell 22 grease. Asymmetry sensor resistance re-zeroed.",
            "technician": "Technician Pradeep Silva",
            "service_status": "Further inspection required",
            "next_inspection_date": "2026-11-05",
            "notes": "Follow-up transit cycle check recommended after 30 flight hours."
        },
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Weather Radar & Multi-Scan Antenna",
            "service_date": "2026-09-10",
            "maintenance_activity": "Collins RTA-4218 MultiScan Radar BITE & Radome Check",
            "fault_reported": "Routine pre-monsoon flight inspection",
            "action_taken": "Radome visual inspection showed no composite erosion or static wick defects. Built-in test (BITE) passed with zero fault codes. 320NM test echo received.",
            "technician": "Technician Kelvin Tan",
            "service_status": "Completed — sample record",
            "next_inspection_date": "2026-11-29",
            "notes": "Predictive windshear (PWS) alert system operational."
        },
        {
            "aircraft_registration": "VT-AER",
            "component_name": "Environmental Control System (ECS)",
            "service_date": "2026-09-02",
            "maintenance_activity": "Cabin Air Filtration & Pack Overhaul",
            "fault_reported": "Slight differential pressure drop across HEPA recirculation filters",
            "action_taken": "Primary and secondary HEPA recirculation filters replaced. Cabin pressurization leak test conducted; outflow valves calibrated.",
            "technician": "Technician S. Kumar",
            "service_status": "Completed — sample record",
            "next_inspection_date": "2026-12-22",
            "notes": "Cabin altitude controller response verified normal."
        }
    ]

    # Only seed if MaintenanceRecords is empty or forced
    cursor.execute("SELECT COUNT(*) FROM MaintenanceRecords;")
    recs_count = cursor.fetchone()[0]

    if recs_count == 0 or force:
        if force:
            cursor.execute("DELETE FROM MaintenanceRecords;")
        for rec in fleet_maintenance_records:
            comp_id = rec.get("component_id") or "SYS-" + rec["component_name"][:3].upper()
            cursor.execute("""
                INSERT INTO MaintenanceRecords (
                    aircraft_registration, component_id, component_name, service_date,
                    maintenance_activity, fault_reported, action_taken,
                    technician, service_status, next_inspection_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                rec["aircraft_registration"], comp_id, rec["component_name"], rec["service_date"],
                rec["maintenance_activity"], rec["fault_reported"], rec["action_taken"],
                rec["technician"], rec["service_status"], rec["next_inspection_date"], rec["notes"]
            ))

    # Also update any existing legacy records in case database already had some
    cursor.execute("UPDATE MaintenanceRecords SET aircraft_registration = 'VT-AER' WHERE aircraft_registration IS NULL OR aircraft_registration = '';")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_sample_data(force=True)
    print("Database schema initialized and single aircraft (VT-AER) seeded with Aircraft QR codes successfully.")
