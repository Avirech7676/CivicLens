import os
import json
import logging
from typing import Optional, Tuple
from app.data.nyc311.client import NYC311Client
from app.data.nyc311.schemas import IngestionStats
from app.data.nyc311.preprocess import preprocess_nyc311_batch

logger = logging.getLogger(__name__)

def collect_and_process_nyc311(
    sample_size: int = 10000,
    batch_size: int = 1000,
    where_clause: Optional[str] = "latitude IS NOT NULL AND complaint_type IS NOT NULL"
) -> Tuple[list, IngestionStats]:
    """Orchestrates download, deduplication, taxonomy mapping, and normalization of NYC 311 data."""
    client = NYC311Client()
    stats = IngestionStats()
    seen_keys = set()
    all_processed = []

    logger.info(f"Starting NYC 311 ingestion pipeline (Sample Size: {sample_size}, Batch Size: {batch_size})...")

    for raw_batch in client.stream_records(total_limit=sample_size, batch_size=batch_size, where_clause=where_clause):
        processed_batch = preprocess_nyc311_batch(raw_batch, seen_keys, stats)
        all_processed.extend(processed_batch)

    logger.info(f"NYC 311 Ingestion Complete: {stats.records_valid} valid records out of {stats.records_downloaded} downloaded.")
    return all_processed, stats
