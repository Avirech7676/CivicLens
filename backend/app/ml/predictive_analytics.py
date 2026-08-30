import logging
import datetime
from typing import List, Dict, Any
import numpy as np

from app.core.enums import SLAStatus, PriorityLevel

logger = logging.getLogger("civiclens.ml.predictive")

class PredictiveHotspotEngine:
    """Calculates predictive risk scores and expected activity for spatial clusters."""

    @staticmethod
    def calculate_predictive_risk(incident_count: int, report_count: int, p1_p2_count: int, recent_hours: float) -> Dict[str, Any]:
        """Calculates 0-100 risk score and predicted activity window."""
        base_score = min(35, incident_count * 10)
        volume_score = min(25, report_count * 3)
        urgency_score = min(25, p1_p2_count * 12)
        recency_score = 15 if recent_hours <= 24 else (10 if recent_hours <= 72 else 5)

        total_risk = min(100, base_score + volume_score + urgency_score + recency_score)

        if total_risk >= 80:
            risk_level = "CRITICAL"
            window = "Next 24 Hours"
        elif total_risk >= 60:
            risk_level = "HIGH"
            window = "Next 48 Hours"
        elif total_risk >= 40:
            risk_level = "MEDIUM"
            window = "Next 7 Days"
        else:
            risk_level = "LOW"
            window = "Next 14 Days"

        return {
            "risk_score": total_risk,
            "risk_level": risk_level,
            "expected_activity_window": window
        }

class SLABreachPredictor:
    """Predicts SLA breach probability and resolution risk for active WorkOrders."""

    @staticmethod
    def predict_work_order_breach_risk(
        priority_level: str,
        created_at: datetime.datetime,
        sla_deadline: Optional[datetime.datetime] = None,
        is_completed: bool = False
    ) -> Dict[str, Any]:
        if is_completed:
            return {
                "predicted_status": "COMPLETED",
                "breach_probability": 0.0,
                "risk_label": "SLA COMPLETED"
            }

        now = datetime.datetime.utcnow()
        if not sla_deadline:
            # Default SLA deadlines if unassigned
            hours = 2 if "P1" in priority_level else (8 if "P2" in priority_level else 24)
            sla_deadline = created_at + datetime.timedelta(hours=hours)

        total_seconds = (sla_deadline - created_at).total_seconds()
        elapsed_seconds = (now - created_at).total_seconds()

        if total_seconds <= 0:
            return {"predicted_status": "BREACHED", "breach_probability": 1.0, "risk_label": "SLA BREACHED"}

        elapsed_ratio = min(1.5, max(0.0, elapsed_seconds / total_seconds))
        
        # Calculate breach probability using sigmoidal scaling
        breach_prob = round(float(1.0 / (1.0 + np.exp(-6.0 * (elapsed_ratio - 0.85)))), 3)

        if now >= sla_deadline:
            risk_label = "SLA BREACHED"
            predicted_status = "BREACHED"
        elif elapsed_ratio >= 0.75 or breach_prob >= 0.60:
            risk_label = "SLA BREACH LIKELY"
            predicted_status = "AT_RISK"
        else:
            risk_label = "SLA ON TRACK"
            predicted_status = "ON_TRACK"

        return {
            "predicted_status": predicted_status,
            "breach_probability": breach_prob,
            "risk_label": risk_label,
            "elapsed_ratio_pct": round(elapsed_ratio * 100, 1)
        }
