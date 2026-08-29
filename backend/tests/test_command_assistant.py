import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import Base, get_db, engine as prod_engine
from app.models.entities import Incident, Report, WorkOrder
from app.core.enums import IncidentStatus, WorkOrderStatus, PriorityLevel, SeverityLevel
from app.services.command_assistant_service import CommandAssistantService

TestingSessionLocal = lambda: Session(bind=prod_engine)

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


def test_1_top_priority_query():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-tp-1", title="Pothole Gate 1", description="Hazardous pothole", priority_score=92, priority_level=PriorityLevel.P1_CRITICAL, assigned_department="Roads", latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-tp-2", title="Water Leak", description="Main leak", priority_score=75, priority_level=PriorityLevel.P2_HIGH, assigned_department="Water", latitude=37.7800, longitude=-122.4100)
    db.add_all([inc1, inc2])
    db.commit()

    res = CommandAssistantService.process_query(db, "What should we fix first?")
    assert res["intent"] == "TOP_PRIORITY_INCIDENTS"
    assert "Pothole Gate 1" in res["answer"]
    assert "92/100" in res["answer"]
    assert len(res["sources"]) >= 1
    assert res["sources"][0]["id"] == "inc-tp-1"
    db.close()


def test_2_hotspot_summary_query():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-hs-1", title="Inc 1", description="Desc 1", category="ROAD_HAZARD", latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-hs-2", title="Inc 2", description="Desc 2", category="ROAD_HAZARD", latitude=37.7750, longitude=-122.4195)
    inc3 = Incident(id="inc-hs-3", title="Inc 3", description="Desc 3", category="ROAD_HAZARD", latitude=37.7751, longitude=-122.4196)
    db.add_all([inc1, inc2, inc3])
    db.commit()

    res = CommandAssistantService.process_query(db, "Where are the biggest civic hotspots?")
    assert res["intent"] == "HOTSPOT_SUMMARY"
    assert "active spatial hotspots" in res["answer"]
    assert len(res["sources"]) >= 1
    assert res["sources"][0]["type"] == "hotspot"
    db.close()


def test_3_incident_explanation_query():
    db = TestingSessionLocal()
    inc = Incident(
        id="inc-exp-1",
        title="Open Storm Drain",
        description="Hazardous drain",
        priority_score=94,
        priority_level=PriorityLevel.P1_CRITICAL,
        priority_reason="Immediate hazard to pedestrians",
        assigned_department="Roads & Infrastructure",
        latitude=37.7749,
        longitude=-122.4194
    )
    db.add(inc)
    db.commit()

    res = CommandAssistantService.process_query(db, "Why is the storm drain P1?")
    assert res["intent"] == "INCIDENT_EXPLANATION"
    assert "Open Storm Drain" in res["answer"]
    assert "94/100" in res["answer"]
    assert "Immediate hazard to pedestrians" in res["answer"]
    assert len(res["sources"]) == 1
    assert res["sources"][0]["id"] == "inc-exp-1"
    db.close()


def test_4_report_count_query():
    db = TestingSessionLocal()
    inc = Incident(id="inc-rep-1", title="Pothole", description="Deep hole", latitude=37.7749, longitude=-122.4194)
    db.add(inc)
    db.commit()

    rep1 = Report(id="r-rc-1", citizen_id="c1", description="Rep 1", latitude=37.7749, longitude=-122.4194, incident_id=inc.id)
    rep2 = Report(id="r-rc-2", citizen_id="c2", description="Rep 2", latitude=37.7749, longitude=-122.4194, incident_id=inc.id)
    db.add_all([rep1, rep2])
    db.commit()

    res = CommandAssistantService.process_query(db, "How many reports belong to the pothole?")
    assert res["intent"] == "INCIDENT_REPORT_COUNT"
    assert "2 citizen reports" in res["answer"]
    assert len(res["sources"]) == 1
    db.close()


def test_5_department_workload_query():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-dw-1", title="Inc 1", description="Desc 1", assigned_department="Roads & Infrastructure", priority_score=85, priority_level=PriorityLevel.P1_CRITICAL)
    inc2 = Incident(id="inc-dw-2", title="Inc 2", description="Desc 2", assigned_department="Roads & Infrastructure", priority_score=70, priority_level=PriorityLevel.P2_HIGH)
    inc3 = Incident(id="inc-dw-3", title="Inc 3", description="Desc 3", assigned_department="Electrical Maintenance", priority_score=60, priority_level=PriorityLevel.P3_MEDIUM)
    db.add_all([inc1, inc2, inc3])
    db.commit()

    res = CommandAssistantService.process_query(db, "Which department has the most active work?")
    assert res["intent"] == "DEPARTMENT_WORKLOAD"
    assert "Roads & Infrastructure: 2 Active Incidents" in res["answer"]
    assert "Electrical Maintenance: 1 Active Incidents" in res["answer"]
    assert len(res["sources"]) >= 2
    db.close()


def test_6_status_summary_query():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-st-1", title="Inc 1", description="Desc 1", status=IncidentStatus.RESOLVED)
    inc2 = Incident(id="inc-st-2", title="Inc 2", description="Desc 2", status=IncidentStatus.IN_PROGRESS)
    db.add_all([inc1, inc2])
    db.commit()

    res = CommandAssistantService.process_query(db, "How many incidents are awaiting verification?")
    assert res["intent"] == "STATUS_SUMMARY"
    assert "Awaiting Citizen Verification: 1" in res["answer"]
    assert "Active In-Progress Repairs: 1" in res["answer"]
    db.close()


def test_7_category_summary_query():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-cat-1", title="Inc 1", description="Desc 1", category="ROAD_HAZARD")
    inc2 = Incident(id="inc-cat-2", title="Inc 2", description="Desc 2", category="ROAD_HAZARD")
    inc3 = Incident(id="inc-cat-3", title="Inc 3", description="Desc 3", category="WATER_LEAK")
    db.add_all([inc1, inc2, inc3])
    db.commit()

    res = CommandAssistantService.process_query(db, "What are the most common civic problems?")
    assert res["intent"] == "CATEGORY_SUMMARY"
    assert "Road Hazard: 2 Incidents" in res["answer"]
    assert "Water Leak: 1 Incidents" in res["answer"]
    db.close()


def test_8_hotspot_incidents_query():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-hi-1", title="Inc 1", description="Desc 1", category="ROAD_HAZARD", latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-hi-2", title="Inc 2", description="Desc 2", category="ROAD_HAZARD", latitude=37.7750, longitude=-122.4195)
    inc3 = Incident(id="inc-hi-3", title="Inc 3", description="Desc 3", category="ROAD_HAZARD", latitude=37.7751, longitude=-122.4196)
    db.add_all([inc1, inc2, inc3])
    db.commit()

    res = CommandAssistantService.process_query(db, "Which incidents are inside the hotspot?")
    assert res["intent"] == "HOTSPOT_INCIDENTS"
    assert "Incidents inside Hotspot" in res["answer"]
    assert len(res["sources"]) >= 3
    db.close()


def test_9_incident_status_query():
    db = TestingSessionLocal()
    inc = Incident(
        id="inc-is-1",
        title="Main Gate Pothole",
        description="Hazardous hole",
        status=IncidentStatus.IN_PROGRESS,
        priority_score=85,
        priority_level=PriorityLevel.P1_CRITICAL,
        assigned_department="Roads & Infrastructure"
    )
    db.add(inc)
    db.commit()

    wo = WorkOrder(id="wo-is-1", incident_id=inc.id, assigned_department="Roads & Infrastructure", recommended_action="Patch asphalt", status=WorkOrderStatus.IN_PROGRESS)
    db.add(wo)
    db.commit()

    res = CommandAssistantService.process_query(db, "What is the status of the main gate pothole?")
    assert res["intent"] == "INCIDENT_STATUS"
    assert "Status for Incident 'Main Gate Pothole'" in res["answer"]
    assert "Incident Status: IN_PROGRESS" in res["answer"]
    assert "Work Order Status: IN_PROGRESS" in res["answer"]
    db.close()


def test_10_unknown_incident_query():
    db = TestingSessionLocal()
    res = CommandAssistantService.process_query(db, "Why is INC-999999 P1?")
    assert res["intent"] == "INCIDENT_EXPLANATION"
    assert "couldn't find that incident" in res["answer"].lower()
    db.close()


def test_11_unsupported_question_query():
    db = TestingSessionLocal()
    res = CommandAssistantService.process_query(db, "What will the city budget next year?")
    assert res["intent"] == "UNSUPPORTED_QUESTION"
    assert "don't have enough information" in res["answer"]
    assert len(res["sources"]) == 0
    db.close()


def test_12_empty_question_query():
    db = TestingSessionLocal()
    res = CommandAssistantService.process_query(db, "   ")
    assert res["intent"] == "EMPTY_QUESTION"
    assert "valid question" in res["answer"].lower()
    db.close()


def test_13_api_assistant_endpoint():
    db = TestingSessionLocal()
    inc = Incident(id="inc-api-ass", title="Open Storm Drain", description="Uncovered drain", priority_score=94, priority_level=PriorityLevel.P1_CRITICAL, assigned_department="Roads")
    db.add(inc)
    db.commit()
    db.close()

    res = client.post("/api/v1/assistant/query", json={"question": "What should we fix first?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "TOP_PRIORITY_INCIDENTS"
    assert "Open Storm Drain" in data["answer"]
    assert len(data["sources"]) >= 1
