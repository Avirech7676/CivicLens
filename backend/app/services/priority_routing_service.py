import datetime
import json
import logging
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.enums import SeverityLevel, PriorityLevel, IncidentCategory
from app.models.entities import Incident
from app.schemas.dto import IncidentAnalysisResult

logger = logging.getLogger(__name__)

# Centralized Department Mapping
DEPARTMENT_MAPPING: Dict[str, Dict[str, str]] = {
    "ROAD_HAZARD": {
        "department": "Public Works - Roads",
        "reason": "ROAD_HAZARD incidents concern roadway degradation, pothole cavities, or street hazards and are routed to Public Works - Roads."
    },
    "STREETLIGHT": {
        "department": "Electrical Maintenance",
        "reason": "STREETLIGHT incidents involve unlit lamp posts, broken street fixtures, or bulb outages and are routed to Electrical Maintenance."
    },
    "SANITATION": {
        "department": "Waste Management",
        "reason": "SANITATION incidents involve overflowing trash, illegal dumping, or uncollected waste and are routed to Waste Management."
    },
    "WATER_LEAK": {
        "department": "Water Department",
        "reason": "WATER_LEAK incidents involve pressurized pipe bursts, leaking fire hydrants, or water waste and are routed to Water Department."
    },
    "DRAINAGE": {
        "department": "Drainage & Sewer",
        "reason": "DRAINAGE incidents involve clogged catch basins, standing storm water, or sewer blockages and are routed to Drainage & Sewer."
    },
    "ELECTRICAL": {
        "department": "Electrical Maintenance",
        "reason": "ELECTRICAL incidents involve exposed wires, transformer spark hazards, or utility infrastructure and are routed to Electrical Maintenance."
    },
    "PUBLIC_PROPERTY": {
        "department": "Public Works",
        "reason": "PUBLIC_PROPERTY incidents involve damaged park amenities, playground defects, or municipal structures and are routed to Public Works."
    },
    "TRAFFIC_SIGNAL": {
        "department": "Traffic Management",
        "reason": "TRAFFIC_SIGNAL incidents involve non-functional traffic lights or turned stop signs and are routed to Traffic Management."
    },
    "OTHER": {
        "department": "General Civic Services",
        "reason": "OTHER uncategorized or general civic inquiries are routed to General Civic Services for manual triage."
    }
}


class PriorityEngine:
    @staticmethod
    def calculate_severity_score(severity: SeverityLevel) -> float:
        """Maps SeverityLevel enum to a 0–100 scale score."""
        sev_str = severity.value if hasattr(severity, 'value') else str(severity)
        sev_str = sev_str.upper()
        if sev_str == "CRITICAL":
            return 100.0
        elif sev_str == "HIGH":
            return 80.0
        elif sev_str == "MEDIUM":
            return 50.0
        elif sev_str == "LOW":
            return 20.0
        return 50.0

    @staticmethod
    def calculate_safety_risk_score(
        severity: SeverityLevel,
        hazards: List[str],
        category: str,
        severity_reason: Optional[str] = None
    ) -> float:
        """Derives safety risk score (0-100) deterministically from hazards & category."""
        base = PriorityEngine.calculate_severity_score(severity)
        
        # Hazard count boost (up to +20 points)
        hazard_boost = min(20.0, len(hazards) * 7.0) if hazards else 0.0

        # Category hazard multiplier/boost
        cat_str = str(category).upper()
        cat_boost = 0.0
        if cat_str in ["ELECTRICAL", "WATER_LEAK", "TRAFFIC_SIGNAL", "ROAD_HAZARD"]:
            cat_boost = 10.0

        risk_score = min(100.0, base * 0.70 + hazard_boost + cat_boost)
        return round(risk_score, 1)

    @staticmethod
    def calculate_report_volume_score(report_count: int) -> float:
        """Calculates non-linear report volume score (0-100)."""
        if report_count <= 1:
            return 20.0
        elif report_count == 2:
            return 45.0
        elif report_count <= 4:
            return 70.0
        elif report_count <= 8:
            return 85.0
        return 100.0

    @staticmethod
    def calculate_duration_score(created_at: Optional[datetime.datetime]) -> float:
        """Calculates duration contribution based on actual age in hours/days."""
        if not created_at:
            return 0.0
        
        now = datetime.datetime.utcnow()
        age_hours = (now - created_at).total_seconds() / 3600.0

        if age_hours < 1:
            return 10.0
        elif age_hours < 24:
            return 30.0
        elif age_hours < 72: # 3 days
            return 60.0
        elif age_hours < 168: # 1 week
            return 85.0
        return 100.0

    @staticmethod
    def calculate_public_impact_score(category: str, severity: SeverityLevel) -> float:
        """Derives public impact score based on category & severity."""
        cat_str = str(category).upper()
        sev_str = severity.value if hasattr(severity, 'value') else str(severity)

        if cat_str in ["ROAD_HAZARD", "TRAFFIC_SIGNAL", "WATER_LEAK", "DRAINAGE"] and sev_str in ["HIGH", "CRITICAL"]:
            return 90.0
        elif cat_str in ["STREETLIGHT", "SANITATION", "ELECTRICAL"]:
            return 60.0
        return 40.0

    @classmethod
    def evaluate_priority(
        cls,
        severity: SeverityLevel,
        category: str,
        hazards: List[str],
        confidence: float,
        report_count: int,
        created_at: Optional[datetime.datetime] = None,
        severity_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates a deterministic 0-100 priority score and maps to PriorityLevel + Factors.
        """
        # Calculate sub-factor scores (0-100)
        sev_score = cls.calculate_severity_score(severity)
        safety_score = cls.calculate_safety_risk_score(severity, hazards, category, severity_reason)
        vol_score = cls.calculate_report_volume_score(report_count)
        dur_score = cls.calculate_duration_score(created_at)
        impact_score = cls.calculate_public_impact_score(category, severity)
        conf_score = min(100.0, max(0.0, confidence * 100.0))

        # Sub-factor contributions
        contrib_sev = settings.PRIORITY_WEIGHT_SEVERITY * sev_score
        contrib_safety = settings.PRIORITY_WEIGHT_SAFETY_RISK * safety_score
        contrib_vol = settings.PRIORITY_WEIGHT_REPORT_VOLUME * vol_score
        contrib_dur = settings.PRIORITY_WEIGHT_DURATION * dur_score
        contrib_impact = settings.PRIORITY_WEIGHT_PUBLIC_IMPACT * impact_score
        contrib_conf = settings.PRIORITY_WEIGHT_EVIDENCE_CONFIDENCE * conf_score

        raw_total = (
            contrib_sev +
            contrib_safety +
            contrib_vol +
            contrib_dur +
            contrib_impact +
            contrib_conf
        )

        final_score = int(round(max(0.0, min(100.0, raw_total))))

        # Determine Priority Level enum
        if final_score >= settings.PRIORITY_P1_THRESHOLD:
            level = PriorityLevel.P1_CRITICAL
        elif final_score >= settings.PRIORITY_P2_THRESHOLD:
            level = PriorityLevel.P2_HIGH
        elif final_score >= settings.PRIORITY_P3_THRESHOLD:
            level = PriorityLevel.P3_MEDIUM
        else:
            level = PriorityLevel.P4_LOW

        sev_str = severity.value if hasattr(severity, 'value') else str(severity)

        factors = [
            {
                "factor": "severity",
                "score": round(sev_score, 1),
                "contribution": round(contrib_sev, 1),
                "reason": f"Incident classified as {sev_str} severity"
            },
            {
                "factor": "safety_risk",
                "score": round(safety_score, 1),
                "contribution": round(contrib_safety, 1),
                "reason": f"Assessed safety hazards ({len(hazards) if hazards else 0} detected)"
            },
            {
                "factor": "report_volume",
                "score": round(vol_score, 1),
                "contribution": round(contrib_vol, 1),
                "reason": f"{report_count} citizen report(s) linked to this incident"
            },
            {
                "factor": "duration",
                "score": round(dur_score, 1),
                "contribution": round(contrib_dur, 1),
                "reason": "Unresolved duration age factor" if created_at else "Newly submitted incident"
            },
            {
                "factor": "public_impact",
                "score": round(impact_score, 1),
                "contribution": round(contrib_impact, 1),
                "reason": f"Community impact baseline for {category}"
            },
            {
                "factor": "evidence_confidence",
                "score": round(conf_score, 1),
                "contribution": round(contrib_conf, 1),
                "reason": f"AI evidence verification confidence {round(conf_score)}%"
            }
        ]

        # Concise summary reason
        top_reasons = []
        if sev_score >= 80:
            top_reasons.append(f"{sev_str} severity")
        if safety_score >= 75:
            top_reasons.append("high safety risk")
        if report_count > 1:
            top_reasons.append(f"repeated citizen reports ({report_count})")

        reason_text = (
            f"Prioritized as {level.value} (Score {final_score}/100) due to " +
            (" + ".join(top_reasons) if top_reasons else f"{sev_str} severity baseline") + "."
        )

        return {
            "priority_score": final_score,
            "priority_level": level,
            "priority_reason": reason_text,
            "priority_factors": factors
        }


class DepartmentRoutingService:
    @staticmethod
    def route_incident(category: str) -> Dict[str, Any]:
        """
        Maps incident category to responsible municipal department deterministically.
        """
        cat_str = category.value if hasattr(category, 'value') else str(category)
        cat_str = cat_str.upper()

        mapping = DEPARTMENT_MAPPING.get(cat_str, DEPARTMENT_MAPPING["OTHER"])
        return {
            "assigned_department": mapping["department"],
            "routing_reason": mapping["reason"],
            "category": cat_str,
            "confidence": 1.0
        }
