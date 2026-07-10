"""Train LightGBM ranking model on collected training data.

Pipeline:
  1. Load CSV files from data_collector output
  2. Build LightGBM Dataset with query groups (func_tt + step)
  3. Train lambdarank model with early stopping
  4. Evaluate NDCG@1/3/5 on held-out functions
  5. Save model and print feature importance

Run in mcts-qoracle env.
"""
from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from feature_extractor import feature_names


def load_data(
    csv_paths: List[Path],
    feature_cols: List[str],
) -> pd.DataFrame:
    """Load and concatenate CSV data files."""
    frames = []
    for p in csv_paths:
        if p.exists():
            df = pd.read_csv(p)
            frames.append(df)
            print(f"  loaded {p.name}: {len(df)} rows")
        else:
            print(f"  missing: {p}")
    if not frames:
        raise FileNotFoundError(f"No data files found in {csv_paths}")
    return pd.concat(frames, ignore_index=True)


def build_groups(df: pd.DataFrame) -> np.ndarray:
    """Build group ID per sample: (func_tt, step) defines a query group."""
    # Use label_type to distinguish: ILP uses func_tt as group, beam uses (func_tt, step)
    groups = np.zeros(len(df), dtype=np.int64)
    # Create composite key: hash of (func_tt, step) -> integer group id
    keys = df["func_tt"].astype(str) + "_" + df["step"].astype(str)
    _, inverse = np.unique(keys.values, return_inverse=True)
    return inverse


def split_by_function(
    df: pd.DataFrame,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split data by function (not by step) to avoid data leakage."""
    func_tts = df["func_tt"].unique()
    rng = random.Random(seed)
    rng.shuffle(func_tts)
    n_val = max(1, int(len(func_tts) * val_ratio))
    val_tts = set(func_tts[:n_val])
    train_df = df[~df["func_tt"].isin(val_tts)]
    val_df = df[df["func_tt"].isin(val_tts)]
    return train_df, val_df


def count_groups(groups: np.ndarray) -> List[int]:
    """Count samples per group for LightGBM Dataset."""
    _, counts = np.unique(groups, return_counts=True)
    return counts.tolist()


def evaluate_ranking(
    model,
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
) -> Dict[str, float]:
    """Evaluate ranking quality: Hit@1, MRR, NDCG proxy."""
    preds = model.predict(X)
    unique_groups = np.unique(groups)

    hit1_list = []
    mrr_list = []

    for g in unique_groups:
        mask = groups == g
        g_preds = preds[mask]
        g_labels = y[mask]

        # Sort by predicted score descending
        order = np.argsort(-g_preds)
        sorted_labels = g_labels[order]

        # Hit@1: is the top-1 prediction the true positive?
        hit1_list.append(1.0 if sorted_labels[0] > 0.5 else 0.0)

        # MRR: rank of first positive
        pos_ranks = np.where(sorted_labels > 0.5)[0]
        if len(pos_ranks) > 0:
            mrr_list.append(1.0 / (pos_ranks[0] + 1))
        else:
            mrr_list.append(0.0)

    return {
        "n_groups": len(unique_groups),
        "hit_at_1": np.mean(hit1_list),
        "mrr": np.mean(mrr_list),
    }


def train_ltr(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    feature_cols: List[str],
    output_dir: Path,
    objective: str = "cnot",
) -> None:
    """Train LightGBM ranking model."""
    import lightgbm as lgb

    X_train = train_df[feature_cols].values.astype(np.float32)
    y_train = train_df["label"].values.astype(np.float32)
    groups_train = build_groups(train_df)
    train_group_sizes = count_groups(groups_train)

    X_val = val_df[feature_cols].values.astype(np.float32)
    y_val = val_df["label"].values.astype(np.float32)
    groups_val = build_groups(val_df)
    val_group_sizes = count_groups(groups_val)

    print(f"  train: {len(X_train)} samples, {len(train_group_sizes)} groups")
    print(f"  val:   {len(X_val)} samples, {len(val_group_sizes)} groups")
    print(f"  label=1 ratio: train={y_train.mean():.4f}, val={y_val.mean():.4f}")

    train_data = lgb.Dataset(
        X_train, label=y_train, group=train_group_sizes,
        feature_name=feature_cols, free_raw_data=False,
    )
    val_data = lgb.Dataset(
        X_val, label=y_val, group=val_group_sizes,
        feature_name=feature_cols, reference=train_data, free_raw_data=False,
    )

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "eval_at": [1, 3, 5, 10],
        "learning_rate": 0.05,
        "num_leaves": 63,
        "min_data_in_leaf": 50,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "lambda_l1": 0.1,
        "lambda_l2": 1.0,
        "max_depth": 6,
        "verbose": -1,
        "seed": 42,
    }

    model = lgb.train(
        params,
        train_data,
        num_boost_round=1000,
        valid_sets=[val_data],
        valid_names=["val"],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50),
            lgb.log_evaluation(period=50),
        ],
    )

    # Save model
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"ranker_{objective}.txt"
    model.save_model(str(model_path))
    print(f"\n  model saved to {model_path}")

    # Feature importance
    gains = model.feature_importance("gain")
    importance = sorted(
        zip(feature_cols, gains), key=lambda x: -x[1]
    )
    print("\n  Feature importance (top 10):")
    for name, gain in importance[:10]:
        print(f"    {name:25s} {gain:.1f}")

    # Evaluate on val set
    val_metrics = evaluate_ranking(model, X_val, y_val, groups_val)
    print(f"\n  Val metrics: {val_metrics}")

    # Also evaluate on train set for sanity
    train_metrics = evaluate_ranking(model, X_train, y_train, groups_train)
    print(f"  Train metrics: {train_metrics}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train AI-SSHR ranking model")
    parser.add_argument("--data-dir", type=Path,
                        default=Path(__file__).parent / "results" / "training_data")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).parent / "results" / "models")
    parser.add_argument("--objective", choices=["cnot", "t", "both"], default="both")
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", nargs="+", type=int, default=None,
                        help="Only use data for these n values")
    args = parser.parse_args()

    fcols = feature_names()

    objectives = ["cnot", "t"] if args.objective == "both" else [args.objective]

    for obj in objectives:
        print(f"\n{'='*60}")
        print(f"Training for objective={obj}")
        print(f"{'='*60}")

        # Find all relevant CSV files
        csv_files = sorted(args.data_dir.glob(f"*_{obj}.csv"))
        if args.n:
            csv_files = [f for f in csv_files
                         if any(f"_n{n}_" in f.name for n in args.n)]

        if not csv_files:
            print(f"  No data files found for objective={obj}")
            continue

        print(f"  Data files: {[f.name for f in csv_files]}")
        df = load_data(csv_files, fcols)
        print(f"  Total: {len(df)} rows, {df['func_tt'].nunique()} functions")

        train_df, val_df = split_by_function(df, args.val_ratio, args.seed)
        print(f"  Split: train={len(train_df)} ({train_df['func_tt'].nunique()} fns), "
              f"val={len(val_df)} ({val_df['func_tt'].nunique()} fns)")

        train_ltr(train_df, val_df, fcols, args.output_dir, obj)


if __name__ == "__main__":
    main()
