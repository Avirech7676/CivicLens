import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import Base, get_db, engine as prod_engine
from app.models.entities import Incident, Report, Notification, WorkOrder, StatusLog
from app.core.enums import IncidentStatus, PriorityLevel, SeverityLevel
from app.services.hotspot_service import HotspotService

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


def test_1_no_incidents_no_hotspots():
    db = TestingSessionLocal()
    res = HotspotService.detect_hotspots(db)
    assert res["total_hotspots"] == 0
    assert len(res["hotspots"]) == 0
    db.close()


def test_2_one_incident_no_hotspot():
    db = TestingSessionLocal()
    inc = Incident(id="inc-single-1", title="Single Pothole", description="Sample description", category="ROAD_HAZARD", latitude=37.7749, longitude=-122.4194)
    db.add(inc)
    db.commit()

    res = HotspotService.detect_hotspots(db)
    assert res["total_hotspots"] == 0
    db.close()


def test_3_multiple_reports_on_one_incident_not_hotspot():
    db = TestingSessionLocal()
    inc = Incident(id="inc-heavy-rep", title="Single Heavily Reported Sinkhole", description="Sample description", category="ROAD_HAZARD", latitude=37.7749, longitude=-122.4194)
    db.add(inc)
    db.commit()

    reps = [
        Report(id=f"rep-s-{i}", citizen_id=f"cit-{i}", description=f"Sinkhole report {i}", latitude=37.7749, longitude=-122.4194, incident_id=inc.id)
        for i in range(15)
    ]
    db.add_all(reps)
    db.commit()

    # 1 Incident with 15 reports MUST NOT become a spatial hotspot (requires >= 2 canonical incidents)
    res = HotspotService.detect_hotspots(db)
    assert res["total_hotspots"] == 0
    db.close()


def test_4_multiple_nearby_canonical_incidents_hotspot_detected():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-n-1", title="Pothole Gate 1", description="Sample description 1", category="ROAD_HAZARD", priority_score=80, priority_level=PriorityLevel.P1_CRITICAL, latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-n-2", title="Curb Crack", description="Sample description 2", category="ROAD_HAZARD", priority_score=70, priority_level=PriorityLevel.P2_HIGH, latitude=37.7752, longitude=-122.4190)
    inc3 = Incident(id="inc-n-3", title="Signal Fault", description="Sample description 3", category="TRAFFIC_SIGNAL", priority_score=75, priority_level=PriorityLevel.P2_HIGH, latitude=37.7746, longitude=-122.4198)

    db.add_all([inc1, inc2, inc3])
    db.commit()

    res = HotspotService.detect_hotspots(db)
    assert res["total_hotspots"] == 1
    hs = res["hotspots"][0]
    assert hs["incident_count"] == 3
    assert hs["hotspot_score"] >= 60
    db.close()


def test_5_nearby_incidents_different_categories_mixed_pattern():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-m-1", title="Pothole", description="Sample desc 1", category="ROAD_HAZARD", latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-m-2", title="Water Leak", description="Sample desc 2", category="WATER_LEAK", latitude=37.7751, longitude=-122.4192)
    inc3 = Incident(id="inc-m-3", title="Garbage Pile", description="Sample desc 3", category="SANITATION", latitude=37.7748, longitude=-122.4196)

    db.add_all([inc1, inc2, inc3])
    db.commit()

    res = HotspotService.detect_hotspots(db)
    assert res["total_hotspots"] == 1
    hs = res["hotspots"][0]
    assert hs["pattern"] == "MIXED_INFRASTRUCTURE"
    db.close()


def test_6_far_away_incidents_separate_no_hotspot():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-far-1", title="San Francisco Pothole", description="Sample desc 1", category="ROAD_HAZARD", latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-far-2", title="Oakland Pothole", description="Sample desc 2", category="ROAD_HAZARD", latitude=37.8044, longitude=-122.2712) # ~12 km away

    db.add_all([inc1, inc2])
    db.commit()

    res = HotspotService.detect_hotspots(db)
    assert res["total_hotspots"] == 0
    db.close()


def test_7_missing_coordinates_excluded_from_spatial_clustering():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-valid-1", title="Valid Coord 1", description="Sample desc 1", category="ROAD_HAZARD", latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-valid-2", title="Valid Coord 2", description="Sample desc 2", category="ROAD_HAZARD", latitude=37.7750, longitude=-122.4195)
    inc_no_coord = Incident(id="inc-nocoord", title="No Coord", description="Sample desc 3", category="ROAD_HAZARD", latitude=0.0, longitude=0.0)

    db.add_all([inc1, inc2, inc_no_coord])
    db.commit()

    res = HotspotService.detect_hotspots(db)
    if res["total_hotspots"] > 0:
        for hs in res["hotspots"]:
            assert "inc-nocoord" not in hs["incident_ids"]
    db.close()


def test_8_hotspot_incident_count_and_9_report_count():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-ic-1", title="Inc 1", description="Sample desc 1", category="ROAD_HAZARD", latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-ic-2", title="Inc 2", description="Sample desc 2", category="ROAD_HAZARD", latitude=37.7750, longitude=-122.4195)
    inc3 = Incident(id="inc-ic-3", title="Inc 3", description="Sample desc 3", category="ROAD_HAZARD", latitude=37.7751, longitude=-122.4196)

    db.add_all([inc1, inc2, inc3])
    db.commit()

    r1 = Report(id="r-ic-1", citizen_id="c1", description="Rep 1", latitude=37.7749, longitude=-122.4194, incident_id=inc1.id)
    r2 = Report(id="r-ic-2", citizen_id="c2", description="Rep 2", latitude=37.7749, longitude=-122.4194, incident_id=inc1.id)
    r3 = Report(id="r-ic-3", citizen_id="c3", description="Rep 3", latitude=37.7750, longitude=-122.4195, incident_id=inc2.id)

    db.add_all([r1, r2, r3])
    db.commit()

    res = HotspotService.detect_hotspots(db)
    assert res["total_hotspots"] == 1
    hs = res["hotspots"][0]
    assert hs["incident_count"] == 3
    assert hs["report_count"] == 4 # 2 for inc1 + 1 for inc2 + 1 fallback for inc3
    db.close()


def test_10_average_priority_and_11_highest_priority_calculation():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-p-1", title="Inc 1", description="Sample desc 1", category="ROAD_HAZARD", priority_score=90, latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-p-2", title="Inc 2", description="Sample desc 2", category="ROAD_HAZARD", priority_score=70, latitude=37.7750, longitude=-122.4195)
    inc3 = Incident(id="inc-p-3", title="Inc 3", description="Sample desc 3", category="ROAD_HAZARD", priority_score=50, latitude=37.7751, longitude=-122.4196)

    db.add_all([inc1, inc2, inc3])
    db.commit()

    res = HotspotService.detect_hotspots(db)
    assert res["total_hotspots"] == 1
    hs = res["hotspots"][0]
    assert hs["average_priority_score"] == 70 # (90+70+50)/3
    assert hs["highest_priority_score"] == 90
    db.close()


def test_12_p1_p2_counts_and_13_category_distribution():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-cd-1", title="Inc 1", description="Sample desc 1", category="ROAD_HAZARD", priority_score=85, priority_level=PriorityLevel.P1_CRITICAL, latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-cd-2", title="Inc 2", description="Sample desc 2", category="ROAD_HAZARD", priority_score=70, priority_level=PriorityLevel.P2_HIGH, latitude=37.7750, longitude=-122.4195)
    inc3 = Incident(id="inc-cd-3", title="Inc 3", description="Sample desc 3", category="TRAFFIC_SIGNAL", priority_score=40, priority_level=PriorityLevel.P3_MEDIUM, latitude=37.7751, longitude=-122.4196)

    db.add_all([inc1, inc2, inc3])
    db.commit()

    res = HotspotService.detect_hotspots(db)
    assert res["total_hotspots"] == 1
    hs = res["hotspots"][0]
    assert hs["p1_count"] == 1
    assert hs["p2_count"] == 1
    assert hs["category_distribution"] == {"ROAD_HAZARD": 2, "TRAFFIC_SIGNAL": 1}
    assert hs["dominant_category"] == "ROAD_HAZARD"
    assert hs["pattern"] == "ROAD_CONDITION"
    db.close()


def test_14_hotspot_score_calculation_and_15_level_thresholds():
    score_normal = HotspotService.calculate_hotspot_score(incident_count=3, report_count=3, avg_priority=40, p1_count=0, p2_count=0)
    score_critical = HotspotService.calculate_hotspot_score(incident_count=7, report_count=25, avg_priority=80, p1_count=2, p2_count=3)

    assert HotspotService.determine_hotspot_level(score_normal) in ["NORMAL", "EMERGING"]
    assert HotspotService.determine_hotspot_level(score_critical) == "CRITICAL"
    assert score_critical >= 80


def test_16_deterministic_explanation_format():
    exp = HotspotService.generate_explanation(
        incident_count=6,
        report_count=21,
        radius_meters=250.0,
        dominant_category="ROAD_HAZARD",
        dominant_cnt=5,
        avg_priority=76
    )
    assert "6 civic incidents" in exp
    assert "21 citizen reports" in exp
    assert "250 meters" in exp
    assert "Road Hazard represents 5" in exp
    assert "average priority score of 76" in exp


def test_17_hotspot_api_endpoint():
    db = TestingSessionLocal()
    inc1 = Incident(id="inc-api-1", title="API Inc 1", description="Sample desc 1", category="ROAD_HAZARD", priority_score=85, priority_level=PriorityLevel.P1_CRITICAL, latitude=37.7749, longitude=-122.4194)
    inc2 = Incident(id="inc-api-2", title="API Inc 2", description="Sample desc 2", category="ROAD_HAZARD", priority_score=75, priority_level=PriorityLevel.P2_HIGH, latitude=37.7750, longitude=-122.4195)
    inc3 = Incident(id="inc-api-3", title="API Inc 3", description="Sample desc 3", category="ROAD_HAZARD", priority_score=65, priority_level=PriorityLevel.P2_HIGH, latitude=37.7751, longitude=-122.4196)

    db.add_all([inc1, inc2, inc3])
    db.commit()
    db.close()

    res = client.get("/api/v1/hotspots")
    assert res.status_code == 200
    data = res.json()
    assert data["total_hotspots"] >= 1
    assert "recommendations" in data
    assert len(data["hotspots"]) >= 1

    # Test incident hotspot drill-down endpoint
    res_hs = client.get(f"/api/v1/incidents/inc-api-1/hotspot")
    assert res_hs.status_code == 200
    hs_data = res_hs.json()
    assert hs_data["hotspot_id"] is not None
