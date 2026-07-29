#!/usr/bin/env python3
"""Train a small neural prior for ANF factor actions."""
from __future__ import annotations

# --- project root bootstrap (so this script runs standalone) ---
import sys as _sys
from pathlib import Path as _Path
_PROJ_ROOT = _Path(__file__).resolve().parent.parent
if str(_PROJ_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJ_ROOT))


import argparse
import csv
import hashlib
import json
import os
import random
import statistics
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Mapping, Sequence, Tuple

import torch
from torch import nn

from src.anf_utils import anf_monomials, random_anf_function, random_truth_function, structured_suite
from src.factor_plan import (
    SearchConfig,
    action_features,
    candidate_actions,
    direct_plan,
    factor_cost,
    greedy_plan,
    boolean_linear_factor_actions,
    linear_factor_actions,
)
from src.neural_policy import ActionNet, default_device, file_sha256, save_model


THIS_DIR = Path(__file__).resolve().parent


TRUTH_HASH_ALGORITHM = "sha256(canonical-json({'n':n,'truth_table_hex':fixed-width-lowercase-without-0x}))"
SPLIT_NAMES = ("train", "valid", "test")


PRESETS = {
    "smoke": {"samples": 80, "epochs": 30, "n_min": 3, "n_max": 7},
    "rollout": {"samples": 520, "epochs": 60, "n_min": 3, "n_max": 9},
    "linear_highdim": {"samples": 260, "epochs": 50, "n_min": 8, "n_max": 14},
    "linear_root_teacher": {"samples": 140, "epochs": 70, "n_min": 10, "n_max": 14},
    "linear_root_pairwise": {"samples": 360, "epochs": 90, "n_min": 10, "n_max": 14},
    "boolean_linear_root_pairwise": {"samples": 260, "epochs": 90, "n_min": 10, "n_max": 14},
    "main": {"samples": 2200, "epochs": 80, "n_min": 3, "n_max": 10},
}


@dataclass(frozen=True)
class FunctionDatasetRecord:
    """Provenance for all action rows derived from one Boolean function."""

    function_hash: str
    n: int
    family: str
    generation_seed: int | None
    name: str
    aliases: tuple[str, ...]
    generator_params: Mapping[str, Any]
    row_start: int
    row_count: int

    def manifest_row(self) -> dict[str, Any]:
        return {
            "function_hash": self.function_hash,
            "truth_table_sha256": self.function_hash,
            "n": self.n,
            "family": self.family,
            "generation_seed": self.generation_seed,
            "name": self.name,
            "aliases": list(self.aliases),
            "generator_params": dict(self.generator_params),
            "row_count": self.row_count,
        }


@dataclass(frozen=True)
class DatasetBundle:
    """Action-level tensors plus their function-level leakage boundary."""

    features: torch.Tensor
    labels: torch.Tensor
    state_groups: torch.Tensor
    row_function_hashes: tuple[str, ...]
    functions: tuple[FunctionDatasetRecord, ...]
    zero_row_functions: tuple[FunctionDatasetRecord, ...]
    excluded_functions: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class FunctionSplit:
    """Indices and function hashes for a strict train/valid/test split."""

    train_idx: torch.Tensor
    valid_idx: torch.Tensor
    test_idx: torch.Tensor
    train_hashes: tuple[str, ...]
    valid_hashes: tuple[str, ...]
    test_hashes: tuple[str, ...]

    def indices(self, split: str) -> torch.Tensor:
        if split not in SPLIT_NAMES:
            raise KeyError(split)
        return getattr(self, f"{split}_idx")

    def hashes(self, split: str) -> tuple[str, ...]:
        if split not in SPLIT_NAMES:
            raise KeyError(split)
        return getattr(self, f"{split}_hashes")


@dataclass
class _GeneratedFunction:
    name: str
    bf: Any
    family: str
    generation_seed: int | None
    generator_params: dict[str, Any]
    aliases: list[str]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def truth_table_sha256(bf_or_n: Any, truth_table: int | str | None = None) -> str:
    """Return the canonical Boolean-function key used by the final benchmark.

    ``n`` is part of the preimage and the truth table is fixed-width, lowercase
    hexadecimal without ``0x``.  This makes leading zeroes and functions with
    different arities unambiguous while matching
    ``submission_competition/benchmark_suite_v1.json``.
    """

    if truth_table is None:
        n = int(bf_or_n.n)
        tt = int(bf_or_n.truth_table)
    else:
        n = int(bf_or_n)
        if isinstance(truth_table, str):
            raw_truth = truth_table.strip().lower()
            tt = int(raw_truth, 0) if raw_truth.startswith("0x") else int(raw_truth, 16)
        else:
            tt = int(truth_table)
    if n < 0:
        raise ValueError("n must be nonnegative")
    width = max(1, ((1 << n) + 3) // 4)
    tt &= (1 << (1 << n)) - 1
    payload = {"n": n, "truth_table_hex": f"{tt:0{width}x}"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


_FUNCTION_HASH_KEYS = {
    "function_key",
    "function_hash",
    "function_truth_hash",
    "truth_table_hash",
    "truth_table_sha256",
}


def _truth_hash_from_mapping(row: Mapping[str, Any]) -> str | None:
    raw_n = row.get("n", row.get("n_inputs"))
    raw_truth = row.get("truth_table_hex", row.get("truth_table"))
    if raw_n in (None, "") or raw_truth in (None, ""):
        return None
    try:
        if isinstance(raw_truth, str):
            value = int(raw_truth, 0) if raw_truth.lower().startswith("0x") else int(raw_truth, 16)
        else:
            value = int(raw_truth)
        return truth_table_sha256(int(raw_n), value)
    except (TypeError, ValueError):
        return None


def _collect_hashes_from_json(value: Any, out: set[str], *, allow_bare_strings: bool = False) -> None:
    if isinstance(value, Mapping):
        derived = _truth_hash_from_mapping(value)
        if derived is not None:
            direct_function_key = value.get("function_key")
            if _is_sha256(direct_function_key) and str(direct_function_key).lower() != derived:
                raise ValueError(
                    "exclude manifest function_key disagrees with its n/truth_table_hex: "
                    f"{direct_function_key} != {derived}"
                )
            out.add(derived)
        for key, item in value.items():
            if key in _FUNCTION_HASH_KEYS and _is_sha256(item):
                out.add(str(item).lower())
            else:
                _collect_hashes_from_json(
                    item,
                    out,
                    allow_bare_strings=key in {"hashes", "function_hashes", "excluded_hashes"},
                )
        return
    if isinstance(value, list):
        for item in value:
            _collect_hashes_from_json(item, out, allow_bare_strings=allow_bare_strings)
        return
    if allow_bare_strings and _is_sha256(value):
        out.add(str(value).lower())


def load_excluded_function_hashes(paths: Sequence[str | Path]) -> set[str]:
    """Load function hashes from JSON/JSONL/CSV benchmark manifests.

    JSON supports the competition suite's ``cases[].function_key`` schema and
    derives the key from ``n[_inputs]`` + ``truth_table_hex`` as a cross-check.
    CSV manifests can contain either a recognized hash column or raw truth
    table columns.  Unrelated model/file SHA256 values are deliberately ignored.
    """

    hashes: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            raise FileNotFoundError(f"exclude manifest not found: {path}")
        suffix = path.suffix.lower()
        if suffix == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    derived = _truth_hash_from_mapping(row)
                    if derived is not None:
                        hashes.add(derived)
                    for key in _FUNCTION_HASH_KEYS:
                        value = row.get(key)
                        if _is_sha256(value):
                            hashes.add(str(value).lower())
        elif suffix in {".jsonl", ".ndjson"}:
            with path.open("r", encoding="utf-8-sig") as stream:
                for lineno, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"invalid JSON on {path}:{lineno}: {exc}") from exc
                    _collect_hashes_from_json(value, hashes, allow_bare_strings=True)
        else:
            with path.open("r", encoding="utf-8-sig") as stream:
                value = json.load(stream)
            _collect_hashes_from_json(value, hashes, allow_bare_strings=isinstance(value, list))
    return hashes


def _structured_generator(name: str) -> str:
    if name.startswith("parity"):
        return "parity"
    if name.startswith("majority"):
        return "majority"
    if name.startswith("threshold"):
        return "threshold"
    if name.startswith("mux"):
        return "mux"
    if name.startswith("adder"):
        return "adder_carry"
    if name.startswith("mul"):
        return "multiplier_bit"
    return "structured"


def _generate_functions(
    preset: str,
    seed: int,
    sample_override: int | None,
) -> list[_GeneratedFunction]:
    cfg = PRESETS[preset]
    generated: list[_GeneratedFunction] = []
    for name, bf in structured_suite():
        if cfg["n_min"] <= bf.n <= cfg["n_max"]:
            generated.append(
                _GeneratedFunction(
                    name=name,
                    bf=bf,
                    family="structured",
                    generation_seed=None,
                    generator_params={"generator": _structured_generator(name)},
                    aliases=[],
                )
            )

    sample_count = cfg["samples"] if sample_override is None else max(0, int(sample_override))
    master_rng = random.Random(seed)
    for sample_index in range(sample_count):
        generation_seed = master_rng.randrange(0, 1 << 63)
        rng = random.Random(generation_seed)
        n = rng.randint(cfg["n_min"], cfg["n_max"])
        if n <= 6 and rng.random() < 0.25:
            family = "random_truth"
            bf = random_truth_function(n, rng)
            params: dict[str, Any] = {"generator": "random_truth_function"}
        else:
            family = "random_anf"
            term_prob = rng.uniform(0.04, 0.22)
            max_degree = rng.randint(2, min(n, 6))
            bf = random_anf_function(n, rng, term_prob=term_prob, max_degree=max_degree)
            params = {
                "generator": "random_anf_function",
                "term_prob": term_prob,
                "max_degree": max_degree,
            }
        generated.append(
            _GeneratedFunction(
                name=f"{family}_n{n}_sample{sample_index}",
                bf=bf,
                family=family,
                generation_seed=generation_seed,
                generator_params=params,
                aliases=[],
            )
        )

    # The truth table, not the source label, is the experimental unit.  Merge
    # aliases so an accidental duplicate cannot leak across dataset splits.
    unique: dict[str, _GeneratedFunction] = {}
    for item in generated:
        function_hash = truth_table_sha256(item.bf)
        existing = unique.get(function_hash)
        if existing is None:
            unique[function_hash] = item
        else:
            existing.aliases.append(item.name)
    return list(unique.values())


def collect_from_terms(
    terms: frozenset[int],
    config: SearchConfig,
    rows: List[List[float]],
    labels: List[float],
    prefix_len: int = 0,
    live_factor_ancilla: int = 0,
    depth: int = 0,
    max_depth: int = 4,
    child_branch: int = 3,
    label_mode: str = "immediate",
    action_family: str = "factor",
    greedy_memo: dict | None = None,
    root_teacher_width: int = 24,
    rest_direct_limit: int = 450,
    teacher_eval_mode: str = "greedy",
    groups: List[int] | None = None,
    group_counter: List[int] | None = None,
) -> None:
    greedy_memo = {} if greedy_memo is None else greedy_memo
    direct_score = direct_plan(terms, prefix_len, live_factor_ancilla, config).score(config.weights)
    if action_family == "linear":
        actions = linear_factor_actions(
            terms,
            prefix_len,
            live_factor_ancilla,
            config,
            action_width=max(2, min(config.candidate_top_k, 24)),
        )
    elif action_family == "boolean_linear":
        actions = boolean_linear_factor_actions(
            terms,
            prefix_len,
            live_factor_ancilla,
            config,
            action_width=max(2, min(config.candidate_top_k, 24)),
        )
    else:
        actions = candidate_actions(terms, prefix_len, live_factor_ancilla, config)
    if not actions:
        return
    if label_mode == "root_teacher":
        group_id = -1
        if groups is not None:
            if group_counter is None:
                raise ValueError("group_counter is required when groups are collected")
            group_id = group_counter[0]
            group_counter[0] += 1
        teacher_actions = actions[: max(1, min(root_teacher_width, len(actions)))]
        child_config = replace(config, greedy_eval_limit=1)
        action_scores = []
        for action in teacher_actions:
            if teacher_eval_mode == "direct":
                group = direct_plan(action.residuals, prefix_len + 1, live_factor_ancilla + 1, child_config)
                rest = direct_plan(action.rest, prefix_len, live_factor_ancilla, child_config)
            else:
                group = greedy_plan(
                    action.residuals,
                    prefix_len + 1,
                    live_factor_ancilla + 1,
                    child_config,
                    memo=greedy_memo,
                )
                if len(action.rest) > rest_direct_limit:
                    rest = direct_plan(action.rest, prefix_len, live_factor_ancilla, child_config)
                else:
                    rest = greedy_plan(
                        action.rest,
                        prefix_len,
                        live_factor_ancilla,
                        child_config,
                        memo=greedy_memo,
                    )
            action_scores.append(factor_cost(action, group, rest, live_factor_ancilla, config).score(config.weights))
        mean_score = statistics.mean(action_scores)
        spread = statistics.pstdev(action_scores)
        for action, action_score in zip(teacher_actions, action_scores):
            rows.append(
                action_features(
                    terms,
                    prefix_len,
                    live_factor_ancilla,
                    action.factor,
                    action.group,
                    action.residuals,
                    action.rest,
                    action.immediate_gain,
                    direct_score,
                )
            )
            if spread <= 1e-9:
                label = 0.0
            else:
                label = (mean_score - action_score) / spread
            labels.append(max(-2.0, min(2.0, label)))
            if groups is not None:
                groups.append(group_id)
    else:
        for action in actions:
            rows.append(
                action_features(
                    terms,
                    prefix_len,
                    live_factor_ancilla,
                    action.factor,
                    action.group,
                    action.residuals,
                    action.rest,
                    action.immediate_gain,
                    direct_score,
                )
            )
            if label_mode == "rollout":
                group = greedy_plan(
                    action.residuals,
                    prefix_len + 1,
                    live_factor_ancilla + 1,
                    config,
                    memo=greedy_memo,
                )
                rest = greedy_plan(
                    action.rest,
                    prefix_len,
                    live_factor_ancilla,
                    config,
                    memo=greedy_memo,
                )
                action_score = factor_cost(action, group, rest, live_factor_ancilla, config).score(config.weights)
                improvement = direct_score - action_score
            else:
                improvement = action.immediate_gain
            labels.append(max(-2.0, min(2.0, 8.0 * improvement / max(direct_score, 1.0))))
            if groups is not None:
                groups.append(-1)
    if depth >= max_depth or not actions:
        return
    # Follow a few strong actions to collect child-state contexts.
    for action in actions[:child_branch]:
        collect_from_terms(
            action.residuals,
            config,
            rows,
            labels,
            prefix_len + 1,
            live_factor_ancilla + 1,
            depth + 1,
            max_depth,
            child_branch,
            label_mode,
            action_family,
            greedy_memo,
            root_teacher_width,
            rest_direct_limit,
            teacher_eval_mode,
            groups,
            group_counter,
        )
        collect_from_terms(
            action.rest,
            config,
            rows,
            labels,
            prefix_len,
            live_factor_ancilla,
            depth + 1,
            max_depth,
            child_branch,
            label_mode,
            action_family,
            greedy_memo,
            root_teacher_width,
            rest_direct_limit,
            teacher_eval_mode,
            groups,
            group_counter,
        )


def build_dataset_bundle(
    preset: str,
    seed: int,
    config: SearchConfig,
    label_mode: str,
    max_depth: int,
    child_branch: int,
    action_family: str,
    root_teacher_width: int,
    rest_direct_limit: int,
    teacher_eval_mode: str,
    sample_override: int | None = None,
    exclude_hashes: set[str] | None = None,
) -> DatasetBundle:
    """Collect action examples while retaining their Boolean-function owner."""

    exclude_hashes = {value.lower() for value in (exclude_hashes or set())}
    rows: List[List[float]] = []
    labels: List[float] = []
    groups: List[int] = []
    group_counter = [0]
    row_function_hashes: list[str] = []
    functions: list[FunctionDatasetRecord] = []
    zero_row_functions: list[FunctionDatasetRecord] = []
    excluded_functions: list[dict[str, Any]] = []

    for item in _generate_functions(preset, seed, sample_override):
        function_hash = truth_table_sha256(item.bf)
        base = {
            "function_hash": function_hash,
            "truth_table_sha256": function_hash,
            "n": int(item.bf.n),
            "family": item.family,
            "generation_seed": item.generation_seed,
            "name": item.name,
            "aliases": list(item.aliases),
            "generator_params": dict(item.generator_params),
        }
        if function_hash in exclude_hashes:
            excluded_functions.append(base)
            continue
        row_start = len(rows)
        collect_from_terms(
            frozenset(anf_monomials(item.bf)),
            config,
            rows,
            labels,
            max_depth=max_depth,
            child_branch=child_branch,
            label_mode=label_mode,
            action_family=action_family,
            root_teacher_width=root_teacher_width,
            rest_direct_limit=rest_direct_limit,
            teacher_eval_mode=teacher_eval_mode,
            groups=groups,
            group_counter=group_counter,
        )
        row_count = len(rows) - row_start
        record = FunctionDatasetRecord(
            function_hash=function_hash,
            n=int(item.bf.n),
            family=item.family,
            generation_seed=item.generation_seed,
            name=item.name,
            aliases=tuple(item.aliases),
            generator_params=dict(item.generator_params),
            row_start=row_start,
            row_count=row_count,
        )
        if row_count:
            functions.append(record)
            row_function_hashes.extend([function_hash] * row_count)
        else:
            zero_row_functions.append(record)

    if not rows:
        raise RuntimeError("no training rows collected after function-hash exclusion")
    if not (len(rows) == len(labels) == len(groups) == len(row_function_hashes)):
        raise AssertionError("dataset provenance length mismatch")
    return DatasetBundle(
        features=torch.tensor(rows, dtype=torch.float32),
        labels=torch.tensor(labels, dtype=torch.float32),
        state_groups=torch.tensor(groups, dtype=torch.long),
        row_function_hashes=tuple(row_function_hashes),
        functions=tuple(functions),
        zero_row_functions=tuple(zero_row_functions),
        excluded_functions=tuple(excluded_functions),
    )


def build_dataset(
    preset: str,
    seed: int,
    config: SearchConfig,
    label_mode: str,
    max_depth: int,
    child_branch: int,
    action_family: str,
    root_teacher_width: int,
    rest_direct_limit: int,
    teacher_eval_mode: str,
    sample_override: int | None = None,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Backward-compatible action-tensor API used by older scripts/tests."""

    bundle = build_dataset_bundle(
        preset,
        seed,
        config,
        label_mode,
        max_depth,
        child_branch,
        action_family,
        root_teacher_width,
        rest_direct_limit,
        teacher_eval_mode,
        sample_override,
    )
    return bundle.features, bundle.labels, bundle.state_groups


def split_dataset_by_function(
    bundle: DatasetBundle,
    *,
    split_seed: int,
    train_frac: float,
    valid_frac: float,
) -> FunctionSplit:
    """Split complete Boolean functions, never individual action rows."""

    if not 0.0 < train_frac < 1.0:
        raise ValueError("train_frac must be in (0, 1)")
    if not 0.0 < valid_frac < 1.0:
        raise ValueError("valid_frac must be in (0, 1)")
    if train_frac + valid_frac >= 1.0:
        raise ValueError("train_frac + valid_frac must be < 1 so test is held out")

    records = list(bundle.functions)
    if len(records) < 3:
        raise RuntimeError("at least three Boolean functions with action rows are required for train/valid/test")
    ordered = sorted(
        records,
        key=lambda record: (
            hashlib.sha256(f"{int(split_seed)}\0{record.function_hash}".encode("ascii")).hexdigest(),
            record.function_hash,
        ),
    )
    total = len(ordered)
    train_count = max(1, int(total * train_frac))
    valid_count = max(1, int(total * valid_frac))
    train_count = min(train_count, total - 2)
    valid_count = min(valid_count, total - train_count - 1)

    hash_sets = {
        "train": tuple(record.function_hash for record in ordered[:train_count]),
        "valid": tuple(record.function_hash for record in ordered[train_count : train_count + valid_count]),
        "test": tuple(record.function_hash for record in ordered[train_count + valid_count :]),
    }
    if any(not hash_sets[name] for name in SPLIT_NAMES):
        raise AssertionError("train/valid/test function split must be non-empty")
    if (
        set(hash_sets["train"]) & set(hash_sets["valid"])
        or set(hash_sets["train"]) & set(hash_sets["test"])
        or set(hash_sets["valid"]) & set(hash_sets["test"])
    ):
        raise AssertionError("Boolean-function hash leaked across splits")

    row_hashes = bundle.row_function_hashes
    index_tensors: dict[str, torch.Tensor] = {}
    for name in SPLIT_NAMES:
        allowed = set(hash_sets[name])
        indices = [index for index, function_hash in enumerate(row_hashes) if function_hash in allowed]
        if not indices:
            raise RuntimeError(f"{name} split has no action rows")
        index_tensors[name] = torch.tensor(indices, dtype=torch.long)

    return FunctionSplit(
        train_idx=index_tensors["train"],
        valid_idx=index_tensors["valid"],
        test_idx=index_tensors["test"],
        train_hashes=hash_sets["train"],
        valid_hashes=hash_sets["valid"],
        test_hashes=hash_sets["test"],
    )


def train_only_normalization(features: torch.Tensor, train_idx: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute normalization statistics from training rows only."""

    if train_idx.numel() == 0:
        raise ValueError("train_idx must be non-empty")
    train_features = features[train_idx]
    mean = train_features.mean(dim=0)
    std = train_features.std(dim=0, unbiased=False).clamp_min(1e-6)
    return mean, std


def pairwise_rank_loss(pred: torch.Tensor, target: torch.Tensor, groups: torch.Tensor) -> torch.Tensor:
    """Pairwise root-action ranking loss within each collected teacher state.

    Root-teacher labels are larger for better actions.  The pairwise loss
    therefore asks the model score difference to be positive whenever one
    action has a larger teacher label than another action from the same state.
    """
    losses = []
    for group in torch.unique(groups):
        if int(group.item()) < 0:
            continue
        idx = torch.nonzero(groups == group, as_tuple=False).flatten()
        if idx.numel() < 2:
            continue
        local_target = target[idx]
        label_diff = local_target[:, None] - local_target[None, :]
        mask = label_diff > 1e-6
        if not bool(mask.any()):
            continue
        local_pred = pred[idx]
        pred_diff = local_pred[:, None] - local_pred[None, :]
        weights = label_diff[mask].clamp(max=2.0)
        losses.append((torch.nn.functional.softplus(-pred_diff[mask]) * weights).mean())
    if not losses:
        return nn.SmoothL1Loss()(pred, target)
    return torch.stack(losses).mean()


def objective_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    groups: torch.Tensor,
    loss_mode: str,
    regression_loss: nn.Module,
) -> torch.Tensor:
    if loss_mode == "pairwise":
        return pairwise_rank_loss(pred, target, groups) + 0.10 * regression_loss(pred, target)
    return regression_loss(pred, target)


def _resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return default_device()
    device = torch.device(requested)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested but torch.cuda.is_available() is false")
    return device


def _runtime_metadata(device: torch.device) -> dict[str, Any]:
    cuda_available = bool(torch.cuda.is_available())
    cuda_device_index: int | None = None
    cuda_device_name: str | None = None
    cuda_capability: list[int] | None = None
    cuda_total_memory_bytes: int | None = None
    if cuda_available:
        cuda_device_index = device.index if device.type == "cuda" and device.index is not None else torch.cuda.current_device()
        props = torch.cuda.get_device_properties(cuda_device_index)
        cuda_device_name = props.name
        cuda_capability = [int(props.major), int(props.minor)]
        cuda_total_memory_bytes = int(props.total_memory)
    cudnn_version = torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None
    return {
        "training_device": str(device),
        "torch_version": str(torch.__version__),
        "cuda_available": cuda_available,
        "torch_cuda_version": torch.version.cuda,
        "cudnn_version": cudnn_version,
        "cuda_device_index": cuda_device_index,
        "cuda_device_name": cuda_device_name,
        "cuda_compute_capability": cuda_capability,
        "cuda_total_memory_bytes": cuda_total_memory_bytes,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "inference_default": "cpu",
    }


def _state_group_count(groups: torch.Tensor) -> int:
    retained = groups[groups >= 0]
    return int(torch.unique(retained).numel()) if retained.numel() else 0


def _split_payload(bundle: DatasetBundle, split: FunctionSplit) -> dict[str, Any]:
    records_by_hash = {record.function_hash: record for record in bundle.functions}
    payload: dict[str, Any] = {}
    for name in SPLIT_NAMES:
        hashes = split.hashes(name)
        indices = split.indices(name)
        records = [records_by_hash[function_hash] for function_hash in hashes]
        payload[name] = {
            "function_count": len(records),
            "row_count": int(indices.numel()),
            "state_group_count": _state_group_count(bundle.state_groups[indices]),
            "functions": [record.manifest_row() for record in records],
        }
    return payload


def _manifest_file_record(path: str | Path) -> dict[str, Any]:
    resolved = Path(path).resolve()
    return {"path": str(resolved), "sha256": file_sha256(resolved)}


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(PRESETS), default="smoke")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--split-seed",
        type=int,
        default=None,
        help="deterministic Boolean-function split seed (defaults to --seed)",
    )
    ap.add_argument("--train-frac", type=float, default=0.70)
    ap.add_argument("--valid-frac", type=float, default=0.15)
    ap.add_argument("--gate-mode", choices=["mct", "logical_and"], default="mct")
    ap.add_argument("--label-mode", choices=["immediate", "rollout", "root_teacher"], default="immediate")
    ap.add_argument("--loss-mode", choices=["regression", "pairwise"], default="regression")
    ap.add_argument("--action-family", choices=["factor", "linear", "boolean_linear"], default="factor")
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--child-branch", type=int, default=3)
    ap.add_argument("--root-teacher-width", type=int, default=24)
    ap.add_argument("--rest-direct-limit", type=int, default=450)
    ap.add_argument("--teacher-eval-mode", choices=["greedy", "direct"], default="greedy")
    ap.add_argument("--samples", type=int, default=None, help="override random sample count for the preset")
    ap.add_argument("--epochs", type=int, default=None, help="override epoch count for the preset")
    ap.add_argument("--hidden", type=int, default=96)
    ap.add_argument("--out", default=str(THIS_DIR / "models" / "action_scorer.pt"))
    ap.add_argument(
        "--exclude-manifest",
        action="append",
        default=[],
        metavar="PATH",
        help="JSON/JSONL/CSV function manifest to exclude; repeat for multiple manifests",
    )
    ap.add_argument(
        "--manifest",
        default=None,
        help="output JSON evidence manifest (default: <model>.manifest.json)",
    )
    ap.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    return ap


def run_training(args: argparse.Namespace) -> dict[str, Any]:
    split_seed = args.seed if args.split_seed is None else int(args.split_seed)
    exclude_hashes = load_excluded_function_hashes(args.exclude_manifest)

    config = SearchConfig(max_factor_ancilla=4, max_factor_size=5, candidate_top_k=24, gate_mode=args.gate_mode)
    bundle = build_dataset_bundle(
        args.preset,
        args.seed,
        config,
        args.label_mode,
        args.max_depth,
        args.child_branch,
        args.action_family,
        args.root_teacher_width,
        args.rest_direct_limit,
        args.teacher_eval_mode,
        args.samples,
        exclude_hashes,
    )
    split = split_dataset_by_function(
        bundle,
        split_seed=split_seed,
        train_frac=float(args.train_frac),
        valid_frac=float(args.valid_frac),
    )
    x_raw = bundle.features
    y = bundle.labels
    groups = bundle.state_groups
    mean, std = train_only_normalization(x_raw, split.train_idx)
    x = (x_raw - mean) / std

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = _resolve_device(args.device)
    runtime = _runtime_metadata(device)
    model = ActionNet(hidden=args.hidden).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = nn.SmoothL1Loss()
    cfg = dict(PRESETS[args.preset])
    if args.epochs is not None:
        cfg["epochs"] = max(1, int(args.epochs))

    x_train, y_train = x[split.train_idx].to(device), y[split.train_idx].to(device)
    x_valid, y_valid = x[split.valid_idx].to(device), y[split.valid_idx].to(device)
    x_test, y_test = x[split.test_idx].to(device), y[split.test_idx].to(device)
    g_train = groups[split.train_idx].to(device)
    g_valid = groups[split.valid_idx].to(device)
    g_test = groups[split.test_idx].to(device)

    best_state = None
    best_valid = float("inf")
    best_epoch = 0
    for epoch in range(cfg["epochs"]):
        model.train()
        pred = model(x_train)
        loss = objective_loss(pred, y_train, g_train, args.loss_mode, loss_fn)
        opt.zero_grad()
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            valid = objective_loss(model(x_valid), y_valid, g_valid, args.loss_mode, loss_fn).item()
        if valid < best_valid:
            best_valid = valid
            best_epoch = epoch + 1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch == 0 or (epoch + 1) % 10 == 0:
            print(f"epoch={epoch+1} train={loss.item():.4f} valid={valid:.4f}")

    if best_state is None:
        raise AssertionError("validation-only checkpoint selection produced no state")
    model.load_state_dict(best_state)
    model.eval()
    # The held-out test split is evaluated exactly once, after the checkpoint
    # has been selected using validation loss.  It never enters the epoch loop.
    with torch.no_grad():
        final_train = objective_loss(model(x_train), y_train, g_train, args.loss_mode, loss_fn).item()
        final_valid = objective_loss(model(x_valid), y_valid, g_valid, args.loss_mode, loss_fn).item()
        final_test = objective_loss(model(x_test), y_test, g_test, args.loss_mode, loss_fn).item()

    split_payload = _split_payload(bundle, split)
    normalization_payload = {
        "source_split": "train",
        "estimator": "population_std",
        "std_floor": 1e-6,
        "mean": mean.detach().cpu().tolist(),
        "std": std.detach().cpu().tolist(),
    }
    dataset_evidence = {
        "truth_table_hash_algorithm": TRUTH_HASH_ALGORITHM,
        "split_unit": "Boolean function truth table SHA256",
        "split_seed": split_seed,
        "requested_fractions": {
            "train": float(args.train_frac),
            "valid": float(args.valid_frac),
            "test": 1.0 - float(args.train_frac) - float(args.valid_frac),
        },
        "total_function_count": len(bundle.functions),
        "total_row_count": int(x.shape[0]),
        "feature_dim": int(x.shape[1]),
        "pairwise_state_group_count": _state_group_count(groups),
        "splits": split_payload,
        "zero_row_functions": [record.manifest_row() for record in bundle.zero_row_functions],
    }
    dataset_manifest_sha256 = hashlib.sha256(_canonical_json(dataset_evidence).encode("utf-8")).hexdigest()
    created_utc = datetime.now(timezone.utc).isoformat()
    training_metadata = {
        "format_version": 2,
        "created_utc": created_utc,
        "architecture": {
            "class": "ActionNet",
            "feature_dim": int(x.shape[1]),
            "hidden": int(args.hidden),
        },
        "training": {
            "preset": args.preset,
            "seed": int(args.seed),
            "split_seed": split_seed,
            "epochs": int(cfg["epochs"]),
            "best_epoch": best_epoch,
            "label_mode": args.label_mode,
            "loss_mode": args.loss_mode,
            "action_family": args.action_family,
            "gate_mode": args.gate_mode,
            "checkpoint_selection": "minimum validation loss only",
            "test_evaluations": 1,
        },
        "data_provenance": {
            "truth_table_hash_algorithm": TRUTH_HASH_ALGORITHM,
            "split_unit": "Boolean function truth table SHA256",
            "normalization_source": "train",
            "dataset_manifest_sha256": dataset_manifest_sha256,
            "split_function_hashes": {
                name: list(split.hashes(name)) for name in SPLIT_NAMES
            },
            "split_row_counts": {
                name: int(split.indices(name).numel()) for name in SPLIT_NAMES
            },
        },
        "runtime": runtime,
    }
    output_path = Path(args.out)
    save_model(output_path, model.cpu(), mean, std, metadata=training_metadata)
    model_sha256 = file_sha256(output_path)

    excluded_records = [_manifest_file_record(path) for path in args.exclude_manifest]
    generated_excluded_hashes = sorted(
        str(row["function_hash"]) for row in bundle.excluded_functions
    )
    all_split_hashes = [function_hash for name in SPLIT_NAMES for function_hash in split.hashes(name)]
    integrity = {
        "function_hash_splits_disjoint": len(all_split_hashes) == len(set(all_split_hashes)),
        "all_action_rows_assigned_once": sum(int(split.indices(name).numel()) for name in SPLIT_NAMES)
        == int(x.shape[0]),
        "excluded_hashes_absent_from_splits": not (set(exclude_hashes) & set(all_split_hashes)),
        "normalization_source_is_train_only": True,
        "checkpoint_uses_test": False,
        "test_evaluations": 1,
    }
    if not (
        integrity["function_hash_splits_disjoint"]
        and integrity["all_action_rows_assigned_once"]
        and integrity["excluded_hashes_absent_from_splits"]
        and integrity["normalization_source_is_train_only"]
        and not integrity["checkpoint_uses_test"]
        and integrity["test_evaluations"] == 1
    ):
        raise AssertionError(f"training integrity failure: {integrity}")
    manifest = {
        "schema_version": 1,
        "created_utc": created_utc,
        "dataset": dataset_evidence,
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "normalization": normalization_payload,
        "exclusion": {
            "manifests": excluded_records,
            "requested_hash_count": len(exclude_hashes),
            "requested_hashes": sorted(exclude_hashes),
            "matched_generated_function_count": len(bundle.excluded_functions),
            "matched_generated_hashes": generated_excluded_hashes,
            "matched_generated_functions": list(bundle.excluded_functions),
        },
        "training": training_metadata["training"],
        "metrics": {
            "train_loss_at_selected_checkpoint": final_train,
            "valid_loss_at_selected_checkpoint": final_valid,
            "best_valid_loss": best_valid,
            "test_loss_once_after_selection": final_test,
            "test_evaluations": 1,
        },
        "model": {
            "path": str(output_path.resolve()),
            "sha256": model_sha256,
            "metadata_embedded": True,
            "metadata": training_metadata,
        },
        "runtime": runtime,
        "integrity": integrity,
        "search_config": asdict(config),
    }
    manifest_path = Path(args.manifest) if args.manifest else output_path.with_suffix(".manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"rows={x.shape[0]} functions={len(bundle.functions)} "
        f"train/valid/test={len(split.train_hashes)}/{len(split.valid_hashes)}/{len(split.test_hashes)}"
    )
    print(
        f"valid_loss={final_valid:.4f} test_loss_once={final_test:.4f} "
        f"device={device} cuda={runtime['cuda_available']}"
    )
    print(f"wrote {output_path} sha256={model_sha256}")
    print(f"wrote {manifest_path}")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    run_training(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
