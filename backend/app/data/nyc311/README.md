# NYC 311 Dataset Integration Module

This module provides data ingestion, Socrata API streaming, taxonomy mapping, and normalization of real-world **NYC 311 Service Requests (2020–Present)** into the CivicLens civic operations domain.

## Pipeline Structure
- `client.py`: Configurable Socrata API client supporting `$limit`, `$offset`, retry/exponential backoff, and timeouts.
- `schemas.py`: Pydantic data schemas (`NYC311Record`, `IngestionStats`).
- `taxonomy.py`: Deterministic mapping rules connecting NYC 311 complaint types/descriptors to CivicLens `IncidentCategory` and `Department`.
- `preprocess.py`: Coordinate validation (NYC bounding box), deduplication, date parsing, and training record generation.
- `collector.py`: Stream orchestrator processing records in memory-safe batches.

## Usage
```python
from app.data.nyc311.collector import collect_and_process_nyc311

records, stats = collect_and_process_nyc311(sample_size=10000, batch_size=1000)
print(f"Downloaded: {stats.records_downloaded}, Valid: {stats.records_valid}")
```
