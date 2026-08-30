import pytest
import asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.data.nyc311.schemas import NYC311Record, IngestionStats
from app.data.nyc311.taxonomy import map_nyc311_to_civiclens
from app.data.nyc311.preprocess import validate_and_parse_record, preprocess_nyc311_batch
from app.services.ai_service import AIService
from app.core.enums import IncidentCategory, UserRole
from app.models.entities import User
from app.core.security import hash_password, create_access_token
from app.ml.evaluator import ClassificationEvaluator
from app.ml.sla_analytics import HistoricalSLAAnalytics
from app.ml.historical_hotspots import HistoricalHotspotAnalytics
from tests.conftest import TestingSessionLocal

client = TestClient(app)

def test_nyc311_taxonomy_mapping():
    # Pothole
    cat1, dept1 = map_nyc311_to_civiclens("Pothole", "Pothole on roadway")
    assert cat1 == IncidentCategory.ROAD_HAZARD
    assert dept1 == "Public Works - Roads"

    # Water Main / Pipe Leak
    cat2, dept2 = map_nyc311_to_civiclens("Water System", "Burst main spraying water")
    assert cat2 == IncidentCategory.WATER_LEAK
    assert dept2 == "Water Department"

    # Catch Basin / Sewer
    cat3, dept3 = map_nyc311_to_civiclens("Sewer", "Clogged catch basin flooding corner")
    assert cat3 == IncidentCategory.DRAINAGE
    assert dept3 == "Drainage & Sewer"

def test_nyc311_record_preprocessing_and_out_of_bounds_coords():
    raw_valid = {
        "unique_key": "1001",
        "complaint_type": "Pothole",
        "descriptor": "Large road crater",
        "latitude": "40.7128",
        "longitude": "-74.0060"
    }
    rec, err = validate_and_parse_record(raw_valid)
    assert err is None
    assert rec.latitude == 40.7128
    assert rec.longitude == -74.0060

    # Out of bounds coordinates (e.g. San Francisco coords in NYC stream)
    raw_invalid = {
        "unique_key": "1002",
        "complaint_type": "Pothole",
        "latitude": "37.7749",
        "longitude": "-122.4194"
    }
    rec_inv, err_inv = validate_and_parse_record(raw_invalid)
    assert rec_inv.latitude is None # Reset to None due to out of bounds

def test_ml_classification_evaluator_baseline():
    dataset = [
        {"nyc_complaint_type": "Pothole", "nyc_descriptor": "Deep cavity", "civiclens_category": "ROAD_HAZARD"},
        {"nyc_complaint_type": "Water System", "nyc_descriptor": "Burst pipe", "civiclens_category": "WATER_LEAK"},
        {"nyc_complaint_type": "Sewer", "nyc_descriptor": "Clogged catch basin", "civiclens_category": "DRAINAGE"}
    ]
    metrics = ClassificationEvaluator.evaluate_taxonomy_baseline(dataset)
    assert metrics["accuracy"] == 1.0
    assert metrics["total_samples"] == 3

def test_historical_sla_analytics():
    dataset = [
        {
            "civiclens_category": "ROAD_HAZARD",
            "created_date": "2026-01-01T10:00:00Z",
            "closed_date": "2026-01-01T14:00:00Z" # 4 hours
        },
        {
            "civiclens_category": "ROAD_HAZARD",
            "created_date": "2026-01-02T10:00:00Z",
            "closed_date": "2026-01-02T18:00:00Z" # 8 hours
        }
    ]
    insights = HistoricalSLAAnalytics.calculate_category_sla_insights(dataset)
    assert "ROAD_HAZARD" in insights
    assert insights["ROAD_HAZARD"]["median_hours"] == 6.0

def test_cross_department_crew_assignment_rejection():
    # 1. Seed users
    db = TestingSessionLocal()
    dispatcher = User(id="usr-disp-cross", email="disp_cross@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp Cross", role=UserRole.DISPATCHER)
    water_worker = User(id="usr-water-1", email="water_worker@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Water Worker", role=UserRole.FIELD_CREW, department="Water Department")
    db.add_all([dispatcher, water_worker])
    db.commit()
    db.close()

    token_disp = create_access_token({"sub": "usr-disp-cross", "role": "DISPATCHER", "email": "disp_cross@civiclens.local"})

    # 2. Create a Roads report
    rep_res = client.post(
        "/api/v1/reports",
        data={"description": "Deep road crater at Main Gate", "latitude": 28.5450, "longitude": 77.1926, "address": "Main Gate"}
    )
    inc_id = rep_res.json()["incident_id"]
    inc = client.get(f"/api/v1/incidents/{inc_id}").json()
    wo_id = inc["work_order"]["id"]

    # 3. Attempting to assign Water Department worker to Roads WorkOrder MUST be rejected with HTTP 403
    bad_cross_assign = client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        json={"assigned_team": "Water Crew", "assigned_worker": "water_worker@civiclens.local"},
        headers={"Authorization": f"Bearer {token_disp}"}
    )
    assert bad_cross_assign.status_code == 403
    assert "Cross-department assignment forbidden" in bad_cross_assign.json()["detail"]
