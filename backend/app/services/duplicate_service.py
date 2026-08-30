import math
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from openai import OpenAI

from app.core.config import settings
from app.core.enums import IncidentStatus, IncidentCategory
from app.models.entities import Incident, Report
from app.schemas.dto import IncidentAnalysisResult

logger = logging.getLogger(__name__)

# Category compatibility map (explicit matching rules)
# Categories match if identical, or if listed in compatible sets.
COMPATIBLE_CATEGORIES: Dict[str, List[str]] = {
    "ROAD_HAZARD": ["ROAD_HAZARD", "TRAFFIC_SIGNAL"],
    "TRAFFIC_SIGNAL": ["TRAFFIC_SIGNAL", "ROAD_HAZARD"],
    "STREETLIGHT": ["STREETLIGHT", "ELECTRICAL"],
    "ELECTRICAL": ["ELECTRICAL", "STREETLIGHT"],
    "WATER_LEAK": ["WATER_LEAK", "DRAINAGE"],
    "DRAINAGE": ["DRAINAGE", "WATER_LEAK"],
    "SANITATION": ["SANITATION"],
    "PUBLIC_PROPERTY": ["PUBLIC_PROPERTY"],
    "OTHER": ["OTHER"]
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points on the Earth in meters
    using the Haversine formula.
    """
    R = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def lexical_similarity(text1: str, text2: str) -> float:
    """
    Fallback text similarity measure (combining Jaccard word set similarity and overlap ratio)
    when embeddings API is unconfigured or unavailable.
    """
    def tokenize(t: str) -> list:
        return re.findall(r'\w+', t.lower())

    words1 = tokenize(text1)
    words2 = tokenize(text2)
    if not words1 or not words2:
        return 0.0
    
    set1 = set(words1)
    set2 = set(words2)
    
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # Also check key keyword overlaps (e.g. pothole, road, gate, water, light)
    overlap_min = len(intersection) / min(len(set1), len(set2)) if min(len(set1), len(set2)) > 0 else 0.0
    
    # Combined lexical score
    return max(jaccard, overlap_min * 0.85)


class EmbeddingService:
    _embedding_cache: Dict[str, List[float]] = {}

    @classmethod
    def get_embedding(cls, text: str) -> Optional[List[float]]:
        """
        Gets vector embedding from OpenAI for text using configured model.
        Returns None if API key missing, demo mode active, or request fails.
        Caches embeddings in memory to prevent duplicate API requests.
        """
        if not text:
            return None
        if text in cls._embedding_cache:
            return cls._embedding_cache[text]

        if settings.AI_DEMO_MODE or not settings.OPENAI_API_KEY:
            return None
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            res = client.embeddings.create(
                input=text,
                model=settings.OPENAI_EMBEDDING_MODEL
            )
            emb = res.data[0].embedding
            if len(cls._embedding_cache) < 500: # Bound cache size
                cls._embedding_cache[text] = emb
            return emb
        except Exception as e:
            logger.warning(f"Failed to fetch embedding: {e}")
            return None


class DuplicateDetectionService:
    @staticmethod
    def is_category_compatible(cat1: str, cat2: str) -> bool:
        """Checks if two category strings are compatible according to taxonomy rules."""
        c1 = cat1.upper() if isinstance(cat1, str) else cat1.value if hasattr(cat1, 'value') else str(cat1)
        c2 = cat2.upper() if isinstance(cat2, str) else cat2.value if hasattr(cat2, 'value') else str(cat2)
        if c1 == c2:
            return True
        allowed = COMPATIBLE_CATEGORIES.get(c1, [c1])
        return c2 in allowed

    @staticmethod
    def calculate_geo_score(distance_meters: Optional[float], max_radius: float) -> float:
        """
        Calculates geographic proximity score (1.0 at 0m distance, decaying smoothly to 0.0 at max_radius).
        If distance is None, returns None.
        """
        if distance_meters is None:
            return 0.0
        if distance_meters <= 0:
            return 1.0
        if distance_meters >= max_radius:
            return 0.0
        # Linear decay within radius
        return 1.0 - (distance_meters / max_radius)

    @classmethod
    def evaluate_candidate(
        cls,
        report_desc: str,
        report_lat: Optional[float],
        report_lon: Optional[float],
        analysis: IncidentAnalysisResult,
        incident: Incident,
        report_embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates duplicate score between incoming report + analysis and an existing active Incident.
        Returns structured dictionary with breakdown and total match confidence.
        """
        # 1. Category Compatibility
        cat_match = cls.is_category_compatible(analysis.category, incident.category)
        
        # 2. Distance Calculation
        distance_meters: Optional[float] = None
        has_location = (report_lat is not None and report_lon is not None and
                        incident.latitude is not None and incident.longitude is not None)
        if has_location:
            distance_meters = haversine_distance(report_lat, report_lon, incident.latitude, incident.longitude)

        geo_score = cls.calculate_geo_score(distance_meters, settings.DUPLICATE_RADIUS_METERS) if has_location else None

        # 3. Semantic Similarity
        # Gather text representation of existing incident
        incident_combined_text = f"{incident.title}. {incident.description}"
        report_combined_text = f"{analysis.title}. {report_desc}"

        semantic_sim: float = 0.0
        if report_embedding is not None:
            incident_emb = EmbeddingService.get_embedding(incident_combined_text)
            if incident_emb:
                semantic_sim = cosine_similarity(report_embedding, incident_emb)
            else:
                semantic_sim = lexical_similarity(report_combined_text, incident_combined_text)
        else:
            semantic_sim = lexical_similarity(report_combined_text, incident_combined_text)

        # 4. Weighted Match Score Calculation
        # Weights: semantic=0.55, geo=0.35, category=0.10
        # If location is missing, rebalance weights across available signals (semantic + category)
        category_score = 1.0 if cat_match else 0.0

        if not cat_match:
            # Strong penalty if categories are incompatible
            total_confidence = semantic_sim * 0.4
        elif geo_score is not None:
            # When category matches and geo location is very close, boost total score
            base_score = (
                settings.WEIGHT_SEMANTIC * semantic_sim +
                settings.WEIGHT_GEOGRAPHIC * geo_score +
                settings.WEIGHT_CATEGORY * category_score
            )
            # If distance is within 30m and category matches, give proximity boost
            if distance_meters is not None and distance_meters <= 50.0:
                total_confidence = max(base_score, 0.50 * geo_score + 0.35 * semantic_sim + 0.15)
            else:
                total_confidence = base_score
        else:
            # Rebalanced weights without location (semantic 0.85, category 0.15)
            total_confidence = 0.85 * semantic_sim + 0.15 * category_score

        # Bound confidence score between 0.0 and 1.0
        total_confidence = max(0.0, min(1.0, total_confidence))

        # Generate Human Readable Match Explanation
        cat_str = analysis.category.value if hasattr(analysis.category, "value") else str(analysis.category)
        reasons = []
        if cat_match:
            reasons.append(f"category matches ({cat_str})")
        else:
            reasons.append(f"category differs ({cat_str} vs {incident.category})")

        if distance_meters is not None:
            reasons.append(f"reported location is {round(distance_meters, 1)}m away")
        else:
            reasons.append("location coordinates unavailable")

        reasons.append(f"semantic similarity is {round(semantic_sim * 100)}%")

        explanation = (
            f"Evaluated against Incident #{incident.id[:8].upper()}: " + ", ".join(reasons) + "."
        )

        return {
            "matched_incident_id": incident.id,
            "incident": incident,
            "semantic_similarity": round(semantic_sim, 4),
            "distance_meters": round(distance_meters, 1) if distance_meters is not None else None,
            "category_match": cat_match,
            "match_confidence": round(total_confidence, 4),
            "reason": explanation
        }

    @classmethod
    def find_matching_incident(
        cls,
        db: Session,
        report_desc: str,
        report_lat: Optional[float],
        report_lon: Optional[float],
        analysis: IncidentAnalysisResult
    ) -> Dict[str, Any]:
        """
        Retrieves active/open incidents and scores them against incoming report.
        Returns match dict if candidate exceeds threshold, else returns no-match result.
        """
        # Active statuses where duplicate aggregation makes sense
        active_statuses = [
            IncidentStatus.SUBMITTED,
            IncidentStatus.TRIAGED,
            IncidentStatus.ASSIGNED,
            IncidentStatus.IN_PROGRESS
        ]

        active_incidents = db.query(Incident).filter(Incident.status.in_(active_statuses)).all()
        if not active_incidents:
            return {
                "is_duplicate": False,
                "matched_incident_id": None,
                "semantic_similarity": 0.0,
                "distance_meters": None,
                "category_match": False,
                "match_confidence": 0.0,
                "reason": "No active incidents found to match against."
            }

        # Precompute embedding for new report if OpenAI embeddings are enabled
        report_combined_text = f"{analysis.title}. {report_desc}"
        report_embedding = EmbeddingService.get_embedding(report_combined_text)

        best_candidate: Optional[Dict[str, Any]] = None
        highest_confidence: float = -1.0

        for incident in active_incidents:
            candidate = cls.evaluate_candidate(
                report_desc=report_desc,
                report_lat=report_lat,
                report_lon=report_lon,
                analysis=analysis,
                incident=incident,
                report_embedding=report_embedding
            )
            if candidate["match_confidence"] > highest_confidence:
                highest_confidence = candidate["match_confidence"]
                best_candidate = candidate

        threshold = settings.DUPLICATE_CONFIDENCE_THRESHOLD

        if best_candidate and best_candidate["match_confidence"] >= threshold:
            best_candidate["is_duplicate"] = True
            return best_candidate

        return {
            "is_duplicate": False,
            "matched_incident_id": best_candidate["matched_incident_id"] if best_candidate else None,
            "semantic_similarity": best_candidate["semantic_similarity"] if best_candidate else 0.0,
            "distance_meters": best_candidate["distance_meters"] if best_candidate else None,
            "category_match": best_candidate["category_match"] if best_candidate else False,
            "match_confidence": best_candidate["match_confidence"] if best_candidate else 0.0,
            "reason": best_candidate["reason"] if best_candidate else "No matching incident crossed confidence threshold."
        }
