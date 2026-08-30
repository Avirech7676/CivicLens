import time
import logging
import requests
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

NYC_311_ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

class NYC311Client:
    """Configurable Socrata API client for NYC 311 Service Requests."""

    def __init__(
        self,
        base_url: str = NYC_311_ENDPOINT,
        app_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.base_url = base_url
        self.app_token = app_token or getattr(settings, "SOCRATA_APP_TOKEN", None)
        self.timeout = timeout
        self.max_retries = max_retries

    def fetch_batch(
        self,
        limit: int = 1000,
        offset: int = 0,
        where_clause: Optional[str] = None,
        order_by: str = "created_date DESC"
    ) -> List[Dict[str, Any]]:
        """Fetches a single batch of records from NYC 311 Socrata API with retry/backoff."""
        headers = {}
        if self.app_token:
            headers["X-App-Token"] = self.app_token

        params = {
            "$limit": limit,
            "$offset": offset,
            "$order": order_by
        }
        if where_clause:
            params["$where"] = where_clause

        for attempt in range(1, self.max_retries + 1):
            try:
                res = requests.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
                res.raise_for_status()
                return res.json()
            except Exception as e:
                logger.warning(f"NYC 311 API request attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt)

        return []

    def stream_records(
        self,
        total_limit: int = 10000,
        batch_size: int = 1000,
        where_clause: Optional[str] = None
    ):
        """Yields records in batches up to total_limit without loading entire dataset into memory."""
        fetched = 0
        offset = 0

        while fetched < total_limit:
            current_batch_size = min(batch_size, total_limit - fetched)
            batch = self.fetch_batch(limit=current_batch_size, offset=offset, where_clause=where_clause)
            if not batch:
                break
            
            yield batch
            fetched += len(batch)
            offset += len(batch)
            logger.info(f"Progress: Downloaded {fetched}/{total_limit} NYC 311 records...")
