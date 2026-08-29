import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db, engine as prod_engine

# Override get_db to use prod_engine
def override_get_db():
    db = sessionmaker(bind=prod_engine)()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=prod_engine)
    Base.metadata.create_all(bind=prod_engine)
    yield
    Base.metadata.drop_all(bind=prod_engine)

client = TestClient(app)

def test_closed_loop_resolution_and_citizen_verification_flow():
    # 1. Create Report -> Incident #1 created
    res1 = client.post(
        "/api/v1/reports",
        data={
            "description": "Unlit streetlight fixture near Gate 1.",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "Gate 1 Parking Lot"
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

    # 2. Dispatcher Starts Work -> SUBMITTED to IN_PROGRESS
    status_res = client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "IN_PROGRESS", "notes": "Technician dispatched to replace bulb."}
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "IN_PROGRESS"

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
