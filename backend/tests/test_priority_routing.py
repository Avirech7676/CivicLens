import pytest
import datetime
from app.core.enums import SeverityLevel, PriorityLevel, IncidentCategory
from app.services.priority_routing_service import PriorityEngine, DepartmentRoutingService

def test_priority_calculation_critical_manhole():
    # Case 3: Open manhole -> CRITICAL severity, multiple hazards, high confidence
    res = PriorityEngine.evaluate_priority(
        severity=SeverityLevel.CRITICAL,
        category=IncidentCategory.ROAD_HAZARD.value,
        hazards=["Uncovered open shaft", "Pedestrian fall risk"],
        confidence=0.95,
        report_count=2,
        created_at=datetime.datetime.utcnow()
    )

    assert res["priority_score"] >= 80
    assert res["priority_level"] == PriorityLevel.P1_CRITICAL
    assert len(res["priority_factors"]) == 6
    assert "CRITICAL" in res["priority_reason"]


def test_priority_calculation_low_peeling_bench():
    # Case 2: Peeling bench -> LOW severity, no hazards, 1 report
    res = PriorityEngine.evaluate_priority(
        severity=SeverityLevel.LOW,
        category=IncidentCategory.PUBLIC_PROPERTY.value,
        hazards=[],
        confidence=0.80,
        report_count=1,
        created_at=datetime.datetime.utcnow()
    )

    assert res["priority_score"] < 50
    assert res["priority_level"] == PriorityLevel.P4_LOW


def test_priority_calculation_old_high_pothole():
    # Case 1: Dangerous pothole -> HIGH severity, 3 reports, 4 days old
    old_time = datetime.datetime.utcnow() - datetime.timedelta(days=4)
    res = PriorityEngine.evaluate_priority(
        severity=SeverityLevel.HIGH,
        category=IncidentCategory.ROAD_HAZARD.value,
        hazards=["Vehicle rim damage"],
        confidence=0.90,
        report_count=4,
        created_at=old_time
    )

    assert res["priority_score"] >= 75
    assert res["priority_level"] in [PriorityLevel.P1_CRITICAL, PriorityLevel.P2_HIGH]


def test_department_routing_mapping():
    # Department mapping tests for all major categories
    r_road = DepartmentRoutingService.route_incident("ROAD_HAZARD")
    assert r_road["assigned_department"] == "Public Works - Roads"

    r_light = DepartmentRoutingService.route_incident("STREETLIGHT")
    assert r_light["assigned_department"] == "Electrical Maintenance"

    r_san = DepartmentRoutingService.route_incident("SANITATION")
    assert r_san["assigned_department"] == "Waste Management"

    r_water = DepartmentRoutingService.route_incident("WATER_LEAK")
    assert r_water["assigned_department"] == "Water Department"

    r_drain = DepartmentRoutingService.route_incident("DRAINAGE")
    assert r_drain["assigned_department"] == "Drainage & Sewer"

    r_other = DepartmentRoutingService.route_incident("OTHER")
    assert r_other["assigned_department"] == "General Civic Services"
    assert "OTHER" in r_other["routing_reason"]
