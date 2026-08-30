import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.entities import Incident, Report, WorkOrder, Notification, StatusLog
from tests.conftest import TestingSessionLocal, test_engine

client = TestClient(app)

def test_duplicate_detection_end_to_end_flow():
    # 1. First report -> Creates Incident #1 and WorkOrder #1
    res1 = client.post(
        "/api/v1/reports",
        data={
            "description": "Large dangerous pothole near Gate 1 causing tire damage.",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "100 Main Gate"
        }
    )
    assert res1.status_code == 201
    rep1_data = res1.json()
    inc1_id = rep1_data["incident_id"]
    assert inc1_id is not None
    assert rep1_data["duplicate_info"]["is_duplicate"] is False

    # Check database: Exactly 1 Incident, 1 Report, 1 WorkOrder
    db = sessionmaker(bind=test_engine)()
    assert db.query(Incident).count() == 1
    assert db.query(Report).count() == 1
    assert db.query(WorkOrder).count() == 1
    db.close()

    # 2. Second report (Identical issue + location) -> Aggregates into Incident #1, NO new WorkOrder
    res2 = client.post(
        "/api/v1/reports",
        data={
            "description": "Deep road damage and pothole right at Gate 1 main crosswalk.",
            "latitude": 37.77495,
            "longitude": -122.41945,
            "address": "Gate 1 Main Entrance"
        }
    )
    assert res2.status_code == 201
    rep2_data = res2.json()
    
    # Verify report attached to same existing Incident ID
    assert rep2_data["incident_id"] == inc1_id
    assert rep2_data["duplicate_info"]["is_duplicate"] is True
    assert rep2_data["duplicate_info"]["matched_incident_id"] == inc1_id

    # Verify database state after duplicate submission:
    # EXACTLY 1 Incident record
    # EXACTLY 2 Report records attached to Incident #1
    # EXACTLY 1 WorkOrder record
    db = sessionmaker(bind=test_engine)()
    assert db.query(Incident).count() == 1
    assert db.query(Report).count() == 2
    assert db.query(WorkOrder).count() == 1
    
    # Inspect Incident reports relationship
    inc_obj = db.query(Incident).filter(Incident.id == inc1_id).first()
    assert len(inc_obj.reports) == 2
    db.close()

    # 3. Third report (Unrelated issue - Streetlight) -> Creates new Incident #2 and WorkOrder #2
    res3 = client.post(
        "/api/v1/reports",
        data={
            "description": "Unlit streetlight fixture dark at night near Gate 1.",
            "latitude": 37.7750,
            "longitude": -122.4195,
            "address": "Gate 1 Parking Lot"
        }
    )
    assert res3.status_code == 201
    rep3_data = res3.json()
    assert rep3_data["incident_id"] != inc1_id
    assert rep3_data["duplicate_info"]["is_duplicate"] is False

    db = sessionmaker(bind=test_engine)()
    assert db.query(Incident).count() == 2
    assert db.query(Report).count() == 3
    assert db.query(WorkOrder).count() == 2
    db.close()
