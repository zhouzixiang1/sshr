#!/usr/bin/env python3
"""Train a provenance-closed v4 equivariant policy/value checkpoint.

This wrapper deliberately does not infer the history of the development v3
checkpoint.  It starts from a seeded random initialisation, freezes every
Boolean function before optimisation, excludes every registered
``crypto_oracles`` input width, records the exact source/config/command/log
hashes, and writes an immutable artifact bundle.

The original ``train_expert_iteration.py`` remains the implementation source
for sample collection and joint policy/value fitting.  This wrapper fixes two
contract gaps at the orchestration layer: rejected iterations are rolled back,
and an explicit best checkpoint is always emitted even if every iteration is
rejected.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import os
import platform
import random
import resource
import sys
import time
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch

from scripts._pilot_artifacts import environment_record, source_record
from scripts.train_expert_iteration import collect_samples, fit
from src.anf_utils import anf_monomials
from src.contracts.artifacts import ArtifactBundleWriter, verify_bundle
from src.contracts.codec import (
    canonical_json_bytes,
    canonical_json_text,
    sha256_bytes,
    sha256_file,
)
from src.factor_plan import SearchConfig
from src.foundation.adapter import FoundationScorer
from src.foundation.equivariant import EquivariantTrunk
from src.foundation.heads import BooleanOracleModel
from src.nmcts_solver import NeuralMCTSSolver
from src.resource_model import ResourceWeights
from src.search.value_net import LearnedValueEstimator
from src.sshr_lib.bool_func import BooleanFunction


CONFIG_SCHEMA = "xa.foundation-training-config.v4"
DATASET_SCHEMA = "xa.foundation-dataset-manifest.v4"
SOURCE_SCHEMA = "xa.foundation-source-manifest.v4"
COMMAND_SCHEMA = "xa.foundation-training-command.v4"
SUMMARY_SCHEMA = "xa.foundation-training-summary.v4"
MODEL_CARD_SCHEMA = "xa.foundation-model-card.v4"
ESTIMATE_SCHEMA = "xa.foundation-resource-estimate.v4"
SELF_CHECK_SCHEMA = "xa.foundation-training-self-check.v4"
GENERATOR_ID = "xa.synthetic-uniform-shake256.v1"
TRUTH_TABLE_ENCODING = (
    "Unsigned truth_table integer encoded in exactly ceil(2**n/8) bytes, "
    "little-endian; bit x is f(x); SHA-256 is over those bytes."
)
CRYPTO_EVALUATION_MODULE = "src.benchmarks.crypto_oracles"
REQUIRED_SOURCE_PATHS = (
    "scripts/train_foundation_v4.py",
    "scripts/verify_foundation_v4_bundle.py",
    "scripts/train_expert_iteration.py",
    "scripts/_pilot_artifacts.py",
)
REQUIRED_SOURCE_TREES = ("src",)
REQUIRED_ROLES = (
    "config",
    "source",
    "dataset",
    "command",
    "training_log",
    "checkpoint",
    "summary",
    "model_card",
    "resource_estimate",
    "self_checks",
)
EXPECTED_CRYPTO_FAMILIES = [
    {"family": "AES", "input_width": 8, "output_width": 8, "supported": True},
    {"family": "ASCON", "input_width": 5, "output_width": 5, "supported": False},
    {"family": "PRESENT", "input_width": 4, "output_width": 4, "supported": False},
    {"family": "SM4", "input_width": 8, "output_width": 8, "supported": False},
]
EXPECTED_CRYPTO_TRUTH_TABLE_SHA256 = [
    "1e9824b17f9c4881346ee92a37d0ff4efc5d44cadf9c1e558f78ae190d662a05",
    "20b7cdfce4e67e25cb3b5dc4de26118f9b048c02981fa89ad1ceb54bd5274dd5",
    "25bff3db1032e49ddfc2d9bc9d5d48c985b1779930865e47f3780ff950984994",
    "2629f646e4e48c89d27a2fa15d806db1bb59721ec004c19415ae59ac2e72b48f",
    "2f5f6885b68f1f6fafed2be6ab614346c48a8528b51f7b4bdf4a0c1b609df97d",
    "3def4ec7c4026dc026162cdf2279a16a8e9e9f5efdde0521ebbfd91f3d5fec83",
    "3e1685e8e7f2b9529edafc5fd6d96e1174d858091a180d379cd89147ec286256",
    "4e970e8b7f2fb52a79c55db9c9dfaa44658eb64fd37e5ed9d3440a0905803e71",
    "651dfc9a16350c391f9b9f1e02afd433f951246a6fce4691301e3c463266bf71",
    "793b6367e6dd9217673ed5a6aa0bda6faa78da85239f47061ffb470e41c6151f",
    "80713771a1b2e8920d65ad892d27c8e2e8aba5874d587d4b24cf6cf074784ce7",
    "8a20f3428448f5e2bd8da3e9559cb7a3ae091759f4516e80cc65b8f616d6112d",
    "8bb9df77d8e16f65c91cc9fce1b1368b9f23332f6eb41419cc7fbd0ce39e2f4c",
    "8e63f8c394a1ee38340d3be6e9a33b7b8c86d752498720dc80c223b02562e959",
    "ac7c564edb9b2693a5ecf17f055281babf6b97433394169f5448d5af6fc950c2",
    "b3311960f4cf52c6db4d5cbb9cf0d47915e3666175b91f3eb4e08bad9932865a",
    "cac32e76240366ea1129102f26003cec2121742a1742f912da081106857743be",
    "e511dae0b4fd7953dd2e564003d3ef3b86f560ece76e073391bc525e9a45a97d",
    "f1993d2d5719218ea7fe15a97b9c7f977c03863e923def799fc948f669bc613f",
]


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _assert_crypto_evaluation_not_imported() -> None:
    if CRYPTO_EVALUATION_MODULE in sys.modules:
        raise RuntimeError(
            "evaluation-only crypto_oracles module was imported into the training process"
        )


def _require_keys(value: dict[str, Any], expected: Iterable[str], context: str) -> None:
    expected_set = set(expected)
    actual = set(value)
    if actual != expected_set:
        missing = sorted(expected_set - actual)
        extra = sorted(actual - expected_set)
        raise ValueError(f"{context} keys differ; missing={missing}, extra={extra}")


def _normalise_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.name


def _tree_record(relative_root: str, *, include_files: bool) -> dict[str, Any]:
    root = PROJECT_ROOT / relative_root
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        records.append(
            {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    identity_records = [
        {"path": item["path"], "sha256": item["sha256"]} for item in records
    ]
    result = {
        "path": relative_root,
        "sha256": sha256_bytes(canonical_json_bytes(identity_records)),
        "file_count": len(records),
    }
    if include_files:
        result["files"] = records
    return result


def _profile(config: dict[str, Any], profile_name: str) -> dict[str, Any]:
    profiles = config.get("profiles")
    if not isinstance(profiles, dict) or profile_name not in profiles:
        known = ", ".join(sorted(profiles or {}))
        raise ValueError(f"unknown profile {profile_name!r}; known: {known}")
    profile = profiles[profile_name]
    if not isinstance(profile, dict):
        raise ValueError(f"profile {profile_name!r} must be an object")
    return copy.deepcopy(profile)


def validate_config(config: dict[str, Any], profile_name: str) -> dict[str, Any]:
    if config.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("unsupported foundation training config schema")
    _require_keys(
        config,
        (
            "schema_version",
            "status",
            "track",
            "model_id",
            "entrypoint",
            "verifier",
            "generator",
            "crypto_exclusion",
            "source_contract",
            "search",
            "resource_weights",
            "profiles",
            "claim_boundary",
        ),
        "config",
    )
    if config["status"] != "pre_registered_unrun":
        raise ValueError("config status must remain pre_registered_unrun")
    if config["entrypoint"] != "scripts/train_foundation_v4.py":
        raise ValueError("unexpected training entrypoint")
    if config["verifier"] != "scripts/verify_foundation_v4_bundle.py":
        raise ValueError("unexpected verifier entrypoint")
    if config["generator"].get("id") != GENERATOR_ID:
        raise ValueError("unexpected dataset generator")
    if config["generator"].get("truth_table_encoding") != TRUTH_TABLE_ENCODING:
        raise ValueError("truth-table encoding contract differs")

    crypto = config["crypto_exclusion"]
    inventory = EXPECTED_CRYPTO_FAMILIES
    if crypto.get("registered_families") != inventory:
        raise ValueError(
            "crypto_oracles registry inventory differs from the frozen config; "
            "refreeze explicitly before training"
        )
    if crypto.get("forbidden_truth_table_sha256") != EXPECTED_CRYPTO_TRUTH_TABLE_SHA256:
        raise ValueError("registered crypto truth-table SHA denylist differs")
    registry_path = PROJECT_ROOT / crypto["registry_path"]
    if sha256_file(registry_path) != crypto.get("registry_sha256"):
        raise ValueError("crypto_oracles registry SHA-256 differs from frozen config")
    excluded_widths = {int(v) for v in crypto.get("excluded_input_widths", [])}
    registry_widths = {int(item["input_width"]) for item in inventory}
    if not registry_widths <= excluded_widths:
        raise ValueError("not every registered crypto-oracle input width is excluded")
    if crypto.get("strategy") != "exclude_entire_registered_input_widths":
        raise ValueError("crypto exclusion must use whole-input-width exclusion")
    if crypto.get("allow_future_families") is not False:
        raise ValueError("future crypto families must fail closed")
    if crypto.get("evaluation_module_imported_during_training") is not False:
        raise ValueError("the evaluation-only crypto module must not be imported during training")

    source_contract = config["source_contract"]
    _require_keys(source_contract, ("files", "trees"), "source_contract")
    source_entries = source_contract.get("files")
    if not isinstance(source_entries, list):
        raise ValueError("source_contract.files must be a list")
    paths = tuple(item.get("path") for item in source_entries)
    if paths != REQUIRED_SOURCE_PATHS:
        raise ValueError("source contract path list differs from the v4 contract")
    for item in source_entries:
        digest = str(item.get("sha256", ""))
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"invalid frozen source SHA-256 for {item.get('path')}")
        actual = sha256_file(PROJECT_ROOT / item["path"])
        if actual != digest:
            raise ValueError(f"source SHA-256 mismatch for {item['path']}")
    tree_entries = source_contract.get("trees")
    if not isinstance(tree_entries, list):
        raise ValueError("source_contract.trees must be a list")
    tree_paths = tuple(item.get("path") for item in tree_entries)
    if tree_paths != REQUIRED_SOURCE_TREES:
        raise ValueError("source contract tree list differs from the v4 contract")
    for item in tree_entries:
        actual = _tree_record(item["path"], include_files=False)
        if actual["sha256"] != item.get("sha256"):
            raise ValueError(f"source tree SHA-256 mismatch for {item['path']}")

    search = config["search"]
    _require_keys(
        search,
        (
            "gate_mode",
            "max_factor_ancilla",
            "max_factor_size",
            "candidate_top_k",
            "min_factor_count",
            "use_relative_phase",
            "neural_prior_weight",
            "greedy_eval_limit",
            "selfplay_prior",
            "validation_value_net",
        ),
        "search",
    )
    if search["gate_mode"] != "mct":
        raise ValueError("v4 training contract supports only gate_mode=mct")
    if search["selfplay_prior"] != "heuristic":
        raise ValueError("v4 expert targets require heuristic-prior self-play")
    if search["validation_value_net"] is not True:
        raise ValueError("the accept gate must test the deployed value net")

    weights = config["resource_weights"]
    if weights != {"t": 1.0, "cnot": 0.04, "depth": 0.015, "gates": 0.01, "ancilla": 2.0}:
        raise ValueError("resource weights differ from the frozen paper profile")

    profile = _profile(config, profile_name)
    _require_keys(
        profile,
        (
            "purpose",
            "seed",
            "allowed_num_vars",
            "iterations",
            "functions_per_iteration",
            "holdout_functions",
            "simulations",
            "architecture",
            "fit",
            "runtime_estimate",
        ),
        f"profiles.{profile_name}",
    )
    allowed = [int(v) for v in profile["allowed_num_vars"]]
    if not allowed or allowed != sorted(set(allowed)):
        raise ValueError("allowed_num_vars must be a sorted unique non-empty list")
    if set(allowed) & excluded_widths:
        raise ValueError("profile variable counts overlap a crypto-oracle input width")
    for key in ("iterations", "functions_per_iteration", "holdout_functions", "simulations"):
        if isinstance(profile[key], bool) or int(profile[key]) <= 0:
            raise ValueError(f"profiles.{profile_name}.{key} must be positive")
    architecture = profile["architecture"]
    _require_keys(architecture, ("hidden", "layers", "mlp_hidden"), "architecture")
    if any(isinstance(architecture[k], bool) or int(architecture[k]) <= 0 for k in architecture):
        raise ValueError("architecture dimensions must be positive integers")
    if architecture != {"hidden": 32, "layers": 2, "mlp_hidden": 128}:
        raise ValueError("every v4 profile must use the v3-comparable 60,450-parameter architecture")
    fit_config = profile["fit"]
    _require_keys(
        fit_config,
        (
            "epochs",
            "batch_size",
            "learning_rate",
            "policy_weight",
            "weight_decay",
            "max_samples",
        ),
        "fit",
    )
    if float(fit_config["weight_decay"]) != 1e-4:
        raise ValueError("train_expert_iteration.fit fixes AdamW weight_decay=1e-4")
    return profile


def source_manifest(config: dict[str, Any]) -> dict[str, Any]:
    files = []
    for item in config["source_contract"]["files"]:
        path = PROJECT_ROOT / item["path"]
        files.append(
            {
                "path": item["path"],
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "schema_version": SOURCE_SCHEMA,
        "files": files,
        "trees": [
            _tree_record(item["path"], include_files=True)
            for item in config["source_contract"]["trees"]
        ],
        "git_identity": source_record(PROJECT_ROOT),
        "note": (
            "Exact file hashes are authoritative for this dirty-tree run; git commit "
            "identity alone is not treated as sufficient provenance."
        ),
    }


def _truth_bytes(num_vars: int, seed_material: bytes) -> tuple[bytes, int]:
    bit_count = 1 << num_vars
    byte_count = (bit_count + 7) // 8
    payload = bytearray(hashlib.shake_256(seed_material).digest(byte_count))
    excess = byte_count * 8 - bit_count
    if excess:
        payload[-1] &= (1 << (8 - excess)) - 1
    raw = bytes(payload)
    return raw, int.from_bytes(raw, "little")


def _function_record(
    *,
    seed: int,
    split: str,
    iteration: int | None,
    draw_index: int,
    allowed_num_vars: list[int],
    used: set[tuple[int, str]],
) -> tuple[dict[str, Any], int]:
    rotation_material = f"{GENERATOR_ID}|seed={seed}|split={split}|rotation".encode()
    rotation = int.from_bytes(hashlib.sha256(rotation_material).digest()[:8], "little")
    num_vars = allowed_num_vars[(rotation + draw_index) % len(allowed_num_vars)]
    nonce = 0
    while True:
        label = (
            f"{GENERATOR_ID}|seed={seed}|split={split}|iteration={iteration}|"
            f"draw={draw_index}|n={num_vars}|nonce={nonce}"
        )
        truth_bytes, truth_table = _truth_bytes(num_vars, label.encode())
        truth_sha = hashlib.sha256(truth_bytes).hexdigest()
        identity = (num_vars, truth_sha)
        terms = sorted(anf_monomials(BooleanFunction(num_vars, truth_table)))
        if len(terms) >= 2 and identity not in used:
            used.add(identity)
            anf_sha = sha256_bytes(canonical_json_bytes(terms))
            suffix = f"iter{iteration:03d}" if iteration is not None else "fixed"
            return (
                {
                    "function_id": (
                        f"synthetic-uniform/{split}/{suffix}/draw{draw_index:04d}/n{num_vars}"
                    ),
                    "source_kind": "synthetic_uniform_hashstream",
                    "split": split,
                    "iteration": iteration,
                    "draw_index": draw_index,
                    "generator_seed": seed,
                    "generator_nonce": nonce,
                    "num_vars": num_vars,
                    "truth_table_sha256": truth_sha,
                    "truth_table_bytes": len(truth_bytes),
                    "anf_sha256": anf_sha,
                    "anf_terms": len(terms),
                },
                truth_table,
            )
        nonce += 1


def build_dataset_manifest(
    config: dict[str, Any], profile_name: str, profile: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, int]]:
    allowed = [int(v) for v in profile["allowed_num_vars"]]
    seed = int(profile["seed"])
    used: set[tuple[int, str]] = set()
    truth_tables: dict[str, int] = {}
    records: list[dict[str, Any]] = []

    holdout_seed = seed + 9999
    for index in range(int(profile["holdout_functions"])):
        record, truth_table = _function_record(
            seed=holdout_seed,
            split="holdout",
            iteration=None,
            draw_index=index,
            allowed_num_vars=allowed,
            used=used,
        )
        records.append(record)
        truth_tables[record["function_id"]] = truth_table

    for iteration in range(1, int(profile["iterations"]) + 1):
        iteration_seed = seed + iteration
        for index in range(int(profile["functions_per_iteration"])):
            record, truth_table = _function_record(
                seed=iteration_seed,
                split="train",
                iteration=iteration,
                draw_index=index,
                allowed_num_vars=allowed,
                used=used,
            )
            records.append(record)
            truth_tables[record["function_id"]] = truth_table

    records.sort(key=lambda item: item["function_id"])
    crypto = config["crypto_exclusion"]
    manifest_without_sha = {
        "schema_version": DATASET_SCHEMA,
        "profile": profile_name,
        "generator": {
            "id": GENERATOR_ID,
            "truth_table_encoding": TRUTH_TABLE_ENCODING,
            "implementation_path": "scripts/train_foundation_v4.py",
            "implementation_sha256": sha256_file(Path(__file__)),
        },
        "split_contract": {
            "train_seed_rule": "profile.seed + iteration",
            "holdout_seed_rule": "profile.seed + 9999",
            "holdout_used_for_fit": False,
            "test_split": None,
            "identity": "(num_vars, truth_table_sha256)",
            "duplicates_allowed": False,
        },
        "crypto_exclusion": {
            "strategy": crypto["strategy"],
            "registry_path": crypto["registry_path"],
            "registry_sha256": crypto["registry_sha256"],
            "registered_families": crypto["registered_families"],
            "forbidden_truth_table_sha256": crypto["forbidden_truth_table_sha256"],
            "excluded_input_widths": crypto["excluded_input_widths"],
            "allowed_num_vars": allowed,
            "evaluation_module_imported_during_training": False,
            "evaluation_not_accessed": True,
            "proof": (
                "Every registered crypto-oracle family is excluded by arity: the "
                "training/holdout variable counts are disjoint from every registered "
                "family input width. No crypto-oracle truth table loader is used."
            ),
        },
        "records": records,
    }
    return (
        {
            **manifest_without_sha,
            "dataset_sha256": sha256_bytes(canonical_json_bytes(manifest_without_sha)),
        },
        truth_tables,
    )


def _search_config(config: dict[str, Any]) -> SearchConfig:
    weights = ResourceWeights(**config["resource_weights"])
    search = config["search"]
    return SearchConfig(
        weights=weights,
        max_factor_ancilla=int(search["max_factor_ancilla"]),
        max_factor_size=int(search["max_factor_size"]),
        candidate_top_k=int(search["candidate_top_k"]),
        min_factor_count=int(search["min_factor_count"]),
        use_relative_phase=bool(search["use_relative_phase"]),
        gate_mode=str(search["gate_mode"]),
        neural_prior_weight=float(search["neural_prior_weight"]),
        greedy_eval_limit=int(search["greedy_eval_limit"]),
    )


def _functions_for(
    dataset: dict[str, Any], truth_tables: dict[str, int], *, split: str, iteration: int | None
) -> list[tuple[dict[str, Any], frozenset[int]]]:
    selected = [
        record
        for record in dataset["records"]
        if record["split"] == split and record["iteration"] == iteration
    ]
    out = []
    for record in selected:
        bf = BooleanFunction(int(record["num_vars"]), truth_tables[record["function_id"]])
        out.append((record, frozenset(anf_monomials(bf))))
    return out


def _evaluate(
    scorer: FoundationScorer,
    search_config: SearchConfig,
    functions: list[tuple[dict[str, Any], frozenset[int]]],
    simulations: int,
    seed: int,
) -> tuple[float, float, list[dict[str, Any]]]:
    total_score = 0.0
    started = time.perf_counter()
    rows = []
    for index, (record, terms) in enumerate(functions):
        one = time.perf_counter()
        estimator = LearnedValueEstimator(scorer, search_config)
        plan = NeuralMCTSSolver(
            search_config,
            simulations=simulations,
            seed=seed + index,
            neural_scorer=scorer,
            value_estimator=estimator,
        ).solve(terms)
        score = float(plan.score(search_config.weights))
        total_score += score
        rows.append(
            {
                "function_id": record["function_id"],
                "num_vars": record["num_vars"],
                "score": score,
                "seconds": round(time.perf_counter() - one, 6),
            }
        )
    return (
        total_score / max(len(functions), 1),
        time.perf_counter() - started,
        rows,
    )


def _state_dict_copy(model: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


def _accept_or_restore_best(
    model: torch.nn.Module,
    *,
    candidate_score: float,
    best_score: float,
    best_state: dict[str, torch.Tensor],
) -> tuple[float, dict[str, torch.Tensor], bool]:
    """Accept an equal/better candidate or restore the last accepted best state."""
    if candidate_score <= best_score:
        return candidate_score, _state_dict_copy(model), True
    model.load_state_dict(best_state)
    return best_score, best_state, False


def _train(
    config: dict[str, Any],
    profile_name: str,
    profile: dict[str, Any],
    dataset: dict[str, Any],
    truth_tables: dict[str, int],
) -> tuple[BooleanOracleModel, list[dict[str, Any]], dict[str, Any]]:
    seed = int(profile["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    torch.use_deterministic_algorithms(True)
    device = torch.device("cpu")
    architecture = profile["architecture"]
    model = BooleanOracleModel(
        EquivariantTrunk(
            hidden=int(architecture["hidden"]), layers=int(architecture["layers"])
        ),
        mlp_hidden=int(architecture["mlp_hidden"]),
    )
    scorer = FoundationScorer(model, device=device)
    search_config = _search_config(config)
    simulations = int(profile["simulations"])
    holdout = _functions_for(dataset, truth_tables, split="holdout", iteration=None)
    validation_seed = seed + 700_000

    log: list[dict[str, Any]] = []
    initial_score, initial_seconds, initial_rows = _evaluate(
        scorer, search_config, holdout, simulations, validation_seed
    )
    log.append(
        {
            "event": "initial_validation",
            "profile": profile_name,
            "mean_score": initial_score,
            "seconds": round(initial_seconds, 6),
            "functions": initial_rows,
        }
    )

    best_score = initial_score
    best_state = _state_dict_copy(model)
    accepted_iterations: list[int] = []
    rejected_iterations: list[int] = []
    fit_config = profile["fit"]
    for iteration in range(1, int(profile["iterations"]) + 1):
        functions = _functions_for(dataset, truth_tables, split="train", iteration=iteration)
        samples = []
        per_function = []
        play_started = time.perf_counter()
        for index, (record, terms) in enumerate(functions):
            one = time.perf_counter()
            solver = NeuralMCTSSolver(
                search_config,
                simulations=simulations,
                seed=seed + iteration * 10_000 + index,
                neural_scorer=None,
            )
            solver.solve(terms)
            harvested = collect_samples(solver, search_config)
            samples.extend(harvested)
            per_function.append(
                {
                    "function_id": record["function_id"],
                    "num_vars": record["num_vars"],
                    "samples": len(harvested),
                    "seconds": round(time.perf_counter() - one, 6),
                }
            )
        play_seconds = time.perf_counter() - play_started
        sampled_before_cap = len(samples)
        max_samples = int(fit_config["max_samples"])
        if len(samples) > max_samples:
            samples = random.Random(seed + 500_000 + iteration).sample(samples, max_samples)
        if not samples:
            raise RuntimeError(f"iteration {iteration} harvested no trainable samples")

        random.seed(seed + 600_000 + iteration)
        fit_started = time.perf_counter()
        value_loss, policy_loss = fit(
            model,
            samples,
            search_config,
            int(fit_config["epochs"]),
            int(fit_config["batch_size"]),
            float(fit_config["learning_rate"]),
            float(fit_config["policy_weight"]),
            device,
        )
        fit_seconds = time.perf_counter() - fit_started
        if not math.isfinite(value_loss) or not math.isfinite(policy_loss):
            raise RuntimeError("non-finite training loss")
        scorer.clear_cache()
        score, validation_seconds, validation_rows = _evaluate(
            scorer,
            search_config,
            holdout,
            simulations,
            validation_seed,
        )
        prior_best_score = best_score
        best_score, best_state, accepted = _accept_or_restore_best(
            model,
            candidate_score=score,
            best_score=best_score,
            best_state=best_state,
        )
        if accepted:
            accepted_iterations.append(iteration)
            verdict = "accept"
        else:
            scorer.clear_cache()
            rejected_iterations.append(iteration)
            verdict = "reject_and_rollback"
        log.append(
            {
                "event": "training_iteration",
                "iteration": iteration,
                "train_functions": per_function,
                "samples_before_cap": sampled_before_cap,
                "samples_fit": len(samples),
                "play_seconds": round(play_seconds, 6),
                "fit_seconds": round(fit_seconds, 6),
                "value_loss": value_loss,
                "policy_loss": policy_loss,
                "validation_mean_score": score,
                "validation_seconds": round(validation_seconds, 6),
                "validation_functions": validation_rows,
                "best_score_before_decision": prior_best_score,
                "verdict": verdict,
            }
        )

    model.load_state_dict(best_state)
    scorer.clear_cache()
    final_score, final_seconds, final_rows = _evaluate(
        scorer, search_config, holdout, simulations, validation_seed
    )
    log.append(
        {
            "event": "final_validation",
            "mean_score": final_score,
            "recorded_best_score": best_score,
            "seconds": round(final_seconds, 6),
            "functions": final_rows,
        }
    )
    if not math.isclose(final_score, best_score, rel_tol=0.0, abs_tol=1e-9):
        raise RuntimeError("restored best checkpoint does not reproduce the recorded best score")
    stats = {
        "initial_validation_score": initial_score,
        "best_validation_score": best_score,
        "accepted_iterations": accepted_iterations,
        "rejected_iterations": rejected_iterations,
        "iterations_completed": int(profile["iterations"]),
    }
    return model, log, stats


def _probe_runtime(
    config: dict[str, Any],
    selected_profile: dict[str, Any],
    formal_profile: dict[str, Any],
) -> dict[str, Any]:
    runtime = selected_profile["runtime_estimate"]
    if runtime.get("enabled") is not True:
        return {
            "schema_version": ESTIMATE_SCHEMA,
            "status": "skipped_by_frozen_profile",
            "target_profile": "formal",
            "reason": "The test-only profile disables the representative timing probe.",
        }
    probe_simulations = int(runtime["probe_simulations"])
    search_config = _search_config(config)
    seed = int(selected_profile["seed"]) + 1_500_000
    probe_rows = []
    for index, num_vars in enumerate(formal_profile["allowed_num_vars"]):
        label = f"{GENERATOR_ID}|runtime-probe|seed={seed}|n={num_vars}|index={index}"
        raw, truth_table = _truth_bytes(int(num_vars), label.encode())
        terms = frozenset(anf_monomials(BooleanFunction(int(num_vars), truth_table)))
        started = time.perf_counter()
        solver = NeuralMCTSSolver(
            search_config,
            simulations=probe_simulations,
            seed=seed + index,
            neural_scorer=None,
        )
        solver.solve(terms)
        probe_rows.append(
            {
                "num_vars": int(num_vars),
                "truth_table_sha256": hashlib.sha256(raw).hexdigest(),
                "anf_terms": len(terms),
                "simulations": probe_simulations,
                "seconds": round(time.perf_counter() - started, 6),
            }
        )

    widths = len(formal_profile["allowed_num_vars"])
    per_iteration = int(formal_profile["functions_per_iteration"])
    holdout = int(formal_profile["holdout_functions"])
    iterations = int(formal_profile["iterations"])
    formal_simulations = int(formal_profile["simulations"])
    sim_scale = formal_simulations / probe_simulations
    selfplay = 0.0
    validation = 0.0
    for row in probe_rows:
        train_count = per_iteration / widths
        holdout_count = holdout / widths
        selfplay += row["seconds"] * train_count * iterations * sim_scale
        validation += row["seconds"] * holdout_count * (iterations + 2) * sim_scale
    # Value-network validation is not the same algorithm as classical probe
    # search, so this is intentionally a planning interval rather than a claim.
    point_seconds = selfplay + 0.5 * validation
    low_seconds = max(point_seconds * 0.5, sum(row["seconds"] for row in probe_rows))
    high_seconds = point_seconds * 4.0
    return {
        "schema_version": ESTIMATE_SCHEMA,
        "status": "planning_estimate_not_benchmark_evidence",
        "target_profile": "formal",
        "method": (
            "One CPU-thread heuristic self-play solve at each formal n, scaled by "
            "function counts and simulation ratio; validation is charged at 0.5x "
            "the classical probe total. The 0.5x-4x interval covers non-linear "
            "tree growth, model evaluation and fitting overhead."
        ),
        "probe": probe_rows,
        "estimate": {
            "cpu_threads": 1,
            "accelerator_required": False,
            "quantum_hardware_required": False,
            "point_cpu_hours": round(point_seconds / 3600.0, 3),
            "planning_interval_cpu_hours": [
                round(low_seconds / 3600.0, 3),
                round(high_seconds / 3600.0, 3),
            ],
            "formal_profile_work": {
                "iterations": iterations,
                "functions_per_iteration": per_iteration,
                "holdout_functions": holdout,
                "simulations": formal_simulations,
            },
        },
        "boundary": (
            "This estimate sizes a future run; it is not a completed formal run, "
            "a performance result, or a wall-clock guarantee."
        ),
    }


def _checkpoint_bytes(
    model: BooleanOracleModel,
    *,
    config_sha256: str,
    source_sha256: str,
    dataset_sha256: str,
    command_sha256: str,
    log_sha256: str,
    profile_name: str,
    seed: int,
) -> bytes:
    trunk = model.trunk
    payload = {
        "state_dict": model.state_dict(),
        "in_channels": int(trunk.in_channels),
        "hidden": int(trunk.hidden),
        "layers": len(trunk.blocks),
        "mlp_hidden": int(model.action_head.mlp[0].out_features),
        "provenance": {
            "schema_version": "xa.foundation-checkpoint-provenance.v4",
            "profile": profile_name,
            "seed": seed,
            "initialization": "seeded_random_from_scratch",
            "parent_checkpoint": None,
            "v3_weights_loaded": False,
            "config_sha256": config_sha256,
            "source_manifest_sha256": source_sha256,
            "dataset_manifest_sha256": dataset_sha256,
            "command_sha256": command_sha256,
            "training_log_sha256": log_sha256,
        },
    }
    buffer = io.BytesIO()
    torch.save(payload, buffer)
    return buffer.getvalue()


def _command_record(
    *, config_path: Path, profile_name: str, output: Path, argv: list[str]
) -> dict[str, Any]:
    return {
        "schema_version": COMMAND_SCHEMA,
        "cwd": "${PROJECT_ROOT}",
        "executable": "python",
        "argv": [
            "scripts/train_foundation_v4.py",
            "--config",
            _normalise_path(config_path),
            "--profile",
            profile_name,
            "--output",
            f"${{OUTPUT_BUNDLE:-{output.name}}}",
        ],
        "observed_cli_argument_count": len(argv),
        "note": "The portable command is authoritative; absolute local paths are omitted.",
    }


def run_training_bundle(
    *, config_path: Path, profile_name: str, output: Path, argv: list[str]
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"output bundle already exists: {output}")
    _assert_crypto_evaluation_not_imported()
    config = _read_json(config_path)
    profile = validate_config(config, profile_name)
    selected_config = {
        **config,
        "selected_profile": profile_name,
    }
    config_bytes = canonical_json_bytes(selected_config)
    config_sha = sha256_bytes(config_bytes)

    sources = source_manifest(config)
    source_bytes = canonical_json_bytes(sources)
    source_sha = sha256_bytes(source_bytes)
    dataset, truth_tables = build_dataset_manifest(config, profile_name, profile)
    dataset_bytes = canonical_json_bytes(dataset)
    dataset_sha = sha256_bytes(dataset_bytes)
    command = _command_record(
        config_path=config_path, profile_name=profile_name, output=output, argv=argv
    )
    command_bytes = canonical_json_bytes(command)
    command_sha = sha256_bytes(command_bytes)

    total_started = time.perf_counter()
    model, log, training_stats = _train(
        config, profile_name, profile, dataset, truth_tables
    )
    total_training_seconds = time.perf_counter() - total_started
    log_text = "".join(canonical_json_text(event) + "\n" for event in log)
    log_bytes = log_text.encode("utf-8")
    log_sha = sha256_bytes(log_bytes)
    estimate = _probe_runtime(config, profile, _profile(config, "formal"))
    estimate_bytes = canonical_json_bytes(estimate)

    checkpoint_bytes = _checkpoint_bytes(
        model,
        config_sha256=config_sha,
        source_sha256=source_sha,
        dataset_sha256=dataset_sha,
        command_sha256=command_sha,
        log_sha256=log_sha,
        profile_name=profile_name,
        seed=int(profile["seed"]),
    )
    checkpoint_sha = sha256_bytes(checkpoint_bytes)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    peak_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    summary = {
        "schema_version": SUMMARY_SCHEMA,
        "model_id": config["model_id"],
        "profile": profile_name,
        "formal_training_completed": profile_name == "formal",
        "performance_evidence": False,
        "training_stats": training_stats,
        "total_training_seconds": round(total_training_seconds, 6),
        "checkpoint": {
            "relative_path": "checkpoint.pt",
            "sha256": checkpoint_sha,
            "size_bytes": len(checkpoint_bytes),
            "parameter_count": parameter_count,
        },
        "hash_links": {
            "config_sha256": config_sha,
            "source_manifest_sha256": source_sha,
            "dataset_manifest_sha256": dataset_sha,
            "command_sha256": command_sha,
            "training_log_sha256": log_sha,
            "resource_estimate_sha256": sha256_bytes(estimate_bytes),
        },
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
            "torch_threads": torch.get_num_threads(),
            "peak_rss_raw": peak_rss,
        },
    }
    summary_bytes = canonical_json_bytes(summary)
    model_card = {
        "schema_version": MODEL_CARD_SCHEMA,
        "model_id": config["model_id"],
        "artifact": summary["checkpoint"],
        "architecture": {
            "in_channels": int(model.trunk.in_channels),
            "hidden": int(model.trunk.hidden),
            "layers": len(model.trunk.blocks),
            "mlp_hidden": int(model.action_head.mlp[0].out_features),
            "parameter_count": parameter_count,
            "symmetry": "S_T x S_n permutation equivariant trunk",
        },
        "training": {
            "profile": profile_name,
            "seed": int(profile["seed"]),
            "initialization": "seeded_random_from_scratch",
            "parent_checkpoint": None,
            "v3_weights_loaded": False,
            "objective": (
                "Joint imitation of MCTS visit counts and regression of "
                "log(achieved_score/direct_score), with holdout accept/reject."
            ),
            "rejected_iteration_policy": "restore_best_state",
            "hash_links": summary["hash_links"],
        },
        "data": {
            "dataset_sha256": dataset["dataset_sha256"],
            "record_count": len(dataset["records"]),
            "allowed_num_vars": profile["allowed_num_vars"],
            "crypto_oracle_training_examples": 0,
            "crypto_excluded": True,
            "evaluation_not_accessed": True,
            "crypto_exclusion_strategy": config["crypto_exclusion"]["strategy"],
            "test_split": None,
        },
        "intended_use": [
            "Development of logical MCT Boolean-oracle factorisation search control",
            "AI-for-Quantum policy/value candidate requiring separate held-out evaluation",
        ],
        "out_of_scope": [
            "crypto-oracle training examples",
            "hardware execution or quantum advantage claims",
            "logical_and cost-domain deployment",
            "performance claims from tiny or training holdout results",
        ],
        "limitations": [
            "The training holdout is an accept gate, not an external test set.",
            "A formal profile run still requires separate C0-C7 and crypto held-out evaluation.",
            "Dirty-tree identity is closed by file hashes, not by commit identity alone.",
        ],
        "claim_boundary": config["claim_boundary"],
    }
    model_card_bytes = canonical_json_bytes(model_card)
    self_checks = {
        "schema_version": SELF_CHECK_SCHEMA,
        "checks": {
            "source_contract_matches": all(
                sha256_file(PROJECT_ROOT / item["path"]) == item["sha256"]
                for item in config["source_contract"]["files"]
            )
            and all(
                _tree_record(item["path"], include_files=False)["sha256"] == item["sha256"]
                for item in config["source_contract"]["trees"]
            ),
            "dataset_identity_unique": len(
                {(r["num_vars"], r["truth_table_sha256"]) for r in dataset["records"]}
            )
            == len(dataset["records"]),
            "split_disjoint": not (
                {
                    (r["num_vars"], r["truth_table_sha256"])
                    for r in dataset["records"]
                    if r["split"] == "train"
                }
                & {
                    (r["num_vars"], r["truth_table_sha256"])
                    for r in dataset["records"]
                    if r["split"] == "holdout"
                }
            ),
            "crypto_input_widths_excluded": not (
                set(profile["allowed_num_vars"])
                & set(config["crypto_exclusion"]["excluded_input_widths"])
            ),
            "crypto_truth_table_hashes_excluded": not (
                {r["truth_table_sha256"] for r in dataset["records"]}
                & set(config["crypto_exclusion"]["forbidden_truth_table_sha256"])
            ),
            "evaluation_not_accessed": dataset["crypto_exclusion"]["evaluation_not_accessed"]
            and CRYPTO_EVALUATION_MODULE not in sys.modules,
            "checkpoint_from_scratch": True,
            "training_log_finite": all(
                all(
                    not isinstance(value, float) or math.isfinite(value)
                    for value in event.values()
                )
                for event in log
            ),
        },
    }
    if not all(self_checks["checks"].values()):
        raise RuntimeError(f"training self-check failed: {self_checks}")
    _assert_crypto_evaluation_not_imported()

    writer = ArtifactBundleWriter(output)
    writer.add_bytes("config", "config_snapshot.json", config_bytes, "application/json")
    writer.add_bytes("source", "source_manifest.json", source_bytes, "application/json")
    writer.add_bytes("dataset", "dataset_manifest.json", dataset_bytes, "application/json")
    writer.add_bytes("command", "command.json", command_bytes, "application/json")
    writer.add_bytes("training_log", "training_log.jsonl", log_bytes, "application/x-ndjson")
    writer.add_bytes("checkpoint", "checkpoint.pt", checkpoint_bytes)
    writer.add_bytes("summary", "training_summary.json", summary_bytes, "application/json")
    writer.add_bytes("model_card", "model_card.json", model_card_bytes, "application/json")
    writer.add_bytes(
        "resource_estimate", "resource_estimate.json", estimate_bytes, "application/json"
    )
    writer.add_json("self_checks", "self_checks.json", self_checks)
    writer.finalize(
        bundle_metadata={
            "track": config["track"],
            "model_id": config["model_id"],
            "profile": profile_name,
            "formal_training_completed": profile_name == "formal",
            "performance_evidence": False,
        }
    )
    generic = verify_bundle(output, required_roles=REQUIRED_ROLES)
    if not generic.ok:
        raise RuntimeError(f"artifact bundle failed generic verification: {generic.errors}")
    return {
        "ok": True,
        "bundle": str(output),
        "profile": profile_name,
        "checkpoint_sha256": checkpoint_sha,
        "parameter_count": parameter_count,
        "dataset_sha256": dataset["dataset_sha256"],
        "formal_training_completed": profile_name == "formal",
        "performance_evidence": False,
        "environment": environment_record(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "xa202609" / "foundation_v4_provenance.json",
    )
    parser.add_argument("--profile", choices=("formal", "tiny", "test"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_training_bundle(
        config_path=args.config.resolve(),
        profile_name=args.profile,
        output=args.output.resolve(),
        argv=list(sys.argv if argv is None else argv),
    )
    print(canonical_json_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
