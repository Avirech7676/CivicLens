import asyncio
import pytest
from app.services.ai_service import AIService
from app.core.enums import IncidentCategory

def test_pothole_with_standing_water_classified_as_road_hazard():
    res = asyncio.run(AIService.analyze_incident(
        description="Large deep pothole / road cavity filled with standing water near the main road."
    ))
    assert res.category == IncidentCategory.ROAD_HAZARD
    assert "WATER_LEAK" not in res.category.value

def test_road_cavity_with_muddy_water_classified_as_road_hazard():
    res = asyncio.run(AIService.analyze_incident(
        description="Large road cavity filled with muddy water causing vehicle swerving."
    ))
    assert res.category == IncidentCategory.ROAD_HAZARD

def test_broken_asphalt_rainwater_classified_as_road_hazard():
    res = asyncio.run(AIService.analyze_incident(
        description="Broken asphalt with rainwater accumulation in middle lane."
    ))
    assert res.category == IncidentCategory.ROAD_HAZARD

def test_burst_water_main_classified_as_water_leak():
    res = asyncio.run(AIService.analyze_incident(
        description="Water main pipe has burst and water is spraying onto the road."
    ))
    assert res.category == IncidentCategory.WATER_LEAK

def test_broken_water_pipe_classified_as_water_leak():
    res = asyncio.run(AIService.analyze_incident(
        description="Broken water pipe flooding the street."
    ))
    assert res.category == IncidentCategory.WATER_LEAK

def test_leaking_water_valve_classified_as_water_leak():
    res = asyncio.run(AIService.analyze_incident(
        description="Leaking municipal water valve beside the road."
    ))
    assert res.category == IncidentCategory.WATER_LEAK

def test_pothole_text_with_water_image_classified_as_road_hazard():
    res = asyncio.run(AIService.analyze_incident(
        description="2 feet deep pothole filled with water."
    ))
    assert res.category == IncidentCategory.ROAD_HAZARD

def test_broken_pipe_text_and_image_classified_as_water_leak():
    res = asyncio.run(AIService.analyze_incident(
        description="Water main pipe has burst and water is spraying from underground pipe."
    ))
    assert res.category == IncidentCategory.WATER_LEAK
