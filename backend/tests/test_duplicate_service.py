import pytest
from app.core.config import settings
from app.core.enums import IncidentCategory, SeverityLevel
from app.models.entities import Incident, Report, WorkOrder
from app.schemas.dto import IncidentAnalysisResult
from app.services.duplicate_service import (
    DuplicateDetectionService, 
    haversine_distance, 
    cosine_similarity, 
    lexical_similarity
)

def test_haversine_distance():
    # Distance between two identical coordinates is 0
    d0 = haversine_distance(37.7749, -122.4194, 37.7749, -122.4194)
    assert round(d0, 2) == 0.0

    # Distance between ~100 meters offset
    # 0.0009 degrees latitude is roughly 100 meters
    d_100 = haversine_distance(37.7749, -122.4194, 37.7758, -122.4194)
    assert 95.0 <= d_100 <= 105.0


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == 0.0


def test_category_compatibility():
    assert DuplicateDetectionService.is_category_compatible("ROAD_HAZARD", "ROAD_HAZARD")
    assert DuplicateDetectionService.is_category_compatible("ROAD_HAZARD", "TRAFFIC_SIGNAL")
    assert DuplicateDetectionService.is_category_compatible("STREETLIGHT", "ELECTRICAL")
    assert not DuplicateDetectionService.is_category_compatible("ROAD_HAZARD", "SANITATION")


def test_evaluate_candidate_same_issue_same_area():
    analysis = IncidentAnalysisResult(
        category=IncidentCategory.ROAD_HAZARD,
        title="Pothole near Gate 1",
        normalized_description="Large pothole near Gate 1 crosswalk",
        severity_level=SeverityLevel.HIGH,
        severity_reason="Road hazard",
        hazards=["Rim damage"],
        evidence_observations=["Cavity in road"],
        confidence=0.9,
        recommended_action="Patch asphalt"
    )

    incident = Incident(
        id="inc-100",
        title="Large Pothole near Gate 1",
        description="Deep pothole in the road near Gate 1 entrance",
        category=IncidentCategory.ROAD_HAZARD.value,
        latitude=37.7749,
        longitude=-122.4194
    )

    # Report located ~10 meters away with high semantic similarity
    candidate = DuplicateDetectionService.evaluate_candidate(
        report_desc="Deep road damage beside main entrance near Gate 1",
        report_lat=37.77495,
        report_lon=-122.41945,
        analysis=analysis,
        incident=incident,
        report_embedding=None # Falls back to lexical similarity
    )

    assert candidate["category_match"] is True
    assert candidate["distance_meters"] < 50.0
    assert candidate["match_confidence"] >= 0.70
    assert "category matches" in candidate["reason"]


def test_evaluate_candidate_same_issue_far_away():
    analysis = IncidentAnalysisResult(
        category=IncidentCategory.ROAD_HAZARD,
        title="Pothole near Gate 1",
        normalized_description="Large pothole near Gate 1",
        severity_level=SeverityLevel.HIGH,
        severity_reason="Road hazard",
        hazards=[],
        evidence_observations=[],
        confidence=0.9,
        recommended_action="Patch asphalt"
    )

    incident = Incident(
        id="inc-101",
        title="Large Pothole near Gate 1",
        description="Deep pothole in the road near Gate 1",
        category=IncidentCategory.ROAD_HAZARD.value,
        latitude=37.7749,
        longitude=-122.4194
    )

    # Report located 5 km away
    candidate = DuplicateDetectionService.evaluate_candidate(
        report_desc="Pothole near Gate 1 crosswalk",
        report_lat=37.8200,
        report_lon=-122.4200,
        analysis=analysis,
        incident=incident
    )

    assert candidate["distance_meters"] > 4000.0
    # Geographic score will be 0, dropping overall confidence below duplicate threshold
    assert candidate["match_confidence"] < settings.DUPLICATE_CONFIDENCE_THRESHOLD


def test_missing_coordinates_handling():
    analysis = IncidentAnalysisResult(
        category=IncidentCategory.STREETLIGHT,
        title="Broken Streetlamp",
        normalized_description="Dark streetlamp on Main Street",
        severity_level=SeverityLevel.MEDIUM,
        severity_reason="Visibility",
        hazards=[],
        evidence_observations=[],
        confidence=0.8,
        recommended_action="Replace fixture"
    )

    incident = Incident(
        id="inc-102",
        title="Broken Streetlamp",
        description="Dark streetlamp on Main Street",
        category=IncidentCategory.STREETLIGHT.value,
        latitude=None,
        longitude=None
    )

    candidate = DuplicateDetectionService.evaluate_candidate(
        report_desc="Dark streetlamp on Main Street",
        report_lat=None,
        report_lon=None,
        analysis=analysis,
        incident=incident
    )

    assert candidate["distance_meters"] is None
    assert "location coordinates unavailable" in candidate["reason"]
