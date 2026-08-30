from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class NYC311Record(BaseModel):
    unique_key: str
    created_date: Optional[str] = None
    closed_date: Optional[str] = None
    complaint_type: str
    descriptor: Optional[str] = None
    agency: Optional[str] = None
    status: Optional[str] = None
    resolution_description: Optional[str] = None
    borough: Optional[str] = None
    incident_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = ConfigDict(extra="ignore")

class IngestionStats(BaseModel):
    records_downloaded: int = 0
    records_valid: int = 0
    records_invalid: int = 0
    duplicates_removed: int = 0
    missing_coordinates: int = 0
    missing_description: int = 0
    categories_found: Dict[str, int] = {}
    agencies_found: Dict[str, int] = {}
