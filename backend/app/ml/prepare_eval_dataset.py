import os
import json
import datetime
import logging
import argparse
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger("civiclens.ml.prepare")

import os
import json
import datetime
import logging
import argparse
import pandas as pd
from typing import Dict, Any, Tuple

logger = logging.getLogger("civiclens.ml.prepare")

def prepare_evaluation_dataset(
    input_path: str = "backend/data/processed/nyc311_processed.csv",
    output_path: str = "backend/data/evaluation/nyc311_eval.csv",
    max_per_class: int = 1000,
    max_samples: Optional[int] = None,
    strategy: str = "category-balanced",
    seed: int = 42
) -> Tuple[str, Dict[str, Any]]:
    """Creates a stratified or random, reproducible evaluation dataset from processed NYC 311 data."""
    if not os.path.exists(input_path):
        from app.data.nyc311.ingest import create_sample_fixture_csv, ingest_nyc311_stream
        logger.info(f"Input path '{input_path}' not found. Generating sample fixture dataset...")
        fixture_path = create_sample_fixture_csv(num_rows=1000)
        ingest_nyc311_stream(csv_path=fixture_path, output_path=input_path, max_rows=1000)

    df = pd.read_csv(input_path)
    if df.empty:
        raise ValueError(f"Processed dataset at {input_path} is empty.")

    logger.info(f"Loaded processed dataset ({len(df)} rows). Strategy: {strategy}, seed: {seed}...")

    category_counts = {}

    if strategy == "random-sample" or max_samples:
        n_tot = min(len(df), max_samples or len(df))
        eval_df = df.sample(n=n_tot, random_state=seed).reset_index(drop=True)
        for cat, group in eval_df.groupby("civiclens_category"):
            category_counts[str(cat)] = len(group)
    else:
        sampled_dfs = []
        grouped = df.groupby("civiclens_category")
        for cat, group in grouped:
            n_sample = min(len(group), max_per_class)
            sampled_group = group.sample(n=n_sample, random_state=seed)
            sampled_dfs.append(sampled_group)
            category_counts[str(cat)] = len(sampled_group)

        eval_df = pd.concat(sampled_dfs, ignore_index=True)
        eval_df = eval_df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    eval_df.to_csv(output_path, index=False)

    metadata = {
        "source_filename": input_path,
        "generation_timestamp": datetime.datetime.utcnow().isoformat(),
        "total_rows": len(eval_df),
        "sampling_strategy": strategy,
        "random_seed": seed,
        "max_per_class": max_per_class,
        "max_samples": max_samples,
        "category_counts": category_counts,
        "taxonomy_mapping_version": "v1.0"
    }

    meta_path = os.path.splitext(output_path)[0] + "_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Evaluation dataset prepared successfully ({len(eval_df)} rows). Saved to {output_path}.")
    return output_path, metadata

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Prepare CivicLens Evaluation Dataset")
    parser.add_argument("--input", type=str, default="backend/data/processed/nyc311_processed.csv")
    parser.add_argument("--output", type=str, default="backend/data/evaluation/nyc311_eval.csv")
    parser.add_argument("--max-per-class", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    prepare_evaluation_dataset(
        input_path=args.input,
        output_path=args.output,
        max_per_class=args.max_per_class,
        seed=args.seed
    )
