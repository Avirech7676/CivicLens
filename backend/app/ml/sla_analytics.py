import logging
from typing import List, Dict, Any
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

class HistoricalSLAAnalytics:
    """Calculates historical resolution time distributions (Median, P75, P90, P95) from historical datasets."""

    @staticmethod
    def calculate_category_sla_insights(dataset: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Calculates resolution time percentiles (in hours) grouped by CivicLens category."""
        category_durations: Dict[str, List[float]] = {}

        for row in dataset:
            cat = row.get("civiclens_category", "OTHER")
            created_str = row.get("created_date")
            closed_str = row.get("closed_date")

            if not created_str or not closed_str:
                continue

            try:
                # ISO date parsing
                c_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                cl_dt = datetime.fromisoformat(closed_str.replace("Z", "+00:00"))
                duration_hours = (cl_dt - c_dt).total_seconds() / 3600.0

                if duration_hours >= 0:
                    if cat not in category_durations:
                        category_durations[cat] = []
                    category_durations[cat].append(duration_hours)
            except Exception:
                continue

        insights = {}
        for cat, durations in category_durations.items():
            if durations:
                arr = np.array(durations)
                insights[cat] = {
                    "sample_size": len(durations),
                    "median_hours": round(float(np.median(arr)), 2),
                    "p75_hours": round(float(np.percentile(arr, 75)), 2),
                    "p90_hours": round(float(np.percentile(arr, 90)), 2),
                    "p95_hours": round(float(np.percentile(arr, 95)), 2),
                }

        return insights
