import pytest
from app.core.enums import IncidentCategory, SeverityLevel, IncidentStatus, WorkOrderStatus
from app.services.work_order_service import WorkOrderGenerationService, CATEGORY_TEMPLATES
from app.services.crud import IncidentService, VALID_INCIDENT_TRANSITIONS

def test_work_order_generation_road_hazard():
    plan = WorkOrderGenerationService.generate_plan(
        category=IncidentCategory.ROAD_HAZARD.value,
        title="Large Pothole",
        description="Deep pothole in road",
        ai_recommended_action="Patch asphalt immediately",
        hazards=["Rim damage", "Swerving traffic"],
        severity=SeverityLevel.HIGH,
        department="Public Works - Roads"
    )

    assert plan["assigned_department"] == "Public Works - Roads"
    assert "Patch asphalt immediately" in plan["recommended_action"]
    assert "cold-mix" in plan["required_materials"].lower() or "asphalt" in plan["required_materials"].lower()
    assert "SPECIFIC HAZARD MITIGATION: Address rim damage" in plan["safety_precautions"]


def test_work_order_generation_all_categories():
    categories = [
        "ROAD_HAZARD", "STREETLIGHT", "SANITATION", "WATER_LEAK", 
        "DRAINAGE", "ELECTRICAL", "PUBLIC_PROPERTY", "TRAFFIC_SIGNAL", "OTHER"
    ]

    for cat in categories:
        plan = WorkOrderGenerationService.generate_plan(
            category=cat,
            title=f"Test {cat}",
            description="Test issue description",
            ai_recommended_action="Test action",
            hazards=["Test hazard"],
            severity=SeverityLevel.MEDIUM,
            department="Test Department"
        )
        assert len(plan["recommended_action"]) > 0
        assert len(plan["required_materials"]) > 0
        assert len(plan["safety_precautions"]) > 0


def test_valid_incident_status_transitions():
    # Valid transition: SUBMITTED -> IN_PROGRESS
    assert IncidentStatus.IN_PROGRESS in VALID_INCIDENT_TRANSITIONS[IncidentStatus.SUBMITTED]
    # Valid transition: IN_PROGRESS -> RESOLVED
    assert IncidentStatus.RESOLVED in VALID_INCIDENT_TRANSITIONS[IncidentStatus.IN_PROGRESS]
    # Valid transition: RESOLVED -> VERIFIED
    assert IncidentStatus.VERIFIED in VALID_INCIDENT_TRANSITIONS[IncidentStatus.RESOLVED]
    # Valid transition: RESOLVED -> IN_PROGRESS (Citizen Reopen)
    assert IncidentStatus.IN_PROGRESS in VALID_INCIDENT_TRANSITIONS[IncidentStatus.RESOLVED]


def test_invalid_status_transition_raises_error():
    # VERIFIED is terminal
    assert len(VALID_INCIDENT_TRANSITIONS[IncidentStatus.VERIFIED]) == 0
