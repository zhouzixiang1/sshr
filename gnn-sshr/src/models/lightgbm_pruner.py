"""LightGBM-based candidate pruner for SSHR.

This module implements the P0 baseline ranker that the GNN candidate scorer
must beat. It learns to rank parallelotope candidates per Boolean function
using LightGBM's LambdaRank objective. When per-group sizes are too small
to support LambdaRank meaningfully, it gracefully falls back to a binary
classification objective.

Typical use:

    >>> pruner = LightGBMPruner()
    >>> pruner.fit(df, feature_cols=['dim', 'cost', 'overlap'])
    >>> scores = pruner.predict(df, feature_cols=['dim', 'cost', 'overlap'])
    >>> pruner.save('results/models/lgbm_n3.txt')
    >>> pruner = LightGBMPruner.load('results/models/lgbm_n3.txt')

CLI:
    python -m src.models.lightgbm_pruner \
        --train data/ilp/n3_ilp_cnot.csv \
        --out results/models/lgbm_n3.txt
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

# --- Default hyperparameters -------------------------------------------------
# Modest defaults are chosen so the baseline trains fast on CPU and provides a
# meaningful target for the GNN to beat without overfitting tiny datasets.
DEFAULT_PARAMS: dict[str, Any] = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 5,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 5,
    "verbose": -1,
}

# Minimum average group size below which LambdaRank is skipped in favour of
# binary classification. Ranking objectives need several items per group to
# learn meaningful pairwise preferences.
_MIN_AVG_GROUP_SIZE_FOR_RANK: float = 3.0


class LightGBMPruner:
    """LightGBM ranker / classifier that scores candidate parallelotopes.

    The pruner trains either a LambdaRank model (preferred) or a binary
    classifier (fallback) on tabular features extracted per (function,
    candidate) pair. At inference time it returns a real-valued score per
    row that downstream code uses to keep the top-K candidates per
    function before handing them to the WP-SCP ILP solver.

    Parameters
    ----------
    params : dict, optional
        Overrides for the default LightGBM hyperparameters. Anything not
        provided falls back to :data:`DEFAULT_PARAMS`.

    Attributes
    ----------
    params : dict
        Resolved hyperparameter dictionary.
    booster_ : lightgbm.Booster | None
        Trained booster. ``None`` until :meth:`fit` is called.
    objective_ : str | None
        Either ``"lambdarank"`` or ``"binary"`` depending on which path
        :meth:`fit` actually took.
    feature_cols_ : list[str] | None
        Feature column names captured at fit time.
    """

    def __init__(self, params: dict | None = None) -> None:
        self.params: dict[str, Any] = dict(DEFAULT_PARAMS)
        if params:
            self.params.update(params)
        self.booster_: lgb.Booster | None = None
        self.objective_: str | None = None
        self.feature_cols_: list[str] | None = None

    # ------------------------------------------------------------------ fit --
    def fit(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        label_col: str = "label",
        group_col: str = "func_id",
    ) -> "LightGBMPruner":
        """Train the model on a dataframe of (function, candidate) rows.

        Parameters
        ----------
        df : pandas.DataFrame
            Rows are individual candidates. Must contain ``feature_cols``,
            ``label_col`` and ``group_col``.
        feature_cols : list[str]
            Column names to feed as features.
        label_col : str, default ``"label"``
            Column with the relevance label (binary 0/1 or graded int).
        group_col : str, default ``"func_id"``
            Column identifying which Boolean function each candidate
            belongs to. Used to build LightGBM group sizes.

        Returns
        -------
        LightGBMPruner
            ``self`` for chaining.

        Notes
        -----
        Uses LambdaRank when there are enough candidates per group;
        otherwise falls back to binary classification. The fallback also
        triggers when there is only a single group, since LambdaRank
        cannot learn pairwise preferences across groups.
        """
        for col in (*feature_cols, label_col, group_col):
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' missing from dataframe")

        # Sort so rows of the same group are contiguous, as LightGBM
        # interprets the group vector as run-lengths over the row order.
        df_sorted = df.sort_values(group_col, kind="stable").reset_index(drop=True)
        X = df_sorted[feature_cols].to_numpy(dtype=np.float32)
        y = df_sorted[label_col].to_numpy()
        groups_series = df_sorted[group_col]
        # value_counts(sort=False) preserves the order of first appearance,
        # which after the stable sort is the contiguous-group order.
        group_sizes = groups_series.value_counts(sort=False).to_numpy()

        n_groups = len(group_sizes)
        avg_group = float(group_sizes.mean()) if n_groups else 0.0
        use_rank = n_groups >= 2 and avg_group >= _MIN_AVG_GROUP_SIZE_FOR_RANK

        params = dict(self.params)
        n_estimators = int(params.pop("n_estimators", 200))

        if use_rank:
            params["objective"] = "lambdarank"
            params.setdefault("metric", "ndcg")
            params.setdefault("label_gain", list(range(int(max(y)) + 2)))
            dataset = lgb.Dataset(X, label=y, group=group_sizes, free_raw_data=False)
            self.objective_ = "lambdarank"
        else:
            # Binary fallback: collapse graded labels to {0, 1}.
            y_bin = (y > 0).astype(np.int32)
            params["objective"] = "binary"
            params.setdefault("metric", "binary_logloss")
            dataset = lgb.Dataset(X, label=y_bin, free_raw_data=False)
            self.objective_ = "binary"

        self.booster_ = lgb.train(
            params,
            dataset,
            num_boost_round=n_estimators,
        )
        self.feature_cols_ = list(feature_cols)
        return self

    # -------------------------------------------------------------- predict --
    def predict(self, df: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
        """Score each row of ``df``.

        Parameters
        ----------
        df : pandas.DataFrame
            Rows to score.
        feature_cols : list[str]
            Feature column names. Must match what was used at fit time.

        Returns
        -------
        numpy.ndarray
            One score per row. Higher is better. For ranking models this
            is the LambdaRank raw score; for the binary fallback it is
            the predicted probability of the positive class.
        """
        if self.booster_ is None:
            raise RuntimeError("LightGBMPruner.predict called before fit/load")
        X = df[feature_cols].to_numpy(dtype=np.float32)
        return np.asarray(self.booster_.predict(X), dtype=np.float64)

    # ------------------------------------------------------------ save/load --
    def save(self, path: str) -> None:
        """Persist the model and its sidecar metadata.

        Parameters
        ----------
        path : str
            Output path for the LightGBM text model file. A companion
            ``<path>.meta.json`` is also written holding objective and
            feature column names.
        """
        if self.booster_ is None:
            raise RuntimeError("LightGBMPruner.save called before fit")
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self.booster_.save_model(str(out_path))
        meta = {
            "objective": self.objective_,
            "feature_cols": self.feature_cols_,
            "params": self.params,
        }
        out_path.with_suffix(out_path.suffix + ".meta.json").write_text(
            json.dumps(meta, indent=2)
        )

    @classmethod
    def load(cls, path: str) -> "LightGBMPruner":
        """Load a previously saved model from disk.

        Parameters
        ----------
        path : str
            Path passed to :meth:`save`.

        Returns
        -------
        LightGBMPruner
            A pruner with ``booster_``, ``objective_`` and
            ``feature_cols_`` populated.
        """
        in_path = Path(path)
        meta_path = in_path.with_suffix(in_path.suffix + ".meta.json")
        meta: dict[str, Any] = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        instance = cls(params=meta.get("params"))
        instance.booster_ = lgb.Booster(model_file=str(in_path))
        instance.objective_ = meta.get("objective")
        instance.feature_cols_ = meta.get("feature_cols")
        return instance


# ---------------------------------------------------------------------- CLI --
def _infer_feature_cols(
    df: pd.DataFrame,
    label_col: str,
    group_col: str,
    extra_drop: list[str] | None = None,
) -> list[str]:
    """Pick numeric feature columns by excluding bookkeeping columns."""
    drop = {label_col, group_col}
    if extra_drop:
        drop.update(extra_drop)
    return [
        c
        for c in df.columns
        if c not in drop and pd.api.types.is_numeric_dtype(df[c])
    ]


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train the LightGBM SSHR candidate pruner (P0 baseline).",
    )
    parser.add_argument(
        "--train",
        required=True,
        help="Path to a CSV with one row per (function, candidate) pair.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Destination path for the saved LightGBM model.",
    )
    parser.add_argument(
        "--label-col",
        default="label",
        help="Column with relevance labels (default: 'label').",
    )
    parser.add_argument(
        "--group-col",
        default="func_id",
        help="Column identifying functions / query groups (default: 'func_id').",
    )
    parser.add_argument(
        "--feature-cols",
        default=None,
        help=(
            "Comma-separated feature column names. If omitted, all numeric "
            "columns except --label-col and --group-col are used."
        ),
    )
    parser.add_argument(
        "--n-estimators", type=int, default=DEFAULT_PARAMS["n_estimators"]
    )
    parser.add_argument(
        "--max-depth", type=int, default=DEFAULT_PARAMS["max_depth"]
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=DEFAULT_PARAMS["learning_rate"],
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    df = pd.read_csv(args.train)
    if args.feature_cols:
        feature_cols = [c.strip() for c in args.feature_cols.split(",") if c.strip()]
    else:
        feature_cols = _infer_feature_cols(df, args.label_col, args.group_col)
        if not feature_cols:
            raise SystemExit(
                "No numeric feature columns found; pass --feature-cols explicitly."
            )

    params = {
        "n_estimators": args.n_estimators,
        "max_depth": args.max_depth,
        "learning_rate": args.learning_rate,
    }
    pruner = LightGBMPruner(params=params)
    pruner.fit(
        df,
        feature_cols=feature_cols,
        label_col=args.label_col,
        group_col=args.group_col,
    )
    pruner.save(args.out)

    print(
        json.dumps(
            {
                "objective": pruner.objective_,
                "n_rows": int(len(df)),
                "n_features": len(feature_cols),
                "features": feature_cols,
                "model_path": os.path.abspath(args.out),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
