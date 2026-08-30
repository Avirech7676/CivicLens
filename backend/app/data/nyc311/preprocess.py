import logging
from typing import List, Dict, Any, Tuple, Optional
from app.data.nyc311.schemas import NYC311Record, IngestionStats
from app.data.nyc311.taxonomy import map_nyc311_to_civiclens

logger = logging.getLogger(__name__)

# NYC Bounding Box Coordinates Validation
MIN_LAT, MAX_LAT = 40.4, 40.9
MIN_LON, MAX_LON = -74.3, -73.6

def validate_and_parse_record(raw: Dict[str, Any]) -> Tuple[Optional[NYC311Record], Optional[str]]:
    """Validates raw Socrata dictionary and parses into NYC311Record."""
    unique_key = raw.get("unique_key")
    complaint_type = raw.get("complaint_type")

    if not unique_key or not complaint_type:
        return None, "missing_key_or_complaint_type"

    # Parse coordinates
    lat, lon = None, None
    try:
        if raw.get("latitude") and raw.get("longitude"):
            lat = float(raw["latitude"])
            lon = float(raw["longitude"])
            if not (MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON):
                lat, lon = None, None # Out of bounds
    except (ValueError, TypeError):
        lat, lon = None, None

    record = NYC311Record(
        unique_key=str(unique_key),
        created_date=raw.get("created_date"),
        closed_date=raw.get("closed_date"),
        complaint_type=complaint_type,
        descriptor=raw.get("descriptor"),
        agency=raw.get("agency"),
        status=raw.get("status"),
        resolution_description=raw.get("resolution_description"),
        borough=raw.get("borough"),
        incident_address=raw.get("incident_address"),
        latitude=lat,
        longitude=lon
    )

    return record, None

def preprocess_nyc311_batch(
    raw_batch: List[Dict[str, Any]],
    seen_keys: set,
    stats: IngestionStats
) -> List[Dict[str, Any]]:
    """Deduplicates, validates, and transforms NYC 311 records into normalized training/evaluation schema."""
    processed = []

    for raw in raw_batch:
        stats.records_downloaded += 1
        record, err = validate_and_parse_record(raw)

        if not record:
            stats.records_invalid += 1
            continue

        if record.unique_key in seen_keys:
            stats.duplicates_removed += 1
            continue

        seen_keys.add(record.unique_key)

        if not record.latitude or not record.longitude:
            stats.missing_coordinates += 1

        if not record.descriptor:
            stats.missing_description += 1

        category, dept = map_nyc311_to_civiclens(record.complaint_type, record.descriptor)

        # Track category and agency distributions
        stats.categories_found[category.value] = stats.categories_found.get(category.value, 0) + 1
        if record.agency:
            stats.agencies_found[record.agency] = stats.agencies_found.get(record.agency, 0) + 1

        stats.records_valid += 1

        text = f"{record.complaint_type}: {record.descriptor or 'No descriptor provided'} at {record.incident_address or record.borough or 'NYC'}"
        
        normalized = {
            "unique_key": record.unique_key,
            "text": text,
            "nyc_complaint_type": record.complaint_type,
            "nyc_descriptor": record.descriptor,
            "agency": record.agency,
            "civiclens_category": category.value,
            "department": dept,
            "latitude": record.latitude,
            "longitude": record.longitude,
            "created_date": record.created_date,
            "closed_date": record.closed_date,
            "resolution_description": record.resolution_description
        }
        processed.append(normalized)

    return processed
