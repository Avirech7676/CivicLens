import logging
from typing import List, Dict, Any
from app.services.hotspot_service import HotspotService

logger = logging.getLogger(__name__)

class HistoricalHotspotAnalytics:
    """Calculates spatial density hotspots on historical datasets without polluting operational DB."""

    @staticmethod
    def calculate_historical_clusters(dataset: List[Dict[str, Any]], radius_meters: float = 250.0) -> List[Dict[str, Any]]:
        """Groups historical dataset records into spatial density clusters using Haversine distance."""
        valid_records = [
            r for r in dataset 
            if r.get("latitude") and r.get("longitude")
        ]

        visited = set()
        clusters = []

        for i, rec in enumerate(valid_records):
            if i in visited:
                continue

            lat1, lon1 = rec["latitude"], rec["longitude"]
            cluster_members = [rec]
            visited.add(i)

            for j, other in enumerate(valid_records):
                if j in visited:
                    continue
                lat2, lon2 = other["latitude"], other["longitude"]
                dist = HotspotService.haversine_distance(lat1, lon1, lat2, lon2)
                if dist <= radius_meters:
                    cluster_members.append(other)
                    visited.add(j)

            if len(cluster_members) >= 3:
                categories = [m.get("civiclens_category", "OTHER") for m in cluster_members]
                dominant_cat = max(set(categories), key=categories.count)
                
                clusters.append({
                    "cluster_id": f"hist-hs-{len(clusters) + 1}",
                    "center_latitude": lat1,
                    "center_longitude": lon1,
                    "incident_count": len(cluster_members),
                    "dominant_category": dominant_cat,
                    "location_summary": rec.get("nyc_descriptor") or rec.get("nyc_complaint_type") or "Historical Cluster Area"
                })

        return clusters
