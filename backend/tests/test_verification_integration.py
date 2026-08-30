import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from tests.conftest import TestingSessionLocal, test_engine

client = TestClient(app)

def test_closed_loop_resolution_and_citizen_verification_flow():
    # Verify SUBMITTED / IN_PROGRESS verification rejection
    res_unready = client.post(
        "/api/v1/reports",
        data={
            "description": "Pothole for unready verification rejection test.",
            "latitude": 28.5450,
            "longitude": 77.1926,
            "address": "Main Gate Road"
        }
    )
    inc_unready_id = res_unready.json()["incident_id"]

    # Attempting verification on SUBMITTED incident must fail with 400
    bad_verify = client.post(
        f"/api/v1/incidents/{inc_unready_id}/verify",
        data={"verified_fixed": "true", "citizen_notes": "Premature verification attempt"}
    )
    assert bad_verify.status_code == 400
    assert "Invalid status transition" in bad_verify.json()["detail"]

    # 1. Create Report -> Incident #1 created
    res1 = client.post(
        "/api/v1/reports",
        data={
            "description": "Unlit streetlight fixture near East Avenue.",
            "latitude": 28.5800,
            "longitude": 77.2200,
            "address": "500 East Avenue"
        }
    )
    assert res1.status_code == 201
    rep_data = res1.json()
    inc_id = rep_data["incident_id"]

    # Verify initial status SUBMITTED & Work Order PENDING
    inc_res = client.get(f"/api/v1/incidents/{inc_id}")
    assert inc_res.status_code == 200
    inc_obj = inc_res.json()
    assert inc_obj["status"] == "SUBMITTED"
    assert inc_obj["work_order"]["status"] == "PENDING"
    assert inc_obj["assigned_department"] == "Electrical Maintenance"

    # Direct PENDING -> COMPLETED on WorkOrder must fail with 400
    bad_wo_completion = client.patch(
        f"/api/v1/work-orders/{inc_obj['work_order']['id']}/status",
        data={"status": "COMPLETED", "completion_notes": "Attempting completion on PENDING work order"}
    )
    assert bad_wo_completion.status_code == 400
    assert "Invalid WorkOrder" in bad_wo_completion.json()["detail"]

    # 2. Dispatcher Starts Work -> SUBMITTED to IN_PROGRESS
    status_res = client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "IN_PROGRESS", "notes": "Technician dispatched to replace bulb."}
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "IN_PROGRESS"

    # Attempting verification on IN_PROGRESS incident must also fail with 400
    bad_verify_inp = client.post(
        f"/api/v1/incidents/{inc_id}/verify",
        data={"verified_fixed": "true", "citizen_notes": "Premature verification attempt"}
    )
    assert bad_verify_inp.status_code == 400

    # 3. Work Order Complete -> RESOLVED
    wo_id = inc_obj["work_order"]["id"]
    wo_res = client.patch(
        f"/api/v1/work-orders/{wo_id}/status",
        data={"status": "COMPLETED", "completion_notes": "Bulb replaced and tested night glow."}
    )
    assert wo_res.status_code == 200
    assert wo_res.json()["status"] == "COMPLETED"

    # Verify Incident synced to RESOLVED
    inc_res2 = client.get(f"/api/v1/incidents/{inc_id}")
    assert inc_res2.json()["status"] == "RESOLVED"

    # 4. Citizen Reopens (Still not fixed) -> RESOLVED back to IN_PROGRESS
    reopen_res = client.post(
        f"/api/v1/incidents/{inc_id}/verify",
        data={"verified_fixed": "false", "citizen_notes": "Light is still flickering."}
    )
    assert reopen_res.status_code == 200
    assert reopen_res.json()["status"] == "IN_PROGRESS"

    # 5. Field crew fixes again & completes Work Order -> RESOLVED
    wo_res2 = client.patch(
        f"/api/v1/work-orders/{wo_id}/status",
        data={"status": "COMPLETED", "completion_notes": "Replaced entire electrical wiring fixture."}
    )
    assert wo_res2.status_code == 200

    # 6. Citizen Verifies Fixed -> RESOLVED to VERIFIED
    verify_res = client.post(
        f"/api/v1/incidents/{inc_id}/verify",
        data={"verified_fixed": "true", "citizen_notes": "Perfect! Fully illuminated now."}
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "VERIFIED"


def test_new_report_appears_in_incidents_list():
    res = client.post(
        "/api/v1/reports",
        data={
            "description": "Burst pipe water main leak at Market Road.",
            "latitude": 28.5200,
            "longitude": 77.1700,
            "address": "Market Road"
        }
    )
    assert res.status_code == 201
    inc_id = res.json()["incident_id"]

    inc_list = client.get("/api/v1/incidents").json()
    assert any(i["id"] == inc_id for i in inc_list)


def test_start_work_updates_incident_and_workorder_synchronization():
    res = client.post(
        "/api/v1/reports",
        data={
            "description": "Traffic signal light flickering at North Block junction.",
            "latitude": 28.5520,
            "longitude": 77.1990,
            "address": "North Block Junction"
        }
    )
    inc_id = res.json()["incident_id"]

    # Start Work via incident status endpoint
    st_res = client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "IN_PROGRESS", "notes": "Signal repair team dispatched."}
    )
    assert st_res.status_code == 200
    assert st_res.json()["status"] == "IN_PROGRESS"

    # Verify WorkOrder is synchronized to IN_PROGRESS
    wo_list = client.get("/api/v1/work-orders").json()
    target_wo = next(w for w in wo_list if w["incident_id"] == inc_id)
    assert target_wo["status"] == "IN_PROGRESS"


def test_reopen_returns_workorder_to_active_queue_without_duplicates():
    res = client.post(
        "/api/v1/reports",
        data={
            "description": "Open manhole drain cover near Hostel Block 3.",
            "latitude": 28.5450,
            "longitude": 77.1926,
            "address": "Hostel Block 3"
        }
    )
    inc_id = res.json()["incident_id"]

    # Move to IN_PROGRESS and then RESOLVED
    client.patch(f"/api/v1/incidents/{inc_id}/status", json={"status": "IN_PROGRESS"})
    wo_list_1 = client.get("/api/v1/work-orders").json()
    target_wo = next(w for w in wo_list_1 if w["incident_id"] == inc_id)
    initial_wo_count = len([w for w in wo_list_1 if w["incident_id"] == inc_id])
    assert initial_wo_count == 1

    client.patch(f"/api/v1/work-orders/{target_wo['id']}/status", data={"status": "COMPLETED", "completion_notes": "Cover replaced."})

    # Reopen via citizen verification
    reopen_res = client.post(
        f"/api/v1/incidents/{inc_id}/verify",
        data={"verified_fixed": "false", "citizen_notes": "Manhole cover is loose and noisy when vehicles cross."}
    )
    assert reopen_res.status_code == 200
    assert reopen_res.json()["status"] == "IN_PROGRESS"

    # Verify WorkOrder count remains exactly 1 (no duplicate WorkOrder created)
    wo_list_2 = client.get("/api/v1/work-orders").json()
    reopened_wos = [w for w in wo_list_2 if w["incident_id"] == inc_id]
    assert len(reopened_wos) == 1
    assert reopened_wos[0]["status"] == "IN_PROGRESS"


def test_terminal_verified_state_prohibits_further_transitions():
    res = client.post(
        "/api/v1/reports",
        data={
            "description": "Overflowing garbage dump near Bus Stop.",
            "latitude": 28.5450,
            "longitude": 77.1926,
            "address": "Bus Stop"
        }
    )
    inc_id = res.json()["incident_id"]

    client.patch(f"/api/v1/incidents/{inc_id}/status", json={"status": "IN_PROGRESS"})
    wo = next(w for w in client.get("/api/v1/work-orders").json() if w["incident_id"] == inc_id)
    client.patch(f"/api/v1/work-orders/{wo['id']}/status", data={"status": "COMPLETED", "completion_notes": "Cleared bins."})
    client.post(f"/api/v1/incidents/{inc_id}/verify", data={"verified_fixed": "true", "citizen_notes": "Cleaned up completely."})

    # Attempting to move VERIFIED back to IN_PROGRESS must fail with 400
    bad_transition = client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "IN_PROGRESS", "notes": "Illegal attempt"}
    )
    assert bad_transition.status_code == 400
    assert "Invalid status transition" in bad_transition.json()["detail"]
