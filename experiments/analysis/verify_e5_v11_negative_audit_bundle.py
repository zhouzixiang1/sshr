#!/usr/bin/env python3
"""Independently verify the immutable E5-v1.1 post-hoc negative audit.

This verifier never imports the audit producer and never treats the audit
summary as evidence.  It authenticates the original failed 90-row bundle,
reconstructs every search/Plan/native result from the frozen inputs, and only
then compares the reconstructed audit rows and summary with the audit bundle.

The audit proves that two representation/timing comparisons in the frozen E5
verifier were false negatives.  It deliberately does *not* change the genuine
protocol outcome: ASCON has no schedulable root, so the E5 experiment remains
incomplete and provides no accepted performance endpoint.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import importlib.machinery
import json
import math
import os
import platform
import re
import sys
import sysconfig
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch


PROJECT_ROOT = Path(__file__).resolve().parent.parent
override = os.environ.get("XA_E5_PROJECT_ROOT")
if override and Path(override).resolve() != PROJECT_ROOT:
    raise RuntimeError("XA_E5_PROJECT_ROOT does not match the audit source tree")
os.environ["XA_E5_PROJECT_ROOT"] = str(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Importing the frozen verifier does not load the crypto hold-out registry.  We
# use only its frozen constructors/decoders and low-level synthesis primitives;
# the two buggy high-level comparison functions are never called here.
from scripts import verify_e5_external_crypto_holdout_bundle as frozen  # noqa: E402
from src.contracts.artifacts import verify_bundle  # noqa: E402
from src.contracts.codec import (  # noqa: E402
    canonical_json_bytes,
    canonical_json_text,
    sha256_bytes,
    sha256_file,
)


TRACK = "xa202609/e5-v11-negative-posthoc-audit-v1"
RUN_SCHEMA = "xa.e5-v11-negative-audit-run.v1"
ROW_SCHEMA = "xa.e5-v11-negative-audit-row.v1"
SUMMARY_SCHEMA = "xa.e5-v11-negative-audit-summary.v1"
DECLARED_SCHEMA = "xa.e5-v11-negative-audit-declared-verifier.v1"
REPORT_SCHEMA = "xa.e5-v11-negative-audit-independent-report.v1"

PORTABLE_TRACK = "xa202609/e5-v11-portable-negative-posthoc-audit-v2"
PORTABLE_RUN_SCHEMA = "xa.e5-v11-portable-negative-audit-run.v2"
PORTABLE_ROW_SCHEMA = "xa.e5-v11-portable-negative-audit-row.v2"
PORTABLE_SUMMARY_SCHEMA = "xa.e5-v11-portable-negative-audit-summary.v2"
PORTABLE_DECLARED_SCHEMA = "xa.e5-v11-portable-negative-audit-declared-verifier.v2"
PORTABLE_REPORT_SCHEMA = "xa.e5-v11-portable-negative-audit-independent-report.v2"

PORTABLE_V3_TRACK = "xa202609/e5-v11-portable-negative-posthoc-audit-v3"
PORTABLE_V3_RUN_SCHEMA = "xa.e5-v11-portable-negative-audit-run.v3"
PORTABLE_V3_ROW_SCHEMA = "xa.e5-v11-portable-negative-audit-row.v3"
PORTABLE_V3_SUMMARY_SCHEMA = "xa.e5-v11-portable-negative-audit-summary.v3"
PORTABLE_V3_DECLARED_SCHEMA = (
    "xa.e5-v11-portable-negative-audit-declared-verifier.v3"
)
PORTABLE_V3_REPORT_SCHEMA = (
    "xa.e5-v11-portable-negative-audit-independent-report.v3"
)

FRESH_VALIDATION_TRACK = "xa202609/e5-v11-portable-fresh-validation-v1"
FRESH_VALIDATION_RUN_SCHEMA = "xa.e5-v11-portable-fresh-validation-run.v1"
FRESH_VALIDATION_ROW_SCHEMA = "xa.e5-v11-portable-fresh-validation-command.v1"
FRESH_VALIDATION_SUMMARY_SCHEMA = (
    "xa.e5-v11-portable-fresh-validation-summary.v1"
)
FRESH_VALIDATION_DECLARED_SCHEMA = (
    "xa.e5-v11-portable-fresh-validation-declared-verifier.v1"
)
FRESH_VALIDATION_REPORT_SCHEMA = (
    "xa.e5-v11-portable-fresh-validation-independent-report.v1"
)
PORTABLE_V3_RUN_ID = "20260812-e5-v11-portable-negative-audit-v3-s950000"
FRESH_VALIDATION_COMMAND_CONTRACT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pip_freeze", ("python", "-m", "pip", "freeze", "--all")),
    ("pip_check", ("python", "-m", "pip", "check")),
    (
        "targeted_e5",
        ("python", "-m", "pytest", "tests/test_e5_v11_negative_audit.py", "-q"),
    ),
    ("full_pytest", ("python", "-m", "pytest", "tests", "-q")),
    ("legacy_smoke", ("python", "tests/tests_smoke.py")),
    ("default_clean_install", ("python", "scripts/verify_clean_install.py")),
    (
        "portable_v3_verifier",
        (
            "python",
            "analysis/verify_e5_v11_negative_audit_bundle.py",
            f"results/xa202609/{PORTABLE_V3_RUN_ID}",
        ),
    ),
)

PORTABLE_RTOL = 1e-6
PORTABLE_ATOL = 5e-6

# These are the only continuous fields allowed to vary across otherwise
# identical PyTorch builds.  ``[*]`` is a literal normalized list index.  The
# allowlist covers model-produced priors/utilities and the deterministic
# scheduler/QUBO/QAOA values derived from those utilities; unrelated floats
# (logical costs, physical metrics, penalties, endpoints, etc.) remain exact.
PORTABLE_FLOAT_PATHS = frozenset(
    {
        "candidate_pool.action_signatures[*].prior",
        "candidate_pool.utilities[*]",
        "raw_scheduler_utilities[*]",
        "adjusted_scheduler_utilities[*]",
        "scheduler.objective",
        "scheduler.diagnostics.adjusted_utilities[*]",
        "scheduler.diagnostics.effective_objective",
        "scheduler.diagnostics.exact_objective",
        "scheduler.diagnostics.execution_feedback.diagnostics.adjusted_utilities[*]",
        "scheduler.diagnostics.execution_feedback.diagnostics.candidates[*].adjusted_utility",
        "scheduler.diagnostics.execution_feedback.diagnostics.candidates[*].raw_utility",
        "scheduler.diagnostics.execution_feedback.diagnostics.raw_utilities[*]",
        "scheduler.diagnostics.objective",
        "scheduler.diagnostics.qaoa.diagnostics.cost_offset",
        "scheduler.diagnostics.qaoa.diagnostics.cost_scale",
        "scheduler.diagnostics.qaoa.diagnostics.ideal_feasible_probability",
        "scheduler.diagnostics.qaoa.diagnostics.ideal_source_probability",
        "scheduler.diagnostics.qaoa.diagnostics.infeasible_penalty",
        "scheduler.diagnostics.qaoa.diagnostics.optimized_expected_energy",
        "scheduler.diagnostics.qaoa.energy",
        "scheduler.diagnostics.qaoa.sampled_energy",
        "scheduler.diagnostics.qaoa_energy_with_constant",
        "scheduler.diagnostics.qubo.constant",
        "scheduler.diagnostics.qubo.linear[*]",
        "scheduler.diagnostics.qubo.quadratic[*][2]",
        "scheduler.diagnostics.qubo.rho",
        "scheduler.diagnostics.raw_qaoa_objective",
        "scheduler.diagnostics.raw_utilities[*]",
        "scheduler.diagnostics.utilities[*]",
        "scheduler.diagnostics.utility_sum",
        "execution_feedback.diagnostics.adjusted_utilities[*]",
        "execution_feedback.diagnostics.candidates[*].adjusted_utility",
        "execution_feedback.diagnostics.candidates[*].raw_utility",
        "execution_feedback.diagnostics.raw_utilities[*]",
    }
)

# The execution-feedback SHA includes the model-produced prior.  Both the
# stored and replayed SHA are independently checked against their own full
# action payload before this path is normalized.  No arbitrary SHA is accepted.
PORTABLE_DERIVED_FINGERPRINT_PATHS = frozenset(
    {
        "scheduler.diagnostics.execution_feedback.diagnostics.candidate_action_sha256[*]",
        "scheduler.diagnostics.execution_feedback.diagnostics.candidates[*].action_sha256",
        "execution_feedback.diagnostics.candidate_action_sha256[*]",
        "execution_feedback.diagnostics.candidates[*].action_sha256",
    }
)

# The immutable 90-row source was produced with this reference build.  The v2
# verifier records, but does not require, the replay runtime to match it.
REFERENCE_RUNTIME_BUILD = {
    "schema_version": "xa.torch-runtime-build.v1",
    "python_version": "3.11.15",
    "platform": "macOS-26.5.2-arm64-arm-64bit",
    "machine": "arm64",
    "torch_version": "2.12.0",
    "torch_git_version": "9624dbeff08348fd8f57eb92d39e5942163454f3",
    "blas_info": "open",
    "libtorch_cpu_sha256": "22414bb6f70dac2d0818ebca892e645b304c618ab707049f8d573af83eb67fef",
    "libtorch_cpu_bytes": 175450992,
}
REFERENCE_BUILD_MATCH_KEYS = (
    "torch_version",
    "torch_git_version",
    "blas_info",
    "libtorch_cpu_sha256",
)
LEGACY_V2_PRODUCER_SOURCE_BINDING = {
    "producer": "e1f8c1e76c6e2f1d9d234dccaa678900065ceb3e97cabc6aa415e9ccf96495b9",
    "independent_verifier": "4687a67c0b91742f24812fed43597832636f5d60f40907dfa48e64d61507c9d3",
    "contract_test": "f16795b38427e8cfdaac4175363c48aae3d48d7577ed83ed4793b7fa39dd5964",
}
LEGACY_V1_PRODUCER_SOURCE_BINDING = {
    "producer": "82b802debe06be286cfe97ef06e47592283ad31b83f1729c072a4242baf86368",
    "independent_verifier": "f0882df24802cec1d1747416a20f61a0e126db9430903ba30dce0eee30b1393d",
    "contract_test": "eea04c9c2794baeba0470a9c2b75e70fce9318d08c288b53ac8d40ded6f5f408",
}

SOURCE_RUN_ID = "20260812-e5-v11-ascon-primary-present-secondary-v1-s940000"
SOURCE_SNAPSHOT_SHA256 = "922838ff8dc0d47d6a13a390b8b4e2c1a9fde2516f7c84abfebca5163cbc4313"
FROZEN_VERIFIER_SHA256 = "534c96654fb88f7b0f357f8ba39dbafab0ccd5ba3acf79821948d97ae004f00e"
STATIC_LOCK_FILE_SHA256 = "83552827de80abb449cbc7d199116719ebd36c4b20f40091ea4dc71052780981"
STATIC_LOCK_CANONICAL_SHA256 = "ed72e457b8a1e6ce22a68f4661fe148863bc50343ea8525d69796b9d030aa9df"
EVALUATION_LOCK_SHA256 = "cc319a82e032e9b870c267f285019b49699c25edf453ce646513fe050027b5c7"
STATIC_LOCK_SOURCE_TREE_SHA256 = "240c69f99dc1c183b9c85280116963da7340913588161d018317e082c3746dde"
EVALUATION_SOURCE_TREE_SHA256 = "b19eeb9948e85173764206d8f502c1c14ab138f4110e8d9aa2e78ab4a9b6989b"
SEAL_RUN_ID = "20260812-e5-v11-seal-external-crypto-v1-s840000"
SEAL_SUMMARY_SHA256 = "5ac54670154d971bfe35e293d563adc7e3fbae9cbb4682aeb0a3ebd0c989e1cf"
PREFLIGHT_RUN_ID = "20260812-e5-v11-preflight-external-crypto-v1-s840000"
PREFLIGHT_SUMMARY_SHA256 = "768a299f282de094596a42f17f5c8288ff7233f48d61e1b81abd0eec501a11ca"
PREFLIGHT_RAW_SHA256 = "a471881b9ebc96df0a94c9e9c2125c14479f3c3a836a2545210b6aa3d37f4019"
WEIGHTS_SHA256 = "b5e832cae44ff4660192a8f4c9800ad19b87299084fc172de79f6ea481f1da5e"
CONFIG_FILE_SHA256 = "c046e68aff93afaa113ab352f53d5fcdd69a8fdc0e1e2536d9e18651c46eb838"
CONFIG_CANONICAL_SHA256 = "eca0a399601d20ecc77ba2da659a1f752f91d2a0fdda8e779a243bbe5d968e24"

SOURCE_FILE_SHA256 = {
    "artifacts.manifest.json": "90935d2594712881b266609d5d6c42a02be1908ea4a6ab24655d5ab7396de216",
    "checksums.sha256": "df40a0b9fdf7eb9f0753300c728b0854c258d3bb67d29917871e5611c1046f7f",
    "events.jsonl": "fd822f14c99b05a752928222ac5c3b36803ccf641447fda4787e89683f510c78",
    "raw.jsonl": "7413e050a51f323a111ac5ee625d5fe4147753418e681672268252c88688c62a",
    "run.json": "e3c6af89465b831c1a270576ed4d2d26599a7e41d427b1ab3b413c63fdf201b5",
    "stderr.log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "stdout.log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "summary.json": "5016da35425cb73e4cba6f72a2435620af066b4af2947fe9e246a804e7256d8f",
    "verifier.json": "b3716f65ac7115d4f002f4a05c9c8854d65f2fe03482102963e8cd83329eab30",
}

EXPECTED_FILES = {
    "run.json",
    "raw.jsonl",
    "summary.json",
    "verifier.json",
    "events.jsonl",
    "stdout.log",
    "stderr.log",
    "artifacts.manifest.json",
    "checksums.sha256",
}
REQUIRED_ROLES = ("run", "raw", "summary", "verifier", "events", "stdout", "stderr")

ELAPSED_FIELDS = (
    "execution_feedback_elapsed_s",
    "qaoa_elapsed_s",
    "total_elapsed_s",
    "utility_elapsed_s",
)
PORTABLE_TIMER_PATHS = frozenset(
    f"scheduler.diagnostics.{name}" for name in ELAPSED_FIELDS
)
SCHEDULER_ARRAY_PATH = "scheduler.diagnostics.selection_order"
NATIVE_ARRAY_PATHS = (
    "native.initial_logical_to_physical",
    "native.final_logical_to_physical",
)
EXPECTED_ELAPSED_COUNTS = {
    "scheduler.diagnostics.execution_feedback_elapsed_s": 30,
    "scheduler.diagnostics.qaoa_elapsed_s": 8,
    "scheduler.diagnostics.total_elapsed_s": 30,
    "scheduler.diagnostics.utility_elapsed_s": 30,
}
EXPECTED_ARRAY_COUNTS = {
    SCHEDULER_ARRAY_PATH: 18,
    NATIVE_ARRAY_PATHS[0]: 90,
    NATIVE_ARRAY_PATHS[1]: 90,
}


class AuditMismatch(RuntimeError):
    """A deterministic scientific field failed independent reconstruction."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditMismatch(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} line {number} is not an object")
        rows.append(value)
    return rows


def _payload_sha(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _snapshot_records(root: Path) -> list[list[object]]:
    return [
        [path.name, path.stat().st_size, sha256_file(path)]
        for path in sorted(root.iterdir(), key=lambda item: item.name)
        if path.is_file()
    ]


def _snapshot_sha(records: Sequence[Sequence[object]]) -> str:
    # This exact historical algorithm produced SOURCE_SNAPSHOT_SHA256 before
    # the post-hoc audit existed.  It intentionally has no trailing newline.
    payload = json.dumps(
        list(records), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _directory_snapshot_binding(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    records = _snapshot_records(root)
    return {
        "run_id": root.name,
        "snapshot_algorithm": "sha256(compact-json(sorted([name,size,sha256])))",
        "snapshot_sha256": _snapshot_sha(records),
        "snapshot_files": [
            {"path": name, "size_bytes": size, "sha256": digest}
            for name, size, digest in records
        ],
    }


def normalization_contract() -> dict[str, Any]:
    return {
        "schema_version": "xa.e5-v11-negative-audit-normalization.v1",
        "scheduler_elapsed_exact_allowlist": [
            f"scheduler.diagnostics.{name}" for name in ELAPSED_FIELDS
        ],
        "scheduler_elapsed_rule": "both_present_same_scope_numeric_finite_nonnegative_then_value_excluded",
        "json_array_exact_allowlist": [SCHEDULER_ARRAY_PATH, *NATIVE_ARRAY_PATHS],
        "json_array_rule": "outer_list_tuple_only_then_order_length_and_values_exact",
        "all_other_fields": "python_type_and_value_exact_or_canonical_sha_exact_as_specified",
        "top_level_scheduler_wall_s": "finite_nonnegative_not_value_replayed_existing_contract",
        "top_level_solve_elapsed_s": "finite_nonnegative_not_value_replayed_existing_contract",
    }


NORMALIZATION_CONTRACT_SHA256 = _payload_sha(normalization_contract())


def portable_normalization_contract() -> dict[str, Any]:
    """Return the explicit v2 cross-build replay contract.

    The immutable source bytes are never rewritten.  Replay checks a strict
    discrete projection plus an exact path allowlist of finite continuous
    model outputs and their deterministic downstream values.
    """

    return {
        "schema_version": "xa.e5-v11-portable-normalization.v2",
        "relative_tolerance": PORTABLE_RTOL,
        "absolute_tolerance": PORTABLE_ATOL,
        "portable_float_path_allowlist": sorted(PORTABLE_FLOAT_PATHS),
        "portable_float_rule": (
            "both numeric finite and math.isclose(rebuilt,stored,"
            "rel_tol=1e-6,abs_tol=5e-6)"
        ),
        "derived_fingerprint_path_allowlist": sorted(
            PORTABLE_DERIVED_FINGERPRINT_PATHS
        ),
        "derived_fingerprint_rule": (
            "stored and rebuilt SHA-256 each exactly bind their own full action "
            "payload before the cross-build fingerprint path is normalized"
        ),
        "scheduler_elapsed_exact_allowlist": sorted(PORTABLE_TIMER_PATHS),
        "scheduler_elapsed_rule": (
            "both present same scope numeric finite nonnegative then value excluded"
        ),
        "json_array_exact_allowlist": [SCHEDULER_ARRAY_PATH, *NATIVE_ARRAY_PATHS],
        "candidate_pool_binding": (
            "immutable stored full SHA exact; replay discrete projection SHA exact; "
            "portable floats compared path-by-path and never re-sign stored evidence"
        ),
        "all_other_fields": "python type and value exact",
        "discrete_fail_closed": (
            "candidate core/order, selected/order, QAOA bit/count/status, Plan, QASM, "
            "native, endpoint, summary counts and negative flags are exact"
        ),
        "historical_v1_contract_changed": False,
    }


PORTABLE_NORMALIZATION_CONTRACT_SHA256 = _payload_sha(
    portable_normalization_contract()
)


def portable_normalization_contract_v3() -> dict[str, Any]:
    """Return the fail-closed v3 cross-build replay contract.

    V3 retains the v2 numerical tolerance but closes the nested scheduler
    execution-feedback fingerprint gap before any portable projection occurs.
    """

    contract = copy.deepcopy(portable_normalization_contract())
    contract.update(
        {
            "schema_version": "xa.e5-v11-portable-normalization.v3",
            "derived_fingerprint_rule": (
                "stored and rebuilt top-level execution_feedback and nested "
                "scheduler.diagnostics.execution_feedback candidate SHA-256 values "
                "must each exactly bind their own ordered full action payload before "
                "any cross-build fingerprint path is normalized"
            ),
            "nested_feedback_binding": (
                "candidate_action_sha256[*] and candidates[*].action_sha256 are "
                "validated independently in both feedback copies; re-signing the "
                "candidate pool or top-level feedback cannot authorize a nested SHA"
            ),
            "runtime_fingerprint": (
                "reference and replay record Python, torch, numpy, scipy, BLAS and "
                "dynamically discovered package native-binary inventories; equality is "
                "reported for the complete versioned frozen subset and is never "
                "required for replay"
            ),
        }
    )
    return contract


PORTABLE_V3_NORMALIZATION_CONTRACT_SHA256 = _payload_sha(
    portable_normalization_contract_v3()
)


def _is_runtime_binary(path: Path) -> bool:
    try:
        with path.open("rb") as stream:
            magic = stream.read(8)
    except OSError:
        return False
    return (
        magic.startswith(b"\x7fELF")
        or magic.startswith(b"MZ")
        or magic.startswith(b"!<arch>\n")
        or magic[:4]
        in {
            b"\xfe\xed\xfa\xce",
            b"\xce\xfa\xed\xfe",
            b"\xfe\xed\xfa\xcf",
            b"\xcf\xfa\xed\xfe",
            b"\xca\xfe\xba\xbe",
            b"\xbe\xba\xfe\xca",
            b"\xca\xfe\xba\xbf",
            b"\xbf\xba\xfe\xca",
        }
    )


def _binary_inventory(root: Path) -> list[dict[str, Any]]:
    """Hash every dynamically discovered package binary below ``root``."""

    root = Path(root).resolve()
    _require(root.is_dir(), f"runtime package root is unavailable: {root}")
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or not _is_runtime_binary(path):
            continue
        records.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    _require(records, f"no runtime binaries discovered below {root}")
    return records


def _binary_record(path: Path) -> dict[str, Any]:
    path = Path(path).resolve()
    _require(path.is_file(), f"runtime binary is unavailable: {path}")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def runtime_build_fingerprint_v2() -> dict[str, Any]:
    """Return the portable-audit v3 runtime and numerical-binary fingerprint."""

    numpy = importlib.import_module("numpy")
    scipy = importlib.import_module("scipy")
    torch_c = importlib.import_module("torch._C")
    python_executable = Path(sys.executable)
    torch_root = Path(torch.__file__).resolve().parent
    numpy_root = Path(numpy.__file__).resolve().parent
    scipy_root = Path(scipy.__file__).resolve().parent
    config = torch.__config__.show()
    match = re.search(r"(?:^|[, ])BLAS_INFO=([^,\n ]+)", config)
    return {
        "schema_version": "xa.numeric-runtime-build.v2",
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "cache_tag": str(sys.implementation.cache_tag),
            "soabi": str(sysconfig.get_config_var("SOABI")),
            "extension_suffix": str(sysconfig.get_config_var("EXT_SUFFIX")),
            "executable": _binary_record(python_executable),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "blas": {
            "torch_blas_info": match.group(1) if match else "unknown",
            "torch_config_sha256": hashlib.sha256(config.encode("utf-8")).hexdigest(),
        },
        "torch": {
            "version": str(torch.__version__).split("+")[0],
            "git_version": str(torch.version.git_version),
            "package_root": str(torch_root),
            "torch_c": _binary_record(Path(torch_c.__file__)),
            "binary_inventory": _binary_inventory(torch_root),
        },
        "numpy": {
            "version": str(numpy.__version__),
            "build_config_sha256": _payload_sha(
                numpy.__config__.show(mode="dicts")
            ),
            "package_root": str(numpy_root),
            "binary_inventory": _binary_inventory(numpy_root),
        },
        "scipy": {
            "version": str(scipy.__version__),
            "build_config_sha256": _payload_sha(
                scipy.__config__.show(mode="dicts")
            ),
            "package_root": str(scipy_root),
            "binary_inventory": _binary_inventory(scipy_root),
        },
    }


def runtime_build_frozen_subset_v2(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Select every v3 equality-bearing field, excluding only absolute paths."""

    python_record = runtime["python"]
    python_executable = python_record["executable"]
    torch_record = runtime["torch"]
    return {
        "schema_version": runtime["schema_version"],
        "python": {
            "implementation": python_record["implementation"],
            "version": python_record["version"],
            "cache_tag": python_record["cache_tag"],
            "soabi": python_record["soabi"],
            "extension_suffix": python_record["extension_suffix"],
            "executable_sha256": python_executable["sha256"],
            "executable_bytes": python_executable["bytes"],
        },
        "platform": copy.deepcopy(runtime["platform"]),
        "blas": copy.deepcopy(runtime["blas"]),
        "torch": {
            "version": torch_record["version"],
            "git_version": torch_record["git_version"],
            "torch_c_sha256": torch_record["torch_c"]["sha256"],
            "torch_c_bytes": torch_record["torch_c"]["bytes"],
            "binary_inventory": copy.deepcopy(torch_record["binary_inventory"]),
        },
        "numpy": {
            "version": runtime["numpy"]["version"],
            "build_config_sha256": runtime["numpy"]["build_config_sha256"],
            "binary_inventory": copy.deepcopy(runtime["numpy"]["binary_inventory"]),
        },
        "scipy": {
            "version": runtime["scipy"]["version"],
            "build_config_sha256": runtime["scipy"]["build_config_sha256"],
            "binary_inventory": copy.deepcopy(runtime["scipy"]["binary_inventory"]),
        },
    }


def _runtime_difference(
    reference: object, runtime: object, *, path: str = ""
) -> list[dict[str, Any]]:
    if isinstance(reference, Mapping) and isinstance(runtime, Mapping):
        differences: list[dict[str, Any]] = []
        for key in sorted(set(reference) | set(runtime)):
            child = f"{path}.{key}" if path else str(key)
            if key not in reference or key not in runtime:
                differences.append(
                    {
                        "field": child,
                        "reference_present": key in reference,
                        "runtime_present": key in runtime,
                    }
                )
            else:
                differences.extend(
                    _runtime_difference(reference[key], runtime[key], path=child)
                )
        return differences
    if isinstance(reference, list) and isinstance(runtime, list):
        if reference == runtime:
            return []
        return [
            {
                "field": path,
                "reference_count": len(reference),
                "runtime_count": len(runtime),
                "reference_sha256": _payload_sha(reference),
                "runtime_sha256": _payload_sha(runtime),
            }
        ]
    if type(reference) is type(runtime) and reference == runtime:
        return []
    return [{"field": path, "reference": reference, "runtime": runtime}]


def runtime_build_differences_v2(
    runtime: Mapping[str, Any], reference: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return _runtime_difference(
        runtime_build_frozen_subset_v2(reference),
        runtime_build_frozen_subset_v2(runtime),
    )


def runtime_matches_reference_v2(
    runtime: Mapping[str, Any], reference: Mapping[str, Any]
) -> bool:
    return not runtime_build_differences_v2(runtime, reference)


def runtime_build_fingerprint_valid_v2(runtime: object) -> bool:
    try:
        if not isinstance(runtime, Mapping):
            return False
        subset = runtime_build_frozen_subset_v2(runtime)
        if subset.get("schema_version") != "xa.numeric-runtime-build.v2":
            return False
        for package in ("torch", "numpy", "scipy"):
            inventory = subset[package]["binary_inventory"]
            if not isinstance(inventory, list) or not inventory:
                return False
            paths = [item["relative_path"] for item in inventory]
            if paths != sorted(paths) or len(paths) != len(set(paths)):
                return False
            for item in inventory:
                if (
                    not isinstance(item, Mapping)
                    or re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", "")))
                    is None
                    or not isinstance(item.get("bytes"), int)
                    or int(item["bytes"]) <= 0
                ):
                    return False
        sha_fields = (
            subset["python"]["executable_sha256"],
            subset["torch"]["torch_c_sha256"],
            subset["blas"]["torch_config_sha256"],
        )
        return all(re.fullmatch(r"[0-9a-f]{64}", str(value)) for value in sha_fields)
    except (KeyError, TypeError, ValueError):
        return False


# Populated with the canonical reference-runtime fingerprint before the v3
# bundle is generated.  It is deliberately a source constant, not inferred
# from the bundle under verification.
REFERENCE_RUNTIME_BUILD_V2: dict[str, Any] = {"blas":{"torch_blas_info":"open","torch_config_sha256":"cd470fdb0fc36f37cc6b0d7f7f41791392ab8659ba523063c252e8a287d5dc77"},"numpy":{"binary_inventory":[{"bytes":138432,"relative_path":"_core/_multiarray_tests.cpython-311-darwin.so","sha256":"0057160ec28fbaefc173220ae6d24113f42cc06fb245f85c2e5c3f9ab7cb7854"},{"bytes":3516240,"relative_path":"_core/_multiarray_umath.cpython-311-darwin.so","sha256":"efac707b8cced10b5509068bcfd8a3073e1275fec830348e3b859ff92bdea304"},{"bytes":69088,"relative_path":"_core/_operand_flag_tests.cpython-311-darwin.so","sha256":"4b20f728fc6e1b8967fecd6e3e597f9a03203f6db15a0ee3f2a20620628ee0bc"},{"bytes":90976,"relative_path":"_core/_rational_tests.cpython-311-darwin.so","sha256":"23dd56ad6a6bde35e09d345583092339ea354e5013291de65604395389d00089"},{"bytes":388944,"relative_path":"_core/_simd.cpython-311-darwin.so","sha256":"528fca7ef63cf66376210254e8aec6b6f1041422c5e36713c48c70a00489945d"},{"bytes":69584,"relative_path":"_core/_struct_ufunc_tests.cpython-311-darwin.so","sha256":"44f213f119683d1cb058e792f9e54d67da32a36fcd026c7d54fda9adaf2e2820"},{"bytes":90048,"relative_path":"_core/_umath_tests.cpython-311-darwin.so","sha256":"d035b2780a6cce33ab27b14ed64365498f7af528821570813b9dc428df145588"},{"bytes":33112,"relative_path":"_core/lib/libnpymath.a","sha256":"e3c4264c19b6d54eda11fe2537fb134792176a81eaf7ad8bf1fe4da91e4e8351"},{"bytes":332032,"relative_path":"fft/_pocketfft_umath.cpython-311-darwin.so","sha256":"201093af9c805f852a836e8750b13e6c372b185dbe5a7600d92368a8859e71d7"},{"bytes":171488,"relative_path":"linalg/_umath_linalg.cpython-311-darwin.so","sha256":"6a2601c82ab65858dcf963103d76fccda39a5a7f3f2d51e5e81a0a98bfae63a9"},{"bytes":70864,"relative_path":"linalg/lapack_lite.cpython-311-darwin.so","sha256":"c28816c1786842eed0111205e2b18805f19f9c96010b21d017ea12946b55106d"},{"bytes":329600,"relative_path":"random/_bounded_integers.cpython-311-darwin.so","sha256":"8c56851ee457c01d4b92bded0cb6b6ab61d19650cc6bdc9c233db72fd5880088"},{"bytes":251200,"relative_path":"random/_common.cpython-311-darwin.so","sha256":"fa1ae86f9d366dcfbd738635e1b33cb229eb6a9332602496ca0cf7d36ef08b55"},{"bytes":687840,"relative_path":"random/_generator.cpython-311-darwin.so","sha256":"c6973932ad984720931b58001f2ee411c2219ec099b1fc35b124acbba93074af"},{"bytes":151888,"relative_path":"random/_mt19937.cpython-311-darwin.so","sha256":"a6de6db6bf4844a14802ba19ec9446e382deab2d357291e21af52e1e9d617158"},{"bytes":154832,"relative_path":"random/_pcg64.cpython-311-darwin.so","sha256":"e6c114c2f6ecac8a41b3ad8ff34a5d40fc0e5b3c8705c8a4ed13fd1c8877181e"},{"bytes":135552,"relative_path":"random/_philox.cpython-311-darwin.so","sha256":"f40d8f1dcac05b236de4d1d3d519fd671bd2e2c919377907d5a2827ea08a58e4"},{"bytes":116240,"relative_path":"random/_sfc64.cpython-311-darwin.so","sha256":"294536ca0f988fbea0ca74ff2a0d37c3133448d3fbe09d21cc9a64e3caeede6d"},{"bytes":220112,"relative_path":"random/bit_generator.cpython-311-darwin.so","sha256":"2d3cc27f5fc44990a81872ce71706c1416b94252f871d35295b7fc3274733156"},{"bytes":51400,"relative_path":"random/lib/libnpyrandom.a","sha256":"010832c12855486945fe111b74f307cdafcff609cde5cec124e175472d4ee006"},{"bytes":578880,"relative_path":"random/mtrand.cpython-311-darwin.so","sha256":"beaf24c4a35f6c56ed7be0c813bbdae7d475f8fdb725669a54d6d1d6f778cbc8"}],"build_config_sha256":"f32362cb6f2501256b934e9dce9e4013dd2d5ed66a55b099bbb3acfd7d3699ad","package_root":"/opt/anaconda3/envs/mcts-qoracle/lib/python3.11/site-packages/numpy","version":"2.4.6"},"platform":{"machine":"arm64","platform":"macOS-26.5.2-arm64-arm-64bit","release":"25.5.0","system":"Darwin","version":"Darwin Kernel Version 25.5.0: Tue Jun  9 22:28:34 PDT 2026; root:xnu-12377.121.10~1/RELEASE_ARM64_T6041"},"python":{"cache_tag":"cpython-311","executable":{"bytes":5978400,"path":"/opt/anaconda3/envs/mcts-qoracle/bin/python3.11","sha256":"f62a21d70d6845fe535c84c092a6ba852bd1c4e38a619e54f4c9f2eae294d7b4"},"extension_suffix":".cpython-311-darwin.so","implementation":"CPython","soabi":"cpython-311-darwin","version":"3.11.15"},"schema_version":"xa.numeric-runtime-build.v2","scipy":{"binary_inventory":[{"bytes":183040,"relative_path":".dylibs/libgcc_s.1.1.dylib","sha256":"6781ce1f79dc10e211ba532b766b0a844265767d3343f029a08112802450a730"},{"bytes":1901520,"relative_path":".dylibs/libgfortran.5.dylib","sha256":"869a6555a787fd5590e2c440ccb4d82d963586168659fbf3354e1570e3f10bcc"},{"bytes":363936,"relative_path":".dylibs/libquadmath.0.dylib","sha256":"676d86e51a3950f75b41945a758bdb02be1c11fef4f4a45b1994d483228e2504"},{"bytes":169776,"relative_path":"_cyutility.cpython-311-darwin.so","sha256":"e88f49d5d785073fcf7439ef2fb1c773c5fcddb3c8ec646af445d0b19d884b14"},{"bytes":114560,"relative_path":"_lib/_ccallback_c.cpython-311-darwin.so","sha256":"8e452b132d98d67e96ed459c139d6b73f119acf12d99efb9ca1d835ff78acae6"},{"bytes":50208,"relative_path":"_lib/_fpumode.cpython-311-darwin.so","sha256":"75f2774112016482c30da398d6e38b1cd5bce3a2ceebf03a15295879fe717583"},{"bytes":53032,"relative_path":"_lib/_test_ccallback.cpython-311-darwin.so","sha256":"589b4ee776eafd3391323fe0a4ba3e66f9b8634bfd7a2c18c64ddac3ef0ab326"},{"bytes":74816,"relative_path":"_lib/_test_deprecation_call.cpython-311-darwin.so","sha256":"f787f9fcaf95cee5064d4a861f2eae31eb97217b4cac4f0f52c11d098c401596"},{"bytes":54968,"relative_path":"_lib/_test_deprecation_def.cpython-311-darwin.so","sha256":"bc0d68b8c6b7c5a8acb510b3d41d5af61fa90f7c6421914c27a43ac8236409c9"},{"bytes":120320,"relative_path":"_lib/_uarray/_uarray.cpython-311-darwin.so","sha256":"3b285ded5dabd0fd043d4b5ffb2863311ce669c62a6ef6e8a9b768bab9a89fc6"},{"bytes":96784,"relative_path":"_lib/messagestream.cpython-311-darwin.so","sha256":"e364beca69c619fbc2eb287f1ac2f92aefdd1acda4276ad2d9b1f440f4a669cd"},{"bytes":220672,"relative_path":"cluster/_hierarchy.cpython-311-darwin.so","sha256":"e0744c0ed7fa40b3d87e128940316faccf74a5afd598db2758dd25b00d22c573"},{"bytes":151632,"relative_path":"cluster/_optimal_leaf_ordering.cpython-311-darwin.so","sha256":"a2a15a22bc50c3ea878a6ef7faaf8a8464db8bb401e18eec5d6b7047eda9c7c9"},{"bytes":128344,"relative_path":"cluster/_vq.cpython-311-darwin.so","sha256":"c81aa0f4c4fc609e526dfffac50a06af4f2ef49698a68c882ea1f1863de9f81d"},{"bytes":942080,"relative_path":"fft/_pocketfft/pypocketfft.cpython-311-darwin.so","sha256":"851bf52bd0684e401c722e8b9721c84dd6e897b9342b401ba2187a0ad492dc8f"},{"bytes":114112,"relative_path":"fftpack/convolve.cpython-311-darwin.so","sha256":"e835ee778741c021963af66b31966a13d591139e24b677da81c883c24bb87600"},{"bytes":85368,"relative_path":"integrate/_dop.cpython-311-darwin.so","sha256":"70164bc7aab5d605b12d3218b0a4ce77a7f65300467f89ce12771635f3140a50"},{"bytes":86592,"relative_path":"integrate/_odepack.cpython-311-darwin.so","sha256":"6fc0a3012143e3b3625ad431734c242b49b475abba44376c8520d6b7fc90faaa"},{"bytes":104240,"relative_path":"integrate/_quadpack.cpython-311-darwin.so","sha256":"d13adf9af2b9e7a37bccb3374f8d6435949fc2e89dca8a22fd7ad5b875cd98d9"},{"bytes":50664,"relative_path":"integrate/_test_multivariate.cpython-311-darwin.so","sha256":"b7f19a0404015678d3426f1363fbca4f909c1d81dbb8013d3cff3497f0d470a3"},{"bytes":120840,"relative_path":"integrate/_vode.cpython-311-darwin.so","sha256":"860cd783467c5cd3f08da4397c1c8df1f918f7d4d7927aaf109f60c6ac8b0289"},{"bytes":312368,"relative_path":"interpolate/_dfitpack.cpython-311-darwin.so","sha256":"90905506c9b5888cc328e3ce7c6020737c3c43f402fa0a1c9fd1756e12712719"},{"bytes":109328,"relative_path":"interpolate/_dierckx.cpython-311-darwin.so","sha256":"b49d32476255e71af44cdeba999548bfc1b27c0499233c3b42a447067b7aaf11"},{"bytes":121056,"relative_path":"interpolate/_fitpack.cpython-311-darwin.so","sha256":"b75e9b61d15fde1cef34b55db713a2ad9b92bc2acd74a56ec55529754d3413a3"},{"bytes":204448,"relative_path":"interpolate/_interpnd.cpython-311-darwin.so","sha256":"3b23d92ce29756a033c08a958a458554180182b091aba90478c4751f6eaa81e5"},{"bytes":200128,"relative_path":"interpolate/_ppoly.cpython-311-darwin.so","sha256":"7e3e92cdd245024bdb527479f4e35b5f995c88342f353f09faf10fdbc8e6c5dc"},{"bytes":303592,"relative_path":"interpolate/_rbfinterp_pythran.cpython-311-darwin.so","sha256":"c16fdc1fdb192e3c007efdfa8142adcef46c3546d6f0df366593f35b102c3d8a"},{"bytes":116160,"relative_path":"interpolate/_rgi_cython.cpython-311-darwin.so","sha256":"33377edbb9667ae7fa025841e0af7058ecd489169ea5fea55d39c118b053d5ba"},{"bytes":2150672,"relative_path":"io/_fast_matrix_market/_fmm_core.cpython-311-darwin.so","sha256":"c942f7569b14b4734bd1013a51345b5d67a052fb34f729083e1079480319d27d"},{"bytes":206176,"relative_path":"io/matlab/_mio5_utils.cpython-311-darwin.so","sha256":"e1a55c7326f9f6642135c6299015334ed9391864f4eae5b54bcd1d09ab25f0de"},{"bytes":94528,"relative_path":"io/matlab/_mio_utils.cpython-311-darwin.so","sha256":"4879929658a5a0dc119dab7720a4791331b8e909f6199c15d086fe9839a8a1d2"},{"bytes":132752,"relative_path":"io/matlab/_streams.cpython-311-darwin.so","sha256":"f277af2c220faf573c2fe0ae7bd81c9f14479dff3dfb75aa9005f5913d1ab9d1"},{"bytes":129672,"relative_path":"linalg/_batched_linalg.cpython-311-darwin.so","sha256":"21c7828fe18269231fd0ce9930676fb80c54007a01c446ecdf53ab2c34846050"},{"bytes":277632,"relative_path":"linalg/_cythonized_array_utils.cpython-311-darwin.so","sha256":"49d7688451b7ba348351d0e05eef9ae5b5b8ba17dc59e39f5133f93d0d95b25c"},{"bytes":550648,"relative_path":"linalg/_decomp_interpolative.cpython-311-darwin.so","sha256":"ecfed6559136b037239e7d96ce0ab90d0694b0a969b61f5ca7ff802c2aa473e7"},{"bytes":113432,"relative_path":"linalg/_decomp_lu_cython.cpython-311-darwin.so","sha256":"9342c58717fcd43335e7668185666f9881fc55efd1edbaa3e2dc85f1b6263957"},{"bytes":233144,"relative_path":"linalg/_decomp_update.cpython-311-darwin.so","sha256":"f39c233740fa9c638607d3edbfb4c47a64b6c0779b9951092e952a7e07eed64e"},{"bytes":553648,"relative_path":"linalg/_fblas.cpython-311-darwin.so","sha256":"46072eac04e7028a71033de1163c2fc67fed353bc40ef6f2889e02d058e1fe47"},{"bytes":1871104,"relative_path":"linalg/_flapack.cpython-311-darwin.so","sha256":"2bfdb73cf57d795236339bb5400d134ebc32044c1b6fcb745e8417a6a159d946"},{"bytes":145992,"relative_path":"linalg/_linalg_pythran.cpython-311-darwin.so","sha256":"4ba27958b16a904e8278da77b69f6a9c83de249bc618e77e4129d9e20c1f7890"},{"bytes":105304,"relative_path":"linalg/_matfuncs_expm.cpython-311-darwin.so","sha256":"24238470e886aea18e01b8dc16d938a2bed9697b6b0ffad4bf1e4f245914869e"},{"bytes":70216,"relative_path":"linalg/_matfuncs_schur_sqrtm.cpython-311-darwin.so","sha256":"c4401ac77d175ecd0ad7e3bcad5ccae41c0e8bd07092db6dc750ff5b86bfc71e"},{"bytes":98296,"relative_path":"linalg/_matfuncs_sqrtm_triu.cpython-311-darwin.so","sha256":"886a4af807ead0d6410ea0535058b31adf8db28a1dd7100d8ed643e7d6b223b4"},{"bytes":114952,"relative_path":"linalg/_solve_toeplitz.cpython-311-darwin.so","sha256":"7351ec838f7665d09b66a35a1d1c38120f5ede077fca737ce14929e4831a5cab"},{"bytes":131200,"relative_path":"linalg/cython_blas.cpython-311-darwin.so","sha256":"72cb3abf198e8db15fce2ef09b25c077578318453e788e5a6928a7038e9cab9b"},{"bytes":372752,"relative_path":"linalg/cython_lapack.cpython-311-darwin.so","sha256":"71c50b95a1744f53957743a3eb70caf0f46f81b0ead41de4aee955e66402dde8"},{"bytes":51120,"relative_path":"ndimage/_ctest.cpython-311-darwin.so","sha256":"c8a55ff1bb1ddae5af76a54738f4e2618768c3cd66beb1240c6dd11e332af10d"},{"bytes":96304,"relative_path":"ndimage/_cytest.cpython-311-darwin.so","sha256":"31d8238e6141622e5718b57754599620fbd7526776a47817cc60cc87e99fc846"},{"bytes":156160,"relative_path":"ndimage/_nd_image.cpython-311-darwin.so","sha256":"92f15cb9fe9d9e7674772d90564ab5bae01bd41096e0c8d25d54f56ff62897d5"},{"bytes":188272,"relative_path":"ndimage/_ni_label.cpython-311-darwin.so","sha256":"70aafae6a19d905de772c371b58e486b6d427662e21c535986fc831337da996d"},{"bytes":69048,"relative_path":"ndimage/_rank_filter_1d.cpython-311-darwin.so","sha256":"654f195c2221fdb6d172833083c3ccef680a501341d5408853d907ae3b3ddb93"},{"bytes":240624,"relative_path":"odr/__odrpack.cpython-311-darwin.so","sha256":"61a2a3715317b42fa97d62e449827b099d55580419824f2b25ee0820a4712f7e"},{"bytes":171792,"relative_path":"optimize/_bglu_dense.cpython-311-darwin.so","sha256":"d2240d062004c97775af5ad3b4dbfef372db8d3470e5c332cb4bf0f1922bf5ef"},{"bytes":69232,"relative_path":"optimize/_direct.cpython-311-darwin.so","sha256":"cdd4ed23f162b9b56306166ba5fbf983d6414b4a64c29bff4ef59123e48cc310"},{"bytes":95272,"relative_path":"optimize/_group_columns.cpython-311-darwin.so","sha256":"5bfa05deeb8dea0fec4e1dfb0d41d9aebd638b8856e3e95d357d0f734e5acdff"},{"bytes":5215624,"relative_path":"optimize/_highspy/_core.cpython-311-darwin.so","sha256":"5e486e7d6b9cf94bfa84707da15069604c7ebe78dd8f84fe8a56eebbf896a250"},{"bytes":404520,"relative_path":"optimize/_highspy/_highs_options.cpython-311-darwin.so","sha256":"c510f1e276386e778f1cb37dc5d311f81749fd3d07fb614269ca05dd1f387e22"},{"bytes":68592,"relative_path":"optimize/_lbfgsb.cpython-311-darwin.so","sha256":"df505595db603a5fd1adf883f9226b57865783d8eac525ba3594bbba76d4243c"},{"bytes":70744,"relative_path":"optimize/_lsap.cpython-311-darwin.so","sha256":"f2e01db65a21589962d7ee09c5b6af3c0ad815ba4e05daab0d6658066a27fffe"},{"bytes":77704,"relative_path":"optimize/_lsq/givens_elimination.cpython-311-darwin.so","sha256":"933888d05bdd3254f25a3c45d6e6f379eea79f306767b01103c3712f576a20e9"},{"bytes":103520,"relative_path":"optimize/_minpack.cpython-311-darwin.so","sha256":"9c0f7472cc4c048198cf6e41a172bad25e9c6ff0a91a380f327ae48dbf8d25d6"},{"bytes":145856,"relative_path":"optimize/_moduleTNC.cpython-311-darwin.so","sha256":"617c986ca7c6f7dc748cb80e4a816b8c5e73e9abf272e5abd407b1c8e9f61434"},{"bytes":223216,"relative_path":"optimize/_pava_pybind.cpython-311-darwin.so","sha256":"9d6ee1001cf02b90f6521a15646273fce98a17b3b4f975634affac163712a1d2"},{"bytes":70624,"relative_path":"optimize/_slsqplib.cpython-311-darwin.so","sha256":"070af91c38f03bac1ccb2757e84df6d5f60e3a91632917f69629826e67bc89f8"},{"bytes":182688,"relative_path":"optimize/_trlib/_trlib.cpython-311-darwin.so","sha256":"a21d550d62ab7999ac9c17e86da54e7f0bc99c56b8735bac84a6f87807f8f39d"},{"bytes":51312,"relative_path":"optimize/_zeros.cpython-311-darwin.so","sha256":"d43e2cd304708560bd0afd228e9db88c524efd50b05ee4331406c79e264a9fe4"},{"bytes":97904,"relative_path":"optimize/cython_optimize/_zeros.cpython-311-darwin.so","sha256":"e090a511685c973e5931004d9c058c4b8c90850dce33d9528e7bce77e085e68a"},{"bytes":75992,"relative_path":"signal/_max_len_seq_inner.cpython-311-darwin.so","sha256":"6e836892d7fcc1b0b417e2c5e7931627179cc678fef315a47845293adc56b4aa"},{"bytes":131128,"relative_path":"signal/_peak_finding_utils.cpython-311-darwin.so","sha256":"59573f6984ce06240fceb62fdbb1897aa0397013ee01a36e7bb2776f56922edc"},{"bytes":123024,"relative_path":"signal/_sigtools.cpython-311-darwin.so","sha256":"83318fb616a82abdb40ba0ecc049258e62810812045031def10cf68506d0f4bb"},{"bytes":114320,"relative_path":"signal/_sosfilt.cpython-311-darwin.so","sha256":"6e066169486090c61000a8ce77263c4d16c8ab3be1a80e0779250967e456f9c0"},{"bytes":69744,"relative_path":"signal/_spline.cpython-311-darwin.so","sha256":"7520934bb3a5a3fea0464d4265ecb3e7f26249fd4b84afe029ad146275e08053"},{"bytes":184888,"relative_path":"signal/_upfirdn_apply.cpython-311-darwin.so","sha256":"bcfb4e0605ef2cabd3dcd2011f95e27abd5ea52a2a7be78aec8c7a4a0cffa774"},{"bytes":404480,"relative_path":"sparse/_csparsetools.cpython-311-darwin.so","sha256":"e2e50bd1b3a66560e6df3f5ffb40ed680af9a66dd99d23102720b639d379512e"},{"bytes":3614784,"relative_path":"sparse/_sparsetools.cpython-311-darwin.so","sha256":"f2185bccce989298f646d6ec7bd59b9b69c3c960c3c15d4d48e65af013f965b3"},{"bytes":165880,"relative_path":"sparse/csgraph/_flow.cpython-311-darwin.so","sha256":"ce5e9ddf91c60f1ef04e0d9567e872496c43b7d7adf460a2e832df1adc0497b1"},{"bytes":164848,"relative_path":"sparse/csgraph/_matching.cpython-311-darwin.so","sha256":"37a2cc1850c6f72a499c59ebd9df89d848698e15a3b58fa6a554bcc8d414cff2"},{"bytes":114088,"relative_path":"sparse/csgraph/_min_spanning_tree.cpython-311-darwin.so","sha256":"46711625028d5b8561f2821ff1d01c0ee5543a1f8deddfe38a6f11ad3e4d84f6"},{"bytes":149856,"relative_path":"sparse/csgraph/_reordering.cpython-311-darwin.so","sha256":"312a547483d3bc863f97c194ebb7faeeeb0e1e41f5915927ff0e4f14b6d1801a"},{"bytes":362568,"relative_path":"sparse/csgraph/_shortest_path.cpython-311-darwin.so","sha256":"c455a451bdb289f2b62bce843d61b89a293c6ab15696c19691441df782497146"},{"bytes":164752,"relative_path":"sparse/csgraph/_tools.cpython-311-darwin.so","sha256":"929fdcc839b5ae6a21f37faba38e8fb1b6deb3ae121c8128fbfb47b727f74992"},{"bytes":269456,"relative_path":"sparse/csgraph/_traversal.cpython-311-darwin.so","sha256":"08cd148b49764ebcaf3a6f811a5d33052f72434a96ea11c12bbbe0be388baf5f"},{"bytes":280928,"relative_path":"sparse/linalg/_dsolve/_superlu.cpython-311-darwin.so","sha256":"4d409753c8e5b6783de2e0f505066ac2538e0de7d105c69d5f50fa0a22876871"},{"bytes":179168,"relative_path":"sparse/linalg/_eigen/arpack/_arpacklib.cpython-311-darwin.so","sha256":"d87a14c360c84acb344f20875c445a6738415340aa0cf124aa718e3f9959f99d"},{"bytes":140112,"relative_path":"sparse/linalg/_propack.cpython-311-darwin.so","sha256":"1ada7660a3a48c0b2857d05d3892505b92e8916b91051c8aaab42034473e6427"},{"bytes":514656,"relative_path":"spatial/_ckdtree.cpython-311-darwin.so","sha256":"a4c2bd5024fef1fc336b4bebd9fc6eac2ad12dfd361bf5f15b26d04fda61af04"},{"bytes":546664,"relative_path":"spatial/_distance_pybind.cpython-311-darwin.so","sha256":"f44526ba82f3a1ac440155958e0c06bdf7ae300213fddc11f4b3589bfbaec655"},{"bytes":104408,"relative_path":"spatial/_distance_wrap.cpython-311-darwin.so","sha256":"929627a6cc507702d78cb626f3c44808e41e15e17f1e031acb5764536f4a018a"},{"bytes":96832,"relative_path":"spatial/_hausdorff.cpython-311-darwin.so","sha256":"c99b5d783c25fb365218f8f6a60e7ac63468e2b4b9fe69d8d51a0e7cbb84995a"},{"bytes":720688,"relative_path":"spatial/_qhull.cpython-311-darwin.so","sha256":"a4159010f18b05cfb4afaa587ccde36b0d06806fe24cd38eeadf1b295a25650a"},{"bytes":96496,"relative_path":"spatial/_voronoi.cpython-311-darwin.so","sha256":"5524fd9ce0de5ff4f5a3f33c68b94d86a05e7a800c1095b4d4d74d073bb3ada9"},{"bytes":217688,"relative_path":"spatial/transform/_rigid_transform_cy.cpython-311-darwin.so","sha256":"ce680625153d914ad576ea8fbf6509a3e3ff50aa9112a70706063901ef0ed250"},{"bytes":408192,"relative_path":"spatial/transform/_rotation_cy.cpython-311-darwin.so","sha256":"5472abd27ff41e9915e368483e271bec5c24ae1576371f97623635037659fc88"},{"bytes":76968,"relative_path":"special/_comb.cpython-311-darwin.so","sha256":"1553ed9902e305db66ca2e6b3f542d0a4c2b661115ce119595760770aa759ead"},{"bytes":112960,"relative_path":"special/_ellip_harm_2.cpython-311-darwin.so","sha256":"46c15905573eceba5ab8a5a3f97ac0e7885b6b203c43c68c52f5eb5c43a678c1"},{"bytes":627808,"relative_path":"special/_gufuncs.cpython-311-darwin.so","sha256":"c9ec2c739929c9922c220b195b472916dc92aa88b189d656dcddaa91a37557d3"},{"bytes":184016,"relative_path":"special/_specfun.cpython-311-darwin.so","sha256":"c6ac6765b09196e8401c022c14503dcff6da4c173366646931c49ad57192c959"},{"bytes":1130872,"relative_path":"special/_special_ufuncs.cpython-311-darwin.so","sha256":"edc1aa109be752f742d2cec328f2fcdcb29f947f24e91a41326ba92bf770dbd6"},{"bytes":96632,"relative_path":"special/_test_internal.cpython-311-darwin.so","sha256":"05e90740e77c74d84fb9ec882faa74bc07f7ad522be16b332f09181afcefa78f"},{"bytes":702736,"relative_path":"special/_ufuncs.cpython-311-darwin.so","sha256":"330c343b2d52377297b30c23d31c2c4b09f73626a2b880c5d015e3fa28a1eeb8"},{"bytes":1353808,"relative_path":"special/_ufuncs_cxx.cpython-311-darwin.so","sha256":"f687b496168098298f507bc8c611450bd16b9ca295f3f64888987e5a7d5386bf"},{"bytes":1662888,"relative_path":"special/cython_special.cpython-311-darwin.so","sha256":"4e5c1a4a80d021d970af20b020c44fe16d0e472f879f61b803d5e61249813aa3"},{"bytes":113696,"relative_path":"stats/_ansari_swilk_statistics.cpython-311-darwin.so","sha256":"beb4e4525b74c6ce9e139e45c7387fe4afc51b838623d28ae964cea4792cc5bc"},{"bytes":157152,"relative_path":"stats/_biasedurn.cpython-311-darwin.so","sha256":"06fbf4c2f03fc0c65f7c26e15f204be6a8e2abe86cdab657bf576f74810d7dcc"},{"bytes":77872,"relative_path":"stats/_levy_stable/levyst.cpython-311-darwin.so","sha256":"d0381f96ebdcfbfaa0b558cda28e209dfcb15edb91dc93607a8297183c3c421a"},{"bytes":122288,"relative_path":"stats/_qmc_cy.cpython-311-darwin.so","sha256":"e7f7a5d1b6d0385244ae38d3f705d69ab4de9a649f84004c01c53663cfd3df6f"},{"bytes":131296,"relative_path":"stats/_qmvnt_cy.cpython-311-darwin.so","sha256":"e08519c37f676322c816ac6fbe3a7b6f4125c85cc3debe05815b7949438d9d09"},{"bytes":96456,"relative_path":"stats/_rcont/rcont.cpython-311-darwin.so","sha256":"5ec7a6f0ddf37ad33c184907f57ae14e4ba7149db068a867fbca77ee9511336e"},{"bytes":167456,"relative_path":"stats/_sobol.cpython-311-darwin.so","sha256":"5cf36605df351921f1c96177d487ea7fdde487677770abef80b95e01816349c5"},{"bytes":390384,"relative_path":"stats/_stats.cpython-311-darwin.so","sha256":"5a19c22a89fb87fd5e5426600b77504b2dfca3d195e48ba4e7ace38fca5d822f"},{"bytes":192120,"relative_path":"stats/_stats_pythran.cpython-311-darwin.so","sha256":"21c8d7a32cec0fde967db6c06816ab549105bfc42bd348c1ca2e9047701fc491"},{"bytes":521288,"relative_path":"stats/_unuran/unuran_wrapper.cpython-311-darwin.so","sha256":"3a87a79642ba0554440941e76fa0132c32a0c052f465fb4b4ea93f1d030750d7"}],"build_config_sha256":"98a58d7cc52a80933cfdc0395c9018552319c7d4bfb958173230569c600c924b","package_root":"/opt/anaconda3/envs/mcts-qoracle/lib/python3.11/site-packages/scipy","version":"1.17.1"},"torch":{"binary_inventory":[{"bytes":68048,"relative_path":"_C.cpython-311-darwin.so","sha256":"8fa53872cbf22bb8ad053833357d8780f9694654c54c318988ded86f2ab2f0f7"},{"bytes":77056,"relative_path":"bin/torch_shm_manager","sha256":"65715fa4e34b28b168b5c5d343f4cffd377532a74c493ad1d598cd285f0744a4"},{"bytes":1119888,"relative_path":"lib/libc10.dylib","sha256":"61493b29c03e1f420c604b6e21f9fdb010f44f4befc915f591670cec8e39a4c6"},{"bytes":844336,"relative_path":"lib/libomp.dylib","sha256":"31f7092bdc099ec18b334b184a643ec45cf12e43a6d819be12be39e900681447"},{"bytes":184288,"relative_path":"lib/libshm.dylib","sha256":"faa041d3758f8473dbf8e434e9d2fee9e97843de2aaad74935775640e148e61c"},{"bytes":133968,"relative_path":"lib/libtorch.dylib","sha256":"1dddf5ae1090005b9b6a761e7e7a0d06be47d96c412318197c4973f3836a9724"},{"bytes":175450992,"relative_path":"lib/libtorch_cpu.dylib","sha256":"22414bb6f70dac2d0818ebca892e645b304c618ab707049f8d573af83eb67fef"},{"bytes":34896,"relative_path":"lib/libtorch_global_deps.dylib","sha256":"faeaacc54961d6b178e0955aaaa96109d1cc39d2cf3ee4f9b96d8ed3226d5d79"}],"git_version":"9624dbeff08348fd8f57eb92d39e5942163454f3","package_root":"/opt/anaconda3/envs/mcts-qoracle/lib/python3.11/site-packages/torch","torch_c":{"bytes":68048,"path":"/opt/anaconda3/envs/mcts-qoracle/lib/python3.11/site-packages/torch/_C.cpython-311-darwin.so","sha256":"8fa53872cbf22bb8ad053833357d8780f9694654c54c318988ded86f2ab2f0f7"},"version":"2.12.0"}}


def runtime_build_fingerprint() -> dict[str, Any]:
    """Describe the actual replay build without treating it as frozen input."""

    config = torch.__config__.show()
    match = re.search(r"(?:^|[, ])BLAS_INFO=([^,\n ]+)", config)
    libtorch = Path(torch.__file__).resolve().parent / "lib" / "libtorch_cpu.dylib"
    _require(libtorch.is_file(), "libtorch_cpu.dylib is unavailable")
    return {
        "schema_version": "xa.torch-runtime-build.v1",
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "torch_version": str(torch.__version__).split("+")[0],
        "torch_git_version": str(torch.version.git_version),
        "blas_info": match.group(1) if match else "unknown",
        "libtorch_cpu_sha256": sha256_file(libtorch),
        "libtorch_cpu_bytes": libtorch.stat().st_size,
    }


def runtime_matches_reference(runtime: Mapping[str, Any]) -> bool:
    return all(
        runtime.get(key) == REFERENCE_RUNTIME_BUILD[key]
        for key in REFERENCE_BUILD_MATCH_KEYS
    )


def _portable_path(path: str) -> str:
    quadratic = re.fullmatch(
        r"scheduler\.diagnostics\.qubo\.quadratic\[\d+\]\[(\d+)\]", path
    )
    if quadratic is not None:
        return f"scheduler.diagnostics.qubo.quadratic[*][{quadratic.group(1)}]"
    return re.sub(r"\[\d+\]", "[*]", path)


def _new_portable_stats() -> dict[str, Any]:
    return {
        "portable_float_paths": set(),
        "portable_float_value_count": 0,
        "derived_fingerprint_paths": set(),
        "derived_fingerprint_value_count": 0,
        "max_absolute_difference": 0.0,
        "max_relative_difference": 0.0,
        "nonzero_portable_float_value_count": 0,
    }


def _portable_stats_report(stats: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "portable_float_paths": sorted(stats["portable_float_paths"]),
        "portable_float_path_count": len(stats["portable_float_paths"]),
        "portable_float_value_count": int(stats["portable_float_value_count"]),
        "derived_fingerprint_paths": sorted(stats["derived_fingerprint_paths"]),
        "derived_fingerprint_path_count": len(stats["derived_fingerprint_paths"]),
        "derived_fingerprint_value_count": int(
            stats["derived_fingerprint_value_count"]
        ),
        "max_absolute_difference": float(stats["max_absolute_difference"]),
        "max_relative_difference": float(stats["max_relative_difference"]),
        "nonzero_portable_float_value_count": int(
            stats["nonzero_portable_float_value_count"]
        ),
    }


def _merge_portable_stats(target: dict[str, Any], source: Mapping[str, Any]) -> None:
    target["portable_float_paths"].update(source["portable_float_paths"])
    target["portable_float_value_count"] += int(source["portable_float_value_count"])
    target["derived_fingerprint_paths"].update(
        source["derived_fingerprint_paths"]
    )
    target["derived_fingerprint_value_count"] += int(
        source["derived_fingerprint_value_count"]
    )
    target["max_absolute_difference"] = max(
        float(target["max_absolute_difference"]),
        float(source["max_absolute_difference"]),
    )
    target["max_relative_difference"] = max(
        float(target["max_relative_difference"]),
        float(source["max_relative_difference"]),
    )
    target["nonzero_portable_float_value_count"] += int(
        source["nonzero_portable_float_value_count"]
    )


def _portable_project_and_compare(
    stored: object,
    rebuilt: object,
    *,
    path: str,
    stats: dict[str, Any],
) -> object:
    """Compare one replay tree and return its runtime-independent projection."""

    normalized = _portable_path(path)
    if normalized in PORTABLE_FLOAT_PATHS:
        if stored is None or rebuilt is None:
            _require(
                stored is None and rebuilt is None,
                f"portable float optional scope mismatch: {path}",
            )
            return None
        _require(
            not isinstance(stored, bool)
            and not isinstance(rebuilt, bool)
            and isinstance(stored, (int, float))
            and isinstance(rebuilt, (int, float)),
            f"portable float path is not numeric: {path}",
        )
        left = float(stored)
        right = float(rebuilt)
        _require(
            math.isfinite(left) and math.isfinite(right),
            f"portable float path is non-finite: {path}",
        )
        _require(
            math.isclose(left, right, rel_tol=PORTABLE_RTOL, abs_tol=PORTABLE_ATOL),
            f"portable float tolerance exceeded: {path}: stored={left}, rebuilt={right}",
        )
        absolute = abs(left - right)
        relative = absolute / max(abs(left), abs(right), 1e-300)
        stats["portable_float_paths"].add(normalized)
        stats["portable_float_value_count"] += 1
        stats["max_absolute_difference"] = max(
            float(stats["max_absolute_difference"]), absolute
        )
        stats["max_relative_difference"] = max(
            float(stats["max_relative_difference"]), relative
        )
        stats["nonzero_portable_float_value_count"] += int(absolute > 0.0)
        return {"portable_float_path": normalized}

    if normalized in PORTABLE_DERIVED_FINGERPRINT_PATHS:
        for value in (stored, rebuilt):
            _require(
                isinstance(value, str)
                and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
                f"portable derived fingerprint is not SHA-256: {path}",
            )
        stats["derived_fingerprint_paths"].add(normalized)
        stats["derived_fingerprint_value_count"] += 1
        return {"portable_derived_fingerprint_path": normalized}

    if normalized in PORTABLE_TIMER_PATHS:
        _finite_nonnegative(stored, f"stored {path}")
        _finite_nonnegative(rebuilt, f"rebuilt {path}")
        return {"allowed_nonreplayable_elapsed_field": normalized}

    if isinstance(stored, Mapping) or isinstance(rebuilt, Mapping):
        _require(
            isinstance(stored, Mapping) and isinstance(rebuilt, Mapping),
            f"portable mapping type mismatch: {path}",
        )
        _require(set(stored) == set(rebuilt), f"portable mapping keys mismatch: {path}")
        return {
            str(key): _portable_project_and_compare(
                stored[key], rebuilt[key], path=f"{path}.{key}", stats=stats
            )
            for key in sorted(stored)
        }

    sequence_types = (list, tuple)
    if isinstance(stored, sequence_types) or isinstance(rebuilt, sequence_types):
        _require(
            isinstance(stored, sequence_types) and isinstance(rebuilt, sequence_types),
            f"portable sequence type mismatch: {path}",
        )
        if normalized != SCHEDULER_ARRAY_PATH:
            _require(type(stored) is type(rebuilt), f"portable sequence class mismatch: {path}")
        else:
            _require(
                isinstance(stored, list) and isinstance(rebuilt, tuple),
                "portable selection_order must preserve JSON-list/frozen-tuple scope",
            )
        _require(len(stored) == len(rebuilt), f"portable sequence length mismatch: {path}")
        return [
            _portable_project_and_compare(
                left, right, path=f"{path}[{index}]", stats=stats
            )
            for index, (left, right) in enumerate(zip(stored, rebuilt))
        ]

    _require(type(stored) is type(rebuilt), f"portable scalar type mismatch: {path}")
    _require(stored == rebuilt, f"portable exact field mismatch: {path}")
    return copy.deepcopy(stored)


def _validate_feedback_action_shas(
    feedback: Mapping[str, Any], action_signatures: Sequence[Mapping[str, Any]]
) -> None:
    if feedback.get("enabled") is not True:
        return
    diagnostics = feedback.get("diagnostics")
    _require(isinstance(diagnostics, Mapping), "execution feedback diagnostics missing")
    hashes = diagnostics.get("candidate_action_sha256")
    candidates = diagnostics.get("candidates")
    _require(
        isinstance(hashes, list)
        and isinstance(candidates, list)
        and len(hashes) == len(candidates) == len(action_signatures),
        "execution feedback action SHA scope mismatch",
    )
    for index, signature in enumerate(action_signatures):
        expected = _payload_sha(signature)
        _require(hashes[index] == expected, "execution feedback candidate action SHA mismatch")
        _require(
            isinstance(candidates[index], Mapping)
            and candidates[index].get("action_sha256") == expected,
            "execution feedback candidate record action SHA mismatch",
        )


def _establish_compute_contract(config: Mapping[str, Any], *, context: str) -> dict[str, Any]:
    expected = {
        "device": "cpu",
        "torch_intraop_threads": 1,
        "torch_interop_threads": 1,
        "torch_deterministic_algorithms": True,
    }
    _require(config.get("compute_contract") == expected, "compute contract differs from frozen CPU/1/1/deterministic")
    before = {
        "device": str(torch.get_default_device()),
        "torch_intraop_threads": int(torch.get_num_threads()),
        "torch_interop_threads": int(torch.get_num_interop_threads()),
        "torch_deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
    }
    setter_errors: list[str] = []
    for name, setter, value in (
        ("device", torch.set_default_device, "cpu"),
        ("torch_interop_threads", torch.set_num_interop_threads, 1),
        ("torch_intraop_threads", torch.set_num_threads, 1),
        ("torch_deterministic_algorithms", torch.use_deterministic_algorithms, True),
    ):
        try:
            setter(value)
        except Exception as exc:  # Postconditions below remain authoritative.
            setter_errors.append(f"{name}:{type(exc).__name__}:{exc}")
    after = {
        "device": str(torch.get_default_device()),
        "torch_intraop_threads": int(torch.get_num_threads()),
        "torch_interop_threads": int(torch.get_num_interop_threads()),
        "torch_deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
    }
    _require(after == expected, f"cannot establish compute contract during {context}: {after}")
    return {
        "context": context,
        "before": before,
        "after": after,
        "reset_applied": before != after,
        "setter_errors_ignored_only_after_matching_postconditions": setter_errors,
    }


def _finite_nonnegative(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AuditMismatch(f"{path} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise AuditMismatch(f"{path} must be finite and nonnegative")
    return result


def _scheduler_projection(
    stored: Mapping[str, Any], expected: Mapping[str, Any]
) -> tuple[dict[str, Any], list[str], list[str], bool]:
    """Normalize exactly four timers and one explicit JSON-array path."""

    left = copy.deepcopy(dict(stored))
    right = copy.deepcopy(dict(expected))
    left_diag = left.get("diagnostics")
    right_diag = right.get("diagnostics")
    _require(isinstance(left_diag, dict) and isinstance(right_diag, dict), "scheduler diagnostics missing")

    all_elapsed = {
        key
        for key in set(left_diag) | set(right_diag)
        if isinstance(key, str) and key.endswith("elapsed_s")
    }
    unknown = sorted(all_elapsed - set(ELAPSED_FIELDS))
    _require(not unknown, f"unregistered scheduler elapsed field(s): {unknown}")

    elapsed_paths: list[str] = []
    for name in ELAPSED_FIELDS:
        in_left = name in left_diag
        in_right = name in right_diag
        _require(in_left == in_right, f"scheduler timing scope mismatch: {name}")
        if not in_left:
            continue
        _finite_nonnegative(left_diag[name], f"stored scheduler.diagnostics.{name}")
        _finite_nonnegative(right_diag[name], f"rebuilt scheduler.diagnostics.{name}")
        sentinel = {"allowed_nonreplayable_elapsed_field": name}
        left_diag[name] = sentinel
        right_diag[name] = copy.deepcopy(sentinel)
        elapsed_paths.append(f"scheduler.diagnostics.{name}")

    array_paths: list[str] = []
    selection_left = left_diag.get("selection_order")
    selection_right = right_diag.get("selection_order")
    _require(
        (selection_left is None) == (selection_right is None),
        "scheduler selection_order scope mismatch",
    )
    if selection_left is not None:
        _require(isinstance(selection_left, list), "stored selection_order must be a JSON list")
        _require(isinstance(selection_right, tuple), "rebuilt selection_order must be the frozen tuple form")
        _require(list(selection_left) == list(selection_right), "selection_order value/order mismatch")
        left_diag["selection_order"] = list(selection_left)
        right_diag["selection_order"] = list(selection_right)
        array_paths.append(SCHEDULER_ARRAY_PATH)

    strict_original_equal = dict(stored) == dict(expected)
    _require(left == right, "deterministic scheduler field mismatch outside the exact allowlist")
    return left, elapsed_paths, array_paths, strict_original_equal


def _native_expected(row: Mapping[str, Any], compilation: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    diagnostics = compilation.diagnostics
    qasm = frozen.native_to_openqasm3(compilation)
    raw_expected = {
        "profile_name": compilation.profile.name,
        "profile_sha256": row["native"]["profile_sha256"],
        "topology_family": compilation.profile.topology_family,
        "n_qubits": compilation.profile.n_qubits,
        "coupling_edges": [list(edge) for edge in compilation.profile.coupling_edges],
        **asdict(diagnostics),
        "native_gate_set": ["rz", "sx", "x", "cx"],
        "native_gate_set_ok": all(
            gate.name in {"rz", "sx", "x", "cx"} for gate in compilation.native_gates
        ),
        "coupling_ok": all(
            tuple(sorted(gate.qubits)) in compilation.profile.coupling_edges
            for gate in compilation.native_gates
            if gate.name == "cx"
        ),
        "native_qasm3": qasm,
        "native_qasm3_sha256": sha256_bytes(qasm.encode("utf-8")),
        "hardware_execution": False,
        "noisy_simulation": False,
    }
    normalized = copy.deepcopy(raw_expected)
    for key in ("initial_logical_to_physical", "final_logical_to_physical"):
        value = normalized.get(key)
        _require(isinstance(value, tuple), f"rebuilt native.{key} must use frozen tuple form")
        normalized[key] = list(value)
    return raw_expected, normalized


def _verify_reversible_all_targets(circuit: Any, coordinate: Any) -> bool:
    for x in range(1 << int(coordinate.input_width)):
        prefix = [(x >> bit) & 1 for bit in range(int(coordinate.input_width))]
        for target_input in (0, 1):
            bits = prefix + [target_input]
            bits.extend(0 for _ in range(circuit.n_qubits - len(bits)))
            for gate in circuit.gates:
                if gate.type == "X":
                    bits[gate.target] ^= 1
                elif gate.type == "CNOT":
                    if bits[gate.controls[0]]:
                        bits[gate.target] ^= 1
                elif gate.type == "MCT":
                    if all(bits[control] for control in gate.controls):
                        bits[gate.target] ^= 1
                else:
                    return False
            width = int(coordinate.input_width)
            if (
                bits[:width] != prefix
                or bits[width] != (target_input ^ int(coordinate.evaluate(x)))
                or any(bits[width + 1 :])
            ):
                return False
    return True


def _search_reconstruction(
    row: Mapping[str, Any],
    config: Mapping[str, Any],
    weights: Any,
    checkpoint: Path,
    coordinate: Any,
    *,
    portable: bool = False,
    portable_contract_sha256: str = PORTABLE_NORMALIZATION_CONTRACT_SHA256,
) -> dict[str, Any]:
    """Rebuild search, scheduler, policy/value, Plan and logical QASM."""

    try:
        portable_stats = _new_portable_stats()
        portable_pool_projection: object | None = None
        portable_scheduler_projection: object | None = None
        portable_feedback_projection: object | None = None
        family = str(row["family"])
        bit = int(row["output_bit"])
        solver_seed = int(row["solver_seed"])
        arm = str(row["arm"])
        arm_spec = frozen._arm_contract(config, arm)
        terms = frozenset(frozen.anf_monomials(coordinate.boolean_function))
        search_config = frozen._search_config(config)
        structural_actions = frozen.candidate_actions(terms, 0, 0, search_config, neural_scorer=None)
        root_action_count = len(structural_actions)
        root_eligibility = "schedulable" if root_action_count > 0 else "degenerate_direct_root"
        scheduler_config = frozen._scheduler_config(
            config, arm, family=family, output_bit=bit, solver_seed=solver_seed
        )
        _require(row.get("record_type") == "e5_external_family_trial", "record_type mismatch")
        _require(row.get("phase") == "evaluate", "row phase mismatch")
        _require(row.get("arm_spec") == dict(arm_spec), "arm_spec mismatch")
        _require(row.get("same_pool_group") == arm_spec["same_pool_group"], "same_pool_group mismatch")
        _require(row.get("search_config") == asdict(search_config), "search_config mismatch")
        _require(row.get("scheduler_config") == scheduler_config.to_dict(), "scheduler_config mismatch")
        _require(row.get("simulations") == int(config["search"]["simulations"]), "simulation budget mismatch")
        _require(row.get("scheduler_seed") == scheduler_config.seed, "scheduler seed mismatch")
        _require(row.get("root_action_count") == root_action_count, "root action count mismatch")
        _require(row.get("root_eligibility") == root_eligibility, "root eligibility mismatch")
        _require(
            row.get("root_structural_action_signatures")
            == [frozen._action_signature(action) for action in structural_actions],
            "structural action signature/prior mismatch",
        )

        scorer = None
        policy = None
        value_estimator = None
        if arm_spec["learned_policy"]:
            scorer = frozen.FoundationScorer.from_checkpoint(checkpoint)
            _require(
                all(parameter.device.type == "cpu" for parameter in scorer.model.parameters()),
                "checkpoint left CPU compute contract",
            )
            policy = frozen.TermThresholdPolicyScorer(
                scorer, int(config["search"]["policy_term_threshold"])
            )
            value_estimator = frozen.LearnedValueEstimator(scorer, search_config)
        adjuster = None
        if arm_spec["execution_aware"]:
            profile_spec = frozen._profile_spec(config)
            adjuster = frozen.make_root_rollout_execution_utility_adjuster(
                n_inputs=int(coordinate.input_width),
                search_config=search_config,
                profile_spec=profile_spec,
                penalty_weights=weights,
                expected_profile_sha256=profile_spec.profile_sha256,
                execution_n_qubits=int(config["native_profile"]["frozen_n_qubits"]),
            )
        solver = frozen.NeuralMCTSSolver(
            config=search_config,
            simulations=int(config["search"]["simulations"]),
            seed=solver_seed,
            neural_scorer=policy,
            value_estimator=value_estimator,
            rollout_scorer=None,
            scheduler_config=scheduler_config,
            execution_utility_adjuster=adjuster,
        )
        plan = solver.solve(terms)
        root = solver.nodes.get(frozen.StateKey(terms, 0, 0))
        _require(root is not None and len(root.actions) == root_action_count, "root reconstruction mismatch")

        if root_eligibility == "degenerate_direct_root":
            _require(root.scheduler_decision is None and root.admitted_indices is None, "degenerate root invoked scheduler")
            decision = None
            diagnostics = {
                "root_eligibility": root_eligibility,
                "status": "not_invoked_degenerate_direct_root",
                "node_id": frozen.NeuralMCTSSolver._state_id(frozen.StateKey(terms, 0, 0)),
                "candidate_count": 0,
                "utilities": [],
                "raw_utilities": [],
                "adjusted_utilities": [],
                "execution_feedback": {"enabled": False, "reason": "degenerate_direct_root"},
                "qaoa_attempted": False,
                "qaoa_succeeded": False,
                "qaoa_repaired": False,
                "qaoa_fallback": False,
                "not_invoked_reason": "root_action_count_zero",
            }
            width = 0
            actions: tuple[Any, ...] = ()
            raw: list[float] = []
            adjusted: list[float] = []
            redundancy: list[list[float]] = []
            _require(
                frozen.PlanTrace.from_plan(plan).to_dict()
                == frozen.PlanTrace.from_plan(frozen.direct_plan(terms, 0, 0, search_config)).to_dict(),
                "degenerate root did not emit the direct Plan",
            )
        else:
            _require(root.scheduler_decision is not None and root.admitted_indices is not None, "schedulable root lacks scheduler")
            decision = root.scheduler_decision
            diagnostics = dict(decision.diagnostics)
            diagnostics["root_eligibility"] = root_eligibility
            width = int(diagnostics["candidate_count"])
            actions = tuple(root.actions[:width])
            raw = [float(value) for value in diagnostics.get("raw_utilities", diagnostics["utilities"])]
            adjusted = [
                float(value)
                for value in diagnostics.get("adjusted_utilities", diagnostics["utilities"])
            ]
            redundancy = [
                [float(value) for value in values]
                for values in frozen.action_redundancy_matrix(
                    actions, alpha=scheduler_config.redundancy_alpha
                )
            ]

        expected_pool = {
            "schema_version": "xa.e5-external-family-candidate-pool.v1",
            "family": family,
            "output_bit": bit,
            "truth_table_sha256": coordinate.truth_table_sha256,
            "node_id": diagnostics["node_id"],
            "candidate_count": width,
            "budget_requested": int(config["search"]["scheduler_budget"]),
            "budget_effective": min(int(config["search"]["scheduler_budget"]), width),
            "action_signatures": [frozen._action_signature(action) for action in actions],
            "utilities": raw,
            "redundancy": redundancy,
            "redundancy_weight": float(config["search"]["redundancy_weight"]),
            "redundancy_alpha": float(config["search"]["redundancy_alpha"]),
        }
        if portable:
            stored_pool = row.get("candidate_pool")
            _require(isinstance(stored_pool, Mapping), "stored candidate pool missing")
            _require(
                row.get("candidate_pool_sha256") == _payload_sha(stored_pool),
                "stored candidate pool SHA mismatch",
            )
            portable_pool_projection = _portable_project_and_compare(
                stored_pool,
                expected_pool,
                path="candidate_pool",
                stats=portable_stats,
            )
            _portable_project_and_compare(
                row.get("raw_scheduler_utilities"),
                raw,
                path="raw_scheduler_utilities",
                stats=portable_stats,
            )
            _portable_project_and_compare(
                row.get("adjusted_scheduler_utilities"),
                adjusted,
                path="adjusted_scheduler_utilities",
                stats=portable_stats,
            )
        else:
            _require(row.get("candidate_pool") == expected_pool, "candidate pool/raw utility mismatch")
            _require(row.get("candidate_pool_sha256") == _payload_sha(expected_pool), "candidate pool SHA mismatch")
            _require(row.get("raw_scheduler_utilities") == raw, "raw scheduler utility mismatch")
            _require(row.get("adjusted_scheduler_utilities") == adjusted, "adjusted scheduler utility mismatch")

        selected = [int(value) for value in decision.selected_indices] if decision is not None else []
        selected_set = set(selected)
        visits = [root.stats[index].visits for index in range(len(root.actions))]
        expected_scheduler = {
            "method": scheduler_config.method,
            "qaoa_mode": scheduler_config.qaoa_mode if arm.endswith("qaoa_shot") else None,
            "candidate_count": width,
            "budget_requested": int(config["search"]["scheduler_budget"]),
            "budget_effective": min(int(config["search"]["scheduler_budget"]), width),
            "selected_indices": selected,
            "selected_action_visits": [visits[index] for index in selected],
            "selected_action_visits_total": sum(visits[index] for index in selected),
            "excluded_action_visits_total": sum(
                count for index, count in enumerate(visits) if index not in selected_set
            ),
            "status": diagnostics.get("status"),
            "objective": diagnostics.get("effective_objective", diagnostics.get("objective")),
            "qaoa_attempted": bool(diagnostics.get("qaoa_attempted")),
            "qaoa_succeeded": bool(diagnostics.get("qaoa_succeeded")),
            "qaoa_repaired": bool(diagnostics.get("qaoa_repaired")),
            "qaoa_fallback": bool(diagnostics.get("qaoa_fallback")),
            "diagnostics": diagnostics,
        }
        if portable:
            stored_feedback = row.get("execution_feedback")
            rebuilt_feedback = diagnostics.get("execution_feedback", {})
            _require(
                isinstance(stored_feedback, Mapping)
                and isinstance(rebuilt_feedback, Mapping),
                "execution feedback payload missing",
            )
            _validate_feedback_action_shas(
                stored_feedback,
                row["candidate_pool"]["action_signatures"],
            )
            _validate_feedback_action_shas(rebuilt_feedback, expected_pool["action_signatures"])
            if portable_contract_sha256 == PORTABLE_V3_NORMALIZATION_CONTRACT_SHA256:
                stored_scheduler = row.get("scheduler")
                _require(
                    isinstance(stored_scheduler, Mapping)
                    and isinstance(stored_scheduler.get("diagnostics"), Mapping),
                    "stored scheduler diagnostics missing",
                )
                stored_nested_feedback = stored_scheduler["diagnostics"].get(
                    "execution_feedback", {}
                )
                rebuilt_nested_feedback = expected_scheduler["diagnostics"].get(
                    "execution_feedback", {}
                )
                _require(
                    isinstance(stored_nested_feedback, Mapping)
                    and isinstance(rebuilt_nested_feedback, Mapping),
                    "nested scheduler execution feedback payload missing",
                )
                # These validations are v3-only and precede projection.  A
                # re-signed pool or top-level copy cannot authorize a nested SHA.
                _validate_feedback_action_shas(
                    stored_nested_feedback,
                    row["candidate_pool"]["action_signatures"],
                )
                _validate_feedback_action_shas(
                    rebuilt_nested_feedback,
                    expected_pool["action_signatures"],
                )
            portable_scheduler_projection = _portable_project_and_compare(
                row["scheduler"],
                expected_scheduler,
                path="scheduler",
                stats=portable_stats,
            )
            portable_feedback_projection = _portable_project_and_compare(
                stored_feedback,
                rebuilt_feedback,
                path="execution_feedback",
                stats=portable_stats,
            )
            elapsed_paths = [
                path
                for path in sorted(PORTABLE_TIMER_PATHS)
                if path.removeprefix("scheduler.diagnostics.")
                in row["scheduler"]["diagnostics"]
            ]
            array_paths = []
            if row["scheduler"]["diagnostics"].get("selection_order") is not None:
                array_paths.append(SCHEDULER_ARRAY_PATH)
            strict_scheduler_equal = dict(row["scheduler"]) == expected_scheduler
            scheduler_projection = copy.deepcopy(dict(row["scheduler"]))
            scheduler_projection["diagnostics"] = copy.deepcopy(
                scheduler_projection["diagnostics"]
            )
            for name in ELAPSED_FIELDS:
                if name in scheduler_projection["diagnostics"]:
                    scheduler_projection["diagnostics"][name] = {
                        "allowed_nonreplayable_elapsed_field": name
                    }
        else:
            scheduler_projection, elapsed_paths, array_paths, strict_scheduler_equal = _scheduler_projection(
                row["scheduler"], expected_scheduler
            )

        if root_eligibility == "degenerate_direct_root":
            expected_status = "not_invoked_degenerate"
        elif not arm.endswith("qaoa_shot"):
            expected_status = "classical_invoked"
        elif diagnostics.get("status") == "qaoa_not_invoked":
            expected_status = "not_invoked_small_pool"
        elif diagnostics.get("qaoa_fallback"):
            expected_status = "fallback"
        elif diagnostics.get("qaoa_repaired"):
            expected_status = "direct_repaired"
        elif diagnostics.get("qaoa_succeeded"):
            expected_status = "direct_unrepaired"
        else:
            expected_status = "invalid"
        _require(expected_status in frozen.EXECUTION_STATUSES, "unregistered execution status")
        _require(row.get("execution_status") == expected_status, "execution status mismatch")
        _require(row.get("qaoa_execution") == expected_status, "qaoa execution status mismatch")

        if root_eligibility == "degenerate_direct_root":
            _require(
                row.get("execution_feedback")
                == {"enabled": False, "reason": "degenerate_direct_root"}
                and not raw
                and not adjusted,
                "degenerate execution feedback mismatch",
            )
        elif arm_spec["execution_aware"]:
            feedback = diagnostics.get("execution_feedback", {})
            if not portable:
                _require(row.get("execution_feedback") == feedback, "execution-aware feedback mismatch")
            _require(feedback.get("model_metadata", {}).get("n_inputs") == coordinate.input_width, "feedback n_inputs mismatch")
            _require(feedback.get("model_metadata", {}).get("execution_n_qubits") == 10, "feedback qubit profile mismatch")
            _require(
                feedback.get("diagnostics", {}).get("heldout_noisy_outcome_used") is False,
                "held-out outcome entered utility",
            )
        else:
            _require(adjusted == raw, "historical arm adjusted raw utility")
            if not portable:
                _require(row.get("execution_feedback") == diagnostics.get("execution_feedback", {}), "historical feedback mismatch")

        policy_record = frozen._policy_stats_from_row(row)
        value_record = frozen._value_stats_from_row(row)
        if policy is None:
            _require(row.get("checkpoint_sha256") is None, "heuristic arm bound checkpoint")
            _require(row.get("learned_policy_enabled") is False, "heuristic policy flag mismatch")
            _require(row.get("learned_policy_active_at_root") is False, "heuristic policy active")
            _require(row.get("learned_value_enabled") is False, "heuristic value flag mismatch")
            _require(row.get("learned_value_active") is False, "heuristic value active")
            _require(all(int(value or 0) == 0 for value in policy_record.values()), "heuristic policy stats nonzero")
            _require(all(int(value or 0) == 0 for value in value_record.values()), "heuristic value stats nonzero")
            _require(row.get("learned_policy_stats") == {"learned_states": 0, "gated_states": 0}, "heuristic policy stats mismatch")
            _require(row.get("learned_value_stats") == frozen.ValueStats().as_dict(), "heuristic value stats mismatch")
        else:
            expected_policy = {
                "learned_states": policy.learned_states,
                "gated_states": policy.gated_states,
            }
            expected_value = value_estimator.stats.as_dict() if value_estimator else {}
            expected_policy_active = bool(root_eligibility == "schedulable" and policy.learned_states > 0)
            expected_value_active = bool(
                root_eligibility == "schedulable" and expected_value.get("value_calls", 0) > 0
            )
            _require(row.get("checkpoint_sha256") == config["foundation_v4"]["checkpoint_sha256"], "checkpoint SHA mismatch")
            _require(row.get("learned_policy_enabled") is True, "learned policy disabled")
            _require(row.get("learned_policy_active_at_root") is expected_policy_active, "learned policy activation mismatch")
            _require(row.get("learned_value_enabled") is True, "learned value disabled")
            _require(row.get("learned_value_active") is expected_value_active, "learned value activation mismatch")
            _require(row.get("learned_policy_stats") == expected_policy, "policy stats mismatch")
            _require(row.get("learned_value_stats") == expected_value, "value stats mismatch")
            _require(row.get("policy_cache_hits") == scorer.cache_hits, "policy cache hits mismatch")
            _require(row.get("policy_cache_misses") == scorer.cache_misses, "policy cache misses mismatch")
            if root_eligibility == "schedulable":
                _require(policy.learned_states > 0 and expected_value.get("value_calls", 0) > 0, "schedulable learned arm inactive")

        trace = frozen.PlanTrace.from_plan(plan).to_dict()
        _require(canonical_json_bytes(trace) == canonical_json_bytes(row.get("plan_trace")), "Plan trace mismatch")
        _require(row.get("plan_trace_sha256") == _payload_sha(trace), "Plan trace SHA mismatch")
        _require(asdict(plan.cost) == row.get("logical_cost"), "logical cost mismatch")
        _require(plan.score(frozen.PAPER_WEIGHTS) == row.get("logical_resource_score"), "logical resource score mismatch")
        _require(root.visits == row.get("root_visits"), "root visits mismatch")
        _require(len(solver.nodes) == row.get("search_nodes"), "search node count mismatch")
        _finite_nonnegative(row.get("scheduler_wall_s"), "scheduler_wall_s")
        _finite_nonnegative(row.get("solve_elapsed_s"), "solve_elapsed_s")

        allocated = min(search_config.max_factor_ancilla, plan.cost.explicit_ancilla)
        circuit = frozen.emit_plan_to_circuit(plan, coordinate.input_width, allocated)
        frozen_n = int(config["native_profile"]["frozen_n_qubits"])
        if circuit.n_qubits < frozen_n:
            padded = frozen.QuantumCircuit(frozen_n)
            padded.gates = list(circuit.gates)
            circuit = padded
        logical = frozen.export_openqasm3(circuit)
        _require(
            frozen.circuit_to_logical_ir(circuit)
            == frozen.circuit_to_logical_ir(frozen._circuit_from_ir(row["logical_circuit_ir"])),
            "logical circuit IR mismatch",
        )
        _require(row.get("allocated_factor_ancilla") == allocated, "allocated ancilla mismatch")
        _require(row.get("logical_qasm3") == logical.qasm, "logical QASM mismatch")
        _require(row.get("logical_qasm3_sha256") == sha256_bytes(logical.qasm.encode("utf-8")), "logical QASM SHA mismatch")

        deterministic_projection = {
            "root_structural_action_signatures": row["root_structural_action_signatures"],
            "candidate_pool": row["candidate_pool"] if portable else expected_pool,
            "raw_scheduler_utilities": row["raw_scheduler_utilities"] if portable else raw,
            "adjusted_scheduler_utilities": row["adjusted_scheduler_utilities"] if portable else adjusted,
            "scheduler": scheduler_projection,
            "execution_status": expected_status,
            "execution_feedback": row["execution_feedback"],
            "policy": row["learned_policy_stats"],
            "value": row["learned_value_stats"],
            "policy_cache_hits": row["policy_cache_hits"],
            "policy_cache_misses": row["policy_cache_misses"],
            "plan_trace": trace,
            "logical_cost": asdict(plan.cost),
            "logical_resource_score": plan.score(frozen.PAPER_WEIGHTS),
            "logical_qasm3_sha256": row["logical_qasm3_sha256"],
        }
        result = {
            "ok": True,
            "deterministic_projection_sha256": _payload_sha(deterministic_projection),
            "elapsed_fields": elapsed_paths,
            "json_array_fields": array_paths,
            "frozen_strict_comparison_would_pass": strict_scheduler_equal,
        }
        if portable:
            _require(portable_pool_projection is not None, "portable pool projection missing")
            _require(
                portable_scheduler_projection is not None,
                "portable scheduler projection missing",
            )
            _require(
                portable_feedback_projection is not None,
                "portable feedback projection missing",
            )
            discrete_projection = {
                "root_structural_action_signatures": row[
                    "root_structural_action_signatures"
                ],
                "candidate_pool": portable_pool_projection,
                "scheduler": portable_scheduler_projection,
                "execution_feedback": portable_feedback_projection,
                "execution_status": expected_status,
                "policy": row["learned_policy_stats"],
                "value": row["learned_value_stats"],
                "policy_cache_hits": row["policy_cache_hits"],
                "policy_cache_misses": row["policy_cache_misses"],
                "plan_trace_sha256": row["plan_trace_sha256"],
                "logical_cost": asdict(plan.cost),
                "logical_resource_score": plan.score(frozen.PAPER_WEIGHTS),
                "logical_qasm3_sha256": row["logical_qasm3_sha256"],
            }
            stable_stats = _portable_stats_report(portable_stats)
            result.update(
                {
                    "portable_normalization_contract_sha256": portable_contract_sha256,
                    "portable_discrete_projection_sha256": _payload_sha(
                        discrete_projection
                    ),
                    "portable_float_paths": stable_stats["portable_float_paths"],
                    "portable_float_path_count": stable_stats[
                        "portable_float_path_count"
                    ],
                    "portable_float_value_count": stable_stats[
                        "portable_float_value_count"
                    ],
                    "derived_fingerprint_paths": stable_stats[
                        "derived_fingerprint_paths"
                    ],
                    "derived_fingerprint_path_count": stable_stats[
                        "derived_fingerprint_path_count"
                    ],
                    "derived_fingerprint_value_count": stable_stats[
                        "derived_fingerprint_value_count"
                    ],
                    "portable_runtime_stats": portable_stats,
                }
            )
        return result
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}:{exc}",
            "elapsed_fields": [],
            "json_array_fields": [],
            "frozen_strict_comparison_would_pass": False,
        }


def _semantics_native_reconstruction(
    row: Mapping[str, Any], config: Mapping[str, Any], coordinate: Any
) -> dict[str, Any]:
    """Rebuild truth semantics, logical circuit, native compilation and endpoint."""

    try:
        _require(row.get("schema_version") == frozen.EVALUATION_ROW_SCHEMA, "evaluation row schema mismatch")
        _require(row.get("record_type") == "e5_external_family_trial", "record type mismatch")
        _require(row.get("phase") == "evaluate", "phase mismatch")
        _require(row.get("family") == coordinate.family, "family mismatch")
        _require(
            row.get("family_role") == config["holdout_access"]["families"][coordinate.family]["role"],
            "family role mismatch",
        )
        for key in ("operation", "output_bit", "input_width", "output_width", "bit_order", "source", "provenance"):
            _require(row.get(key) == getattr(coordinate, key), f"coordinate {key} mismatch")
        _require(row.get("vector_truth_table_sha256") == coordinate.vector_truth_table_sha256, "vector truth SHA mismatch")
        _require(row.get("truth_table_sha256") == coordinate.truth_table_sha256, "coordinate truth SHA mismatch")
        _require(int(str(row["truth_table_hex"]), 16) == int(coordinate.boolean_function.truth_table), "truth table integer mismatch")
        _require(row.get("family_exclusion_label") == frozen.HOLDOUT_LABEL, "family exclusion label mismatch")
        _require(row.get("benchmark_partition") == "external_crypto_family_holdout", "benchmark partition mismatch")
        _require(row.get("training_access_allowed") is False, "training access was allowed")

        plan = frozen._plan_from_trace(row["plan_trace"])
        terms = frozenset(frozen.anf_monomials(coordinate.boolean_function))
        _require(row.get("anf_term_count") == len(terms), "ANF term count mismatch")
        _require(frozen.verify_plan_anf(plan).ok and plan.terms == terms, "Plan ANF semantics mismatch")
        _require(asdict(plan.cost) == row["logical_cost"], "Plan logical cost mismatch")
        _require(row.get("plan_trace_sha256") == _payload_sha(row["plan_trace"]), "stored Plan trace SHA mismatch")

        circuit = frozen.emit_plan_to_circuit(
            plan, coordinate.input_width, int(row["allocated_factor_ancilla"])
        )
        frozen_n = int(config["native_profile"]["frozen_n_qubits"])
        if circuit.n_qubits < frozen_n:
            padded = frozen.QuantumCircuit(frozen_n)
            padded.gates = list(circuit.gates)
            circuit = padded
        expected_logical = frozen.export_openqasm3(circuit)
        expected_ir = {
            "n_qubits": expected_logical.logical_ir.n_qubits,
            "gate_mode": expected_logical.logical_ir.gate_mode,
            "gates": [
                {
                    "gate_type": gate.gate_type,
                    "controls": list(gate.controls),
                    "target": gate.target,
                }
                for gate in expected_logical.logical_ir.gates
            ],
        }
        stored_circuit = frozen._circuit_from_ir(row["logical_circuit_ir"])
        _require(row.get("logical_circuit_ir") == expected_ir, "logical circuit IR payload mismatch")
        _require(
            frozen.circuit_to_logical_ir(circuit) == frozen.circuit_to_logical_ir(stored_circuit),
            "logical circuit reconstruction mismatch",
        )
        _require(frozen.verify_circuit_anf(stored_circuit, coordinate.input_width, terms).ok, "circuit ANF verification failed")
        _require(frozen.verify_oracle(stored_circuit, coordinate.boolean_function), "oracle truth verification failed")
        _require(_verify_reversible_all_targets(stored_circuit, coordinate), "all-target reversible verification failed")
        _require(row.get("plan_anf_ok") is True, "stored plan ANF flag false")
        _require(row.get("circuit_anf_ok") is True, "stored circuit ANF flag false")
        _require(row.get("oracle_ok") is True, "stored oracle flag false")
        _require(row.get("reversible_oracle_all_targets_ok") is True, "stored reversible flag false")

        logical = frozen.export_openqasm3(stored_circuit)
        _require(row.get("logical_qasm3") == logical.qasm, "logical QASM content mismatch")
        _require(row.get("logical_qasm3_sha256") == sha256_bytes(logical.qasm.encode("utf-8")), "logical QASM SHA mismatch")
        _require(row.get("logical_gate_count") == len(stored_circuit.gates), "logical gate count mismatch")

        profile_spec = frozen._profile_spec(config)
        profile = profile_spec.build(frozen_n)
        compilation = frozen.compile_superconducting(stored_circuit, profile)
        frozen_profile, profile_sha = frozen._frozen_profile(config)
        raw_native, expected_native = _native_expected(row, compilation)
        stored_native = row.get("native")
        _require(isinstance(stored_native, dict), "stored native record missing")
        array_paths: list[str] = []
        for path, key in zip(
            NATIVE_ARRAY_PATHS,
            ("initial_logical_to_physical", "final_logical_to_physical"),
        ):
            _require(isinstance(stored_native.get(key), list), f"stored {path} must be JSON list")
            _require(isinstance(raw_native.get(key), tuple), f"rebuilt {path} must be frozen tuple")
            _require(stored_native.get(key) == list(raw_native[key]), f"{path} value/order mismatch")
            array_paths.append(path)
        _require(stored_native == expected_native, "native deterministic field mismatch")
        _require(row.get("native_record_sha256") == _payload_sha(expected_native), "native record SHA mismatch")

        endpoint = {
            "metric": "native.two_qubit_gate_count",
            "value": int(compilation.diagnostics.two_qubit_gate_count),
            "direction": "lower_is_better",
        }
        _require(stored_circuit.n_qubits == frozen_n == 10, "fixed-10q logical circuit mismatch")
        _require(row.get("logical_n_qubits") == frozen_n, "stored logical qubit count mismatch")
        _require(row.get("profile_spec_sha256") == profile_spec.profile_sha256, "profile spec SHA mismatch")
        _require(row.get("profile_sha256") == profile_sha, "profile SHA mismatch")
        _require(row.get("frozen_profile") == frozen_profile, "frozen profile payload mismatch")
        _require(stored_native.get("profile_sha256") == profile_sha, "native profile SHA mismatch")
        _require(stored_native.get("n_qubits") == frozen_n, "native qubit count mismatch")
        _require(row.get("primary_endpoint") == endpoint, "primary endpoint mismatch")
        _require(row.get("primary_endpoint_sha256") == _payload_sha(endpoint), "primary endpoint SHA mismatch")
        _require(row.get("noisy_endpoint") is None and not row.get("noisy_endpoints"), "noisy endpoint present")
        _require(row.get("hardware_execution") is False, "hardware execution claimed")
        _require(row.get("noisy_diagnostic_run") is False, "noisy diagnostic claimed")

        return {
            "ok": True,
            "deterministic_projection_sha256": _payload_sha(
                {
                    "truth_table_sha256": coordinate.truth_table_sha256,
                    "plan_trace_sha256": row["plan_trace_sha256"],
                    "logical_qasm3_sha256": row["logical_qasm3_sha256"],
                    "native": expected_native,
                    "primary_endpoint": endpoint,
                }
            ),
            "json_array_fields": array_paths,
            "frozen_strict_comparison_would_pass": stored_native == raw_native,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}:{exc}",
            "json_array_fields": [],
            "frozen_strict_comparison_would_pass": False,
        }


def _source_binding(root: Path, snapshot: list[list[object]], run: Mapping[str, Any]) -> dict[str, Any]:
    binding = run["binding"]
    return {
        "bundle_hint": SOURCE_RUN_ID,
        "source_run_id": SOURCE_RUN_ID,
        "snapshot_algorithm": "sha256(compact-json(sorted([name,size,sha256])))",
        "snapshot_sha256": SOURCE_SNAPSHOT_SHA256,
        "snapshot_files": [
            {"path": name, "size_bytes": size, "sha256": digest}
            for name, size, digest in snapshot
        ],
        "manifest_sha256": SOURCE_FILE_SHA256["artifacts.manifest.json"],
        "checksums_sha256": SOURCE_FILE_SHA256["checksums.sha256"],
        "raw_sha256": SOURCE_FILE_SHA256["raw.jsonl"],
        "run_sha256": SOURCE_FILE_SHA256["run.json"],
        "summary_sha256": SOURCE_FILE_SHA256["summary.json"],
        "declared_verifier_sha256": SOURCE_FILE_SHA256["verifier.json"],
        "frozen_verifier_sha256": FROZEN_VERIFIER_SHA256,
        "static_lock_canonical_sha256": STATIC_LOCK_CANONICAL_SHA256,
        "evaluation_lock_sha256": EVALUATION_LOCK_SHA256,
        "source_tree_sha256": binding["source_tree_sha256"],
        "preflight_summary_sha256": PREFLIGHT_SUMMARY_SHA256,
        "preflight_raw_sha256": PREFLIGHT_RAW_SHA256,
        "seal_summary_sha256": SEAL_SUMMARY_SHA256,
        "weights_sha256": WEIGHTS_SHA256,
        "checkpoint_sha256": binding["checkpoint_sha256"],
        "model_card_sha256": binding["model_card_sha256"],
    }


def _authenticate_source(root: Path) -> dict[str, Any]:
    root = root.resolve()
    _require(root.name == SOURCE_RUN_ID, "source bundle run-id/path mismatch")
    _require(root.parent == (PROJECT_ROOT / "results" / "xa202609").resolve(), "source bundle is outside frozen results directory")
    generic = verify_bundle(root, required_roles=REQUIRED_ROLES)
    _require(generic.ok, f"source artifact bundle invalid: {generic.errors}")
    _require({path.name for path in root.iterdir()} == EXPECTED_FILES, "source bundle is not exact nine-file evidence")
    for name, digest in SOURCE_FILE_SHA256.items():
        _require(sha256_file(root / name) == digest, f"source {name} SHA mismatch")
    snapshot = _snapshot_records(root)
    _require(_snapshot_sha(snapshot) == SOURCE_SNAPSHOT_SHA256, "source bundle snapshot SHA mismatch")

    run = _read_json(root / "run.json")
    _require(run.get("run_id") == SOURCE_RUN_ID and run.get("phase") == "evaluate", "source run identity mismatch")
    _require(run.get("status") == "failed", "source result must remain failed")
    _require(run.get("evidence_ok") is False and run.get("experiment_completed") is False, "source completion boundary changed")
    _require(run.get("counts", {}).get("rows") == 90, "source row count mismatch")

    config_path = PROJECT_ROOT / "configs" / "xa202609" / "e5_external_crypto_holdout_v1.json"
    lock_path = PROJECT_ROOT / "configs" / "xa202609" / "e5_external_crypto_holdout_v1.protocol.lock.json"
    verifier_path = PROJECT_ROOT / "scripts" / "verify_e5_external_crypto_holdout_bundle.py"
    _require(sha256_file(config_path) == CONFIG_FILE_SHA256, "frozen E5 config file SHA mismatch")
    _require(sha256_file(lock_path) == STATIC_LOCK_FILE_SHA256, "frozen static-lock file SHA mismatch")
    _require(sha256_file(verifier_path) == FROZEN_VERIFIER_SHA256, "frozen verifier SHA mismatch")
    config = _read_json(config_path)
    lock = _read_json(lock_path)
    _require(_payload_sha(config) == CONFIG_CANONICAL_SHA256, "frozen config canonical SHA mismatch")
    _require(_payload_sha(lock) == STATIC_LOCK_CANONICAL_SHA256, "static-lock canonical SHA mismatch")
    _require(run.get("config", {}).get("effective_config") == config, "source embedded config mismatch")
    _require(run.get("config", {}).get("canonical_sha256") == CONFIG_CANONICAL_SHA256, "source config binding mismatch")
    # The static-lock tree digest and the sealed evaluation tree digest use
    # distinct frozen projections.  Bind each to its historical value rather
    # than incorrectly equating the two algorithms.
    _require(
        lock.get("source_tree_sha256") == STATIC_LOCK_SOURCE_TREE_SHA256,
        "static-lock source-tree projection mismatch",
    )
    _require(
        run["binding"].get("source_tree_sha256") == EVALUATION_SOURCE_TREE_SHA256,
        "sealed evaluation source-tree projection mismatch",
    )
    for record in lock.get("sources", {}).values():
        path = PROJECT_ROOT / str(record["path"])
        _require(path.is_file() and sha256_file(path) == record["sha256"], f"locked source mismatch: {record['path']}")

    compute_runtime = _establish_compute_contract(config, context="negative-audit-before-checkpoint-inference")
    foundation = config["foundation_v4"]
    checkpoint = PROJECT_ROOT / foundation["checkpoint"]
    _require(checkpoint.is_file() and sha256_file(checkpoint) == foundation["checkpoint_sha256"], "foundation checkpoint mismatch")
    foundation_root = PROJECT_ROOT / foundation["bundle"]
    foundation_report = frozen.verify_foundation_v4_bundle(foundation_root, require_current_source=True)
    _require(foundation_report.get("ok") is True, "foundation-v4 provenance gate failed")
    _require(foundation_report.get("checkpoint_sha256") == foundation["checkpoint_sha256"], "foundation-v4 checkpoint report mismatch")
    _require(foundation_report.get("dataset_sha256") == foundation["dataset_sha256"], "foundation-v4 dataset report mismatch")

    seal_root = root.parent / SEAL_RUN_ID
    preflight_root = root.parent / PREFLIGHT_RUN_ID
    for linked in (seal_root, preflight_root):
        linked_report = verify_bundle(linked, required_roles=REQUIRED_ROLES)
        _require(linked_report.ok, f"linked frozen bundle invalid: {linked.name}")
    _require(sha256_file(seal_root / "summary.json") == SEAL_SUMMARY_SHA256, "seal summary SHA mismatch")
    _require(sha256_file(preflight_root / "summary.json") == PREFLIGHT_SUMMARY_SHA256, "preflight summary SHA mismatch")
    _require(sha256_file(preflight_root / "raw.jsonl") == PREFLIGHT_RAW_SHA256, "preflight raw SHA mismatch")
    seal_summary = _read_json(seal_root / "summary.json")
    _require(_payload_sha(seal_summary["evaluation_lock"]) == EVALUATION_LOCK_SHA256, "evaluation-lock canonical SHA mismatch")
    _require(seal_summary.get("evaluation_lock_sha256") == EVALUATION_LOCK_SHA256, "seal evaluation-lock binding mismatch")
    _require(seal_summary.get("static_lock_sha256") == STATIC_LOCK_CANONICAL_SHA256, "seal static-lock binding mismatch")
    _require(
        seal_summary.get("source_tree_sha256") == EVALUATION_SOURCE_TREE_SHA256
        and seal_summary["evaluation_lock"].get("source_tree_sha256")
        == EVALUATION_SOURCE_TREE_SHA256,
        "seal evaluation source-tree binding mismatch",
    )
    _require(seal_summary.get("preflight_binding", {}).get("summary_sha256") == PREFLIGHT_SUMMARY_SHA256, "seal preflight summary binding mismatch")
    _require(seal_summary.get("preflight_binding", {}).get("raw_sha256") == PREFLIGHT_RAW_SHA256, "seal preflight raw binding mismatch")
    _require(seal_summary.get("preflight_binding", {}).get("weights_sha256") == WEIGHTS_SHA256, "seal weights binding mismatch")
    _require(run["binding"].get("evaluation_lock_sha256") == EVALUATION_LOCK_SHA256, "source evaluation-lock binding mismatch")
    _require(run["binding"].get("static_lock_sha256") == STATIC_LOCK_CANONICAL_SHA256, "source static-lock binding mismatch")
    _require(run["binding"].get("preflight_summary_sha256") == PREFLIGHT_SUMMARY_SHA256, "source preflight binding mismatch")
    _require(run["binding"].get("seal_summary_sha256") == SEAL_SUMMARY_SHA256, "source seal binding mismatch")
    _require(run["binding"].get("weights_sha256") == WEIGHTS_SHA256, "source weights binding mismatch")

    weights = frozen._weights_from_payload(seal_summary["evaluation_lock"]["frozen_penalty_weights"])
    _require(weights.weights_sha256 == WEIGHTS_SHA256, "reconstructed frozen weights SHA mismatch")
    # This is the first hold-out-table access in this verifier, after every
    # source/model/preflight/seal/lock gate above has succeeded.
    coordinates = frozen._load_and_verify_holdouts(config)
    rows = _read_jsonl(root / "raw.jsonl")
    return {
        "root": root,
        "run": run,
        "config": config,
        "checkpoint": checkpoint,
        "weights": weights,
        "coordinates": coordinates,
        "rows": rows,
        "snapshot": snapshot,
        "compute_runtime": compute_runtime,
    }


def audit_one_source_row(
    row: Mapping[str, Any],
    *,
    ordinal: int,
    config: Mapping[str, Any],
    weights: Any,
    checkpoint: Path,
    coordinates: Mapping[str, Sequence[Any]],
) -> dict[str, Any]:
    family = str(row.get("family"))
    bit = int(row.get("output_bit", -1))
    coordinate = coordinates[family][bit]
    search = _search_reconstruction(row, config, weights, checkpoint, coordinate)
    semantics = _semantics_native_reconstruction(row, config, coordinate)
    return {
        "schema_version": ROW_SCHEMA,
        "ordinal": ordinal,
        "identity": {
            "family": family,
            "output_bit": bit,
            "solver_seed": int(row.get("solver_seed", -1)),
            "arm": str(row.get("arm")),
        },
        "source_row_sha256": _payload_sha(row),
        "root_eligibility": row.get("root_eligibility"),
        "execution_status": row.get("execution_status"),
        "search_plan_scheduler_reconstruction": search,
        "logical_semantics_native_endpoint_reconstruction": semantics,
    }


def _audit_one_source_row_portable_with_runtime(
    row: Mapping[str, Any],
    *,
    ordinal: int,
    config: Mapping[str, Any],
    weights: Any,
    checkpoint: Path,
    coordinates: Mapping[str, Sequence[Any]],
    row_schema: str = PORTABLE_ROW_SCHEMA,
    contract_sha256: str = PORTABLE_NORMALIZATION_CONTRACT_SHA256,
) -> tuple[dict[str, Any], dict[str, Any]]:
    family = str(row.get("family"))
    bit = int(row.get("output_bit", -1))
    coordinate = coordinates[family][bit]
    search = _search_reconstruction(
        row,
        config,
        weights,
        checkpoint,
        coordinate,
        portable=True,
        portable_contract_sha256=contract_sha256,
    )
    runtime = search.pop("portable_runtime_stats", _new_portable_stats())
    semantics = _semantics_native_reconstruction(row, config, coordinate)
    record = {
        "schema_version": row_schema,
        "ordinal": ordinal,
        "identity": {
            "family": family,
            "output_bit": bit,
            "solver_seed": int(row.get("solver_seed", -1)),
            "arm": str(row.get("arm")),
        },
        "source_row_sha256": _payload_sha(row),
        "source_full_candidate_pool_sha256": row.get("candidate_pool_sha256"),
        "portable_normalization_contract_sha256": contract_sha256,
        "root_eligibility": row.get("root_eligibility"),
        "execution_status": row.get("execution_status"),
        "search_plan_scheduler_reconstruction": search,
        "logical_semantics_native_endpoint_reconstruction": semantics,
    }
    return record, runtime


def audit_one_source_row_portable(
    row: Mapping[str, Any],
    *,
    ordinal: int,
    config: Mapping[str, Any],
    weights: Any,
    checkpoint: Path,
    coordinates: Mapping[str, Sequence[Any]],
) -> dict[str, Any]:
    """Replay one row under v2 without serializing runtime-specific floats."""

    record, _runtime = _audit_one_source_row_portable_with_runtime(
        row,
        ordinal=ordinal,
        config=config,
        weights=weights,
        checkpoint=checkpoint,
        coordinates=coordinates,
    )
    return record


def audit_one_source_row_portable_v3(
    row: Mapping[str, Any],
    *,
    ordinal: int,
    config: Mapping[str, Any],
    weights: Any,
    checkpoint: Path,
    coordinates: Mapping[str, Sequence[Any]],
) -> dict[str, Any]:
    """Replay one row under v3 with nested feedback SHA binding."""

    record, _runtime = _audit_one_source_row_portable_with_runtime(
        row,
        ordinal=ordinal,
        config=config,
        weights=weights,
        checkpoint=checkpoint,
        coordinates=coordinates,
        row_schema=PORTABLE_V3_ROW_SCHEMA,
        contract_sha256=PORTABLE_V3_NORMALIZATION_CONTRACT_SHA256,
    )
    return record


def _expected_order(config: Mapping[str, Any]) -> list[tuple[str, int, int, str]]:
    arms = [str(item["name"]) for item in config["evaluation"]["arms"]]
    return [
        (family, int(bit), int(seed), arm)
        for family in config["evaluation"]["family_order"]
        for bit in config["holdout_access"]["families"][family]["coordinates"]
        for seed in config["evaluation"]["solver_seeds"]
        for arm in arms
    ]


def recompute_source_audit(source_root: Path) -> dict[str, Any]:
    """Authenticate and independently reconstruct the original 90 rows."""

    source = _authenticate_source(Path(source_root))
    rows = source["rows"]
    config = source["config"]
    expected_order = _expected_order(config)
    actual_order = [
        (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"]), str(row["arm"]))
        for row in rows
    ]
    _require(len(rows) == 90 and actual_order == expected_order, "source 90-row order/matrix mismatch")

    audit_rows = [
        audit_one_source_row(
            row,
            ordinal=ordinal,
            config=config,
            weights=source["weights"],
            checkpoint=source["checkpoint"],
            coordinates=source["coordinates"],
        )
        for ordinal, row in enumerate(rows)
    ]
    _require(
        all(item["search_plan_scheduler_reconstruction"]["ok"] for item in audit_rows),
        "one or more search/Plan/scheduler rows failed post-hoc reconstruction",
    )
    _require(
        all(item["logical_semantics_native_endpoint_reconstruction"]["ok"] for item in audit_rows),
        "one or more semantics/native/endpoint rows failed post-hoc reconstruction",
    )

    family_groups: dict[tuple[str, int, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        family_groups.setdefault(
            (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"])), []
        ).append(row)
    schedulable_groups: dict[str, int] = {family: 0 for family in config["evaluation"]["family_order"]}
    degenerate_groups = 0
    for (family, _bit, _seed), group in family_groups.items():
        _require(len(group) == 5, "family-bit-seed group does not contain five arms")
        classes = {str(row["root_eligibility"]) for row in group}
        _require(len(classes) == 1, "root eligibility differs by arm")
        if classes == {"schedulable"}:
            schedulable_groups[family] += 1
        elif classes == {"degenerate_direct_root"}:
            degenerate_groups += 1
        else:
            raise AuditMismatch(f"unregistered root eligibility: {classes}")
    _require(schedulable_groups == {"ASCON": 0, "PRESENT": 6}, "family schedulable group counts changed")
    _require(degenerate_groups == 12 and len(family_groups) == 18, "root group accounting mismatch")

    elapsed_counts = {path: 0 for path in EXPECTED_ELAPSED_COUNTS}
    array_counts = {path: 0 for path in EXPECTED_ARRAY_COUNTS}
    raw_search_pass = 0
    raw_native_pass = 0
    schedulable_rows = 0
    degenerate_rows = 0
    for item in audit_rows:
        search = item["search_plan_scheduler_reconstruction"]
        native = item["logical_semantics_native_endpoint_reconstruction"]
        raw_search_pass += int(search["frozen_strict_comparison_would_pass"])
        raw_native_pass += int(native["frozen_strict_comparison_would_pass"])
        for path in search["elapsed_fields"]:
            elapsed_counts[path] += 1
        for path in [*search["json_array_fields"], *native["json_array_fields"]]:
            array_counts[path] += 1
        schedulable_rows += int(item["root_eligibility"] == "schedulable")
        degenerate_rows += int(item["root_eligibility"] == "degenerate_direct_root")
    _require(elapsed_counts == EXPECTED_ELAPSED_COUNTS, f"elapsed allowlist scope/count mismatch: {elapsed_counts}")
    _require(array_counts == EXPECTED_ARRAY_COUNTS, f"array normalization scope/count mismatch: {array_counts}")
    _require(raw_search_pass == 60 and raw_native_pass == 0, "frozen verifier false-negative baseline changed")
    _require(schedulable_rows == 30 and degenerate_rows == 60, "row eligibility accounting mismatch")

    final_snapshot = _snapshot_records(source["root"])
    _require(final_snapshot == source["snapshot"], "original result bundle changed during audit")
    binding = _source_binding(source["root"], source["snapshot"], source["run"])
    return {
        "source_binding": binding,
        "audit_rows": audit_rows,
        "counts": {
            "row_count": 90,
            "search_plan_scheduler_reconstructed": 90,
            "logical_semantics_native_endpoint_reconstructed": 90,
            "frozen_strict_search_passed": raw_search_pass,
            "frozen_strict_search_failed": 90 - raw_search_pass,
            "frozen_strict_native_passed": raw_native_pass,
            "frozen_strict_native_failed": 90 - raw_native_pass,
            "degenerate_rows": degenerate_rows,
            "schedulable_rows": schedulable_rows,
            "degenerate_groups": degenerate_groups,
            "schedulable_groups": sum(schedulable_groups.values()),
        },
        "elapsed_field_counts": elapsed_counts,
        "json_array_field_counts": array_counts,
        "family_schedulable_group_counts": schedulable_groups,
        "each_family_has_schedulable_activity": all(
            value > 0 for value in schedulable_groups.values()
        ),
        "compute_runtime": source["compute_runtime"],
    }


def _recompute_source_portable_audit(
    source_root: Path, *, portable_version: int
) -> dict[str, Any]:
    """Authenticate and replay all 90 rows under one versioned contract."""

    _require(portable_version in (2, 3), "unsupported portable audit version")
    row_schema = PORTABLE_ROW_SCHEMA if portable_version == 2 else PORTABLE_V3_ROW_SCHEMA
    contract_sha256 = (
        PORTABLE_NORMALIZATION_CONTRACT_SHA256
        if portable_version == 2
        else PORTABLE_V3_NORMALIZATION_CONTRACT_SHA256
    )

    source = _authenticate_source(Path(source_root))
    rows = source["rows"]
    config = source["config"]
    expected_order = _expected_order(config)
    actual_order = [
        (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"]), str(row["arm"]))
        for row in rows
    ]
    _require(len(rows) == 90 and actual_order == expected_order, "source 90-row order/matrix mismatch")

    aggregate_runtime = _new_portable_stats()
    audit_rows: list[dict[str, Any]] = []
    for ordinal, row in enumerate(rows):
        record, runtime = _audit_one_source_row_portable_with_runtime(
            row,
            ordinal=ordinal,
            config=config,
            weights=source["weights"],
            checkpoint=source["checkpoint"],
            coordinates=source["coordinates"],
            row_schema=row_schema,
            contract_sha256=contract_sha256,
        )
        audit_rows.append(record)
        _merge_portable_stats(aggregate_runtime, runtime)
    _require(
        all(item["search_plan_scheduler_reconstruction"]["ok"] for item in audit_rows),
        "one or more portable search/Plan/scheduler rows failed reconstruction",
    )
    _require(
        all(
            item["logical_semantics_native_endpoint_reconstruction"]["ok"]
            for item in audit_rows
        ),
        "one or more portable semantics/native/endpoint rows failed reconstruction",
    )

    family_groups: dict[tuple[str, int, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        family_groups.setdefault(
            (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"])), []
        ).append(row)
    schedulable_groups: dict[str, int] = {
        family: 0 for family in config["evaluation"]["family_order"]
    }
    degenerate_groups = 0
    for (family, _bit, _seed), group in family_groups.items():
        _require(len(group) == 5, "portable family-bit-seed group does not contain five arms")
        classes = {str(row["root_eligibility"]) for row in group}
        _require(len(classes) == 1, "portable root eligibility differs by arm")
        if classes == {"schedulable"}:
            schedulable_groups[family] += 1
        elif classes == {"degenerate_direct_root"}:
            degenerate_groups += 1
        else:
            raise AuditMismatch(f"unregistered portable root eligibility: {classes}")
    _require(
        schedulable_groups == {"ASCON": 0, "PRESENT": 6},
        "portable family schedulable group counts changed",
    )
    _require(
        degenerate_groups == 12 and len(family_groups) == 18,
        "portable root group accounting mismatch",
    )

    elapsed_counts = {path: 0 for path in EXPECTED_ELAPSED_COUNTS}
    array_counts = {path: 0 for path in EXPECTED_ARRAY_COUNTS}
    raw_search_pass = 0
    raw_native_pass = 0
    schedulable_rows = 0
    degenerate_rows = 0
    for item in audit_rows:
        search = item["search_plan_scheduler_reconstruction"]
        native = item["logical_semantics_native_endpoint_reconstruction"]
        raw_search_pass += int(search["frozen_strict_comparison_would_pass"])
        raw_native_pass += int(native["frozen_strict_comparison_would_pass"])
        for path in search["elapsed_fields"]:
            elapsed_counts[path] += 1
        for path in [*search["json_array_fields"], *native["json_array_fields"]]:
            array_counts[path] += 1
        schedulable_rows += int(item["root_eligibility"] == "schedulable")
        degenerate_rows += int(item["root_eligibility"] == "degenerate_direct_root")
    _require(
        elapsed_counts == EXPECTED_ELAPSED_COUNTS,
        f"portable elapsed allowlist scope/count mismatch: {elapsed_counts}",
    )
    _require(
        array_counts == EXPECTED_ARRAY_COUNTS,
        f"portable array normalization scope/count mismatch: {array_counts}",
    )
    _require(
        raw_search_pass == 60 and raw_native_pass == 0,
        "portable frozen-verifier false-negative baseline changed",
    )
    _require(
        schedulable_rows == 30 and degenerate_rows == 60,
        "portable row eligibility accounting mismatch",
    )

    final_snapshot = _snapshot_records(source["root"])
    _require(final_snapshot == source["snapshot"], "original result bundle changed during portable audit")
    stable_stats = _portable_stats_report(aggregate_runtime)
    counts = {
        "row_count": 90,
        "portable_search_plan_scheduler_reconstructed": 90,
        "logical_semantics_native_endpoint_reconstructed": 90,
        "frozen_strict_search_passed": raw_search_pass,
        "frozen_strict_search_failed": 90 - raw_search_pass,
        "frozen_strict_native_passed": raw_native_pass,
        "frozen_strict_native_failed": 90 - raw_native_pass,
        "degenerate_rows": degenerate_rows,
        "schedulable_rows": schedulable_rows,
        "degenerate_groups": degenerate_groups,
        "schedulable_groups": sum(schedulable_groups.values()),
        "portable_float_path_count": stable_stats["portable_float_path_count"],
        "portable_float_value_count": stable_stats["portable_float_value_count"],
        "derived_fingerprint_path_count": stable_stats[
            "derived_fingerprint_path_count"
        ],
        "derived_fingerprint_value_count": stable_stats[
            "derived_fingerprint_value_count"
        ],
    }
    if portable_version == 2:
        reference_runtime = copy.deepcopy(REFERENCE_RUNTIME_BUILD)
        runtime = runtime_build_fingerprint()
        matches_reference = runtime_matches_reference(runtime)
        runtime_differences: list[dict[str, Any]] = []
    else:
        _require(
            bool(REFERENCE_RUNTIME_BUILD_V2),
            "v3 reference runtime fingerprint is not populated",
        )
        reference_runtime = copy.deepcopy(REFERENCE_RUNTIME_BUILD_V2)
        runtime = runtime_build_fingerprint_v2()
        runtime_differences = runtime_build_differences_v2(
            runtime, REFERENCE_RUNTIME_BUILD_V2
        )
        matches_reference = not runtime_differences
    return {
        "source_binding": _source_binding(source["root"], source["snapshot"], source["run"]),
        "audit_rows": audit_rows,
        "counts": counts,
        "elapsed_field_counts": elapsed_counts,
        "json_array_field_counts": array_counts,
        "family_schedulable_group_counts": schedulable_groups,
        "each_family_has_schedulable_activity": False,
        "reference_runtime_build": reference_runtime,
        "runtime_build": runtime,
        "runtime_matches_reference": matches_reference,
        "runtime_build_differences": runtime_differences,
        "runtime_portability_diagnostics": stable_stats,
        "compute_runtime": source["compute_runtime"],
    }


def recompute_source_portable_audit(source_root: Path) -> dict[str, Any]:
    """Authenticate and replay all 90 rows under historical v2."""

    return _recompute_source_portable_audit(source_root, portable_version=2)


def recompute_source_portable_audit_v3(source_root: Path) -> dict[str, Any]:
    """Authenticate and replay all 90 rows under fail-closed v3."""

    return _recompute_source_portable_audit(source_root, portable_version=3)


def expected_summary(run_id: str, recomputed: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SUMMARY_SCHEMA,
        "track": TRACK,
        "run_id": run_id,
        "audit_role": "posthoc_negative_evidence_authentication",
        "source_bundle": recomputed["source_binding"],
        "normalization_contract": normalization_contract(),
        "normalization_contract_sha256": NORMALIZATION_CONTRACT_SHA256,
        "counts": recomputed["counts"],
        "elapsed_field_counts": recomputed["elapsed_field_counts"],
        "json_array_field_counts": recomputed["json_array_field_counts"],
        "family_schedulable_group_counts": recomputed["family_schedulable_group_counts"],
        "each_family_has_schedulable_activity": False,
        "row_reconstruction_complete": True,
        "audit_evidence_ok": True,
        "audit_completed": True,
        "original_result_changed": False,
        "source_experiment_completed": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "performance_claim_supported": False,
        "claim_boundary": (
            "The stored 90-row scientific fields reconstruct under the exact post-hoc "
            "normalization contract. ASCON has zero schedulable groups, so the original "
            "pre-registered family-activity gate still fails and no performance endpoint "
            "is accepted."
        ),
    }


def expected_portable_summary(
    run_id: str, recomputed: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": PORTABLE_SUMMARY_SCHEMA,
        "track": PORTABLE_TRACK,
        "run_id": run_id,
        "audit_role": "cross_build_portable_posthoc_negative_evidence_authentication",
        "source_bundle": recomputed["source_binding"],
        "portable_normalization_contract": portable_normalization_contract(),
        "portable_normalization_contract_sha256": PORTABLE_NORMALIZATION_CONTRACT_SHA256,
        "reference_runtime_build": copy.deepcopy(REFERENCE_RUNTIME_BUILD),
        "runtime_build_may_differ_from_reference": True,
        "stored_historical_floats_resigned_by_replay": False,
        "counts": recomputed["counts"],
        "elapsed_field_counts": recomputed["elapsed_field_counts"],
        "json_array_field_counts": recomputed["json_array_field_counts"],
        "family_schedulable_group_counts": recomputed[
            "family_schedulable_group_counts"
        ],
        "each_family_has_schedulable_activity": False,
        "row_reconstruction_complete": True,
        "portable_audit_evidence_ok": True,
        "audit_completed": True,
        "original_result_changed": False,
        "source_experiment_completed": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "performance_claim_supported": False,
        "claim_boundary": (
            "The immutable 90-row source is authenticated byte-for-byte. A strict "
            "discrete projection reconstructs across the recorded reference and replay "
            "PyTorch builds; only the explicit finite learned-float dependency closure "
            "uses the v2 tolerance. ASCON still has zero schedulable groups, so no "
            "accepted performance endpoint exists."
        ),
    }


def expected_portable_summary_v3(
    run_id: str, recomputed: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": PORTABLE_V3_SUMMARY_SCHEMA,
        "track": PORTABLE_V3_TRACK,
        "run_id": run_id,
        "audit_role": "cross_build_portable_posthoc_negative_evidence_authentication_v3",
        "source_bundle": recomputed["source_binding"],
        "portable_normalization_contract": portable_normalization_contract_v3(),
        "portable_normalization_contract_sha256": (
            PORTABLE_V3_NORMALIZATION_CONTRACT_SHA256
        ),
        "reference_runtime_build": copy.deepcopy(REFERENCE_RUNTIME_BUILD_V2),
        "reference_runtime_frozen_subset_sha256": _payload_sha(
            runtime_build_frozen_subset_v2(REFERENCE_RUNTIME_BUILD_V2)
        ),
        "runtime_build_may_differ_from_reference": True,
        "stored_historical_floats_resigned_by_replay": False,
        "nested_feedback_action_shas_bound_before_projection": True,
        "counts": recomputed["counts"],
        "elapsed_field_counts": recomputed["elapsed_field_counts"],
        "json_array_field_counts": recomputed["json_array_field_counts"],
        "family_schedulable_group_counts": recomputed[
            "family_schedulable_group_counts"
        ],
        "each_family_has_schedulable_activity": False,
        "row_reconstruction_complete": True,
        "portable_audit_evidence_ok": True,
        "audit_completed": True,
        "original_result_changed": False,
        "source_experiment_completed": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "performance_claim_supported": False,
        "claim_boundary": (
            "The immutable 90-row source is authenticated byte-for-byte. V3 binds "
            "both top-level and nested execution-feedback action fingerprints before "
            "portable projection, reports the complete numerical runtime frozen subset, "
            "and retains the finite v2 learned-float tolerance. ASCON still has zero "
            "schedulable groups, so no accepted performance endpoint exists."
        ),
    }


def expected_declared_verifier(run_id: str) -> dict[str, Any]:
    checks = {
        "original_bundle_hard_bound_and_unchanged": True,
        "frozen_verifier_static_and_evaluation_locks_bound": True,
        "search_plan_scheduler_reconstruction_90_of_90": True,
        "logical_semantics_native_endpoint_reconstruction_90_of_90": True,
        "exact_elapsed_and_json_array_allowlists": True,
        "family_activity_failure_preserved": True,
        "protocol_and_experiment_remain_incomplete": True,
    }
    return {
        "schema_version": DECLARED_SCHEMA,
        "run_id": run_id,
        "ok": True,
        "audit_evidence_ok": True,
        "audit_completed": True,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "independent_recomputation": False,
        "checks": checks,
    }


def expected_portable_declared_verifier(run_id: str) -> dict[str, Any]:
    checks = {
        "original_bundle_hard_bound_and_unchanged": True,
        "reference_and_runtime_builds_reported_without_equality_claim": True,
        "portable_float_allowlist_finite_and_within_tolerance": True,
        "candidate_pool_discrete_projection_exact": True,
        "selected_order_qaoa_plan_qasm_native_endpoint_exact": True,
        "portable_search_plan_scheduler_reconstruction_90_of_90": True,
        "logical_semantics_native_endpoint_reconstruction_90_of_90": True,
        "family_activity_failure_preserved": True,
        "protocol_and_experiment_remain_incomplete": True,
    }
    return {
        "schema_version": PORTABLE_DECLARED_SCHEMA,
        "run_id": run_id,
        "ok": True,
        "portable_audit_evidence_ok": True,
        "audit_completed": True,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "independent_recomputation": False,
        "checks": checks,
    }


def expected_portable_declared_verifier_v3(run_id: str) -> dict[str, Any]:
    checks = {
        "original_bundle_hard_bound_and_unchanged": True,
        "complete_runtime_frozen_subset_reported_without_equality_claim": True,
        "portable_float_allowlist_finite_and_within_tolerance": True,
        "candidate_pool_discrete_projection_exact": True,
        "top_and_nested_feedback_action_shas_bound_before_projection": True,
        "selected_order_qaoa_plan_qasm_native_endpoint_exact": True,
        "portable_search_plan_scheduler_reconstruction_90_of_90": True,
        "logical_semantics_native_endpoint_reconstruction_90_of_90": True,
        "family_activity_failure_preserved": True,
        "protocol_and_experiment_remain_incomplete": True,
    }
    return {
        "schema_version": PORTABLE_V3_DECLARED_SCHEMA,
        "run_id": run_id,
        "ok": True,
        "portable_audit_evidence_ok": True,
        "audit_completed": True,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "independent_recomputation": False,
        "checks": checks,
    }


def _fresh_rows_by_id(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(row.get("command_id")): row for row in rows}


def _fresh_stdout(row: Mapping[str, Any]) -> str:
    value = row.get("stdout")
    if not isinstance(value, Mapping) or not isinstance(value.get("text"), str):
        raise ValueError("fresh-validation stdout record is malformed")
    return str(value["text"])


def _fresh_json_stdout(row: Mapping[str, Any]) -> dict[str, Any]:
    value = json.loads(_fresh_stdout(row))
    if not isinstance(value, dict):
        raise ValueError("fresh-validation JSON stdout is not an object")
    return value


def _pytest_passed_count(text: str) -> int:
    matches = re.findall(r"(?:^|\s)(\d+) passed(?:[,\s]|$)", text)
    if not matches:
        raise ValueError("pytest passed count is absent")
    return int(matches[-1])


def expected_fresh_validation_summary(
    run_id: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    requirements_binding: Mapping[str, Any],
    scientific_bundle_binding: Mapping[str, Any],
    fresh_runtime_build: Mapping[str, Any],
) -> dict[str, Any]:
    by_id = _fresh_rows_by_id(rows)
    pip_freeze = _fresh_stdout(by_id["pip_freeze"])
    installed: dict[str, str] = {}
    for line in pip_freeze.splitlines():
        if "==" in line and not line.startswith("#"):
            name, version = line.split("==", 1)
            installed[name.strip().lower()] = version.strip()
    required_pins = {
        "numpy": "2.4.6",
        "scipy": "1.17.1",
        "pulp": "3.3.1",
        "torch": "2.12.0",
        "pytest": "9.0.3",
    }
    default_report = _fresh_json_stdout(by_id["default_clean_install"])
    portable_report = _fresh_json_stdout(by_id["portable_v3_verifier"])
    return {
        "schema_version": FRESH_VALIDATION_SUMMARY_SCHEMA,
        "track": FRESH_VALIDATION_TRACK,
        "run_id": run_id,
        "validation_role": "clean_install_cross_build_software_evidence",
        "requirements": copy.deepcopy(dict(requirements_binding)),
        "scientific_bundle": copy.deepcopy(dict(scientific_bundle_binding)),
        "fresh_runtime_build": copy.deepcopy(dict(fresh_runtime_build)),
        "fresh_runtime_frozen_subset_sha256": _payload_sha(
            runtime_build_frozen_subset_v2(fresh_runtime_build)
        ),
        "command_count": len(rows),
        "successful_command_count": sum(
            int(row.get("success") is True and row.get("exit_code") == 0)
            for row in rows
        ),
        "total_duration_seconds": sum(float(row["duration_seconds"]) for row in rows),
        "required_pins": required_pins,
        "installed_required_pins": {
            name: installed.get(name) for name in sorted(required_pins)
        },
        "pip_check_ok": "No broken requirements found." in _fresh_stdout(by_id["pip_check"]),
        "targeted_e5_passed": _pytest_passed_count(
            _fresh_stdout(by_id["targeted_e5"])
        ),
        "full_pytest_passed": _pytest_passed_count(
            _fresh_stdout(by_id["full_pytest"])
        ),
        "legacy_smoke_ok": _fresh_stdout(by_id["legacy_smoke"]).strip()
        == "smoke ok",
        "default_clean_install_ok": default_report.get("ok") is True,
        "portable_v3_verifier_ok": portable_report.get("ok") is True
        and len(portable_report.get("checks", {})) == 20
        and all(portable_report.get("checks", {}).values()),
        "portable_v3_runtime_matches_reference": portable_report.get(
            "runtime_matches_reference"
        ),
        "historical_commands_authenticated": True,
        "historical_commands_independently_rerun_by_bundle_verifier": False,
        "scientific_bundle_independently_recomputed": True,
        "software_validation_ok": True,
        "scientific_evidence": False,
        "hardware_execution": False,
        "performance_claim_supported": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "claim_boundary": (
            "This bundle authenticates historical fresh-environment software commands "
            "and independently re-verifies the linked v3 negative scientific bundle. "
            "It does not independently rerun the recorded pytest commands, validate "
            "hardware, or create an accepted performance endpoint."
        ),
    }


def expected_fresh_validation_declared_verifier(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": FRESH_VALIDATION_DECLARED_SCHEMA,
        "run_id": run_id,
        "ok": True,
        "software_validation_ok": True,
        "scientific_evidence": False,
        "independent_recomputation": False,
        "historical_commands_authenticated": True,
        "historical_commands_independently_rerun": False,
        "scientific_bundle_independently_recomputed": True,
        "protocol_acceptance": False,
        "experiment_completed": False,
    }


def _producer_source_binding() -> dict[str, str]:
    paths = {
        "producer": PROJECT_ROOT / "analysis" / "audit_e5_v11_negative_bundle.py",
        "independent_verifier": Path(__file__).resolve(),
        "contract_test": PROJECT_ROOT / "tests" / "test_e5_v11_negative_audit.py",
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def verify_negative_audit_bundle(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def check(value: bool, name: str) -> None:
        checks[name] = bool(value)
        if not value:
            errors.append(f"failed check: {name}")

    generic = verify_bundle(root, required_roles=REQUIRED_ROLES)
    check(generic.ok, "audit_artifact_manifest_and_checksums")
    check(root.is_dir() and {path.name for path in root.iterdir()} == EXPECTED_FILES, "audit_exact_nine_file_bundle")
    try:
        run = _read_json(root / "run.json")
        raw = _read_jsonl(root / "raw.jsonl")
        summary = _read_json(root / "summary.json")
        declared = _read_json(root / "verifier.json")
        events = _read_jsonl(root / "events.jsonl")
    except Exception as exc:
        return {
            "schema_version": REPORT_SCHEMA,
            "bundle": str(root),
            "ok": False,
            "audit_evidence_ok": False,
            "audit_completed": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
            "checks": checks,
            "errors": [*errors, f"cannot parse audit bundle: {type(exc).__name__}:{exc}"],
        }

    run_id = str(run.get("run_id", ""))
    check(
        bool(run_id)
        and run_id == root.name == summary.get("run_id") == declared.get("run_id"),
        "audit_run_id_consistent",
    )
    check(
        run.get("schema_version") == RUN_SCHEMA
        and run.get("track") == TRACK
        and run.get("phase") == "posthoc_negative_audit"
        and run.get("status") == "complete_negative_audit"
        and run.get("audit_evidence_ok") is True
        and run.get("audit_completed") is True
        and run.get("protocol_acceptance") is False
        and run.get("experiment_completed") is False
        and run.get("performance_claim_supported") is False
        and set(run.get("expected_artifacts", [])) == EXPECTED_FILES,
        "audit_run_schema_and_negative_boundary",
    )
    check(
        run.get("normalization_contract") == normalization_contract()
        and run.get("normalization_contract_sha256") == NORMALIZATION_CONTRACT_SHA256,
        "audit_normalization_contract_frozen",
    )
    check(
        run.get("producer_sources") == LEGACY_V1_PRODUCER_SOURCE_BINDING,
        "audit_historical_producer_sources_bound",
    )

    # The original result location is a hard-coded authority, never supplied
    # by the audit bundle or inferred from an attacker-controlled parent path.
    source_root = PROJECT_ROOT / "results" / "xa202609" / SOURCE_RUN_ID
    try:
        recomputed = recompute_source_audit(source_root)
    except Exception as exc:
        errors.append(f"independent source reconstruction failed: {type(exc).__name__}:{exc}")
        checks["original_bundle_hard_bound"] = False
        recomputed = None
    else:
        checks["original_bundle_hard_bound"] = True

    if recomputed is not None:
        check(run.get("source_bundle") == recomputed["source_binding"], "audit_run_source_binding_recomputed")
        check(raw == recomputed["audit_rows"], "audit_raw_rows_independently_recomputed")
        check(summary == expected_summary(run_id, recomputed), "audit_summary_independently_recomputed")
        check(
            recomputed["counts"]["search_plan_scheduler_reconstructed"] == 90
            and recomputed["counts"]["logical_semantics_native_endpoint_reconstructed"] == 90,
            "audit_two_reconstruction_tracks_90_of_90",
        )
        check(
            recomputed["elapsed_field_counts"] == EXPECTED_ELAPSED_COUNTS
            and recomputed["json_array_field_counts"] == EXPECTED_ARRAY_COUNTS,
            "audit_exact_allowlist_scope_counts",
        )
        check(
            recomputed["family_schedulable_group_counts"] == {"ASCON": 0, "PRESENT": 6}
            and recomputed["each_family_has_schedulable_activity"] is False,
            "audit_family_activity_failure_recomputed",
        )
    else:
        for name in (
            "audit_run_source_binding_recomputed",
            "audit_raw_rows_independently_recomputed",
            "audit_summary_independently_recomputed",
            "audit_two_reconstruction_tracks_90_of_90",
            "audit_exact_allowlist_scope_counts",
            "audit_family_activity_failure_recomputed",
        ):
            checks[name] = False

    check(declared == expected_declared_verifier(run_id), "audit_declared_verifier_nonindependent_and_exact")
    check(
        len(events) == 4
        and [event.get("event") for event in events]
        == [
            "negative_audit_started",
            "original_bundle_authenticated",
            "ninety_rows_reconstructed",
            "negative_audit_completed",
        ]
        and all(event.get("run_id") == run_id for event in events),
        "audit_event_sequence",
    )
    check(
        (root / "stdout.log").read_text(encoding="utf-8")
        == "Post-hoc negative audit completed; no evaluate run was started and no endpoint was accepted.\n"
        and (root / "stderr.log").read_text(encoding="utf-8") == "",
        "audit_terminal_logs_scope",
    )

    ok = bool(checks) and all(checks.values()) and not errors
    return {
        "schema_version": REPORT_SCHEMA,
        "bundle": str(root),
        "ok": ok,
        "audit_evidence_ok": ok,
        "audit_completed": ok,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "checks": checks,
        "errors": errors,
        "independent_recomputation": True,
        "reconstruction_counts": recomputed["counts"] if recomputed is not None else None,
        "family_schedulable_group_counts": (
            recomputed["family_schedulable_group_counts"] if recomputed is not None else None
        ),
        "compute_runtime": recomputed["compute_runtime"] if recomputed is not None else None,
    }


def verify_portable_audit_bundle(root: Path) -> dict[str, Any]:
    """Independently verify the v2 portable negative-audit bundle."""

    root = Path(root).resolve()
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def check(value: bool, name: str) -> None:
        checks[name] = bool(value)
        if not value:
            errors.append(f"failed check: {name}")

    generic = verify_bundle(root, required_roles=REQUIRED_ROLES)
    check(generic.ok, "portable_audit_artifact_manifest_and_checksums")
    check(
        root.is_dir() and {path.name for path in root.iterdir()} == EXPECTED_FILES,
        "portable_audit_exact_nine_file_bundle",
    )
    try:
        run = _read_json(root / "run.json")
        raw = _read_jsonl(root / "raw.jsonl")
        summary = _read_json(root / "summary.json")
        declared = _read_json(root / "verifier.json")
        events = _read_jsonl(root / "events.jsonl")
    except Exception as exc:
        return {
            "schema_version": PORTABLE_REPORT_SCHEMA,
            "bundle": str(root),
            "ok": False,
            "portable_audit_evidence_ok": False,
            "audit_completed": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
            "checks": checks,
            "errors": [*errors, f"cannot parse portable audit bundle: {type(exc).__name__}:{exc}"],
        }

    run_id = str(run.get("run_id", ""))
    check(
        bool(run_id)
        and run_id == root.name == summary.get("run_id") == declared.get("run_id"),
        "portable_audit_run_id_consistent",
    )
    producer_runtime = run.get("producer_runtime_build")
    check(
        run.get("schema_version") == PORTABLE_RUN_SCHEMA
        and run.get("track") == PORTABLE_TRACK
        and run.get("phase") == "portable_posthoc_negative_audit"
        and run.get("status") == "complete_portable_negative_audit"
        and run.get("portable_audit_evidence_ok") is True
        and run.get("audit_completed") is True
        and run.get("protocol_acceptance") is False
        and run.get("experiment_completed") is False
        and run.get("performance_claim_supported") is False
        and set(run.get("expected_artifacts", [])) == EXPECTED_FILES,
        "portable_audit_run_schema_and_negative_boundary",
    )
    check(
        run.get("portable_normalization_contract")
        == portable_normalization_contract()
        and run.get("portable_normalization_contract_sha256")
        == PORTABLE_NORMALIZATION_CONTRACT_SHA256,
        "portable_audit_normalization_contract_frozen",
    )
    check(
        run.get("reference_runtime_build") == REFERENCE_RUNTIME_BUILD
        and producer_runtime == REFERENCE_RUNTIME_BUILD,
        "portable_audit_reference_and_producer_builds_bound",
    )
    check(
        run.get("producer_sources") == LEGACY_V2_PRODUCER_SOURCE_BINDING,
        "portable_audit_historical_producer_sources_bound",
    )
    check(
        run.get("command_contract")
        == {
            "operation": "read_only_cross_build_portable_posthoc_negative_audit",
            "new_evaluate_started": False,
            "source_bundle_mutated": False,
            "historical_floats_resigned": False,
            "model_refit": False,
            "endpoint_reclassified": False,
        },
        "portable_audit_command_contract",
    )

    source_root = PROJECT_ROOT / "results" / "xa202609" / SOURCE_RUN_ID
    try:
        recomputed = recompute_source_portable_audit(source_root)
    except Exception as exc:
        errors.append(
            f"independent portable source reconstruction failed: {type(exc).__name__}:{exc}"
        )
        checks["portable_original_bundle_hard_bound"] = False
        recomputed = None
    else:
        checks["portable_original_bundle_hard_bound"] = True

    if recomputed is not None:
        check(
            run.get("source_bundle") == recomputed["source_binding"],
            "portable_audit_run_source_binding_recomputed",
        )
        check(
            run.get("counts") == recomputed["counts"],
            "portable_audit_run_counts_recomputed",
        )
        check(
            raw == recomputed["audit_rows"],
            "portable_audit_raw_rows_independently_recomputed",
        )
        check(
            summary == expected_portable_summary(run_id, recomputed),
            "portable_audit_summary_independently_recomputed",
        )
        check(
            recomputed["counts"]["portable_search_plan_scheduler_reconstructed"]
            == 90
            and recomputed["counts"][
                "logical_semantics_native_endpoint_reconstructed"
            ]
            == 90,
            "portable_audit_two_reconstruction_tracks_90_of_90",
        )
        check(
            recomputed["elapsed_field_counts"] == EXPECTED_ELAPSED_COUNTS
            and recomputed["json_array_field_counts"] == EXPECTED_ARRAY_COUNTS,
            "portable_audit_exact_elapsed_and_array_scope_counts",
        )
        check(
            recomputed["family_schedulable_group_counts"]
            == {"ASCON": 0, "PRESENT": 6}
            and recomputed["each_family_has_schedulable_activity"] is False,
            "portable_audit_family_activity_failure_recomputed",
        )
        check(
            recomputed["counts"]["portable_float_path_count"]
            == len(PORTABLE_FLOAT_PATHS.intersection(
                recomputed["runtime_portability_diagnostics"]["portable_float_paths"]
            ))
            and recomputed["counts"]["derived_fingerprint_path_count"]
            == len(PORTABLE_DERIVED_FINGERPRINT_PATHS),
            "portable_audit_allowlist_usage_accounted",
        )
    else:
        for name in (
            "portable_audit_run_source_binding_recomputed",
            "portable_audit_run_counts_recomputed",
            "portable_audit_raw_rows_independently_recomputed",
            "portable_audit_summary_independently_recomputed",
            "portable_audit_two_reconstruction_tracks_90_of_90",
            "portable_audit_exact_elapsed_and_array_scope_counts",
            "portable_audit_family_activity_failure_recomputed",
            "portable_audit_allowlist_usage_accounted",
        ):
            checks[name] = False

    check(
        declared == expected_portable_declared_verifier(run_id),
        "portable_audit_declared_verifier_nonindependent_and_exact",
    )
    check(
        len(events) == 4
        and [event.get("event") for event in events]
        == [
            "portable_negative_audit_started",
            "original_bundle_authenticated",
            "ninety_rows_portably_reconstructed",
            "portable_negative_audit_completed",
        ]
        and all(event.get("run_id") == run_id for event in events),
        "portable_audit_event_sequence",
    )
    check(
        (root / "stdout.log").read_text(encoding="utf-8")
        == (
            "Portable post-hoc negative audit completed; stored historical floats were "
            "not re-signed, no evaluate run was started, and no endpoint was accepted.\n"
        )
        and (root / "stderr.log").read_text(encoding="utf-8") == "",
        "portable_audit_terminal_logs_scope",
    )

    ok = bool(checks) and all(checks.values()) and not errors
    runtime = runtime_build_fingerprint()
    return {
        "schema_version": PORTABLE_REPORT_SCHEMA,
        "bundle": str(root),
        "ok": ok,
        "portable_audit_evidence_ok": ok,
        "audit_completed": ok,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "checks": checks,
        "errors": errors,
        "independent_recomputation": True,
        "reference_runtime_build": copy.deepcopy(REFERENCE_RUNTIME_BUILD),
        "runtime_build": runtime,
        "runtime_matches_reference": runtime_matches_reference(runtime),
        "runtime_portability_diagnostics": (
            recomputed["runtime_portability_diagnostics"]
            if recomputed is not None
            else None
        ),
        "reconstruction_counts": recomputed["counts"] if recomputed is not None else None,
        "family_schedulable_group_counts": (
            recomputed["family_schedulable_group_counts"]
            if recomputed is not None
            else None
        ),
        "compute_runtime": recomputed["compute_runtime"] if recomputed is not None else None,
    }


def verify_portable_audit_bundle_v3(root: Path) -> dict[str, Any]:
    """Independently verify the fail-closed v3 portable negative audit."""

    root = Path(root).resolve()
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def check(value: bool, name: str) -> None:
        checks[name] = bool(value)
        if not value:
            errors.append(f"failed check: {name}")

    generic = verify_bundle(root, required_roles=REQUIRED_ROLES)
    check(generic.ok, "portable_v3_artifact_manifest_and_checksums")
    check(
        root.is_dir() and {path.name for path in root.iterdir()} == EXPECTED_FILES,
        "portable_v3_exact_nine_file_bundle",
    )
    try:
        run = _read_json(root / "run.json")
        raw = _read_jsonl(root / "raw.jsonl")
        summary = _read_json(root / "summary.json")
        declared = _read_json(root / "verifier.json")
        events = _read_jsonl(root / "events.jsonl")
    except Exception as exc:
        return {
            "schema_version": PORTABLE_V3_REPORT_SCHEMA,
            "bundle": str(root),
            "ok": False,
            "portable_audit_evidence_ok": False,
            "audit_completed": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
            "checks": checks,
            "errors": [
                *errors,
                f"cannot parse portable v3 audit bundle: {type(exc).__name__}:{exc}",
            ],
        }

    run_id = str(run.get("run_id", ""))
    check(
        bool(run_id)
        and run_id == root.name == summary.get("run_id") == declared.get("run_id"),
        "portable_v3_run_id_consistent",
    )
    producer_runtime = run.get("producer_runtime_build")
    check(
        run.get("schema_version") == PORTABLE_V3_RUN_SCHEMA
        and run.get("track") == PORTABLE_V3_TRACK
        and run.get("phase") == "portable_posthoc_negative_audit_v3"
        and run.get("status") == "complete_portable_negative_audit_v3"
        and run.get("portable_audit_evidence_ok") is True
        and run.get("audit_completed") is True
        and run.get("protocol_acceptance") is False
        and run.get("experiment_completed") is False
        and run.get("performance_claim_supported") is False
        and set(run.get("expected_artifacts", [])) == EXPECTED_FILES,
        "portable_v3_run_schema_and_negative_boundary",
    )
    check(
        run.get("portable_normalization_contract")
        == portable_normalization_contract_v3()
        and run.get("portable_normalization_contract_sha256")
        == PORTABLE_V3_NORMALIZATION_CONTRACT_SHA256,
        "portable_v3_normalization_contract_frozen",
    )
    reference_subset_sha = _payload_sha(
        runtime_build_frozen_subset_v2(REFERENCE_RUNTIME_BUILD_V2)
    )
    check(
        bool(REFERENCE_RUNTIME_BUILD_V2)
        and runtime_build_fingerprint_valid_v2(REFERENCE_RUNTIME_BUILD_V2)
        and run.get("reference_runtime_build") == REFERENCE_RUNTIME_BUILD_V2
        and runtime_build_fingerprint_valid_v2(producer_runtime)
        and runtime_build_frozen_subset_v2(producer_runtime)
        == runtime_build_frozen_subset_v2(REFERENCE_RUNTIME_BUILD_V2)
        and run.get("reference_runtime_frozen_subset_sha256")
        == reference_subset_sha,
        "portable_v3_reference_and_producer_full_runtime_bound",
    )
    check(
        run.get("producer_sources") == _producer_source_binding(),
        "portable_v3_producer_sources_bound",
    )
    check(
        run.get("command_contract")
        == {
            "operation": "read_only_cross_build_portable_posthoc_negative_audit_v3",
            "new_evaluate_started": False,
            "source_bundle_mutated": False,
            "historical_floats_resigned": False,
            "model_refit": False,
            "endpoint_reclassified": False,
        },
        "portable_v3_command_contract",
    )

    source_root = PROJECT_ROOT / "results" / "xa202609" / SOURCE_RUN_ID
    try:
        recomputed = recompute_source_portable_audit_v3(source_root)
    except Exception as exc:
        errors.append(
            f"independent portable v3 source reconstruction failed: "
            f"{type(exc).__name__}:{exc}"
        )
        checks["portable_v3_original_bundle_hard_bound"] = False
        recomputed = None
    else:
        checks["portable_v3_original_bundle_hard_bound"] = True

    if recomputed is not None:
        check(
            run.get("source_bundle") == recomputed["source_binding"],
            "portable_v3_run_source_binding_recomputed",
        )
        check(
            run.get("counts") == recomputed["counts"],
            "portable_v3_run_counts_recomputed",
        )
        check(
            raw == recomputed["audit_rows"],
            "portable_v3_raw_rows_independently_recomputed",
        )
        check(
            summary == expected_portable_summary_v3(run_id, recomputed),
            "portable_v3_summary_independently_recomputed",
        )
        check(
            recomputed["counts"]["portable_search_plan_scheduler_reconstructed"]
            == 90
            and recomputed["counts"][
                "logical_semantics_native_endpoint_reconstructed"
            ]
            == 90,
            "portable_v3_two_reconstruction_tracks_90_of_90",
        )
        check(
            recomputed["elapsed_field_counts"] == EXPECTED_ELAPSED_COUNTS
            and recomputed["json_array_field_counts"] == EXPECTED_ARRAY_COUNTS,
            "portable_v3_exact_elapsed_and_array_scope_counts",
        )
        check(
            recomputed["family_schedulable_group_counts"]
            == {"ASCON": 0, "PRESENT": 6}
            and recomputed["each_family_has_schedulable_activity"] is False,
            "portable_v3_family_activity_failure_recomputed",
        )
        check(
            recomputed["counts"]["portable_float_path_count"]
            == len(
                PORTABLE_FLOAT_PATHS.intersection(
                    recomputed["runtime_portability_diagnostics"][
                        "portable_float_paths"
                    ]
                )
            )
            and recomputed["counts"]["derived_fingerprint_path_count"]
            == len(PORTABLE_DERIVED_FINGERPRINT_PATHS)
            and all(
                row["search_plan_scheduler_reconstruction"].get("ok") is True
                for row in recomputed["audit_rows"]
            ),
            "portable_v3_allowlists_and_nested_sha_binding_accounted",
        )
    else:
        for name in (
            "portable_v3_run_source_binding_recomputed",
            "portable_v3_run_counts_recomputed",
            "portable_v3_raw_rows_independently_recomputed",
            "portable_v3_summary_independently_recomputed",
            "portable_v3_two_reconstruction_tracks_90_of_90",
            "portable_v3_exact_elapsed_and_array_scope_counts",
            "portable_v3_family_activity_failure_recomputed",
            "portable_v3_allowlists_and_nested_sha_binding_accounted",
        ):
            checks[name] = False

    check(
        declared == expected_portable_declared_verifier_v3(run_id),
        "portable_v3_declared_verifier_nonindependent_and_exact",
    )
    check(
        len(events) == 4
        and [event.get("event") for event in events]
        == [
            "portable_negative_audit_v3_started",
            "original_bundle_authenticated",
            "ninety_rows_portably_reconstructed_v3",
            "portable_negative_audit_v3_completed",
        ]
        and all(event.get("run_id") == run_id for event in events),
        "portable_v3_event_sequence",
    )
    check(
        (root / "stdout.log").read_text(encoding="utf-8")
        == (
            "Portable post-hoc negative audit v3 completed with nested feedback SHA "
            "binding; stored historical floats were not re-signed, no evaluate run "
            "was started, and no endpoint was accepted.\n"
        )
        and (root / "stderr.log").read_text(encoding="utf-8") == "",
        "portable_v3_terminal_logs_scope",
    )

    ok = bool(checks) and len(checks) == 20 and all(checks.values()) and not errors
    runtime = runtime_build_fingerprint_v2()
    runtime_differences = runtime_build_differences_v2(
        runtime, REFERENCE_RUNTIME_BUILD_V2
    )
    return {
        "schema_version": PORTABLE_V3_REPORT_SCHEMA,
        "bundle": str(root),
        "ok": ok,
        "portable_audit_evidence_ok": ok,
        "audit_completed": ok,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "checks": checks,
        "errors": errors,
        "independent_recomputation": True,
        "reference_runtime_build": copy.deepcopy(REFERENCE_RUNTIME_BUILD_V2),
        "reference_runtime_frozen_subset_sha256": reference_subset_sha,
        "runtime_build": runtime,
        "runtime_matches_reference": not runtime_differences,
        "runtime_build_differences": runtime_differences,
        "runtime_portability_diagnostics": (
            recomputed["runtime_portability_diagnostics"]
            if recomputed is not None
            else None
        ),
        "reconstruction_counts": (
            recomputed["counts"] if recomputed is not None else None
        ),
        "family_schedulable_group_counts": (
            recomputed["family_schedulable_group_counts"]
            if recomputed is not None
            else None
        ),
        "compute_runtime": (
            recomputed["compute_runtime"] if recomputed is not None else None
        ),
    }


def verify_fresh_validation_bundle(root: Path) -> dict[str, Any]:
    """Authenticate fresh-install command evidence and independently recheck v3."""

    root = Path(root).resolve()
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def check(value: bool, name: str) -> None:
        checks[name] = bool(value)
        if not value:
            errors.append(f"failed check: {name}")

    generic = verify_bundle(root, required_roles=REQUIRED_ROLES)
    check(generic.ok, "fresh_validation_artifact_manifest_and_checksums")
    check(
        root.is_dir() and {path.name for path in root.iterdir()} == EXPECTED_FILES,
        "fresh_validation_exact_nine_file_bundle",
    )
    try:
        run = _read_json(root / "run.json")
        raw = _read_jsonl(root / "raw.jsonl")
        summary = _read_json(root / "summary.json")
        declared = _read_json(root / "verifier.json")
        events = _read_jsonl(root / "events.jsonl")
    except Exception as exc:
        return {
            "schema_version": FRESH_VALIDATION_REPORT_SCHEMA,
            "bundle": str(root),
            "ok": False,
            "software_validation_ok": False,
            "scientific_evidence": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
            "checks": checks,
            "errors": [
                *errors,
                f"cannot parse fresh-validation bundle: {type(exc).__name__}:{exc}",
            ],
        }

    run_id = str(run.get("run_id", ""))
    check(
        bool(run_id)
        and run_id == root.name == summary.get("run_id") == declared.get("run_id"),
        "fresh_validation_run_id_consistent",
    )
    check(
        run.get("schema_version") == FRESH_VALIDATION_RUN_SCHEMA
        and run.get("track") == FRESH_VALIDATION_TRACK
        and run.get("status") == "complete_fresh_validation"
        and run.get("software_validation_ok") is True
        and run.get("scientific_evidence") is False
        and run.get("hardware_execution") is False
        and run.get("performance_claim_supported") is False
        and run.get("protocol_acceptance") is False
        and run.get("experiment_completed") is False
        and set(run.get("expected_artifacts", [])) == EXPECTED_FILES,
        "fresh_validation_run_schema_and_claim_boundary",
    )
    check(
        run.get("producer_sources") == _producer_source_binding(),
        "fresh_validation_producer_sources_bound",
    )
    requirements_path = PROJECT_ROOT / "environment" / "requirements" / "dev.txt"
    requirements_binding = {
        "path": "environment/requirements/dev.txt",
        "sha256": sha256_file(requirements_path),
        "bytes": requirements_path.stat().st_size,
    }
    check(
        run.get("requirements") == requirements_binding,
        "fresh_validation_requirements_exactly_bound",
    )

    scientific_root = PROJECT_ROOT / "results" / "xa202609" / PORTABLE_V3_RUN_ID
    try:
        scientific_binding = _directory_snapshot_binding(scientific_root)
        scientific_report = verify_portable_audit_bundle_v3(scientific_root)
    except Exception as exc:
        errors.append(
            f"cannot independently verify fixed v3 scientific bundle: "
            f"{type(exc).__name__}:{exc}"
        )
        scientific_binding = None
        scientific_report = None
    check(
        scientific_binding is not None
        and run.get("scientific_bundle") == scientific_binding,
        "fresh_validation_scientific_bundle_snapshot_bound",
    )
    check(
        scientific_report is not None
        and scientific_report.get("ok") is True
        and len(scientific_report.get("checks", {})) == 20
        and all(scientific_report.get("checks", {}).values())
        and scientific_report.get("protocol_acceptance") is False
        and scientific_report.get("experiment_completed") is False,
        "fresh_validation_scientific_bundle_independently_recomputed",
    )

    expected_contract = [
        {"command_id": command_id, "argv": list(argv)}
        for command_id, argv in FRESH_VALIDATION_COMMAND_CONTRACT
    ]
    check(
        run.get("command_contract") == expected_contract,
        "fresh_validation_fixed_command_contract",
    )
    rows_valid = len(raw) == len(FRESH_VALIDATION_COMMAND_CONTRACT)
    outputs_valid = rows_valid
    if rows_valid:
        for ordinal, ((command_id, argv), row) in enumerate(
            zip(FRESH_VALIDATION_COMMAND_CONTRACT, raw)
        ):
            rows_valid = rows_valid and (
                row.get("schema_version") == FRESH_VALIDATION_ROW_SCHEMA
                and row.get("ordinal") == ordinal
                and row.get("command_id") == command_id
                and row.get("argv") == list(argv)
                and row.get("exit_code") == 0
                and row.get("success") is True
                and isinstance(row.get("duration_seconds"), (int, float))
                and not isinstance(row.get("duration_seconds"), bool)
                and math.isfinite(float(row["duration_seconds"]))
                and float(row["duration_seconds"]) >= 0.0
            )
            for stream_name in ("stdout", "stderr"):
                stream = row.get(stream_name)
                if not isinstance(stream, Mapping):
                    outputs_valid = False
                    continue
                text = stream.get("text")
                outputs_valid = outputs_valid and (
                    set(stream) == {"text", "bytes", "sha256"}
                    and isinstance(text, str)
                    and "\r" not in text
                    and stream.get("bytes") == len(text.encode("utf-8"))
                    and stream.get("sha256")
                    == hashlib.sha256(text.encode("utf-8")).hexdigest()
                )
    check(rows_valid, "fresh_validation_command_rows_exact_and_successful")
    check(outputs_valid, "fresh_validation_command_streams_hash_bound")

    fresh_runtime = run.get("fresh_runtime_build")
    runtime_valid = runtime_build_fingerprint_valid_v2(fresh_runtime)
    try:
        by_id = _fresh_rows_by_id(raw)
        portable_stdout = _fresh_json_stdout(by_id["portable_v3_verifier"])
        default_stdout = _fresh_json_stdout(by_id["default_clean_install"])
    except Exception as exc:
        errors.append(f"cannot parse recorded command reports: {type(exc).__name__}:{exc}")
        portable_stdout = {}
        default_stdout = {}
    check(
        runtime_valid
        and portable_stdout.get("schema_version") == PORTABLE_V3_REPORT_SCHEMA
        and portable_stdout.get("runtime_build") == fresh_runtime
        and portable_stdout.get("runtime_matches_reference") is False
        and run.get("fresh_runtime_matches_reference") is False,
        "fresh_validation_full_runtime_fingerprint_and_v3_stdout_bound",
    )

    try:
        expected_summary = expected_fresh_validation_summary(
            run_id,
            raw,
            requirements_binding=requirements_binding,
            scientific_bundle_binding=scientific_binding or {},
            fresh_runtime_build=fresh_runtime,
        )
        command_semantics_ok = (
            expected_summary["successful_command_count"]
            == len(FRESH_VALIDATION_COMMAND_CONTRACT)
            and expected_summary["required_pins"]
            == expected_summary["installed_required_pins"]
            and expected_summary["pip_check_ok"] is True
            and expected_summary["targeted_e5_passed"] > 0
            and expected_summary["full_pytest_passed"] > 0
            and expected_summary["legacy_smoke_ok"] is True
            and expected_summary["default_clean_install_ok"] is True
            and expected_summary["portable_v3_verifier_ok"] is True
            and default_stdout.get("ok") is True
        )
    except Exception as exc:
        errors.append(
            f"cannot recompute fresh-validation summary: {type(exc).__name__}:{exc}"
        )
        expected_summary = None
        command_semantics_ok = False
    check(command_semantics_ok, "fresh_validation_recorded_command_semantics")
    check(
        expected_summary is not None and summary == expected_summary,
        "fresh_validation_summary_recomputed_from_raw",
    )
    check(
        declared == expected_fresh_validation_declared_verifier(run_id),
        "fresh_validation_declared_verifier_exact",
    )
    check(
        len(events) == 3
        and [event.get("event") for event in events]
        == [
            "fresh_validation_started",
            "portable_v3_scientific_bundle_bound",
            "fresh_validation_completed",
        ]
        and all(event.get("run_id") == run_id for event in events),
        "fresh_validation_event_sequence",
    )
    check(
        (root / "stdout.log").read_text(encoding="utf-8")
        == (
            "Fresh-validation command evidence authenticated: 7/7 historical "
            "commands exited 0; the v3 scientific bundle was independently "
            "recomputed.\n"
        )
        and (root / "stderr.log").read_text(encoding="utf-8") == "",
        "fresh_validation_terminal_logs_scope",
    )

    ok = bool(checks) and all(checks.values()) and not errors
    return {
        "schema_version": FRESH_VALIDATION_REPORT_SCHEMA,
        "bundle": str(root),
        "ok": ok,
        "software_validation_ok": ok,
        "scientific_evidence": False,
        "historical_commands_authenticated": ok,
        "historical_commands_independently_rerun": False,
        "scientific_bundle_independently_recomputed": bool(
            checks.get("fresh_validation_scientific_bundle_independently_recomputed")
        ),
        "protocol_acceptance": False,
        "experiment_completed": False,
        "checks": checks,
        "errors": errors,
        "scientific_bundle_report": scientific_report,
        "summary": expected_summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    run_schema = None
    try:
        run_schema = _read_json(args.bundle / "run.json").get("schema_version")
    except Exception:
        pass
    if run_schema == FRESH_VALIDATION_RUN_SCHEMA:
        report = verify_fresh_validation_bundle(args.bundle)
    elif run_schema == PORTABLE_V3_RUN_SCHEMA:
        report = verify_portable_audit_bundle_v3(args.bundle)
    elif run_schema == PORTABLE_RUN_SCHEMA:
        report = verify_portable_audit_bundle(args.bundle)
    elif run_schema == RUN_SCHEMA:
        report = verify_negative_audit_bundle(args.bundle)
    else:
        report = {
            "schema_version": "xa.e5-v11-audit-unknown-schema-report.v1",
            "bundle": str(args.bundle.resolve()),
            "ok": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
            "checks": {"known_run_schema": False},
            "errors": [f"unknown or unreadable run schema: {run_schema!r}"],
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
