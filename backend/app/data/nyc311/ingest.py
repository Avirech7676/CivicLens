import os
import sys
import time
import json
import logging
import argparse
from typing import Optional, Dict, Any, Generator, Tuple
import pandas as pd

from app.data.nyc311.schemas import IngestionStats
from app.data.nyc311.taxonomy import map_nyc311_to_civiclens
from app.data.nyc311.client import NYC311Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("civiclens.ingest")

MIN_LAT, MAX_LAT = 40.4, 40.9
MIN_LON, MAX_LON = -74.3, -73.6

COLUMN_NAME_MAP = {
    "Unique Key": "unique_key",
    "Created Date": "created_date",
    "Closed Date": "closed_date",
    "Complaint Type": "complaint_type",
    "Descriptor": "descriptor",
    "Agency": "agency",
    "Status": "status",
    "Resolution Description": "resolution_description",
    "Borough": "borough",
    "Incident Address": "incident_address",
    "Latitude": "latitude",
    "Longitude": "longitude"
}

def normalize_chunk_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes column names across CSV variations and Socrata API keys."""
    rename_dict = {}
    for col in df.columns:
        norm_col = str(col).strip().title()
        if norm_col in COLUMN_NAME_MAP:
            rename_dict[col] = COLUMN_NAME_MAP[norm_col]
        else:
            rename_dict[col] = str(col).strip().lower().replace(" ", "_")
    return df.rename(columns=rename_dict)

def process_chunk(
    df_chunk: pd.DataFrame,
    seen_keys: set,
    stats: IngestionStats
) -> pd.DataFrame:
    """Processes, cleans, validates, and taxonomy-maps a single chunk of records."""
    df_chunk = normalize_chunk_columns(df_chunk)

    required_cols = ["complaint_type"]
    for req in required_cols:
        if req not in df_chunk.columns:
            df_chunk[req] = "Unknown"

    if "unique_key" not in df_chunk.columns:
        df_chunk["unique_key"] = [f"gen-key-{i}" for i in range(len(df_chunk))]

    processed_rows = []

    for idx, row in df_chunk.iterrows():
        stats.records_downloaded += 1
        key = str(row.get("unique_key", f"row-{idx}"))

        if key in seen_keys:
            stats.duplicates_removed += 1
            continue

        seen_keys.add(key)

        ctype = str(row.get("complaint_type", "")).strip()
        if not ctype or ctype.lower() == "nan" or ctype.lower() == "unknown":
            stats.missing_description += 1

        descriptor = str(row.get("descriptor", "")).strip() if pd.notna(row.get("descriptor")) else ""
        
        # Latitude & Longitude validation
        lat, lon = None, None
        try:
            raw_lat = row.get("latitude")
            raw_lon = row.get("longitude")
            if pd.notna(raw_lat) and pd.notna(raw_lon):
                plat = float(raw_lat)
                plon = float(raw_lon)
                if MIN_LAT <= plat <= MAX_LAT and MIN_LON <= plon <= MAX_LON:
                    lat, lon = plat, plon
                else:
                    stats.records_invalid += 1
            else:
                stats.missing_coordinates += 1
        except (ValueError, TypeError):
            stats.records_invalid += 1

        category, department = map_nyc311_to_civiclens(ctype, descriptor)

        stats.records_valid += 1
        stats.categories_found[category.value] = stats.categories_found.get(category.value, 0) + 1
        
        agency = str(row.get("agency", "NYC311")).strip()
        stats.agencies_found[agency] = stats.agencies_found.get(agency, 0) + 1

        text = f"{ctype}: {descriptor or 'No descriptor provided'} at {row.get('incident_address') or row.get('borough') or 'NYC'}"

        processed_rows.append({
            "unique_key": key,
            "text": text,
            "nyc_complaint_type": ctype,
            "nyc_descriptor": descriptor,
            "agency": agency,
            "civiclens_category": category.value,
            "department": department,
            "latitude": lat,
            "longitude": lon,
            "created_date": str(row.get("created_date", "")) if pd.notna(row.get("created_date")) else "",
            "closed_date": str(row.get("closed_date", "")) if pd.notna(row.get("closed_date")) else "",
            "resolution_description": str(row.get("resolution_description", "")) if pd.notna(row.get("resolution_description")) else ""
        })

    return pd.DataFrame(processed_rows)

def ingest_nyc311_stream(
    csv_path: Optional[str] = None,
    output_path: str = "backend/data/processed/nyc311_processed.csv",
    chunk_size: int = 10000,
    max_rows: int = 100000
) -> Tuple[str, IngestionStats]:
    """Streams and ingests NYC 311 CSV or Socrata API chunks without loading full file into memory."""
    t0 = time.time()
    stats = IngestionStats()
    seen_keys = set()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if os.path.exists(output_path):
        os.remove(output_path)

    header_written = False
    total_written = 0

    if csv_path and os.path.exists(csv_path):
        logger.info(f"Streaming NYC 311 CSV input from {csv_path} (Chunk size: {chunk_size}, Max rows: {max_rows})...")
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
            if total_written >= max_rows:
                break
            
            processed_df = process_chunk(chunk, seen_keys, stats)
            if not processed_df.empty:
                processed_df.to_csv(output_path, mode='a', header=not header_written, index=False)
                header_written = True
                total_written += len(processed_df)
                logger.info(f"Processed chunk ({len(processed_df)} rows). Total processed: {total_written}/{max_rows}")
    else:
        logger.info(f"CSV file '{csv_path}' not found or omitted. Streaming from NYC 311 Socrata API...")
        client = NYC311Client()
        for raw_batch in client.stream_records(total_limit=max_rows, batch_size=chunk_size):
            chunk_df = pd.DataFrame(raw_batch)
            if chunk_df.empty:
                break
            
            processed_df = process_chunk(chunk_df, seen_keys, stats)
            if not processed_df.empty:
                processed_df.to_csv(output_path, mode='a', header=not header_written, index=False)
                header_written = True
                total_written += len(processed_df)
                logger.info(f"Processed Socrata API batch ({len(processed_df)} rows). Total processed: {total_written}/{max_rows}")

    duration = time.time() - t0
    logger.info(f"Streaming Ingestion Completed in {duration:.2f}s. Saved {total_written} valid records to {output_path}.")
    return output_path, stats

def create_sample_fixture_csv(path: str = "backend/data/nyc311_sample.csv", num_rows: int = 500) -> str:
    """Generates a small local synthetic NYC 311 sample fixture CSV for testing when 5GB CSV is absent."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sample_data = []

    types_desc = [
        ("Pothole", "Pothole on roadway surface causing traffic swerving", "Public Works - Roads"),
        ("Water System", "Burst water main pipe spraying water on street", "Water Department"),
        ("Sewer", "Clogged catch basin storm drain causing street flooding", "Drainage & Sewer"),
        ("Street Light Condition", "Unlit street lamp fixture pole 102", "Electrical Maintenance"),
        ("Traffic Signal Condition", "Flickering red signal head", "Traffic Management"),
        ("Sanitation Condition", "Overflowing garbage bin corner", "Waste Management"),
        ("Overgrown Tree/Branches", "Park tree branch hanging low", "Public Works")
    ]

    for i in range(1, num_rows + 1):
        ctype, desc, dept = types_desc[i % len(types_desc)]
        sample_data.append({
            "Unique Key": f"nyc-key-{i}",
            "Created Date": f"2026-01-01T{(i%24):02d}:00:00.000",
            "Closed Date": f"2026-01-02T{(i%24):02d}:00:00.000",
            "Complaint Type": ctype,
            "Descriptor": desc,
            "Agency": "DOT" if "Pothole" in ctype else "DEP",
            "Status": "Closed",
            "Resolution Description": "The City responded to the complaint and resolved the condition.",
            "Borough": "MANHATTAN",
            "Incident Address": f"{100 + i} Campus Ave",
            "Latitude": 40.7128 + (i * 0.0001),
            "Longitude": -74.0060 - (i * 0.0001)
        })

    df = pd.DataFrame(sample_data)
    df.to_csv(path, index=False)
    logger.info(f"Created sample fixture CSV with {num_rows} records at {path}")
    return path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CivicLens NYC 311 Streaming Ingestion Pipeline")
    parser.add_argument("--input", type=str, default=None, help="Path to raw NYC 311 CSV file")
    parser.add_argument("--output", type=str, default="backend/data/processed/nyc311_processed.csv", help="Output path for processed CSV")
    parser.add_argument("--chunk-size", type=int, default=10000, help="Chunk size for streaming")
    parser.add_argument("--max-rows", type=int, default=100000, help="Maximum rows to process")
    args = parser.parse_args()

    ingest_nyc311_stream(
        csv_path=args.input,
        output_path=args.output,
        chunk_size=args.chunk_size,
        max_rows=args.max_rows
    )
