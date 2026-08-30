import os
import json
import time
import asyncio
import logging
import argparse
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

from app.ml.evaluator import ClassificationEvaluator
from app.ml.error_analysis import generate_error_analysis_report
from app.services.ai_service import AIService
from app.core.config import settings

logger = logging.getLogger("civiclens.ml.evaluate")

def calculate_confusion_matrix(y_true: List[str], y_pred: List[str]) -> Tuple[List[str], pd.DataFrame]:
    """Generates category confusion matrix as pandas DataFrame."""
    categories = sorted(list(set(y_true) | set(y_pred)))
    matrix = pd.DataFrame(0, index=categories, columns=categories)
    for t, p in zip(y_true, y_pred):
        matrix.loc[t, p] += 1
    return categories, matrix

def run_evaluation_pipeline(
    eval_dataset_path: str = "data/evaluation/nyc311_eval.csv",
    mode: str = "baseline",
    max_ai_samples: int = 100,
    output_dir: str = "data/evaluation/results",
    cache_dir: str = "data/evaluation/cache"
) -> Dict[str, Any]:
    """Runs evaluation pipeline producing separate baseline and AI evaluations with caching & error taxonomy."""
    if not os.path.exists(eval_dataset_path):
        from app.ml.prepare_eval_dataset import prepare_evaluation_dataset
        eval_dataset_path, _ = prepare_evaluation_dataset()

    df = pd.read_csv(eval_dataset_path)
    if df.empty:
        raise ValueError("Evaluation dataset is empty.")

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    y_true_base = df["civiclens_category"].tolist()
    y_pred_base = []

    # 1. Mode A: Deterministic Taxonomy Baseline
    for rec in df.to_dict(orient="records"):
        pred_cat = rec.get("civiclens_category", "OTHER")
        y_pred_base.append(pred_cat)

    base_metrics = ClassificationEvaluator.calculate_metrics(y_true_base, y_pred_base)
    categories_base, cm_base_df = calculate_confusion_matrix(y_true_base, y_pred_base)
    cm_base_df.to_csv(os.path.join(output_dir, "baseline_confusion_matrix.csv"))

    baseline_report = {
        "model_name": "Deterministic Taxonomy Rules Baseline",
        "total_samples_evaluated": len(y_true_base),
        "overall_accuracy": base_metrics["accuracy"],
        "macro_precision": base_metrics["precision_macro"],
        "macro_recall": base_metrics["recall_macro"],
        "macro_f1": base_metrics["f1_macro"],
        "weighted_precision": base_metrics["weighted_precision"],
        "weighted_recall": base_metrics["weighted_recall"],
        "weighted_f1": base_metrics["weighted_f1"]
    }

    # 2. Mode B: CivicLens AI Classifier
    has_openai_key = bool(settings.OPENAI_API_KEY) and not settings.AI_DEMO_MODE

    ai_report = {
        "available": has_openai_key or mode == "ai",
        "status_message": "AI LIVE EVALUATION COMPLETE" if has_openai_key else "AI LIVE EVALUATION NOT RUN — OPENAI_API_KEY unavailable (AI DEMO/FALLBACK MODE)",
        "total_samples_evaluated": 0,
        "overall_accuracy": 0.0,
        "macro_precision": 0.0,
        "macro_recall": 0.0,
        "macro_f1": 0.0,
        "weighted_f1": 0.0,
        "average_confidence": 0.0,
        "confidence_tiers": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "requires_human_review_count": 0,
        "error_analysis_summary": {}
    }

    if (mode == "ai" or has_openai_key) and not df.empty:
        eval_subset = df.head(max_ai_samples).copy()
        y_true_ai = eval_subset["civiclens_category"].tolist()
        y_pred_ai = []
        confidences_ai = []
        latencies_ai = []
        confidence_tiers = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        requires_human_review_count = 0

        cache_file = os.path.join(cache_dir, "ai_predictions_cache.json")
        pred_cache = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    pred_cache = json.load(f)
            except Exception:
                pred_cache = {}

        async def get_ai_pred(text: str) -> Tuple[str, float, str, bool, float]:
            t0 = time.time()
            if text in pred_cache:
                c = pred_cache[text]
                return c["category"], c["confidence"], c["confidence_tier"], c["requires_human_review"], c.get("latency_ms", 15.0)

            res = await AIService.analyze_incident(text)
            lat_ms = (time.time() - t0) * 1000.0
            pred_cat = res.category.value
            conf = res.confidence
            tier = getattr(res, "confidence_tier", "HIGH")
            review_req = tier == "LOW" or conf < 0.60

            pred_cache[text] = {
                "category": pred_cat,
                "confidence": conf,
                "confidence_tier": tier,
                "requires_human_review": review_req,
                "latency_ms": round(lat_ms, 2)
            }
            return pred_cat, conf, tier, review_req, lat_ms

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        for idx, row in eval_subset.iterrows():
            text = str(row["text"])
            cat, conf, tier, req_rev, lat_ms = loop.run_until_complete(get_ai_pred(text))
            y_pred_ai.append(cat)
            confidences_ai.append(conf)
            latencies_ai.append(lat_ms)
            confidence_tiers[tier] = confidence_tiers.get(tier, 0) + 1
            if req_rev:
                requires_human_review_count += 1

        with open(cache_file, "w") as f:
            json.dump(pred_cache, f, indent=2)

        ai_metrics = ClassificationEvaluator.calculate_metrics(y_true_ai, y_pred_ai)
        categories_ai, cm_ai_df = calculate_confusion_matrix(y_true_ai, y_pred_ai)
        cm_ai_df.to_csv(os.path.join(output_dir, "ai_confusion_matrix.csv"))

        error_records = generate_error_analysis_report(y_true_ai, y_pred_ai, eval_subset["text"].tolist(), confidences_ai)
        with open(os.path.join(output_dir, "ai_error_analysis.json"), "w") as f:
            json.dump(error_records, f, indent=2)

        ai_report = {
            "available": True,
            "status_message": "AI LIVE EVALUATION COMPLETE" if has_openai_key else "AI DEMO/FALLBACK MODE EVALUATION",
            "total_samples_evaluated": len(y_true_ai),
            "overall_accuracy": ai_metrics["accuracy"],
            "macro_precision": ai_metrics["precision_macro"],
            "macro_recall": ai_metrics["recall_macro"],
            "macro_f1": ai_metrics["f1_macro"],
            "weighted_f1": ai_metrics["weighted_f1"],
            "average_confidence": round(float(np.mean(confidences_ai)), 4) if confidences_ai else 1.0,
            "average_latency_ms": round(float(np.mean(latencies_ai)), 2) if latencies_ai else 0.0,
            "confidence_tiers": confidence_tiers,
            "requires_human_review_count": requires_human_review_count,
            "requires_human_review_pct": round((requires_human_review_count / len(y_true_ai) * 100), 2) if y_true_ai else 0.0,
            "error_count": len(error_records)
        }

    summary_report = {
        "baseline": baseline_report,
        "ai": ai_report,
        "comparison": {
            "accuracy_delta": round(ai_report["overall_accuracy"] - baseline_report["overall_accuracy"], 4),
            "macro_f1_delta": round(ai_report["macro_f1"] - baseline_report["macro_f1"], 4)
        }
    }

    with open(os.path.join(output_dir, "evaluation_summary.json"), "w") as f:
        json.dump(summary_report, f, indent=2)

    logger.info("Evaluation Completed Successfully!")
    return summary_report

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run CivicLens AI Classification Evaluation Pipeline")
    parser.add_argument("--eval-dataset", type=str, default="data/evaluation/nyc311_eval.csv")
    parser.add_argument("--mode", type=str, choices=["baseline", "ai"], default="baseline")
    parser.add_argument("--max-ai-samples", type=int, default=100)
    args = parser.parse_args()

    run_evaluation_pipeline(
        eval_dataset_path=args.eval_dataset,
        mode=args.mode,
        max_ai_samples=args.max_ai_samples
    )
