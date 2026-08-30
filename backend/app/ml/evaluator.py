import logging
from typing import List, Dict, Any, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class ClassificationEvaluator:
    """Evaluates classification performance across AI, TF-IDF baseline, and Taxonomy rules."""

    @staticmethod
    def calculate_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
        """Calculates accuracy, precision, recall, and macro F1 score."""
        if not y_true or not y_pred or len(y_true) != len(y_pred):
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0}

        total = len(y_true)
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        accuracy = correct / total if total > 0 else 0.0

        categories = sorted(list(set(y_true) | set(y_pred)))
        precisions, recalls, f1s = [], [], []

        for cat in categories:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == cat and p == cat)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != cat and p == cat)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == cat and p != cat)

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            precisions.append(prec)
            recalls.append(rec)
            f1s.append(f1)

        supports = [sum(1 for t in y_true if t == cat) for cat in categories]
        total_support = sum(supports)
        weighted_prec = sum(p * s for p, s in zip(precisions, supports)) / total_support if total_support > 0 else 0.0
        weighted_rec = sum(r * s for r, s in zip(recalls, supports)) / total_support if total_support > 0 else 0.0
        weighted_f1 = sum(f * s for f, s in zip(f1s, supports)) / total_support if total_support > 0 else 0.0

        return {
            "total_samples": total,
            "accuracy": round(accuracy, 4),
            "precision_macro": round(float(np.mean(precisions)), 4) if precisions else 0.0,
            "recall_macro": round(float(np.mean(recalls)), 4) if recalls else 0.0,
            "f1_macro": round(float(np.mean(f1s)), 4) if f1s else 0.0,
            "weighted_precision": round(float(weighted_prec), 4),
            "weighted_recall": round(float(weighted_rec), 4),
            "weighted_f1": round(float(weighted_f1), 4),
            "category_count": len(categories)
        }

    @classmethod
    def evaluate_taxonomy_baseline(cls, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluates deterministic taxonomy rules against dataset."""
        from app.data.nyc311.taxonomy import map_nyc311_to_civiclens

        y_true = [row["civiclens_category"] for row in dataset]
        y_pred = []

        for row in dataset:
            cat, _ = map_nyc311_to_civiclens(row.get("nyc_complaint_type", ""), row.get("nyc_descriptor", ""))
            y_pred.append(cat.value)

        metrics = cls.calculate_metrics(y_true, y_pred)
        metrics["model_name"] = "Deterministic Taxonomy Rules Baseline"
        return metrics
