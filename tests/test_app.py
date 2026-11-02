import os
import sys
import tempfile
import pytest
import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import init_db, seed_sample_data, generate_qr_code, get_db_connection

@pytest.fixture
def client():
    db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    import database
    orig_db_path = database.DB_PATH
    database.DB_PATH = temp_db_path

    init_db(temp_db_path)
    seed_sample_data(temp_db_path, force=True)

    with app.test_client() as client:
        with app.app_context():
            yield client

    # Cleanup
    database.DB_PATH = orig_db_path
    os.close(db_fd)
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

def test_dashboard_loads_with_aircraft(client):
    """Test dashboard displays single dedicated aircraft (VT-AER - Air India / AeroFleet)."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Air India / AeroFleet" in response.data
    assert b"VT-AER" in response.data

def test_fleet_view_and_aircraft_qr_codes(client):
    """Test fleet view renders the aircraft with Master QR tags."""
    res = client.get("/fleet")
    assert res.status_code == 200
    assert b"Active Airline Fleet" in res.data
    assert b"VT-AER" in res.data
    assert b"Air India / AeroFleet" in res.data

def test_aircraft_master_view_and_past_logs(client):
    """Test viewing VT-AER loads its full profile and all historical maintenance logs."""
    res = client.get("/aircraft/VT-AER")
    assert res.status_code == 200
    assert b"VT-AER" in res.data
    assert b"Air India / AeroFleet" in res.data
    assert b"Airbus A320neo" in res.data
    assert b"Engine Hot Section Boroscope Inspection" in res.data
    assert b"Landing Gear Retraction" in res.data
    assert b"Tariq Al-Nuaimi" in res.data

def test_api_lookup_aircraft_qr(client):
    """Test scanning / looking up aircraft QR codes via API."""
    res = client.get("/api/lookup/VT-AER")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["component_id"] == "VT-AER"
    assert "/aircraft/VT-AER" in data["redirect_url"]

    # Unknown
    res_unknown = client.get("/api/lookup/INVALID-999")
    assert res_unknown.status_code == 404
    assert res_unknown.get_json()["success"] is False

def test_maintenance_logging_flow_and_preservation(client):
    """
    CRITICAL WORKFLOW TEST:
    1. Verify maintenance/new loads and asks for aircraft.
    2. Add new maintenance record for VT-AER.
    3. Verify redirect to VT-AER master page with the new log and previous logs.
    """
    # 1. GET maintenance/new
    res_get = client.get("/maintenance/new")
    assert res_get.status_code == 200
    assert b"Which Aircraft Are You Servicing?" in res_get.data

    # 2. POST new record for VT-AER
    new_data = {
        "aircraft_registration": "VT-AER",
        "component_name": "Weather Radar & Radome",
        "service_date": "2026-10-31",
        "technician": "Lead Inspector K. Verma",
        "maintenance_activity": "Pre-departure radome lightning strike check",
        "fault_reported": "Pilot reported suspected static discharge near radome tip",
        "action_taken": "Ohmic resistance test on static diverter strips within 0.05 ohm spec",
        "service_status": "Completed — sample record",
        "next_inspection_date": "2026-11-30",
        "notes": "Radome surface undamaged. Cleared for line service."
    }

    res_post = client.post("/maintenance/new", data=new_data, follow_redirects=True)
    assert res_post.status_code == 200

    # 3. Verify on aircraft page that both the new log and previous logs exist!
    assert b"Pre-departure radome lightning strike check" in res_post.data
    assert b"Lead Inspector K. Verma" in res_post.data
    assert b"Brake Wear Pin Measurement" in res_post.data # Previous log preserved!
    assert b"Nose Wheel Tyre Replacement" in res_post.data # Previous log preserved!

def test_register_new_aircraft_generates_qr(client):
    """Test registering a new aircraft and verifying its exclusive Master QR Code is generated."""
    data = {
        "registration": "A6-EYA",
        "model": "Boeing 787-9 Dreamliner",
        "airline": "Etihad Airways",
        "msn": "MSN-39650",
        "flight_hours": "3,120 hrs",
        "cycles": "890 cycles",
        "engine_type": "2x GEnx-1B70",
        "home_base": "Abu Dhabi (AUH)",
        "airworthiness_status": "Airworthy & In Service"
    }

    res = client.post("/aircraft/new", data=data, follow_redirects=True)
    assert res.status_code == 200
    assert b"A6-EYA" in res.data
    assert b"Etihad Airways" in res.data
    assert b"Boeing 787-9 Dreamliner" in res.data

    # Check QR code file created on disk
    qr_file = os.path.join(os.path.dirname(__file__), "..", "static", "qr_codes", "A6-EYA.png")
    assert os.path.exists(qr_file)

def test_records_page_and_export_csv(client):
    """Test all records page and CSV export."""
    res = client.get("/records")
    assert res.status_code == 200
    assert b"Digital Maintenance Audit Logs" in res.data

    res_csv = client.get("/records/export.csv")
    assert res_csv.status_code == 200
    assert res_csv.mimetype == "text/csv"
    assert b"Aircraft Registration,Airline,Aircraft Model" in res_csv.data
    assert b"VT-AER,Air India / AeroFleet" in res_csv.data
