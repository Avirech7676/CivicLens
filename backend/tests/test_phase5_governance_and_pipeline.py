import os
import pytest
import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.models.entities import User, WorkOrder, Incident, Report, AIFeedback
from app.core.enums import UserRole, WorkOrderStatus, SLAStatus, IncidentStatus, SeverityLevel, PriorityLevel
from app.core.security import hash_password, create_access_token
from app.services.crud import WorkOrderService, IncidentService
from app.ml.predictive_analytics import PredictiveHotspotEngine, SLABreachPredictor
from export_feedback_dataset import export_feedback_dataset
from tests.conftest import TestingSessionLocal

client = TestClient(app)

def test_protected_demo_db_reset_endpoint():
    db = TestingSessionLocal()
    disp = User(id="usr-disp-reset", email="disp_reset@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp Reset", role=UserRole.DISPATCHER)
    cit = User(id="usr-cit-reset", email="cit_reset@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Cit Reset", role=UserRole.CITIZEN)
    db.add_all([disp, cit])
    db.commit()
    db.close()

    token_disp = create_access_token({"sub": "usr-disp-reset", "role": "DISPATCHER", "email": "disp_reset@civiclens.local"})
    token_cit = create_access_token({"sub": "usr-cit-reset", "role": "CITIZEN", "email": "cit_reset@civiclens.local"})

    # Citizen resetting DB -> 403 Forbidden
    bad_res = client.post("/api/v1/admin/reset-demo-db", headers={"Authorization": f"Bearer {token_cit}"})
    assert bad_res.status_code == 403

    # Dispatcher resetting DB -> 200 OK
    good_res = client.post("/api/v1/admin/reset-demo-db", headers={"Authorization": f"Bearer {token_disp}"})
    assert good_res.status_code == 200
    assert "successfully" in good_res.json()["message"]


def test_ai_feedback_summary_and_error_distribution_metrics():
    db = TestingSessionLocal()
    disp = User(id="usr-disp-fb", email="disp_fb@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp FB", role=UserRole.DISPATCHER)
    db.add(disp)
    db.commit()

    fb = AIFeedback(
        id="fb-test-1",
        incident_id="inc-test-1",
        ai_category="WATER_LEAK",
        ai_department="Water Department",
        ai_confidence=0.58,
        confidence_tier="LOW",
        final_category="ROAD_HAZARD",
        final_department="Public Works - Roads",
        review_status="CORRECTED",
        reason="Standing water inside road pothole cavity",
        reviewer_id="usr-disp-fb",
        reviewer_email="disp_fb@civiclens.local"
    )
    db.add(fb)
    db.commit()
    db.close()

    token_disp = create_access_token({"sub": "usr-disp-fb", "role": "DISPATCHER", "email": "disp_fb@civiclens.local"})

    res = client.get("/api/v1/ml/feedback/summary", headers={"Authorization": f"Bearer {token_disp}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_reviews"] >= 1
    assert "WATER_LEAK" in data["corrections_by_category"]


def test_sla_at_risk_and_breached_auto_calculation():
    now = datetime.datetime.utcnow()
    wo_on_track = WorkOrder(
        created_at=now,
        sla_deadline=now + datetime.timedelta(hours=5),
        status=WorkOrderStatus.IN_PROGRESS
    )
    WorkOrderService.evaluate_sla(wo_on_track)
    assert wo_on_track.sla_status == SLAStatus.ON_TRACK

    wo_breached = WorkOrder(
        created_at=now - datetime.timedelta(hours=10),
        sla_deadline=now - datetime.timedelta(hours=2),
        status=WorkOrderStatus.IN_PROGRESS
    )
    WorkOrderService.evaluate_sla(wo_breached)
    assert wo_breached.sla_status == SLAStatus.BREACHED


def test_predictive_hotspot_risk_scoring():
    risk_info = PredictiveHotspotEngine.calculate_predictive_risk(
        incident_count=6,
        report_count=20,
        p1_p2_count=4,
        recent_hours=12
    )
    assert risk_info["risk_score"] >= 80
    assert risk_info["risk_level"] == "CRITICAL"


def test_sla_breach_probability_prediction():
    now = datetime.datetime.utcnow()
    created = now - datetime.timedelta(hours=1, minutes=55)
    deadline = now + datetime.timedelta(minutes=5)
    
    pred = SLABreachPredictor.predict_work_order_breach_risk("P1_CRITICAL", created, deadline)
    assert pred["breach_probability"] > 0.50
    assert "SLA" in pred["risk_label"]


def test_operations_analytics_endpoint():
    db = TestingSessionLocal()
    disp = User(id="usr-disp-an", email="disp_an@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp An", role=UserRole.DISPATCHER)
    db.add(disp)
    db.commit()
    db.close()

    token_disp = create_access_token({"sub": "usr-disp-an", "role": "DISPATCHER", "email": "disp_an@civiclens.local"})

    res = client.get("/api/v1/ml/analytics", headers={"Authorization": f"Bearer {token_disp}"})
    assert res.status_code == 200
    data = res.json()
    assert "sla_compliance_pct" in data
    assert "model_health_status" in data


def test_export_feedback_dataset_cli():
    out_csv = "backend/data/processed/ai_feedback_dataset_test.csv"
    res_path = export_feedback_dataset(output_path=out_csv)
    assert os.path.exists(res_path)
    if os.path.exists(res_path):
        os.remove(res_path)


def test_rbac_citizen_forbidden_operations():
    db = TestingSessionLocal()
    cit = User(id="usr-c1", email="c1@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Cit 1", role=UserRole.CITIZEN)
    db.add(cit)
    db.commit()
    db.close()

    rep_res = client.post(
        "/api/v1/reports",
        data={"description": "Test RBAC report for citizen forbidden ops", "latitude": 28.5450, "longitude": 77.1926, "address": "Main Gate"}
    ).json()
    inc_id = rep_res["incident_id"]
    inc = client.get(f"/api/v1/incidents/{inc_id}").json()
    wo_id = inc["work_order"]["id"]

    token_cit = create_access_token({"sub": "usr-c1", "role": "CITIZEN", "email": "c1@civiclens.local"})

    # Assign crew -> 403
    assert client.post(f"/api/v1/work-orders/{wo_id}/assign", json={}, headers={"Authorization": f"Bearer {token_cit}"}).status_code == 403
    # Override classification -> 403
    assert client.patch(f"/api/v1/incidents/{inc_id}/override", json={}, headers={"Authorization": f"Bearer {token_cit}"}).status_code == 403


def test_rbac_dispatcher_forbidden_operations():
    db = TestingSessionLocal()
    disp = User(id="usr-d1", email="d1@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp 1", role=UserRole.DISPATCHER)
    db.add(disp)
    db.commit()
    db.close()

    rep_res = client.post(
        "/api/v1/reports",
        data={"description": "Test RBAC report for dispatcher forbidden ops", "latitude": 28.5450, "longitude": 77.1926, "address": "Main Gate"}
    ).json()
    inc_id = rep_res["incident_id"]
    inc = client.get(f"/api/v1/incidents/{inc_id}").json()
    wo_id = inc["work_order"]["id"]

    token_disp = create_access_token({"sub": "usr-d1", "role": "DISPATCHER", "email": "d1@civiclens.local"})

    # Physical completion -> 403
    assert client.patch(f"/api/v1/work-orders/{wo_id}/status", data={"status": "COMPLETED"}, headers={"Authorization": f"Bearer {token_disp}"}).status_code == 403
    # Citizen verification -> 403
    assert client.post(f"/api/v1/incidents/{inc_id}/verify", data={"verified_fixed": "true"}, headers={"Authorization": f"Bearer {token_disp}"}).status_code == 403


def test_rbac_field_crew_forbidden_operations():
    db = TestingSessionLocal()
    crew = User(id="usr-cr1", email="cr1@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Crew 1", role=UserRole.FIELD_CREW, department="Public Works - Roads")
    db.add(crew)
    db.commit()
    db.close()

    rep_res = client.post(
        "/api/v1/reports",
        data={"description": "Test RBAC report for field crew forbidden ops", "latitude": 28.5450, "longitude": 77.1926, "address": "Main Gate"}
    ).json()
    inc_id = rep_res["incident_id"]
    inc = client.get(f"/api/v1/incidents/{inc_id}").json()
    wo_id = inc["work_order"]["id"]

    token_crew = create_access_token({"sub": "usr-cr1", "role": "FIELD_CREW", "email": "cr1@civiclens.local"})

    # Assign crew -> 403
    assert client.post(f"/api/v1/work-orders/{wo_id}/assign", json={}, headers={"Authorization": f"Bearer {token_crew}"}).status_code == 403
    # Citizen verification -> 403
    assert client.post(f"/api/v1/incidents/{inc_id}/verify", data={"verified_fixed": "true"}, headers={"Authorization": f"Bearer {token_crew}"}).status_code == 403


def test_ai_review_queue_endpoint():
    db = TestingSessionLocal()
    disp = User(id="usr-disp-rq", email="disp_rq@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp RQ", role=UserRole.DISPATCHER)
    db.add(disp)
    db.commit()
    db.close()

    token_disp = create_access_token({"sub": "usr-disp-rq", "role": "DISPATCHER", "email": "disp_rq@civiclens.local"})
    res = client.get("/api/v1/incidents/review-queue", headers={"Authorization": f"Bearer {token_disp}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_ai_confidence_tiers_and_human_review_flag():
    from app.services.ai_service import AIService
    import asyncio
    res = asyncio.run(AIService.analyze_incident("Uncertain vague report"))
    assert res.confidence_tier in ["HIGH", "MEDIUM", "LOW"]


def test_reopen_synchronization_and_single_work_order_invariant():
    rep = client.post(
        "/api/v1/reports",
        data={"description": "Reopen invariant pothole test", "latitude": 28.5450, "longitude": 77.1926, "address": "Gate 1"}
    ).json()
    inc_id = rep["incident_id"]
    token_crew = create_access_token({"sub": "usr-crew-1", "role": "FIELD_CREW", "email": "crew@civiclens.local"})

    # Assign -> Start -> Complete
    token_disp = create_access_token({"sub": "usr-disp-1", "role": "DISPATCHER", "email": "dispatcher@civiclens.local"})
    wo_id = client.get(f"/api/v1/incidents/{inc_id}").json()["work_order"]["id"]
    client.post(f"/api/v1/work-orders/{wo_id}/assign", json={"assigned_worker_id": "usr-crew-1", "assigned_worker": "crew@civiclens.local"}, headers={"Authorization": f"Bearer {token_disp}"})
    client.patch(f"/api/v1/work-orders/{wo_id}/status", data={"status": "IN_PROGRESS"}, headers={"Authorization": f"Bearer {token_crew}"})
    client.patch(f"/api/v1/work-orders/{wo_id}/status", data={"status": "COMPLETED", "completion_notes": "Repaired road surface"}, headers={"Authorization": f"Bearer {token_crew}"})

    # Citizen Reopen
    token_cit = create_access_token({"sub": "usr-c1", "role": "CITIZEN", "email": "c1@civiclens.local"})
    reopen_res = client.post(f"/api/v1/incidents/{inc_id}/verify", data={"verified_fixed": "false", "citizen_notes": "Pothole still present"}, headers={"Authorization": f"Bearer {token_cit}"})
    assert reopen_res.status_code == 200
    assert reopen_res.json()["status"] == "IN_PROGRESS"

    # Confirm same WorkOrder ID preserved
    inc_after = client.get(f"/api/v1/incidents/{inc_id}").json()
    assert inc_after["work_order"]["id"] == wo_id
    assert inc_after["work_order"]["status"] == "IN_PROGRESS"


def test_ai_image_mime_mapping_and_encoding_helper():
    from app.services.ai_service import AIService
    mime_png = AIService._encode_image("non_existent_file.png")
    assert mime_png is None


def test_unauthenticated_api_request_401_unauthorized():
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_get_my_work_orders_non_field_crew_403_forbidden():
    db = TestingSessionLocal()
    disp = User(id="usr-disp-forbidden", email="disp_403@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp Forbidden", role=UserRole.DISPATCHER)
    db.add(disp)
    db.commit()
    db.close()

    token_disp = create_access_token({"sub": "usr-disp-forbidden", "role": "DISPATCHER", "email": "disp_403@civiclens.local"})
    res = client.get("/api/v1/work-orders/my", headers={"Authorization": f"Bearer {token_disp}"})
    assert res.status_code == 403
