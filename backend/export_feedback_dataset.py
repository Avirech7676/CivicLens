import os
import sys
import logging
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.session import SessionLocal
from app.models.entities import AIFeedback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("civiclens.export_feedback")

def export_feedback_dataset(output_path: str = "backend/data/processed/ai_feedback_dataset.csv") -> str:
    """Exports validated human review and override feedback records to CSV dataset."""
    db = SessionLocal()
    try:
        feedbacks = db.query(AIFeedback).all()
        if not feedbacks:
            logger.info("No AIFeedback records found in database.")
            records = []
        else:
            records = [
                {
                    "id": fb.id,
                    "incident_id": fb.incident_id,
                    "ai_category": fb.ai_category,
                    "ai_department": fb.ai_department,
                    "ai_confidence": fb.ai_confidence,
                    "confidence_tier": fb.confidence_tier,
                    "final_category": fb.final_category,
                    "final_department": fb.final_department,
                    "final_priority": fb.final_priority,
                    "review_status": fb.review_status,
                    "override_reason": fb.reason,
                    "reviewer_email": fb.reviewer_email,
                    "created_at": fb.created_at.isoformat() if fb.created_at else ""
                }
                for fb in feedbacks
            ]

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df = pd.DataFrame(records)
        df.to_csv(output_path, index=False)
        logger.info(f"Successfully exported {len(records)} feedback records to {output_path}")
        return output_path
    finally:
        db.close()

if __name__ == "__main__":
    export_feedback_dataset()
