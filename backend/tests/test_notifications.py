import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db, engine as prod_engine
from app.core.config import settings
from app.models.entities import Incident, Report, WorkOrder, Notification, StatusLog
from app.core.enums import IncidentStatus, WorkOrderStatus, SeverityLevel, PriorityLevel
from app.services.notification_service import NotificationService

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=prod_engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=prod_engine)
    Base.metadata.create_all(bind=prod_engine)
    yield
    Base.metadata.drop_all(bind=prod_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_1_report_received_notification():
    db = TestingSessionLocal()
    rep = Report(id="rep-101", description="Broken curb near park", citizen_id="citizen-101")
    db.add(rep)
    db.commit()

    notif = NotificationService.notify_report_received(db, rep)
    assert notif is not None
    assert notif.event_type == "REPORT_RECEIVED"
    assert notif.recipient_type == "CITIZEN"
    assert notif.provider == "DEMO"
    assert "received" in notif.message.lower()
    db.close()


def test_2_report_consolidated_notification():
    db = TestingSessionLocal()
    inc = Incident(id="inc-201", title="Water Main Burst", description="Flooding near school", category="WATER_LEAK")
    rep = Report(id="rep-102", description="Water everywhere", citizen_id="citizen-102", incident_id=inc.id)
    db.add_all([inc, rep])
    db.commit()

    notif = NotificationService.notify_report_consolidated(db, rep, inc)
    assert notif is not None
    assert notif.event_type == "REPORT_CONSOLIDATED"
    assert notif.recipient_type == "CITIZEN"
    assert "linked" in notif.message.lower()
    db.close()


def test_3_high_priority_incident_alert():
    db = TestingSessionLocal()
    inc = Incident(
        id="inc-301",
        title="P1 Severe Gas Leak",
        description="Hazardous gas smell near station",
        priority_score=92,
        priority_level=PriorityLevel.P1_CRITICAL,
        assigned_department="Public Safety & Utilities"
    )
    db.add(inc)
    db.commit()

    notif = NotificationService.notify_incident_priority_alert(db, inc, report_count=3)
    assert notif is not None
    assert notif.event_type == "INCIDENT_PRIORITY_ALERT"
    assert notif.recipient_type == "DISPATCHER"
    assert "P1 ALERT" in notif.title
    assert "92/100" in notif.message
    db.close()


def test_4_department_assignment_notification():
    db = TestingSessionLocal()
    inc = Incident(id="inc-401", title="Power Pole Leaning", description="Hazardous angle", assigned_department="Electrical & Energy Systems")
    db.add(inc)
    db.commit()

    notif = NotificationService.notify_department_assigned(db, inc)
    assert notif is not None
    assert notif.event_type == "DEPARTMENT_ASSIGNED"
    assert "Electrical & Energy Systems" in notif.message
    db.close()


def test_5_work_order_assignment_notification():
    db = TestingSessionLocal()
    inc = Incident(id="inc-501", title="Traffic Signal Glitch", description="Signal stuck green")
    wo = WorkOrder(id="wo-501", incident_id=inc.id, assigned_department="Traffic & Transportation Operations", recommended_action="Reset controller unit")
    db.add_all([inc, wo])
    db.commit()

    notif = NotificationService.notify_work_order_assigned(db, wo, inc)
    assert notif is not None
    assert notif.event_type == "WORK_ORDER_ASSIGNED"
    assert notif.recipient_type == "FIELD_TEAM"
    assert "Traffic & Transportation Operations" in notif.message
    db.close()


def test_6_work_started_notification():
    db = TestingSessionLocal()
    inc = Incident(id="inc-601", title="Pothole Repair", description="2ft hole")
    wo = WorkOrder(id="wo-601", incident_id=inc.id, assigned_department="Roads & Infrastructure", recommended_action="Cold patch")
    db.add_all([inc, wo])
    db.commit()

    notif = NotificationService.notify_work_started(db, wo, inc)
    assert notif is not None
    assert notif.event_type == "WORK_STARTED"
    assert "begun repair work" in notif.message
    db.close()


def test_7_resolution_notification_and_8_verification_request():
    db = TestingSessionLocal()
    inc = Incident(id="inc-701", title="Streetlight Fixed", description="Bulb unlit", status=IncidentStatus.RESOLVED)
    wo = WorkOrder(id="wo-701", incident_id=inc.id, assigned_department="Electrical", recommended_action="Replace bulb", completion_notes="LED replaced")
    db.add_all([inc, wo])
    db.commit()

    notif = NotificationService.notify_incident_resolved(db, inc, wo)
    assert notif is not None
    assert notif.event_type == "VERIFICATION_REQUIRED"
    assert "verify" in notif.message.lower()
    db.close()


def test_9_citizen_verification_notification():
    db = TestingSessionLocal()
    inc = Incident(id="inc-901", title="Drain Cleared", description="Clogged drain", status=IncidentStatus.VERIFIED)
    db.add(inc)
    db.commit()

    notif = NotificationService.notify_incident_verified(db, inc)
    assert notif is not None
    assert notif.event_type == "INCIDENT_VERIFIED"
    assert "closed" in notif.message.lower()
    db.close()


def test_10_citizen_reopening_notification():
    db = TestingSessionLocal()
    inc = Incident(id="inc-1001", title="Drain Still Overflowing", description="Reopened", status=IncidentStatus.IN_PROGRESS, assigned_department="Stormwater Management")
    db.add(inc)
    db.commit()

    notif = NotificationService.notify_incident_reopened(db, inc)
    assert notif is not None
    assert notif.event_type == "INCIDENT_REOPENED"
    assert "returned to the operational queue" in notif.message.lower()
    db.close()


def test_11_demo_notification_mode():
    db = TestingSessionLocal()
    rep = Report(id="rep-demo-mode", description="Demo report test", citizen_id="demo-citizen")
    db.add(rep)
    db.commit()

    with patch.object(settings, "NOTIFICATION_MODE", "demo"):
        notif = NotificationService.notify_report_received(db, rep)
        assert notif is not None
        assert notif.provider == "DEMO"
        assert notif.status == "DELIVERED"
    db.close()


def test_12_real_provider_configuration_validation():
    db = TestingSessionLocal()
    rep = Report(id="rep-courier-mode", description="Courier test", citizen_id="courier-citizen")
    db.add(rep)
    db.commit()

    mock_courier_module = MagicMock()
    mock_courier_instance = MagicMock()
    mock_courier_module.Courier.return_value = mock_courier_instance

    with patch.dict(sys.modules, {"courier": mock_courier_module}), \
         patch.object(settings, "NOTIFICATION_MODE", "courier"), \
         patch.object(settings, "COURIER_API_KEY", "sk_test_mock_12345"):
        
        notif = NotificationService.notify_report_received(db, rep)
        assert notif is not None
        assert notif.provider == "COURIER"
        assert notif.status == "DELIVERED"
        mock_courier_instance.send.message.assert_called_once()
    db.close()


def test_13_notification_failure_does_not_rollback_incident_state():
    db = TestingSessionLocal()
    inc = Incident(id="inc-res-fail", title="Resilient Incident", description="Failure test", status=IncidentStatus.SUBMITTED)
    db.add(inc)
    db.commit()

    mock_courier_module = MagicMock()
    mock_courier_module.Courier.side_effect = RuntimeError("Network Connection Timeout")

    with patch.dict(sys.modules, {"courier": mock_courier_module}), \
         patch.object(settings, "NOTIFICATION_MODE", "courier"), \
         patch.object(settings, "COURIER_API_KEY", "sk_test_key"):
        
        notif = NotificationService.notify_department_assigned(db, inc)
        db_inc = db.query(Incident).filter(Incident.id == "inc-res-fail").first()
        assert db_inc is not None
        assert notif is not None
        assert notif.status == "FAILED"
    db.close()


def test_14_duplicate_event_prevention():
    db = TestingSessionLocal()
    rep = Report(id="rep-dup-1", description="Duplicate check", citizen_id="cit-dup")
    db.add(rep)
    db.commit()

    notif1 = NotificationService.notify_report_received(db, rep)
    notif2 = NotificationService.notify_report_received(db, rep)

    assert notif1.id == notif2.id
    count = db.query(Notification).filter(Notification.event_type == "REPORT_RECEIVED").count()
    assert count == 1
    db.close()


def test_15_notification_api_endpoints_and_read_unread():
    db = TestingSessionLocal()
    n1 = Notification(id="n-api-1", recipient_type="CITIZEN", channel="IN_APP", event_type="REPORT_RECEIVED", title="Test 1", message="Msg 1", is_read=False)
    n2 = Notification(id="n-api-2", recipient_type="DISPATCHER", channel="IN_APP", event_type="INCIDENT_PRIORITY_ALERT", title="Test 2", message="Msg 2", is_read=False)
    db.add_all([n1, n2])
    db.commit()
    db.close()

    # GET /notifications
    res = client.get("/api/v1/notifications")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2

    # GET /notifications/unread
    res_unread = client.get("/api/v1/notifications/unread")
    assert res_unread.status_code == 200
    assert res_unread.json()["unread_count"] >= 2

    # PATCH /notifications/{id}/read
    res_patch = client.patch("/api/v1/notifications/n-api-1/read")
    assert res_patch.status_code == 200
    assert res_patch.json()["is_read"] is True

    # PATCH /notifications/read-all
    res_readall = client.patch("/api/v1/notifications/read-all")
    assert res_readall.status_code == 200

    res_unread3 = client.get("/api/v1/notifications/unread")
    assert res_unread3.json()["unread_count"] == 0
