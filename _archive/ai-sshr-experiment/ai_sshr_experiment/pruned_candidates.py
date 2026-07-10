"""Candidate pruning helpers for future AI-pruned WP-SCP experiments."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional

from feature_extractor import (
    CandidateRecord,
    build_candidates,
    candidate_features,
    onset_mask,
)
from rankers import CandidateRanker, RuleRanker

from feature_extractor import ensure_sshr_on_path

ensure_sshr_on_path()

from bool_func import BooleanFunction  # noqa: E402


def select_pruned_candidates(
    bf: BooleanFunction,
    keep_ratio: float = 0.1,
    keep_min: int = 100,
    objective: str = "cnot",
    ranker: Optional[CandidateRanker] = None,
    keep_onset_singletons: bool = True,
) -> List[CandidateRecord]:
    """Rank candidates and return a pruned set with singleton safeguards."""
    if not 0 < keep_ratio <= 1:
        raise ValueError("keep_ratio must be in (0, 1]")
    ranker = ranker or RuleRanker()
    records = build_candidates(bf.n)
    a_mask = onset_mask(bf)

    features_list = [candidate_features(rec, a_mask, bf.n, 0.0, objective) for rec in records]
    scores = ranker.score_many(features_list)
    scored = list(zip(scores, records))
    scored.sort(key=lambda item: item[0], reverse=True)

    keep_count = max(keep_min, int(len(records) * keep_ratio))
    keep_count = min(keep_count, len(records))
    selected = {rec.idx: rec for _, rec in scored[:keep_count]}

    if keep_onset_singletons:
        for rec in records:
            if rec.is_singleton and (rec.mask & a_mask):
                selected[rec.idx] = rec

    return sorted(selected.values(), key=lambda rec: rec.idx)


def write_candidate_csv(path: Path, records: List[CandidateRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "idx",
                "dim",
                "size",
                "cnot_cost",
                "t_cost",
                "control_count",
                "is_singleton",
                "mask",
            ]
        )
        for rec in records:
            writer.writerow(
                [
                    rec.idx,
                    rec.dim,
                    rec.size,
                    rec.cnot_cost,
                    rec.t_cost,
                    rec.control_count,
                    int(rec.is_singleton),
                    rec.mask,
                ]
            )

