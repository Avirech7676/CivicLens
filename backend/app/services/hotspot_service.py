import logging
import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import IncidentStatus, PriorityLevel
from app.models.entities import Incident
from app.services.duplicate_service import haversine_distance

logger = logging.getLogger("civiclens.hotspots")

class HotspotService:

    @staticmethod
    def calculate_hotspot_score(
        incident_count: int,
        report_count: int,
        avg_priority: float,
        p1_count: int,
        p2_count: int
    ) -> int:
        """
        Calculates a deterministic 0-100 score representing civic issue concentration & severity.
        """
        min_incidents = settings.HOTSPOT_MIN_INCIDENTS or 3
        min_reports = settings.HOTSPOT_MIN_REPORTS or 5

        # 1. Density Score (Max 30)
        density_factor = min(30.0, (incident_count / min_incidents) * 15.0 + 10.0)

        # 2. Citizen Report Volume Score (Max 20)
        volume_factor = min(20.0, (report_count / min_reports) * 10.0 + 5.0)

        # 3. Priority Severity Score (Max 30)
        priority_factor = min(30.0, (avg_priority / 100.0) * 30.0)

        # 4. Critical Urgency Score (Max 20)
        urgency_factor = min(20.0, p1_count * 12.0 + p2_count * 6.0)

        total_score = round(density_factor + volume_factor + priority_factor + urgency_factor)
        return max(0, min(100, total_score))

    @staticmethod
    def determine_hotspot_level(score: int) -> str:
        if score >= 80:
            return "CRITICAL"
        elif score >= 60:
            return "HIGH"
        elif score >= 40:
            return "EMERGING"
        else:
            return "NORMAL"

    @staticmethod
    def classify_category_pattern(category_dist: Dict[str, int], dominant_category: str) -> str:
        total = sum(category_dist.values())
        if not total:
            return "OTHER"

        dominant_cnt = category_dist.get(dominant_category, 0)
        # Require >= 50% concentration for single-domain pattern
        if (dominant_cnt / total) >= 0.5:
            cat_upper = dominant_category.upper()
            if cat_upper in ["ROAD_HAZARD", "POTHOLE"]:
                return "ROAD_CONDITION"
            elif cat_upper in ["DRAINAGE", "FLOODING"]:
                return "DRAINAGE_CLUSTER"
            elif cat_upper == "STREETLIGHT":
                return "LIGHTING_CLUSTER"
            elif cat_upper == "WATER_LEAK":
                return "WATER_INFRASTRUCTURE"
            elif cat_upper in ["SANITATION", "GARBAGE"]:
                return "SANITATION_CLUSTER"
            elif cat_upper in ["ELECTRICAL", "POWER"]:
                return "ELECTRICAL_CLUSTER"
            else:
                return "OTHER"
        return "MIXED_INFRASTRUCTURE"

    @staticmethod
    def generate_explanation(
        incident_count: int,
        report_count: int,
        radius_meters: float,
        dominant_category: str,
        dominant_cnt: int,
        avg_priority: int
    ) -> str:
        cat_formatted = dominant_category.replace("_", " ").title()
        return (
            f"{incident_count} civic incidents involving {report_count} citizen reports "
            f"are concentrated within approximately {int(radius_meters)} meters. "
            f"{cat_formatted} represents {dominant_cnt} of the {incident_count} incidents, "
            f"with an average priority score of {avg_priority}."
        )

    @classmethod
    def detect_hotspots(
        cls,
        db: Session,
        status_filter: Optional[str] = None,
        min_score: int = 0
    ) -> Dict[str, Any]:
        """
        Dynamically detects spatial hotspots from canonical Incident records.
        Uses radius-based Haversine distance clustering without heavyweight PostGIS/DB deps.
        """
        query = db.query(Incident)
        if status_filter:
            query = query.filter(Incident.status == status_filter)
        
        all_incidents = query.all()

        # 1. Filter out incidents without valid spatial coordinates
        valid_incidents = [
            inc for inc in all_incidents 
            if inc.latitude is not None and inc.longitude is not None 
            and not (inc.latitude == 0.0 and inc.longitude == 0.0)
        ]

        if not valid_incidents:
            return {
                "total_hotspots": 0,
                "hotspots": [],
                "recommendations": cls.generate_recommendations([], valid_incidents)
            }

        radius_m = settings.HOTSPOT_RADIUS_METERS or 250.0
        min_incidents = settings.HOTSPOT_MIN_INCIDENTS or 3
        min_reports = settings.HOTSPOT_MIN_REPORTS or 5

        # 2. Radius-based spatial clustering (Greedy Density Clustering)
        visited = set()
        raw_clusters = []

        for inc in valid_incidents:
            if inc.id in visited:
                continue

            # Find all neighbor canonical incidents within radius
            neighbors = []
            for other in valid_incidents:
                dist = haversine_distance(inc.latitude, inc.longitude, other.latitude, other.longitude)
                if dist <= radius_m:
                    neighbors.append(other)

            total_reports_in_group = sum(len(n.reports) if n.reports else 1 for n in neighbors)

            # Check if group meets hotspot criteria
            if len(neighbors) >= min_incidents or total_reports_in_group >= min_reports:
                if len(neighbors) >= 2: # At least 2 incidents required to form a cluster
                    cluster_ids = {n.id for n in neighbors}
                    visited.update(cluster_ids)
                    raw_clusters.append(neighbors)

        # 3. Process clusters into Hotspot DTOs
        hotspots = []
        for idx, cluster in enumerate(raw_clusters, start=1):
            n_count = len(cluster)
            lats = [inc.latitude for inc in cluster]
            lons = [inc.longitude for inc in cluster]
            center_lat = round(sum(lats) / n_count, 6)
            center_lon = round(sum(lons) / n_count, 6)

            total_reports = sum(len(inc.reports) if inc.reports else 1 for inc in cluster)
            p_scores = [inc.priority_score or 50 for inc in cluster]
            avg_priority = round(sum(p_scores) / n_count)
            highest_priority = max(p_scores)

            p1_count = sum(1 for inc in cluster if inc.priority_level == PriorityLevel.P1_CRITICAL or (inc.priority_level and hasattr(inc.priority_level, 'value') and inc.priority_level.value == 'P1_CRITICAL') or (inc.priority_score or 0) >= 80)
            p2_count = sum(1 for inc in cluster if inc.priority_level == PriorityLevel.P2_HIGH or (inc.priority_level and hasattr(inc.priority_level, 'value') and inc.priority_level.value == 'P2_HIGH') or (65 <= (inc.priority_score or 0) < 80))

            # Category distribution
            cat_dist: Dict[str, int] = {}
            for inc in cluster:
                cat_val = inc.category.value if hasattr(inc.category, 'value') else str(inc.category)
                cat_dist[cat_val] = cat_dist.get(cat_val, 0) + 1

            dominant_cat = max(cat_dist.items(), key=lambda x: x[1])[0]
            dominant_cnt = cat_dist[dominant_cat]
            pattern = cls.classify_category_pattern(cat_dist, dominant_cat)

            # Status distribution
            status_dist: Dict[str, int] = {}
            for inc in cluster:
                st_val = inc.status.value if hasattr(inc.status, 'value') else str(inc.status)
                status_dist[st_val] = status_dist.get(st_val, 0) + 1

            hotspot_score = cls.calculate_hotspot_score(n_count, total_reports, avg_priority, p1_count, p2_count)
            hotspot_level = cls.determine_hotspot_level(hotspot_score)

            if hotspot_score < min_score:
                continue

            explanation = cls.generate_explanation(
                n_count, total_reports, radius_m, dominant_cat, dominant_cnt, avg_priority
            )

            # Determine human-friendly name
            sample_address = next((inc.address for inc in cluster if inc.address), None)
            area_name = sample_address or f"{dominant_cat.replace('_', ' ').title()} Cluster Area"

            hotspot_obj = {
                "hotspot_id": f"hs-{idx:03d}",
                "name": area_name,
                "latitude": center_lat,
                "longitude": center_lon,
                "radius_meters": radius_m,
                "incident_count": n_count,
                "report_count": total_reports,
                "average_priority_score": avg_priority,
                "highest_priority_score": highest_priority,
                "p1_count": p1_count,
                "p2_count": p2_count,
                "dominant_category": dominant_cat,
                "pattern": pattern,
                "category_distribution": cat_dist,
                "status_distribution": status_dist,
                "hotspot_score": hotspot_score,
                "hotspot_level": hotspot_level,
                "explanation": explanation,
                "incident_ids": [inc.id for inc in cluster]
            }
            hotspots.append(hotspot_obj)

        # Sort hotspots by score descending
        hotspots.sort(key=lambda x: x["hotspot_score"], reverse=True)

        recommendations = cls.generate_recommendations(hotspots, valid_incidents)

        return {
            "total_hotspots": len(hotspots),
            "hotspots": hotspots,
            "recommendations": recommendations
        }

    @staticmethod
    def generate_recommendations(hotspots: List[dict], incidents: List[Incident]) -> List[dict]:
        """
        Generates deterministic 'What Should We Fix First?' operational recommendations.
        Combines top critical hotspots with top individual P1 incidents.
        """
        recs = []

        # 1. Top Hotspot Recommendation
        if hotspots:
            top_hs = hotspots[0]
            recs.append({
                "type": "HOTSPOT",
                "title": f"Critical Hotspot — {top_hs['name']}",
                "hotspot_id": top_hs["hotspot_id"],
                "incident_count": top_hs["incident_count"],
                "report_count": top_hs["report_count"],
                "score": top_hs["hotspot_score"],
                "level": top_hs["hotspot_level"],
                "reason": f"{top_hs['incident_count']} incidents & {top_hs['report_count']} reports in high-density pattern ({top_hs['pattern']})"
            })

        # 2. Top Individual Incidents by Priority
        sorted_incidents = sorted(
            [inc for inc in incidents if inc.status != IncidentStatus.VERIFIED],
            key=lambda x: x.priority_score or 0,
            reverse=True
        )

        for inc in sorted_incidents[:3]:
            p_level = inc.priority_level.value if hasattr(inc.priority_level, 'value') else str(inc.priority_level)
            recs.append({
                "type": "INCIDENT",
                "title": inc.title,
                "incident_id": inc.id,
                "priority_level": p_level,
                "score": inc.priority_score or 50,
                "department": inc.assigned_department or "Unassigned",
                "reason": inc.priority_reason or "High priority score"
            })

        return recs[:4]

    @classmethod
    def get_hotspot_for_incident(cls, db: Session, incident_id: str) -> Optional[dict]:
        """Finds if a specific incident belongs to any detected hotspot."""
        res = cls.detect_hotspots(db)
        for hs in res.get("hotspots", []):
            if incident_id in hs.get("incident_ids", []):
                return hs
        return None
