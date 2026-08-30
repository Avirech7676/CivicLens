from typing import Dict, Tuple, Optional
from app.core.enums import IncidentCategory

# Deterministic Mapping Layer: NYC 311 Complaint Types -> CivicLens IncidentCategory & Department

CATEGORY_TAXONOMY_MAP: Dict[str, Tuple[IncidentCategory, str]] = {
    # Road Hazards
    "pothole": (IncidentCategory.ROAD_HAZARD, "Public Works - Roads"),
    "street condition": (IncidentCategory.ROAD_HAZARD, "Public Works - Roads"),
    "highway condition": (IncidentCategory.ROAD_HAZARD, "Public Works - Roads"),
    "curb condition": (IncidentCategory.ROAD_HAZARD, "Public Works - Roads"),
    "bridge condition": (IncidentCategory.ROAD_HAZARD, "Public Works - Roads"),
    
    # Water Leak
    "water system": (IncidentCategory.WATER_LEAK, "Water Department"),
    "water leak": (IncidentCategory.WATER_LEAK, "Water Department"),
    "water main": (IncidentCategory.WATER_LEAK, "Water Department"),
    "fire hydrant": (IncidentCategory.WATER_LEAK, "Water Department"),
    
    # Drainage
    "sewer": (IncidentCategory.DRAINAGE, "Drainage & Sewer"),
    "catch basin": (IncidentCategory.DRAINAGE, "Drainage & Sewer"),
    "flooding": (IncidentCategory.DRAINAGE, "Drainage & Sewer"),
    
    # Traffic Signals & Signs
    "traffic signal condition": (IncidentCategory.TRAFFIC_SIGNAL, "Traffic Management"),
    "street sign - damaged": (IncidentCategory.TRAFFIC_SIGNAL, "Traffic Management"),
    "street sign - missing": (IncidentCategory.TRAFFIC_SIGNAL, "Traffic Management"),
    
    # Streetlights
    "street light condition": (IncidentCategory.STREETLIGHT, "Electrical Maintenance"),
    
    # Sanitation
    "sanitation condition": (IncidentCategory.SANITATION, "Waste Management"),
    "dirty conditions": (IncidentCategory.SANITATION, "Waste Management"),
    "overflowing litter basket": (IncidentCategory.SANITATION, "Waste Management"),
    "missed collection": (IncidentCategory.SANITATION, "Waste Management"),
    "recycling enforcement": (IncidentCategory.SANITATION, "Waste Management"),
    
    # Electrical
    "electrical": (IncidentCategory.ELECTRICAL, "Electrical Maintenance"),
    
    # Public Property
    "overgrown tree/branches": (IncidentCategory.PUBLIC_PROPERTY, "Public Works"),
    "damaged tree": (IncidentCategory.PUBLIC_PROPERTY, "Public Works"),
    "park": (IncidentCategory.PUBLIC_PROPERTY, "Public Works"),
    "graffiti": (IncidentCategory.PUBLIC_PROPERTY, "Public Works"),
}

DEPARTMENT_MAP: Dict[IncidentCategory, str] = {
    IncidentCategory.ROAD_HAZARD: "Public Works - Roads",
    IncidentCategory.WATER_LEAK: "Water Department",
    IncidentCategory.DRAINAGE: "Drainage & Sewer",
    IncidentCategory.TRAFFIC_SIGNAL: "Traffic Management",
    IncidentCategory.STREETLIGHT: "Electrical Maintenance",
    IncidentCategory.SANITATION: "Waste Management",
    IncidentCategory.ELECTRICAL: "Electrical Maintenance",
    IncidentCategory.PUBLIC_PROPERTY: "Public Works",
    IncidentCategory.OTHER: "General Civic Services"
}

def map_nyc311_to_civiclens(complaint_type: str, descriptor: Optional[str] = None) -> Tuple[IncidentCategory, str]:
    """
    Maps an NYC 311 complaint_type and optional descriptor into a CivicLens IncidentCategory and Department.
    """
    ctype = complaint_type.strip().lower()
    desc = descriptor.strip().lower() if descriptor else ""

    # Check for direct descriptor overrides first (e.g. water leak inside street condition)
    if "burst pipe" in desc or "water main" in desc or "leaking pipe" in desc:
        return IncidentCategory.WATER_LEAK, DEPARTMENT_MAP[IncidentCategory.WATER_LEAK]
    
    if "pothole" in desc or "cave-in" in desc or "asphalt" in desc or "pavement" in desc:
        return IncidentCategory.ROAD_HAZARD, DEPARTMENT_MAP[IncidentCategory.ROAD_HAZARD]

    if "catch basin" in desc or "flooding" in desc or "clogged drain" in desc:
        return IncidentCategory.DRAINAGE, DEPARTMENT_MAP[IncidentCategory.DRAINAGE]

    # Match complaint_type
    for key, (category, dept) in CATEGORY_TAXONOMY_MAP.items():
        if key in ctype:
            return category, dept

    return IncidentCategory.OTHER, DEPARTMENT_MAP[IncidentCategory.OTHER]
