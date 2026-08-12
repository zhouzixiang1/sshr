#!/usr/bin/env python3
"""Verify one small, ordinary E6 replay-training experiment directory.

The format deliberately has no pre-seal ceremony, nested evidence graph, or
embedded verifier receipt.  Four human-inspectable payloads are covered by one
plain checksum file.  Scientific summaries are recomputed from ``raw.jsonl``;
therefore changing a result and regenerating the outer checksums is not enough
to make a modified experiment pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from e6.final_measurement_replay_v2 import (  # noqa: E402
    TRAINER_REPLAY_CONTRACT,
    canonical_vector_orbit_sha256,
    whole_vector_cluster_id,
)
from e6.frozen_case import (  # noqa: E402
    canonical_action_payload,
    canonical_action_sha256,
    canonical_vector_payload,
)
from e6.replay_training_evaluation_v1 import (  # noqa: E402
    evaluate_replay_training_heldout_v1,
    generate_heldout_bijections_v1,
    paired_arm_statistics_v1,
)
from e6.replay_training_corpus_v1 import (  # noqa: E402
    CorpusBuildSpecV1,
    build_replay_training_corpus_v1,
)
from e6.isolated_head_trainer_v2 import (  # noqa: E402
    CLAIM_BOUNDARY as TRAINER_CLAIM_BOUNDARY,
    ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA,
    fit_isolated_head_from_locked_replay_v2,
)
from e6.shared_oracle import (  # noqa: E402
    MonomialSharedAction,
    SemiAffineSharedAction,
    VectorANF,
    emit_compute_fanout_uncompute,
    verify_vector_oracle_semantics,
)
from e6.shared_scheduler import (  # noqa: E402
    SharedUtilityWeights,
    program_resource_summary,
)

CONFIG_SCHEMA = "xa.e6-q4ai-causal-config.v1"
RESULTS_SCHEMA = "xa.e6-replay-training-results.v1-development"
RAW_SCHEMA = "xa.e6-replay-training-row.v1-development"
HELDOUT_SCHEMA = "xa.e6-replay-training-heldout-evaluation.v1-development"
HELDOUT_CASE_SCHEMA = "xa.e6-replay-training-heldout-case.v1-development"
VERIFIER_SCHEMA = "xa.e6-replay-training-bundle-verifier.v1"
SOURCE_ARMS = (
    "classical_random_bitstring_replay",
    "classical_greedy_repeated_selection_replay",
    "qaoa_final_measurement_replay",
    "qaoa_permuted_label_control",
)
CLAIM_BOUNDARY = (
    "single-researcher deterministic development causal experiment; no "
    "equal-compute claim, hardware evidence, quantum advantage, cryptographic "
    "generalization, or formal performance evidence"
)
OUTCOME_CONTRACT = (
    "Y=emitted_total_abstract_score/direct_total_abstract_score;_lower_is_better;_"
    "failed_arm_uses_direct_fallback_and_ITT_Y=1"
)
EXPECTED_FILES = frozenset(
    {
        "config.json",
        "results.json",
        "raw.jsonl",
        "heldout_evaluation.json",
        "checksums.sha256",
    }
)
PAYLOAD_FILES = EXPECTED_FILES - {"checksums.sha256"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PAPER_RESOURCE_WEIGHTS = {
    "t": 1.0,
    "cnot": 0.04,
    "depth": 0.015,
    "gates": 0.01,
    "ancilla": 2.0,
}


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pairs_no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _decode_json_bytes(raw: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"cannot parse {name}: {exc}") from exc
    if type(value) is not dict:
        raise ValueError(f"{name} must contain one JSON object")
    if raw != _canonical_json(value):
        raise ValueError(f"{name} is not canonical JSON with one final LF")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    return _decode_json_bytes(path.read_bytes(), path.name)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("raw.jsonl must be non-empty and end in one LF")
    lines = raw.splitlines(keepends=True)
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines, 1):
        if line == b"\n":
            raise ValueError(f"raw.jsonl contains blank line {index}")
        rows.append(_decode_json_bytes(line, f"raw.jsonl:{index}"))
    return rows


def _native_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be a native integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _finite(value: object, name: str) -> float:
    if type(value) not in {int, float} or isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _sha(value: object, name: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256")
    return value


def _arm_mapping(value: object, name: str) -> dict[str, Any]:
    # JSON objects are encoded with sorted keys.  Scientific order is carried
    # by the explicit top-level arm list; mappings must contain the exact set.
    if type(value) is not dict or set(value) != set(SOURCE_ARMS):
        raise ValueError(f"{name} must contain the exact four-arm set")
    return value


def _source_tree_sha256(paths: Sequence[Path]) -> str:
    rows: list[dict[str, str]] = []
    seen: set[Path] = set()
    for root in paths:
        candidates = (root,) if root.is_file() else tuple(root.rglob("*.py"))
        for path in candidates:
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            rows.append(
                {
                    "path": resolved.relative_to(PROJECT_ROOT.resolve()).as_posix(),
                    "sha256": _sha256_file(resolved),
                }
            )
    rows.sort(key=lambda row: row["path"])
    return _sha256_bytes(_canonical_json(rows))


def _current_source() -> dict[str, object] | None:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT.parent,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT.parent,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        return {
            "commit_sha": head,
            "dirty": bool(status.strip()),
            "source_tree_sha256": _source_tree_sha256(
                (
                    PROJECT_ROOT / "src",
                    PROJECT_ROOT / "e6",
                    PROJECT_ROOT / "scripts",
                    PROJECT_ROOT / "tests",
                )
            ),
            "e6_tree_sha256": _source_tree_sha256((PROJECT_ROOT / "e6",)),
        }
    except (OSError, subprocess.CalledProcessError):
        return None


def _verify_files(root: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not root.is_dir() or root.is_symlink():
        return {}, ["experiment directory is missing or is a symlink"]
    entries = list(root.iterdir())
    actual = {entry.name for entry in entries}
    if actual != EXPECTED_FILES:
        missing = sorted(EXPECTED_FILES - actual)
        extra = sorted(actual - EXPECTED_FILES)
        if missing:
            errors.append("missing files: " + ", ".join(missing))
        if extra:
            errors.append("unexpected entries: " + ", ".join(extra))
    for entry in entries:
        if entry.is_symlink() or not entry.is_file():
            errors.append(f"non-regular experiment entry: {entry.name}")

    checksums: dict[str, str] = {}
    try:
        raw = (root / "checksums.sha256").read_bytes()
        text = raw.decode("ascii")
        if not raw.endswith(b"\n") or b"\r" in raw:
            raise ValueError("checksum file must use LF and end in one LF")
        for number, line in enumerate(text.splitlines(), 1):
            if not line:
                raise ValueError(f"blank checksum line {number}")
            parts = line.split("  ")
            if len(parts) != 2:
                raise ValueError(f"malformed checksum line {number}")
            digest, name = parts
            if _SHA256_RE.fullmatch(digest) is None:
                raise ValueError(f"invalid SHA-256 on checksum line {number}")
            if name not in PAYLOAD_FILES or "/" in name or "\\" in name:
                raise ValueError(f"unexpected checksum target: {name!r}")
            if name in checksums:
                raise ValueError(f"duplicate checksum target: {name}")
            checksums[name] = digest
        if set(checksums) != PAYLOAD_FILES:
            raise ValueError("checksum targets do not exactly match payload files")
        canonical_lines = "".join(
            f"{checksums[name]}  {name}\n" for name in sorted(PAYLOAD_FILES)
        ).encode("ascii")
        if raw != canonical_lines:
            raise ValueError("checksum entries are not in canonical filename order")
        for name, expected in checksums.items():
            path = root / name
            if (
                path.is_file()
                and not path.is_symlink()
                and _sha256_file(path) != expected
            ):
                errors.append(f"checksum mismatch: {name}")
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"invalid checksums.sha256: {exc}")
    return checksums, errors


def _validate_config(config: Mapping[str, Any]) -> None:
    if set(config) != {
        "base_config",
        "profile_name",
        "effective_profile",
        "source",
        "base_config_file_sha256",
    }:
        raise ValueError("effective config top-level fields changed")
    base = config.get("base_config")
    if type(base) is not dict or base.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("unsupported config schema")
    _native_int(base.get("seed"), "config.base_config.seed", minimum=0)
    source = config.get("source")
    if type(source) is not dict or set(source) != {
        "commit_sha",
        "dirty",
        "source_tree_sha256",
        "e6_tree_sha256",
    }:
        raise ValueError("config.source fields changed")
    commit = source.get("commit_sha")
    if type(commit) is not str or _COMMIT_RE.fullmatch(commit) is None:
        raise ValueError("config.source.commit_sha must be a lowercase Git commit")
    if type(source.get("dirty")) is not bool:
        raise ValueError("config.source.dirty must be a native boolean")
    _sha(source.get("source_tree_sha256"), "config.source.source_tree_sha256")
    _sha(source.get("e6_tree_sha256"), "config.source.e6_tree_sha256")
    base_file_sha = _sha(
        config.get("base_config_file_sha256"), "base_config_file_sha256"
    )
    canonical_base_path = PROJECT_ROOT / "configs/xa202609/e6_q4ai_causal_v1.json"
    canonical_base = json.loads(canonical_base_path.read_text(encoding="utf-8"))
    if base != canonical_base or base_file_sha != _sha256_file(canonical_base_path):
        raise ValueError("embedded base config is not the versioned config file")
    profile_name = config.get("profile_name")
    profiles = base.get("profiles")
    if type(profile_name) is not str or type(profiles) is not dict:
        raise ValueError("config profile selection is invalid")
    if (
        profile_name not in profiles
        or config.get("effective_profile") != profiles[profile_name]
    ):
        raise ValueError("effective_profile is not an exact selected profile copy")
    if base.get("arms") != list(SOURCE_ARMS):
        raise ValueError("config arms changed")
    resource_weights = base.get("resource_weights")
    if type(resource_weights) is not dict or set(resource_weights) != set(
        PAPER_RESOURCE_WEIGHTS
    ):
        raise ValueError("config resource_weights field contract changed")
    if any(
        _finite(resource_weights[field], f"config.resource_weights.{field}") != expected
        for field, expected in PAPER_RESOURCE_WEIGHTS.items()
    ):
        raise ValueError("config resource_weights changed from the paper weights")
    training = base.get("head_training")
    if type(training) is not dict:
        raise ValueError("config.head_training must be an object")
    _native_int(
        training.get("head_hidden"), "config.head_training.head_hidden", minimum=1
    )
    for field in (
        "learning_rate",
        "weight_decay",
        "policy_loss_weight",
        "value_loss_weight",
    ):
        _finite(training.get(field), f"config.head_training.{field}")
    for field in ("head_seed", "sampler_seed"):
        _native_int(training.get(field), f"config.head_training.{field}", minimum=0)
    effective = config["effective_profile"]
    for field in ("update_steps", "batch_size", "train_case_count"):
        _native_int(
            effective.get(field), f"config.effective_profile.{field}", minimum=1
        )
    _native_int(
        effective.get("heldout_dataset_seed"),
        "config.effective_profile.heldout_dataset_seed",
        minimum=0,
    )
    output = base.get("output_contract")
    if type(output) is not dict or output.get("files") != sorted(EXPECTED_FILES):
        # The runner config lists its contract in presentation order; compare sets too.
        if type(output) is not dict or set(output.get("files", [])) != EXPECTED_FILES:
            raise ValueError("config output file contract changed")
    if output.get("overwrite") is not False:
        raise ValueError("config output overwrite contract changed")
    if (
        output.get("performance_evidence") is not False
        or output.get("formal_evaluation") is not False
    ):
        raise ValueError("config output claim flags changed")
    if base.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ValueError("config claim boundary changed")


def _validate_train_rows(
    rows: Sequence[dict[str, Any]], config: Mapping[str, Any]
) -> tuple[object, list[str]]:
    if not rows:
        raise ValueError("raw.jsonl contains no train_case rows")
    case_ids: list[str] = []
    case_shas: list[str] = []
    descriptors: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        if (
            row.get("schema_version") != RAW_SCHEMA
            or row.get("record_type") != "train_case"
        ):
            raise ValueError(f"train row {index} schema/type changed")
        case_id = row.get("case_id")
        if type(case_id) is not str or not case_id:
            raise ValueError(f"train row {index} case_id is invalid")
        case_ids.append(case_id)
        case_shas.append(_sha(row.get("case_sha256"), f"train[{index}].case_sha256"))
        if _native_int(row.get("input_count"), f"train[{index}].input_count") not in {
            6,
            7,
        }:
            raise ValueError("training input_count must be 6 or 7")
        if row.get("split_role") != "train_replay":
            raise ValueError("training split_role changed")
        observations = _arm_mapping(
            row.get("observation_sha256_by_arm"),
            f"train[{index}].observation_sha256_by_arm",
        )
        targets = _arm_mapping(
            row.get("target_sha256_by_arm"),
            f"train[{index}].target_sha256_by_arm",
        )
        for arm in SOURCE_ARMS:
            _sha(observations[arm], f"train[{index}].observation[{arm}]")
            _sha(targets[arm], f"train[{index}].target[{arm}]")
        descriptor = row.get("case_descriptor")
        if type(descriptor) is not dict:
            raise ValueError("train row lacks exact corpus case_descriptor")
        if descriptor.get("case_id") != case_id or descriptor.get(
            "case_sha256"
        ) != row.get("case_sha256"):
            raise ValueError("train row/case descriptor identity mismatch")
        if dict(descriptor.get("arm_observation_sha256", [])) != observations:
            raise ValueError("train row/case descriptor observation binding mismatch")
        if dict(descriptor.get("target_sha256_by_arm", [])) != targets:
            raise ValueError("train row/case descriptor target binding mismatch")
        descriptors.append(descriptor)
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("training case IDs must be unique")
    if len(set(case_shas)) != len(case_shas):
        raise ValueError("training case SHA values must be unique")
    base = config["base_config"]
    effective = config["effective_profile"]
    total = _native_int(effective["train_case_count"], "train_case_count", minimum=1)
    if total % 2:
        raise ValueError("training case count must split equally across n=6/7")
    spec = CorpusBuildSpecV1(
        seed=_native_int(base["seed"], "base seed", minimum=0),
        cases_per_width=total // 2,
        observation_budget=_native_int(
            effective["replay_observation_budget"], "replay budget", minimum=1
        ),
        qaoa_optimizer_restarts=_native_int(
            effective["qaoa_optimizer_restarts"], "QAOA restarts", minimum=1
        ),
        qaoa_optimizer_steps=_native_int(
            effective["qaoa_optimizer_steps"], "QAOA steps", minimum=0
        ),
    )
    rebuilt = build_replay_training_corpus_v1(spec)
    expected_descriptors = [item.to_dict() for item in rebuilt.descriptor.case_roster]
    if descriptors != expected_descriptors:
        raise ValueError(
            "raw train descriptors do not match deterministic corpus rebuild"
        )
    return rebuilt, case_ids


def _action_from_payload(raw: object, name: str) -> object:
    if type(raw) is not dict:
        raise ValueError(f"{name} must be an action object")
    kind = raw.get("kind")
    targets = raw.get("targets")
    if type(targets) is not list or any(type(value) is not int for value in targets):
        raise ValueError(f"{name}.targets must be native integers")
    if kind == "monomial":
        action = MonomialSharedAction(
            _native_int(raw.get("monomial"), f"{name}.monomial", minimum=0),
            tuple(targets),
        )
    elif kind == "semi_affine":
        affine_const = raw.get("affine_const")
        if type(affine_const) is not bool:
            raise ValueError(f"{name}.affine_const must be a native boolean")
        action = SemiAffineSharedAction(
            _native_int(raw.get("base_monomial"), f"{name}.base_monomial", minimum=0),
            _native_int(raw.get("affine_mask"), f"{name}.affine_mask", minimum=1),
            affine_const,
            tuple(targets),
        )
    else:
        raise ValueError(f"{name}.kind is unsupported")
    if canonical_action_payload(action) != raw:
        raise ValueError(f"{name} is not the canonical action payload")
    return action


def _semantic_payload(program: object) -> dict[str, object]:
    verification = verify_vector_oracle_semantics(program, max_assignments=1 << 12)
    payload = verification.to_dict()
    if type(payload) is not dict:
        raise RuntimeError("semantic verifier returned a non-dict payload")
    return payload


def _restore_eval_cases(
    rows: Sequence[dict[str, Any]], *, weights: SharedUtilityWeights
) -> tuple[dict[str, object], ...]:
    if not rows:
        raise ValueError("raw.jsonl contains no eval_case rows")
    restored: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    seen_orbits: set[str] = set()
    for index, raw in enumerate(rows):
        if (
            raw.get("schema_version") != RAW_SCHEMA
            or raw.get("record_type") != "eval_case"
        ):
            raise ValueError(f"eval row {index} schema/type changed")
        row = dict(raw)
        row.pop("record_type")
        row["schema_version"] = HELDOUT_CASE_SCHEMA
        case_id = row.get("case_id")
        if type(case_id) is not str or not case_id or case_id in seen_ids:
            raise ValueError(f"eval row {index} case_id is invalid or duplicated")
        seen_ids.add(case_id)
        width = _native_int(row.get("input_count"), f"eval[{index}].input_count")
        if width not in {4, 5} or row.get("output_count") != width:
            raise ValueError("held-out cases must be n=4/5 bijections")
        values = row.get("value_table")
        if type(values) is not list or len(values) != 1 << width:
            raise ValueError("held-out value_table width changed")
        if any(type(value) is not int for value in values) or set(values) != set(
            range(1 << width)
        ):
            raise ValueError("held-out value_table is not a bijection")
        value_table_sha = _sha256_bytes(
            _canonical_json(
                {
                    "schema_version": "xa.e6-heldout-bijection-value-table.v1",
                    "input_count": width,
                    "output_count": width,
                    "values": values,
                }
            )
        )
        if row.get("value_table_sha256") != value_table_sha:
            raise ValueError("held-out value-table SHA mismatch")
        vector = VectorANF.from_value_table(width, width, values)
        vector_sha = _sha256_bytes(_canonical_json(canonical_vector_payload(vector)))
        if row.get("vector_sha256") != vector_sha:
            raise ValueError("held-out vector SHA mismatch")
        orbit_sha = canonical_vector_orbit_sha256(vector)
        if row.get("orbit_cluster_sha256") != orbit_sha or orbit_sha in seen_orbits:
            raise ValueError("held-out orbit SHA mismatch or duplicate orbit")
        seen_orbits.add(orbit_sha)
        if row.get("whole_vector_cluster_sha256") != whole_vector_cluster_id(vector):
            raise ValueError("held-out whole-vector cluster SHA mismatch")
        direct_program = emit_compute_fanout_uncompute(vector, (), max_ancilla=2)
        direct_resources = program_resource_summary(
            direct_program, weights=weights
        ).to_dict()
        direct_semantics = _semantic_payload(direct_program)
        if row.get("direct_program_resource_summary") != direct_resources:
            raise ValueError("recorded direct resources fail independent recomputation")
        if row.get("direct_semantic_verification") != direct_semantics:
            raise ValueError("recorded direct semantics fail independent recomputation")
        if direct_semantics.get("ok") is not True:
            raise ValueError("recomputed direct program failed semantics")
        direct = _finite(row.get("direct_resource_score"), "direct_resource_score")
        if direct != float(direct_resources["total_abstract_score"]):
            raise ValueError(
                "direct_resource_score disagrees with recomputed resources"
            )
        if direct < 0.0:
            raise ValueError("direct_resource_score cannot be negative")
        arms = _arm_mapping(row.get("arms"), f"eval[{index}].arms")
        common = row.get("common_pool_action_sha256")
        if type(common) is not list or not common:
            raise ValueError("held-out common action pool must be non-empty")
        common_set = {_sha(item, "common action SHA") for item in common}
        if len(common_set) != len(common):
            raise ValueError("held-out common action pool contains duplicates")
        for arm, payload in arms.items():
            if type(payload) is not dict:
                raise ValueError(f"eval[{index}].arms[{arm}] must be an object")
            selected = payload.get("selected_action_sha256")
            if type(selected) is not list or any(
                _sha(item, "selected action SHA") not in common_set for item in selected
            ):
                raise ValueError("selected action is outside the common pool")
            selected_payloads = payload.get("selected_actions")
            if type(selected_payloads) is not list:
                raise ValueError("selected_actions must be a native list")
            selected_actions = tuple(
                _action_from_payload(
                    item, f"eval[{index}].arms[{arm}].action[{offset}]"
                )
                for offset, item in enumerate(selected_payloads)
            )
            if [
                canonical_action_sha256(action) for action in selected_actions
            ] != selected:
                raise ValueError("selected action payload/SHA binding mismatch")
            attempted_program = emit_compute_fanout_uncompute(
                vector, selected_actions, max_ancilla=2
            )
            attempted_resources = program_resource_summary(
                attempted_program, weights=weights
            ).to_dict()
            attempted_semantics = _semantic_payload(attempted_program)
            ratio = _finite(payload.get("score_ratio"), "score_ratio")
            itt = _finite(payload.get("itt_score_ratio_y"), "itt_score_ratio_y")
            semantic = payload.get("semantic_verification")
            degraded = payload.get("degraded")
            valid = payload.get("valid_observation")
            eligible = payload.get("analysis_eligible")
            fallback = payload.get("direct_fallback_used")
            if any(
                type(flag) is not bool
                for flag in (semantic, degraded, valid, eligible, fallback)
            ):
                raise ValueError("arm status flags must be native booleans")
            final_resources = payload.get("final_program_resource_summary")
            if type(final_resources) is not dict:
                raise ValueError("final resource summary is missing")
            final_score = _finite(
                final_resources.get("total_abstract_score"), "final score"
            )
            expected_ratio = (
                1.0 if direct == 0.0 and final_score == 0.0 else final_score / direct
            )
            if not math.isclose(
                ratio, expected_ratio, rel_tol=1.0e-12, abs_tol=1.0e-12
            ):
                raise ValueError("score ratio does not match final/direct resources")
            if valid:
                if degraded or fallback or not eligible or not semantic:
                    raise ValueError("valid arm status flags contradict each other")
                observed = _finite(payload.get("observed_score_ratio_y"), "observed Y")
                if not math.isclose(
                    observed, ratio, rel_tol=0.0, abs_tol=0.0
                ) or not math.isclose(itt, ratio, rel_tol=0.0, abs_tol=0.0):
                    raise ValueError("valid arm Y fields disagree")
                if (
                    payload.get("attempted_program_resource_summary")
                    != attempted_resources
                    or payload.get("final_program_resource_summary")
                    != attempted_resources
                    or payload.get("attempted_semantic_verification")
                    != attempted_semantics
                    or payload.get("final_semantic_verification") != attempted_semantics
                ):
                    raise ValueError("valid arm program evidence fails recomputation")
            else:
                if (
                    not degraded
                    or not fallback
                    or eligible
                    or payload.get("observed_score_ratio_y") is not None
                    or itt != 1.0
                ):
                    raise ValueError(
                        "fallback arm status/Y fields contradict each other"
                    )
                if (
                    payload.get("final_program_resource_summary") != direct_resources
                    or payload.get("final_semantic_verification") != direct_semantics
                ):
                    raise ValueError(
                        "fallback final evidence is not the direct program"
                    )
                recorded_attempted_resources = payload.get(
                    "attempted_program_resource_summary"
                )
                recorded_attempted_semantics = payload.get(
                    "attempted_semantic_verification"
                )
                if recorded_attempted_resources is not None and (
                    recorded_attempted_resources != attempted_resources
                    or recorded_attempted_semantics != attempted_semantics
                ):
                    raise ValueError("fallback attempted evidence fails recomputation")
        if (
            row.get("formal_evaluation") is not False
            or row.get("performance_evidence") is not False
        ):
            raise ValueError("held-out case overclaims its evidence role")
        restored.append(row)
    expected_order = sorted(
        restored,
        key=lambda item: (int(item["input_count"]), str(item["case_id"])),
    )
    if restored != expected_order:
        raise ValueError("held-out rows are not in canonical width/case order")
    if {int(row["input_count"]) for row in restored} != {4, 5}:
        raise ValueError("held-out rows must contain both n=4 and n=5 strata")
    return tuple(restored)


def _recompute_heldout(
    heldout: Mapping[str, Any],
    eval_rows: Sequence[dict[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    weights = SharedUtilityWeights(**config["base_config"]["resource_weights"])
    cases = _restore_eval_cases(eval_rows, weights=weights)
    if heldout.get("schema_version") != HELDOUT_SCHEMA:
        raise ValueError("unsupported held-out evaluation schema")
    protocol = heldout.get("protocol")
    if type(protocol) is not dict:
        raise ValueError("held-out protocol is missing")
    if protocol.get("arm_order") != list(SOURCE_ARMS):
        raise ValueError("held-out arm order changed")
    if (
        protocol.get("input_widths") != [4, 5]
        or protocol.get("outcome_contract") != OUTCOME_CONTRACT
    ):
        raise ValueError("held-out scientific endpoint changed")
    if protocol.get("utility_weights") != config["base_config"]["resource_weights"]:
        raise ValueError("held-out protocol/config mismatch: utility_weights")
    if protocol.get("scheduler_utility") != "arm_neutral_raw_analytic_utility":
        raise ValueError("held-out scheduler utility contract changed")
    dataset_seed = _native_int(
        protocol.get("dataset_seed"), "heldout.protocol.dataset_seed", minimum=0
    )
    bootstrap_seed = _native_int(
        protocol.get("bootstrap_seed"), "heldout.protocol.bootstrap_seed", minimum=0
    )
    signflip_seed = _native_int(
        protocol.get("signflip_seed"), "heldout.protocol.signflip_seed", minimum=0
    )
    resamples = _native_int(
        protocol.get("bootstrap_resamples"),
        "heldout.protocol.bootstrap_resamples",
        minimum=32,
    )
    signflip = _native_int(
        protocol.get("signflip_resamples_requested"),
        "heldout.protocol.signflip_resamples_requested",
        minimum=32,
    )
    base_heldout = config["base_config"]["heldout_evaluation"]
    effective = config["effective_profile"]
    expected_protocol_fields = {
        "input_widths": base_heldout["input_counts"],
        "dataset_seed": effective["heldout_dataset_seed"],
        "cases_per_width": effective["heldout_cases_per_input_count"],
        "source_candidate_cap": base_heldout["candidate_universe_cap"],
        "top_k": base_heldout["learned_top_k"],
        "scheduler_budget": base_heldout["scheduler_budget"],
        "bootstrap_resamples": effective["bootstrap_resamples"],
        "bootstrap_seed": base_heldout["bootstrap_seed"],
        "signflip_resamples_requested": effective["sign_flip_resamples"],
        "signflip_seed": base_heldout["sign_flip_seed"],
    }
    for field, expected_value in expected_protocol_fields.items():
        if protocol.get(field) != expected_value:
            raise ValueError(f"held-out protocol/config mismatch: {field}")
    statistics = paired_arm_statistics_v1(
        cases,
        resamples=resamples,
        signflip_resamples=signflip,
        bootstrap_seed=bootstrap_seed,
        signflip_seed=signflip_seed,
    )
    if heldout.get("case_rows") != list(cases):
        raise ValueError("heldout case_rows do not exactly match raw eval rows")
    if heldout.get("statistics") != statistics:
        raise ValueError(
            "heldout statistics differ from independent raw-row recomputation"
        )
    expected_cases = generate_heldout_bijections_v1(
        seed=dataset_seed,
        cases_per_width=_native_int(
            protocol.get("cases_per_width"),
            "heldout.protocol.cases_per_width",
            minimum=1,
        ),
    )
    expected_identity = [
        (
            item["case_id"],
            item["value_table_sha256"],
            item["vector_sha256"],
            item["orbit_cluster_sha256"],
        )
        for item in expected_cases
    ]
    actual_identity = [
        (
            item["case_id"],
            item["value_table_sha256"],
            item["vector_sha256"],
            item["orbit_cluster_sha256"],
        )
        for item in cases
    ]
    if actual_identity != expected_identity:
        raise ValueError("held-out case roster is not the seeded generator output")
    if heldout.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ValueError("held-out claim boundary changed")
    if (
        heldout.get("heldout_development_evaluation") is not True
        or heldout.get("formal_evaluation") is not False
        or heldout.get("performance_evidence") is not False
    ):
        raise ValueError("held-out evidence flags changed")
    expected = dict(heldout)
    claimed_sha = expected.pop("evaluation_sha256", None)
    if claimed_sha != _sha256_bytes(_canonical_json(expected)):
        raise ValueError("held-out evaluation canonical SHA mismatch")
    return expected | {"evaluation_sha256": claimed_sha}


def _training_config_payload(
    base: Mapping[str, Any], profile: Mapping[str, Any], arm: str
) -> bytes:
    head = base["head_training"]
    return _canonical_json(
        {
            "schema_version": ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA,
            "source_arm": arm,
            "update_steps": profile["update_steps"],
            "batch_size": profile["batch_size"],
            "learning_rate": head["learning_rate"],
            "weight_decay": head["weight_decay"],
            "policy_loss_weight": head["policy_loss_weight"],
            "value_loss_weight": head["value_loss_weight"],
            "max_grad_norm": head["max_grad_norm"],
            "head_hidden": head["head_hidden"],
            "head_seed": head["head_seed"],
            "sampler_seed": head["sampler_seed"],
            "device": head["device"],
            "dtype": head["dtype"],
            "cpu_threads": head["cpu_threads"],
            "optimizer": head["optimizer"],
            "scheduler": head["scheduler"],
            "early_stopping": head["early_stopping"],
            "resume": head["resume"],
            "performance_evidence": False,
        }
    )


def _validate_results(
    results: Mapping[str, Any],
    config: Mapping[str, Any],
    train_rows: Sequence[dict[str, Any]],
    corpus: object,
) -> None:
    expected_fields = {
        "schema_version",
        "run_id",
        "source_commit",
        "source_dirty",
        "config_sha256",
        "corpus_sha256",
        "arms",
        "initial_head_sha",
        "final_head_sha_by_arm",
        "training_report_by_arm",
        "timing",
        "claim_boundary",
        "performance_evidence",
    }
    if set(results) != expected_fields:
        raise ValueError("results.json top-level fields changed")
    if results["schema_version"] != RESULTS_SCHEMA:
        raise ValueError("unsupported results schema")
    if type(results["run_id"]) is not str or not results["run_id"]:
        raise ValueError("results.run_id must be non-empty")
    source = config["source"]
    if results["source_commit"] != source["commit_sha"]:
        raise ValueError("results/config source commit mismatch")
    if results["source_dirty"] is not source["dirty"]:
        raise ValueError("results/config source dirty flag mismatch")
    if results["arms"] != list(SOURCE_ARMS):
        raise ValueError("results arm order changed")
    descriptor = corpus.descriptor
    if results["corpus_sha256"] != descriptor.corpus_sha256:
        raise ValueError("results corpus SHA does not match train rows")
    initial = _sha(results["initial_head_sha"], "results.initial_head_sha")
    finals = _arm_mapping(results["final_head_sha_by_arm"], "final_head_sha_by_arm")
    reports = _arm_mapping(results["training_report_by_arm"], "training_report_by_arm")
    training = config["effective_profile"]
    base = config["base_config"]
    lock_payload = corpus.corpus_lock_payload
    lock = json.loads(lock_payload.decode("utf-8"))
    expected_group_ids = [item.group_id for item in descriptor.case_roster]
    foundation_tensors: set[str] = set()
    schedules: set[str] = set()
    for arm in SOURCE_ARMS:
        final = _sha(finals[arm], f"results.final_head_sha_by_arm[{arm}]")
        if final == initial:
            raise ValueError(f"arm {arm} did not change the initialized head")
        report = reports[arm]
        if type(report) is not dict or report.get("source_arm") != arm:
            raise ValueError(f"training report arm binding changed for {arm}")
        if report.get("initial_head_tensor_sha256") != initial:
            raise ValueError(f"training report initial head mismatch for {arm}")
        if report.get("final_head_tensor_sha256") != final:
            raise ValueError(f"training report final head mismatch for {arm}")
        if report.get("sample_count") != len(train_rows):
            raise ValueError(f"training report sample count mismatch for {arm}")
        if report.get("update_steps") != training["update_steps"]:
            raise ValueError(f"training report update budget mismatch for {arm}")
        if report.get("batch_size") != training["batch_size"]:
            raise ValueError(f"training report batch budget mismatch for {arm}")
        if report.get("sample_presentations") != (
            training["update_steps"] * training["batch_size"]
        ):
            raise ValueError(f"training report presentation budget mismatch for {arm}")
        expected_bindings = {
            "group_ids": expected_group_ids,
            "input_counts": [6, 7],
            "config_payload_sha256": _sha256_bytes(
                _training_config_payload(base, training, arm)
            ),
            "corpus_payload_sha256": _sha256_bytes(lock_payload),
            "corpus_lock_sha256": lock["lock_sha256"],
            "split_registry_sha256": descriptor.registry_sha256,
            "protocol_sha256": descriptor.protocol_sha256,
            "source_manifest_sha256": descriptor.source_manifest_sha256,
            "foundation_checkpoint_sha256": base["head_training"][
                "foundation_checkpoint_sha256"
            ],
            "optimizer": "HeadOnlyIntegrityAdamW",
            "trainer_replay_contract": TRAINER_REPLAY_CONTRACT,
            "compute_budget_equal": False,
            "claim_boundary": TRAINER_CLAIM_BOUNDARY,
        }
        for field, expected_value in expected_bindings.items():
            if report.get(field) != expected_value:
                raise ValueError(f"training report {field} binding mismatch for {arm}")
        foundation_tensors.add(
            _sha(
                report.get("foundation_tensor_sha256"),
                f"training report foundation tensor {arm}",
            )
        )
        schedules.add(
            _sha(
                report.get("training_schedule_sha256"),
                f"training report schedule {arm}",
            )
        )
        _finite(report.get("initial_weighted_loss"), "initial weighted loss")
        _finite(report.get("final_weighted_loss"), "final weighted loss")
        if report.get("head_training_status") != "modified_unsealed":
            raise ValueError(f"training report status changed for {arm}")
        if report.get("formal_evaluation") is not False:
            raise ValueError(f"training report formal claim changed for {arm}")
        if report.get("performance_evidence") is not False:
            raise ValueError(f"training report performance claim changed for {arm}")
    if len(foundation_tensors) != 1:
        raise ValueError("four arms did not use one foundation tensor identity")
    if len(schedules) != 1:
        raise ValueError("four arms did not use one training schedule")
    if results["timing"] != {
        "recorded": False,
        "reason": "excluded_from_bundle_for_deterministic_reproduction",
    }:
        raise ValueError("results.timing must use the deterministic no-timing contract")
    if results["claim_boundary"] != CLAIM_BOUNDARY:
        raise ValueError("results claim boundary changed")
    if results["performance_evidence"] is not False:
        raise ValueError("development results cannot claim performance evidence")


def _replay_training_and_evaluation(
    *,
    config: Mapping[str, Any],
    corpus: object,
    results: Mapping[str, Any],
    heldout: Mapping[str, Any],
) -> None:
    """Rerun the complete deterministic training-to-selection path."""

    base = config["base_config"]
    profile = config["effective_profile"]
    recorded_reports = _arm_mapping(
        results["training_report_by_arm"], "training_report_by_arm"
    )
    recorded_finals = _arm_mapping(
        results["final_head_sha_by_arm"], "final_head_sha_by_arm"
    )
    models: dict[str, object] = {}
    replayed_reports: dict[str, dict[str, object]] = {}
    for arm in SOURCE_ARMS:
        training_payload = _training_config_payload(base, profile, arm)
        trained = fit_isolated_head_from_locked_replay_v2(
            corpus.materials,
            corpus.registry,
            corpus_lock_payload=corpus.corpus_lock_payload,
            expected_corpus_lock_payload_sha256=_sha256_bytes(
                corpus.corpus_lock_payload
            ),
            config_payload=training_payload,
            expected_config_payload_sha256=_sha256_bytes(training_payload),
        )
        report = trained.report.to_dict()
        if _canonical_json(report) != _canonical_json(recorded_reports[arm]):
            raise ValueError(f"deterministic training report mismatch for {arm}")
        if report["final_head_tensor_sha256"] != recorded_finals[arm]:
            raise ValueError(f"deterministic final-head digest mismatch for {arm}")
        models[arm] = trained.model
        replayed_reports[arm] = report

    initial_heads = {
        str(report["initial_head_tensor_sha256"])
        for report in replayed_reports.values()
    }
    if initial_heads != {results["initial_head_sha"]}:
        raise ValueError("deterministic replay initial-head identity mismatch")

    heldout_config = base["heldout_evaluation"]
    weights = SharedUtilityWeights(**base["resource_weights"])
    replayed_heldout = evaluate_replay_training_heldout_v1(
        models,
        seed=profile["heldout_dataset_seed"],
        cases_per_width=profile["heldout_cases_per_input_count"],
        top_k=heldout_config["learned_top_k"],
        scheduler_budget=heldout_config["scheduler_budget"],
        bootstrap_resamples=profile["bootstrap_resamples"],
        signflip_resamples=profile["sign_flip_resamples"],
        bootstrap_seed=heldout_config["bootstrap_seed"],
        signflip_seed=heldout_config["sign_flip_seed"],
        utility_weights=weights,
    )
    if _canonical_json(replayed_heldout) != _canonical_json(heldout):
        raise ValueError("deterministic trained-head held-out evaluation mismatch")


def verify_e6_replay_training_bundle_v1(
    run_dir: str | Path, *, require_current_commit: bool = False
) -> dict[str, Any]:
    root = Path(run_dir)
    checks: dict[str, bool] = {}
    errors: list[str] = []

    _checksums, file_errors = _verify_files(root)
    checks["files_and_checksums"] = not file_errors
    errors.extend(file_errors)
    if file_errors:
        return {
            "schema_version": VERIFIER_SCHEMA,
            "ok": False,
            "checks": checks,
            "errors": errors,
        }

    try:
        config = _read_json(root / "config.json")
        results = _read_json(root / "results.json")
        heldout = _read_json(root / "heldout_evaluation.json")
        raw_rows = _read_jsonl(root / "raw.jsonl")
        checks["canonical_payloads"] = True
    except (OSError, ValueError) as exc:
        checks["canonical_payloads"] = False
        errors.append(str(exc))
        return {
            "schema_version": VERIFIER_SCHEMA,
            "ok": False,
            "checks": checks,
            "errors": errors,
        }

    try:
        _validate_config(config)
        checks["config_contract"] = True
    except (KeyError, TypeError, ValueError) as exc:
        checks["config_contract"] = False
        errors.append(f"config: {exc}")

    current_source = _current_source()
    recorded_source = config.get("source")
    if (
        current_source is not None
        and type(recorded_source) is dict
        and recorded_source.get("commit_sha") == current_source["commit_sha"]
    ):
        source_ok = all(
            recorded_source.get(field) == current_source[field]
            for field in ("commit_sha", "source_tree_sha256", "e6_tree_sha256")
        )
        checks["current_source_hash_binding"] = source_ok
        if not source_ok:
            errors.append("current source tree does not match config source hashes")

    config_sha = _sha256_file(root / "config.json")
    if results.get("config_sha256") == config_sha:
        checks["config_hash_binding"] = True
    else:
        checks["config_hash_binding"] = False
        errors.append("results config SHA does not match config.json bytes")

    train_rows = [row for row in raw_rows if row.get("record_type") == "train_case"]
    eval_rows = [row for row in raw_rows if row.get("record_type") == "eval_case"]
    if len(train_rows) + len(eval_rows) != len(raw_rows):
        checks["raw_record_types"] = False
        errors.append("raw.jsonl contains an unregistered record_type")
    else:
        checks["raw_record_types"] = True

    corpus = None
    corpus_sha = ""
    try:
        corpus, _case_ids = _validate_train_rows(train_rows, config)
        corpus_sha = corpus.descriptor.corpus_sha256
        checks["training_corpus"] = True
    except (KeyError, TypeError, ValueError) as exc:
        checks["training_corpus"] = False
        errors.append(f"training corpus: {exc}")

    try:
        if corpus is None:
            raise ValueError("training corpus did not validate")
        _validate_results(results, config, train_rows, corpus)
        checks["four_arm_training_fairness"] = True
    except (KeyError, TypeError, ValueError) as exc:
        checks["four_arm_training_fairness"] = False
        errors.append(f"results: {exc}")

    try:
        _recompute_heldout(heldout, eval_rows, config)
        checks["heldout_semantic_recomputation"] = True
    except (KeyError, TypeError, ValueError) as exc:
        checks["heldout_semantic_recomputation"] = False
        errors.append(f"heldout: {exc}")

    if errors:
        checks["deterministic_training_to_scheduler_replay"] = False
    else:
        try:
            if corpus is None:
                raise ValueError("training corpus did not validate")
            _replay_training_and_evaluation(
                config=config,
                corpus=corpus,
                results=results,
                heldout=heldout,
            )
            checks["deterministic_training_to_scheduler_replay"] = True
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            checks["deterministic_training_to_scheduler_replay"] = False
            errors.append(f"training replay: {exc}")

    claim_ok = bool(
        config.get("base_config", {}).get("claim_boundary") == CLAIM_BOUNDARY
        and config.get("base_config", {})
        .get("output_contract", {})
        .get("performance_evidence")
        is False
        and results.get("claim_boundary") == CLAIM_BOUNDARY
        and results.get("performance_evidence") is False
        and heldout.get("claim_boundary") == CLAIM_BOUNDARY
        and heldout.get("formal_evaluation") is False
        and heldout.get("performance_evidence") is False
    )
    checks["claim_boundary"] = claim_ok
    if not claim_ok:
        errors.append("development claim boundary changed")

    if require_current_commit:
        current_ok = bool(
            current_source is not None
            and type(recorded_source) is dict
            and all(
                recorded_source.get(field) == current_source[field]
                for field in (
                    "commit_sha",
                    "source_tree_sha256",
                    "e6_tree_sha256",
                )
            )
            and recorded_source.get("dirty") is False
            and current_source.get("dirty") is False
        )
        checks["current_clean_commit"] = current_ok
        if not current_ok:
            errors.append("bundle is not bound to the current clean commit")

    return {
        "schema_version": VERIFIER_SCHEMA,
        "ok": not errors,
        "checks": checks,
        "errors": errors,
        "run_id": results.get("run_id"),
        "source_commit": results.get("source_commit"),
        "config_sha256": config_sha,
        "corpus_sha256": corpus_sha or None,
        "train_case_count": len(train_rows),
        "heldout_case_count": len(eval_rows),
        "claim_supported": heldout.get("statistics", {})
        .get("claim_gate", {})
        .get("claim_supported"),
        "performance_evidence": False,
    }


# Short public alias for callers and tests.
verify_e6_replay_training_bundle = verify_e6_replay_training_bundle_v1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--require-current-commit", action="store_true")
    args = parser.parse_args(argv)
    report = verify_e6_replay_training_bundle_v1(
        args.run_dir, require_current_commit=args.require_current_commit
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
