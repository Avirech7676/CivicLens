import pytest
import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import Base
from app.models.entities import User, WorkOrder, Incident
from app.core.enums import UserRole, WorkOrderStatus, SLAStatus, PriorityLevel
from app.core.security import hash_password, create_access_token
from app.services.crud import WorkOrderService, IncidentService
from tests.conftest import TestingSessionLocal, test_engine

client = TestClient(app)

def test_auth_login_and_me_endpoint():
    # 1. Seed demo user in test DB
    db = TestingSessionLocal()
    user = User(
        id="usr-test-dispatcher",
        email="test_dispatcher@civiclens.local",
        hashed_password=hash_password("Pass123!"),
        full_name="Test Dispatcher",
        role=UserRole.DISPATCHER
    )
    db.add(user)
    db.commit()
    db.close()

    # 2. Login success
    res = client.post("/api/v1/auth/login", json={
        "email": "test_dispatcher@civiclens.local",
        "password": "Pass123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "DISPATCHER"
    token = data["access_token"]

    # 3. GET /auth/me with valid Bearer token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "test_dispatcher@civiclens.local"

    # 4. GET /auth/me without token -> 401
    bad_me = client.get("/api/v1/auth/me")
    assert bad_me.status_code == 401


def test_work_order_crew_assignment_and_sla():
    # 1. Create a report & incident
    rep_res = client.post(
        "/api/v1/reports",
        data={
            "description": "Severe road cavity near Gate 1 Entrance.",
            "latitude": 28.5450,
            "longitude": 77.1926,
            "address": "Gate 1 Entrance"
        }
    )
    assert rep_res.status_code == 201
    inc_id = rep_res.json()["incident_id"]

    inc = client.get(f"/api/v1/incidents/{inc_id}").json()
    wo_id = inc["work_order"]["id"]

    # 2. Assign crew to WorkOrder
    assign_res = client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        json={
            "assigned_team": "Road Maintenance Crew Alpha",
            "assigned_worker": "Ramesh Kumar"
        }
    )
    assert assign_res.status_code == 200
    wo_data = assign_res.json()
    assert wo_data["assigned_team"] == "Road Maintenance Crew Alpha"
    assert wo_data["assigned_worker"] == "Ramesh Kumar"
    assert wo_data["status"] in ["PENDING", "ASSIGNED"]

    # 3. Test SLA Durations
    p1_hours = WorkOrderService.get_sla_duration_hours("P1_CRITICAL")
    p2_hours = WorkOrderService.get_sla_duration_hours("P2_HIGH")
    p3_hours = WorkOrderService.get_sla_duration_hours("P3_MEDIUM")
    p4_hours = WorkOrderService.get_sla_duration_hours("P4_LOW")

    assert p1_hours == 2
    assert p2_hours == 8
    assert p3_hours == 24
    assert p4_hours == 72


def test_rbac_strict_role_separation_enforcement():
    # 1. Seed Citizen, Dispatcher, and Field Crew users
    db = TestingSessionLocal()
    citizen = User(id="usr-c1", email="c1@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Citizen 1", role=UserRole.CITIZEN)
    dispatcher = User(id="usr-d1", email="d1@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Dispatcher 1", role=UserRole.DISPATCHER)
    crew_roads = User(id="usr-cr1", email="cr1@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Crew Roads", role=UserRole.FIELD_CREW, department="Public Works - Roads")
    crew_water = User(id="usr-cw1", email="cw1@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Crew Water", role=UserRole.FIELD_CREW, department="Water Department")
    db.add_all([citizen, dispatcher, crew_roads, crew_water])
    db.commit()
    db.close()

    token_citizen = create_access_token({"sub": "usr-c1", "role": "CITIZEN", "email": "c1@civiclens.local"})
    token_dispatcher = create_access_token({"sub": "usr-d1", "role": "DISPATCHER", "email": "d1@civiclens.local"})
    token_crew_roads = create_access_token({"sub": "usr-cr1", "role": "FIELD_CREW", "email": "cr1@civiclens.local"})
    token_crew_water = create_access_token({"sub": "usr-cw1", "role": "FIELD_CREW", "email": "cw1@civiclens.local"})

    # 2. Create a report (Roads)
    rep_res = client.post(
        "/api/v1/reports",
        data={"description": "Deep road crater at Main Gate", "latitude": 28.5450, "longitude": 77.1926, "address": "Main Gate"},
        headers={"Authorization": f"Bearer {token_citizen}"}
    )
    inc_id = rep_res.json()["incident_id"]
    inc = client.get(f"/api/v1/incidents/{inc_id}").json()
    wo_id = inc["work_order"]["id"]

    # 3. Citizen trying to assign crew -> 403 Forbidden
    bad_assign = client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        json={"assigned_team": "Hacker Team", "assigned_worker": "Bad Actor"},
        headers={"Authorization": f"Bearer {token_citizen}"}
    )
    assert bad_assign.status_code == 403

    # 4. Dispatcher assigns crew -> 200 OK
    good_assign = client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        json={"assigned_team": "Road Maintenance Crew Alpha", "assigned_worker": "cr1@civiclens.local", "assigned_worker_id": "usr-cr1"},
        headers={"Authorization": f"Bearer {token_dispatcher}"}
    )
    assert good_assign.status_code == 200

    # 5. Dispatcher attempting physical completion -> 403 Forbidden
    bad_disp_complete = client.patch(
        f"/api/v1/work-orders/{wo_id}/status",
        data={"status": "COMPLETED", "completion_notes": "Dispatcher trying to complete"},
        headers={"Authorization": f"Bearer {token_dispatcher}"}
    )
    assert bad_disp_complete.status_code == 403

    # 6. Crew Water (wrong department) trying to update Roads WorkOrder -> 403 Forbidden
    bad_crew_update = client.patch(
        f"/api/v1/work-orders/{wo_id}/status",
        data={"status": "IN_PROGRESS"},
        headers={"Authorization": f"Bearer {token_crew_water}"}
    )
    assert bad_crew_update.status_code == 403

    # 7. Crew Roads (correct department) starting work -> 200 OK
    good_start = client.patch(
        f"/api/v1/work-orders/{wo_id}/status",
        data={"status": "IN_PROGRESS"},
        headers={"Authorization": f"Bearer {token_crew_roads}"}
    )
    assert good_start.status_code == 200
    assert good_start.json()["status"] == "IN_PROGRESS"

    # 8. Crew Roads completing work -> 200 OK
    good_complete = client.patch(
        f"/api/v1/work-orders/{wo_id}/status",
        data={"status": "COMPLETED", "completion_notes": "Asphalt patched and compacted."},
        headers={"Authorization": f"Bearer {token_crew_roads}"}
    )
    assert good_complete.status_code == 200
    assert good_complete.json()["status"] == "COMPLETED"

    # 9. Crew and Dispatcher trying to perform citizen verification -> 403 Forbidden
    bad_crew_verify = client.post(
        f"/api/v1/incidents/{inc_id}/verify",
        data={"verified_fixed": "true", "citizen_notes": "Crew trying to verify"},
        headers={"Authorization": f"Bearer {token_crew_roads}"}
    )
    assert bad_crew_verify.status_code == 403

    bad_disp_verify = client.post(
        f"/api/v1/incidents/{inc_id}/verify",
        data={"verified_fixed": "true", "citizen_notes": "Dispatcher trying to verify"},
        headers={"Authorization": f"Bearer {token_dispatcher}"}
    )
    assert bad_disp_verify.status_code == 403


def test_dispatcher_human_override_endpoint():
    db = TestingSessionLocal()
    dispatcher = User(id="usr-disp-ov", email="disp_ov@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp Ov", role=UserRole.DISPATCHER)
    citizen = User(id="usr-cit-ov", email="cit_ov@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Cit Ov", role=UserRole.CITIZEN)
    db.add_all([dispatcher, citizen])
    db.commit()
    db.close()

    token_disp = create_access_token({"sub": "usr-disp-ov", "role": "DISPATCHER", "email": "disp_ov@civiclens.local"})
    token_cit = create_access_token({"sub": "usr-cit-ov", "role": "CITIZEN", "email": "cit_ov@civiclens.local"})

    rep = client.post(
        "/api/v1/reports",
        data={"description": "Misclassified streetlight issue at Gate 1", "latitude": 28.5450, "longitude": 77.1926, "address": "Gate 1"}
    ).json()
    inc_id = rep["incident_id"]

    # Citizen trying to override -> 403
    bad_ov = client.patch(
        f"/api/v1/incidents/{inc_id}/override",
        json={"category": "STREETLIGHT", "assigned_department": "Electrical Maintenance", "reason": "Hacker override"},
        headers={"Authorization": f"Bearer {token_cit}"}
    )
    assert bad_ov.status_code == 403

    # Dispatcher override -> 200
    good_ov = client.patch(
        f"/api/v1/incidents/{inc_id}/override",
        json={"category": "STREETLIGHT", "assigned_department": "Electrical Maintenance", "reason": "Visual inspection confirmed luminaire failure"},
        headers={"Authorization": f"Bearer {token_disp}"}
    )
    assert good_ov.status_code == 200
    inc_data = good_ov.json()
    assert inc_data["category"] == "STREETLIGHT"
    assert inc_data["assigned_department"] == "Electrical Maintenance"


def test_complete_rbac_matrix_authorization():
    db = TestingSessionLocal()
    disp = User(id="usr-disp-matrix", email="disp_matrix@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp Matrix", role=UserRole.DISPATCHER)
    cit = User(id="usr-cit-matrix", email="cit_matrix@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Cit Matrix", role=UserRole.CITIZEN)
    crew = User(id="usr-cr-matrix", email="cr_matrix@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Crew Matrix", role=UserRole.FIELD_CREW, department="Public Works - Roads")
    db.add_all([disp, cit, crew])
    db.commit()
    db.close()

    token_disp = create_access_token({"sub": "usr-disp-matrix", "role": "DISPATCHER", "email": "disp_matrix@civiclens.local"})
    token_cit = create_access_token({"sub": "usr-cit-matrix", "role": "CITIZEN", "email": "cit_matrix@civiclens.local"})
    token_crew = create_access_token({"sub": "usr-cr-matrix", "role": "FIELD_CREW", "email": "cr_matrix@civiclens.local"})

    # 1. GET /ml/analytics
    assert client.get("/api/v1/ml/analytics", headers={"Authorization": f"Bearer {token_disp}"}).status_code == 200
    assert client.get("/api/v1/ml/analytics", headers={"Authorization": f"Bearer {token_cit}"}).status_code == 403
    assert client.get("/api/v1/ml/analytics", headers={"Authorization": f"Bearer {token_crew}"}).status_code == 403

    # 2. GET /work-orders/my
    assert client.get("/api/v1/work-orders/my", headers={"Authorization": f"Bearer {token_crew}"}).status_code == 200
    assert client.get("/api/v1/work-orders/my", headers={"Authorization": f"Bearer {token_disp}"}).status_code == 403
    assert client.get("/api/v1/work-orders/my", headers={"Authorization": f"Bearer {token_cit}"}).status_code == 403


def test_two_worker_isolation_and_my_work_orders_endpoint():
    # 1. Seed two distinct field crew workers in same department (Roads)
    db = TestingSessionLocal()
    crew_a = User(id="usr-ca", email="crew_a@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Worker Alpha", role=UserRole.FIELD_CREW, department="Public Works - Roads")
    crew_b = User(id="usr-cb", email="crew_b@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Worker Beta", role=UserRole.FIELD_CREW, department="Public Works - Roads")
    dispatcher = User(id="usr-disp-iso", email="disp_iso@civiclens.local", hashed_password=hash_password("Pass123!"), full_name="Disp Iso", role=UserRole.DISPATCHER)
    db.add_all([crew_a, crew_b, dispatcher])
    db.commit()
    db.close()

    token_a = create_access_token({"sub": "usr-ca", "role": "FIELD_CREW", "email": "crew_a@civiclens.local"})
    token_b = create_access_token({"sub": "usr-cb", "role": "FIELD_CREW", "email": "crew_b@civiclens.local"})
    token_disp = create_access_token({"sub": "usr-disp-iso", "role": "DISPATCHER", "email": "disp_iso@civiclens.local"})

    # 2. Create two separate road reports
    rep1 = client.post("/api/v1/reports", data={"description": "Pothole A at North Gate", "latitude": 28.5450, "longitude": 77.1926, "address": "North Gate"}).json()
    rep2 = client.post("/api/v1/reports", data={"description": "Pothole B at South Gate", "latitude": 28.5100, "longitude": 77.2150, "address": "South Gate"}).json()

    wo_a_id = client.get(f"/api/v1/incidents/{rep1['incident_id']}").json()["work_order"]["id"]
    wo_b_id = client.get(f"/api/v1/incidents/{rep2['incident_id']}").json()["work_order"]["id"]

    # 3. Assign WorkOrder A -> Crew A, WorkOrder B -> Crew B
    client.post(f"/api/v1/work-orders/{wo_a_id}/assign", json={"assigned_worker_id": "usr-ca", "assigned_worker": "crew_a@civiclens.local"}, headers={"Authorization": f"Bearer {token_disp}"})
    client.post(f"/api/v1/work-orders/{wo_b_id}/assign", json={"assigned_worker_id": "usr-cb", "assigned_worker": "crew_b@civiclens.local"}, headers={"Authorization": f"Bearer {token_disp}"})

    # 4. Query /work-orders/my as Crew A -> Sees WorkOrder A, NOT WorkOrder B
    my_a = client.get("/api/v1/work-orders/my", headers={"Authorization": f"Bearer {token_a}"}).json()
    my_a_ids = [w["id"] for w in my_a]
    assert wo_a_id in my_a_ids
    assert wo_b_id not in my_a_ids

    # 5. Query /work-orders/my as Crew B -> Sees WorkOrder B, NOT WorkOrder A
    my_b = client.get("/api/v1/work-orders/my", headers={"Authorization": f"Bearer {token_b}"}).json()
    my_b_ids = [w["id"] for w in my_b]
    assert wo_b_id in my_b_ids
    assert wo_a_id not in my_b_ids
