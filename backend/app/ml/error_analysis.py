import logging
from typing import List, Dict, Any

logger = logging.getLogger("civiclens.ml.error_analysis")

def categorize_prediction_error(true_cat: str, pred_cat: str, text: str) -> str:
    """Categorizes classification error into actionable error taxonomy."""
    text_lower = text.lower()
    pair = {true_cat, pred_cat}

    if pair == {"ROAD_HAZARD", "WATER_LEAK"}:
        return "ROAD vs WATER ambiguity"
    elif pair == {"ROAD_HAZARD", "DRAINAGE"}:
        return "ROAD vs DRAINAGE ambiguity"
    elif pair == {"TRAFFIC_SIGNAL", "ROAD_HAZARD"}:
        return "TRAFFIC vs ROAD ambiguity"
    elif pair == {"SANITATION", "PUBLIC_PROPERTY"}:
        return "SANITATION vs PUBLIC_PROPERTY ambiguity"
    elif pair == {"ELECTRICAL", "STREETLIGHT"}:
        return "ELECTRICAL vs STREETLIGHT ambiguity"
    elif "no descriptor" in text_lower or len(text.strip()) < 15:
        return "insufficient evidence"
    else:
        return "OTHER / unmapped domain"

def generate_error_analysis_report(y_true: List[str], y_pred: List[str], texts: List[str], confidences: List[float]) -> List[Dict[str, Any]]:
    """Generates detailed error record log for all misclassified samples."""
    errors = []
    for idx, (t, p, txt, conf) in enumerate(zip(y_true, y_pred, texts, confidences)):
        if t != p:
            err_type = categorize_prediction_error(t, p, txt)
            errors.append({
                "sample_id": idx + 1,
                "text": txt,
                "ground_truth_category": t,
                "predicted_category": p,
                "confidence": conf,
                "error_type": err_type,
                "requires_human_review": conf < 0.60 or err_type.endswith("ambiguity")
            })
    return errors
