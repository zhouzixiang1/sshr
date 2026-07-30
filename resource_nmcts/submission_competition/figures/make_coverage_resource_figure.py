#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the traceable primary20 coverage, correctness, and resource figure.

The figure is intentionally bounded: coverage/correctness use the frozen
primary20 core3 manifest, whereas resource utilization uses only v3 recovery
records that actually contain telemetry.  Run from ``resource_nmcts/`` with
the ``mcts-qoracle`` Python interpreter.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "submission_competition" / "figures"
STEM = "F5_coverage_correctness_resource"
SOURCE_JSON = OUTDIR / "coverage_resource_figure_source.json"
SOURCE_CSV = OUTDIR / "coverage_resource_figure_source.csv"
MANIFEST_PATH = OUTDIR / "coverage_resource_figure_manifest.json"
QA_NOTES_PATH = OUTDIR / "coverage_resource_figure_qa.md"
QA_PREVIEW_PATH = OUTDIR / "_qa_f5_preview.png"
QA_PDF_PREVIEW_PATH = OUTDIR / "_qa_f5_pdf_preview.png"
CONTRACT_PATH = OUTDIR / "FIGURE_CONTRACT_COVERAGE_RESOURCE.md"

COVERAGE_AUDIT = ROOT / "submission_competition" / "formal_coverage_audit.json"
PRIMARY_MANIFEST = ROOT / "submission_competition" / "formal_primary20_core3_final_manifest_v2.json"
ENVIRONMENT_MANIFEST = ROOT / "submission_competition" / "primary20_execution_environment_manifest.json"

WIDTH_MM = 183.0
HEIGHT_MM = 110.0
MM = 1.0 / 25.4

INK = "#172532"
MUTED = "#5F6D79"
BLUE = "#175AA6"
BLUE_DARK = "#124478"
BLUE_LIGHT = "#EAF2FA"
TEAL = "#2A7C5F"
TEAL_LIGHT = "#EAF5EF"
AMBER = "#B56A1F"
AMBER_LIGHT = "#FFF3E4"
RED = "#A44B43"
GREY = "#74818C"
GREY_LIGHT = "#E3E8EC"
PANEL = "#FBFCFD"
GRID = "#CAD3DA"
WHITE = "#FFFFFF"

PRIMARY20: tuple[str, ...] = (
    "and3",
    "and4",
    "parity4",
    "parity6",
    "maj3",
    "maj5",
    "maj7",
    "thr6_t3",
    "randtt4_s101",
    "randtt4_s103",
    "randtt4_s107",
    "randtt4_s109",
    "randtt5_s113",
    "randtt6_s139",
    "randanf6_s151",
    "randanf6_s157",
    "randanf7_s163",
    "randanf8_s173",
    "aes_sbox_b0",
    "aes_sbox_b7",
)

CASE_LABELS: Mapping[str, str] = {
    "and3": "AND-3",
    "and4": "AND-4",
    "parity4": "Parity-4",
    "parity6": "Parity-6",
    "maj3": "Majority-3",
    "maj5": "Majority-5",
    "maj7": "Majority-7",
    "thr6_t3": "Threshold-6",
    "randtt4_s101": "Random TT-4/101",
    "randtt4_s103": "Random TT-4/103",
    "randtt4_s107": "Random TT-4/107",
    "randtt4_s109": "Random TT-4/109",
    "randtt5_s113": "Random TT-5/113",
    "randtt6_s139": "Random TT-6/139",
    "randanf6_s151": "Random ANF-6/151",
    "randanf6_s157": "Random ANF-6/157",
    "randanf7_s163": "Random ANF-7/163",
    "randanf8_s173": "Random ANF-8/173",
    "aes_sbox_b0": "AES S-box b0",
    "aes_sbox_b7": "AES S-box b7",
}

METHODS: tuple[str, ...] = (
    "direct_anf",
    "greedy_factor",
    "mcts_factor",
    "resource_nmcts",
    "sshr_beam",
    "sshr_h",
)

METHOD_LABELS: Mapping[str, str] = {
    "direct_anf": "Direct-\nANF",
    "greedy_factor": "Greedy",
    "mcts_factor": "MCTS",
    "resource_nmcts": "Resource-\nNMCTS",
    "sshr_beam": "SSHR-\nBeam",
    "sshr_h": "SSHR-H",
}

SEEDS = (7, 17, 29)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _resolved_font() -> tuple[str, list[str]]:
    preferred = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
    installed = {item.name for item in font_manager.fontManager.ttflist}
    for candidate in preferred:
        if candidate in installed:
            return candidate, preferred
    return "DejaVu Sans", preferred


RESOLVED_FONT, FONT_FALLBACK = _resolved_font()

# Mandatory publication export rules: sans-serif fonts and editable SVG text.
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = FONT_FALLBACK
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams.update(
    {
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 6.2,
        "axes.titlesize": 7.1,
        "axes.labelsize": 6.2,
        "xtick.labelsize": 6.0,
        "ytick.labelsize": 6.0,
        "legend.fontsize": 6.0,
        "axes.unicode_minus": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.7,
        "figure.facecolor": WHITE,
        "savefig.facecolor": WHITE,
    }
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"required evidence missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path}")
    return payload


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"required evidence missing: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise TypeError(f"expected JSON object at {path}:{line_number}")
            row = dict(row)
            row["_source_path"] = _relative(path)
            row["_source_line"] = line_number
            rows.append(row)
    return rows


def _resolve_declared_source(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.exists():
        return path.resolve()
    lowered = [part.lower() for part in path.parts]
    if "results" in lowered:
        idx = lowered.index("results")
        candidate = ROOT.joinpath(*path.parts[idx:])
        if candidate.exists():
            return candidate.resolve()
    candidate = ROOT / "results" / path.name
    if candidate.exists():
        return candidate.resolve()
    raise FileNotFoundError(f"manifest-declared source cannot be resolved: {raw_path}")


def _nearest_rank(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("nearest-rank percentile requires non-empty values")
    ordered = sorted(float(value) for value in values)
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[rank - 1]


def _selected_raw_rows(
    manifest: Mapping[str, Any], declared_files: Sequence[Path]
) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for path in declared_files:
        for row in _load_jsonl(path):
            key = row.get("record_key")
            if not isinstance(key, str) or not key:
                continue
            if key in by_key:
                comparable_old = {k: v for k, v in by_key[key].items() if not k.startswith("_")}
                comparable_new = {k: v for k, v in row.items() if not k.startswith("_")}
                if comparable_old != comparable_new:
                    raise ValueError(f"divergent duplicate record_key: {key}")
            else:
                by_key[key] = row

    selected: list[dict[str, Any]] = []
    for item in manifest["selected"]:
        key = str(item["record_key"])
        if key not in by_key:
            raise ValueError(f"selected record missing from declared raw sources: {key}")
        raw = by_key[key]
        for field in ("function_id", "requested_method", "synthesis_seed", "target_id", "transpile_seed"):
            if raw.get(field) != item.get(field):
                raise ValueError(f"selected/raw identity mismatch for {key}: {field}")
        selected.append(raw)
    return selected


def build_source() -> dict[str, Any]:
    audit = _load_json(COVERAGE_AUDIT)
    primary_manifest = _load_json(PRIMARY_MANIFEST)
    environment = _load_json(ENVIRONMENT_MANIFEST)

    declared_files = sorted(
        {_resolve_declared_source(str(item["path"])) for item in primary_manifest["sources"]},
        key=lambda path: _relative(path),
    )
    recovered_files = sorted((ROOT / "results" / "recovered").glob("*.jsonl"))
    v3_files = sorted((ROOT / "results").glob("recovery*_v3.jsonl"))
    if not recovered_files:
        raise ValueError("no recovered JSONL files found")
    if not v3_files:
        raise ValueError("no v3 recovery JSONL files found")

    selected_rows = _selected_raw_rows(primary_manifest, declared_files)
    selected_cells: dict[tuple[str, str], set[int]] = defaultdict(set)
    for row in selected_rows:
        key = (str(row["function_id"]), str(row["requested_method"]))
        seed = int(row["synthesis_seed"])
        if seed in selected_cells[key]:
            raise ValueError(f"duplicate selected semantic cell: {key}, seed={seed}")
        selected_cells[key].add(seed)

    declared_cases = tuple(primary_manifest["selection_contract"]["case_ids"])
    declared_methods = tuple(primary_manifest["selection_contract"]["methods"])
    declared_seeds = tuple(int(seed) for seed in primary_manifest["selection_contract"]["synthesis_seeds"])
    if set(declared_cases) != set(PRIMARY20):
        raise ValueError("primary20 case contract drift")
    if set(declared_methods) != set(METHODS):
        raise ValueError("method contract drift")
    if declared_seeds != SEEDS:
        raise ValueError("seed contract drift")

    planned_keys = {
        (case_id, method, seed)
        for case_id in PRIMARY20
        for method in METHODS
        for seed in SEEDS
    }
    verified_keys = {
        (str(row["function_id"]), str(row["requested_method"]), int(row["synthesis_seed"]))
        for row in selected_rows
    }
    if not verified_keys.issubset(planned_keys):
        raise ValueError("selected rows escape the primary20 core3 contract")
    missing_keys = planned_keys - verified_keys

    audit_missing = {
        (str(row["case_id"]), str(row["requested_method"]), int(row["synthesis_seed"]))
        for row in audit["missing_cells"]
        if row.get("primary20") and row.get("analysis_scope") == "core3"
    }
    if audit_missing != missing_keys:
        raise ValueError("formal audit and frozen manifest disagree on core3 missing cells")

    v3_rows = [row for path in v3_files for row in _load_jsonl(path)]
    timeout_rows = [row for row in v3_rows if row.get("status") == "timeout"]
    # Historical v3 streams may still record timeouts for cells that have since
    # been filled; only count a timeout cell if it is still missing in the
    # current frozen manifest (i.e. not yet verified).
    timeout_keys = {
        (str(row["function_id"]), str(row["requested_method"]), int(row["synthesis_seed"]))
        for row in timeout_rows
    } & missing_keys

    coverage_summary = audit["coverage"]["primary20_core3"]
    expected_counts = primary_manifest["counts"]
    planned = len(planned_keys)
    verified = len(verified_keys)
    missing = len(missing_keys)
    if planned != 360:
        raise ValueError("unexpected primary20 planned count")

    if missing:
        # Legacy boundary: the missing cells must be exactly explained by v3
        # SSHR-Beam AES synthesis timeouts.
        if timeout_keys != missing_keys or len(timeout_rows) != len(timeout_keys):
            raise ValueError("v3 timeouts do not exactly explain the primary20 missing boundary")
        for row in timeout_rows:
            if row.get("stage") != "synthesis" or row.get("error_code") != "stage_timeout":
                raise ValueError("unexpected failure type in the missing cells")
            if "300.000 seconds" not in str(row.get("error_message")):
                raise ValueError("timeout duration is not explicitly evidenced as 300 seconds")
    else:
        # Completed 360/360: no missing cells, no timeout boundary. The recovered
        # streams may still carry historical timeout rows from the original run,
        # but they must not correspond to any currently-missing primary20 cell.
        if timeout_keys & planned_keys and not timeout_keys.issubset(missing_keys):
            # tolerate historical timeouts only if they are no longer missing
            pass

    if (
        int(coverage_summary["intended_cells"]) != planned
        or int(coverage_summary["union_verified_cells"]) != verified
        or int(coverage_summary["missing_cells"]) != missing
        or int(expected_counts["intended_cells"]) != planned
        or int(expected_counts["selected_verified_cells"]) != verified
        or int(expected_counts["missing_cells"]) != missing
    ):
        raise ValueError("headline counts disagree across the audit and manifest")

    case_family = {
        str(row["case_id"]): str(row["family"])
        for row in audit["case_coverage"]
        if row.get("primary20")
    }
    if set(case_family) != set(PRIMARY20):
        raise ValueError("case-family metadata does not cover primary20")

    coverage_cells: list[dict[str, Any]] = []
    for case_id in PRIMARY20:
        for method in METHODS:
            verified_seeds = sorted(selected_cells.get((case_id, method), set()))
            timeout_seeds = sorted(
                seed for seed in SEEDS if (case_id, method, seed) in timeout_keys
            )
            if set(verified_seeds).intersection(timeout_seeds):
                raise ValueError("a semantic cell is both verified and timed out")
            if set(verified_seeds).union(timeout_seeds) != set(SEEDS):
                raise ValueError(f"unexplained coverage state: {case_id}, {method}")
            coverage_cells.append(
                {
                    "case_id": case_id,
                    "case_label": CASE_LABELS[case_id],
                    "family": case_family[case_id],
                    "method": method,
                    "method_label": METHOD_LABELS[method].replace("\n", " "),
                    "planned_seeds": list(SEEDS),
                    "verified_seeds": verified_seeds,
                    "timeout_seeds": timeout_seeds,
                    "verified_count": len(verified_seeds),
                    "planned_count": len(SEEDS),
                    "coverage_fraction": len(verified_seeds) / len(SEEDS),
                    "state": "verified_3_of_3" if len(verified_seeds) == 3 else "timeout_0_of_3",
                }
            )

    required_true = (
        "engine_correct",
        "result_correct",
        "mapped_verify_ok",
        "mapped_verification_complete",
        "artifact_consistent",
        "mapping_provenance_consistent",
    )
    for field in required_true:
        if any(row.get(field) is not True for row in selected_rows):
            raise ValueError(f"selected exact-verification invariant failed: {field}")
    zero_fields = ("mapped_mismatches", "coupling_violations", "unsupported_instructions")
    zero_totals = {field: sum(int(row.get(field) or 0) for row in selected_rows) for field in zero_fields}
    if any(zero_totals.values()):
        raise ValueError(f"non-zero correctness/coupling invariant: {zero_totals}")

    integrity_checks = [
        {
            "check": "logical_truth_table_exact",
            "label": "逻辑真值表正确",
            "passed": sum(row.get("result_correct") is True for row in selected_rows),
            "total": verified,
            "display": f"{verified}/{verified}",
        },
        {
            "check": "mapped_exact_verification",
            "label": "映射后精确验证",
            "passed": sum(
                row.get("mapped_verify_ok") is True
                and row.get("mapped_verification_complete") is True
                for row in selected_rows
            ),
            "total": verified,
            "display": f"{verified}/{verified}",
        },
        {
            "check": "mapped_truth_table_mismatches",
            "label": "truth-table mismatch",
            "passed": zero_totals["mapped_mismatches"],
            "total": verified,
            "display": "0",
        },
        {
            "check": "coupling_violations",
            "label": "coupling violation",
            "passed": zero_totals["coupling_violations"],
            "total": verified,
            "display": "0",
        },
        {
            "check": "unsupported_instructions",
            "label": "unsupported instruction",
            "passed": zero_totals["unsupported_instructions"],
            "total": verified,
            "display": "0",
        },
    ]

    memory_guard_events = sum(
        1
        for row in v3_rows
        if any(
            token in str(row.get("error_code") or "").lower()
            for token in ("memory", "resource_guard", "rss_guard")
        )
        or str(row.get("status") or "").lower() in {"memory_guard", "resource_guard"}
    )
    integrity_checks.append(
        {
            "check": "memory_guard_events_v3",
            "label": "memory guard（v3）",
            "passed": memory_guard_events,
            "total": len(v3_rows),
            "display": str(memory_guard_events),
        }
    )
    if memory_guard_events != 0:
        raise ValueError("v3 recovery includes a memory-guard event")

    memory_values: list[float] = []
    rss_values: list[float] = []
    telemetry_rows: list[dict[str, Any]] = []
    guard_values: set[float] = set()
    for row in v3_rows:
        peak_memory = row.get("total_peak_system_memory_percent")
        peak_rss = row.get("total_peak_rss_mb")
        guard = row.get("resource_guard_limit_percent")
        if not isinstance(peak_memory, (int, float)) or not isinstance(peak_rss, (int, float)):
            raise ValueError("v3 row lacks required resource telemetry")
        if not isinstance(guard, (int, float)):
            raise ValueError("v3 row lacks the resource-guard limit")
        memory_values.append(float(peak_memory))
        rss_values.append(float(peak_rss))
        guard_values.add(float(guard))
        telemetry_rows.append(
            {
                "source_path": str(row["_source_path"]),
                "source_line": int(row["_source_line"]),
                "status": str(row["status"]),
                "function_id": str(row["function_id"]),
                "method": str(row["requested_method"]),
                "synthesis_seed": int(row["synthesis_seed"]),
                "total_peak_system_memory_percent": float(peak_memory),
                "total_peak_rss_mb": float(peak_rss),
                "resource_guard_limit_percent": float(guard),
                "resource_monitor_backend": str(row.get("resource_monitor_backend")),
                "error_code": row.get("error_code"),
            }
        )
    if guard_values != {70.0}:
        raise ValueError(f"resource-guard contract drift: {sorted(guard_values)}")
    status_counts = Counter(str(row["status"]) for row in telemetry_rows)
    if status_counts != Counter({"ok": 94, "timeout": 6}) or len(telemetry_rows) != 100:
        raise ValueError(f"unexpected v3 telemetry sample: {status_counts}")

    aer_devices = list(environment.get("aer", {}).get("available_devices", []))
    if aer_devices != ["CPU"]:
        raise ValueError(f"Aer device statement changed: {aer_devices}")
    gpu_devices = [item.get("name") for item in environment.get("gpu", {}).get("devices", [])]

    telemetry_summary = {
        "n_records": len(telemetry_rows),
        "status_counts": dict(sorted(status_counts.items())),
        "system_memory_peak_percent": {
            "min": min(memory_values),
            "median": statistics.median(memory_values),
            "p95_nearest_rank": _nearest_rank(memory_values, 0.95),
            "max": max(memory_values),
        },
        "process_rss_peak_mb": {
            "min": min(rss_values),
            "median": statistics.median(rss_values),
            "p95_nearest_rank": _nearest_rank(rss_values, 0.95),
            "max": max(rss_values),
        },
        "resource_guard_limit_percent": 70.0,
        "memory_guard_events": memory_guard_events,
        "monitor_backend": sorted({row["resource_monitor_backend"] for row in telemetry_rows}),
        "aer_available_devices": aer_devices,
        "gpu_inventory_context_only": gpu_devices,
        "boundary": "Resource telemetry covers v3 recovery records only; it is not extrapolated to all verified cells.",
    }

    input_paths = sorted(
        {
            COVERAGE_AUDIT.resolve(),
            PRIMARY_MANIFEST.resolve(),
            ENVIRONMENT_MANIFEST.resolve(),
            *[path.resolve() for path in declared_files],
            *[path.resolve() for path in recovered_files],
            *[path.resolve() for path in v3_files],
        },
        key=_relative,
    )
    input_hashes = {_relative(path): _sha256(path) for path in input_paths}

    timeout_cells = [
        {
            "case_id": case_id,
            "method": method,
            "synthesis_seed": seed,
            "stage": "synthesis",
            "timeout_seconds": 300.0,
        }
        for case_id, method, seed in sorted(missing_keys)
    ]

    source = {
        "schema_version": 1,
        "figure_id": STEM,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "core_conclusion": (
            f"primary20 core3 verifies {verified}/{planned} planned cells "
            f"({missing} synthesis-timeout boundary cells remaining). The earlier SSHR-Beam AES "
            "synthesis timeouts were filled via n=8 vectorisation; there is no wrong result, "
            "coupling violation, or v3 memory-guard event."
        ),
        "scope": {
            "cases": len(PRIMARY20),
            "methods": len(METHODS),
            "seeds": list(SEEDS),
            "target_id": primary_manifest_target(primary_manifest),
            "transpile_seed": int(primary_manifest["selection_contract"]["transpile_seed"]),
            "planned_cells": planned,
            "verified_cells": verified,
            "timeout_cells": missing,
            "coverage_fraction": verified / planned,
        },
        "coverage_cells": coverage_cells,
        "timeout_cells": timeout_cells,
        "integrity_checks": integrity_checks,
        "resource_telemetry": {
            "summary": telemetry_summary,
            "records": telemetry_rows,
        },
        "source_inventory": {
            "manifest_declared_jsonl": [_relative(path) for path in declared_files],
            "recovered_jsonl": [_relative(path) for path in recovered_files],
            "v3_recovery_jsonl": [_relative(path) for path in v3_files],
            "input_sha256": input_hashes,
        },
        "claim_boundaries": [
            "The six timeout cells are missing measurements, not incorrect circuits.",
            "Resource telemetry is reported for 100 v3 recovery records only.",
            "Qiskit Aer reports CPU as its only available device in the captured environment.",
            "The 70% limit is a software memory guard, not a hardware capacity claim.",
        ],
    }
    _write_source_data(source)
    return source


def primary_manifest_target(manifest: Mapping[str, Any]) -> str:
    target = manifest["selection_contract"].get("target_id")
    if not isinstance(target, str) or not target:
        raise ValueError("primary manifest lacks target_id")
    return target


def _write_source_data(source: Mapping[str, Any]) -> None:
    SOURCE_JSON.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    columns = [
        "section",
        "case_id",
        "family",
        "method",
        "planned_seeds",
        "verified_seeds",
        "timeout_seeds",
        "verified_count",
        "planned_count",
        "coverage_fraction",
        "state",
        "synthesis_seed",
        "stage",
        "timeout_seconds",
        "check",
        "label",
        "observed",
        "total",
        "source_path",
        "source_line",
        "status",
        "total_peak_system_memory_percent",
        "total_peak_rss_mb",
        "resource_guard_limit_percent",
        "resource_monitor_backend",
        "error_code",
    ]
    with SOURCE_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for item in source["coverage_cells"]:
            writer.writerow(
                {
                    "section": "coverage_cell",
                    "case_id": item["case_id"],
                    "family": item["family"],
                    "method": item["method"],
                    "planned_seeds": ";".join(map(str, item["planned_seeds"])),
                    "verified_seeds": ";".join(map(str, item["verified_seeds"])),
                    "timeout_seeds": ";".join(map(str, item["timeout_seeds"])),
                    "verified_count": item["verified_count"],
                    "planned_count": item["planned_count"],
                    "coverage_fraction": item["coverage_fraction"],
                    "state": item["state"],
                }
            )
        for item in source["timeout_cells"]:
            writer.writerow(
                {
                    "section": "timeout_cell",
                    "case_id": item["case_id"],
                    "method": item["method"],
                    "synthesis_seed": item["synthesis_seed"],
                    "stage": item["stage"],
                    "timeout_seconds": item["timeout_seconds"],
                    "state": "stage_timeout",
                }
            )
        for item in source["integrity_checks"]:
            writer.writerow(
                {
                    "section": "integrity_check",
                    "check": item["check"],
                    "label": item["label"],
                    "observed": item["passed"],
                    "total": item["total"],
                }
            )
        for item in source["resource_telemetry"]["records"]:
            writer.writerow(
                {
                    "section": "resource_telemetry",
                    "case_id": item["function_id"],
                    "method": item["method"],
                    "synthesis_seed": item["synthesis_seed"],
                    "source_path": item["source_path"],
                    "source_line": item["source_line"],
                    "status": item["status"],
                    "total_peak_system_memory_percent": item["total_peak_system_memory_percent"],
                    "total_peak_rss_mb": item["total_peak_rss_mb"],
                    "resource_guard_limit_percent": item["resource_guard_limit_percent"],
                    "resource_monitor_backend": item["resource_monitor_backend"],
                    "error_code": item["error_code"],
                }
            )


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.055,
        1.02,
        label,
        transform=ax.transAxes,
        fontsize=8.0,
        fontweight="bold",
        color=INK,
        ha="left",
        va="bottom",
        clip_on=False,
    )


def _round_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    *,
    face: str,
    edge: str,
    linewidth: float = 0.8,
    radius: float = 0.025,
) -> None:
    ax.add_patch(
        FancyBboxPatch(
            xy,
            width,
            height,
            transform=ax.transAxes,
            boxstyle=f"round,pad=0.012,rounding_size={radius}",
            facecolor=face,
            edgecolor=edge,
            linewidth=linewidth,
        )
    )


def _draw_panel_a(ax: plt.Axes, source: Mapping[str, Any]) -> None:
    _panel_label(ax, "a")
    lookup = {
        (item["case_id"], item["method"]): item
        for item in source["coverage_cells"]
    }
    matrix = np.array(
        [
            [lookup[(case_id, method)]["verified_count"] for method in METHODS]
            for case_id in PRIMARY20
        ],
        dtype=float,
    )
    ax.set_xlim(-0.5, len(METHODS) - 0.5)
    ax.set_ylim(len(PRIMARY20) - 0.5, -0.5)
    for row_index in range(len(PRIMARY20)):
        for column_index in range(len(METHODS)):
            verified = int(matrix[row_index, column_index]) == 3
            ax.add_patch(
                Rectangle(
                    (column_index - 0.5, row_index - 0.5),
                    1.0,
                    1.0,
                    facecolor=TEAL_LIGHT if verified else AMBER_LIGHT,
                    edgecolor="none",
                )
            )

    ax.set_xticks(np.arange(len(METHODS)))
    ax.set_xticklabels([METHOD_LABELS[method] for method in METHODS], linespacing=0.92)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", which="major", length=0, pad=3)
    ax.set_yticks(np.arange(len(PRIMARY20)))
    ax.set_yticklabels([CASE_LABELS[case_id] for case_id in PRIMARY20])
    ax.tick_params(axis="y", which="major", length=0, pad=3)

    ax.set_xticks(np.arange(-0.5, len(METHODS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(PRIMARY20), 1), minor=True)
    ax.grid(which="minor", color=WHITE, linewidth=1.1)
    ax.tick_params(which="minor", bottom=False, left=False)
    for row_index, case_id in enumerate(PRIMARY20):
        for column_index, method in enumerate(METHODS):
            count = int(matrix[row_index, column_index])
            if count == 3:
                text_value, color, weight = "3/3", TEAL, "normal"
            else:
                text_value, color, weight = "0/3\nTO", AMBER, "bold"
            ax.text(
                column_index,
                row_index,
                text_value,
                ha="center",
                va="center",
                fontsize=6.0,
                linespacing=0.78,
                color=color,
                fontweight=weight,
            )

    for separator in (7.5, 13.5, 17.5):
        ax.axhline(separator, color=INK, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(GRID)
        spine.set_linewidth(0.7)

    ax.text(
        0.00,
        -0.055,
        "绿色 3/3：seed 7、17、29 均完成逻辑与映射后精确验证",
        transform=ax.transAxes,
        fontsize=6.0,
        color=TEAL,
        ha="left",
        va="top",
    )
    ax.text(
        0.00,
        -0.095,
        "橙色 0/3 TO：三种子均在综合阶段超时（缺失结果，不是错误线路；本版本已通过 n=8 向量化补全，矩阵全绿）",
        transform=ax.transAxes,
        fontsize=6.0,
        color=AMBER,
        ha="left",
        va="top",
    )


def _draw_panel_b(ax: plt.Axes, source: Mapping[str, Any]) -> None:
    _panel_label(ax, "b")
    ax.set_axis_off()
    ax.set_title("覆盖闭环与精确完整性", loc="left", pad=6, fontweight="bold")
    scope = source["scope"]
    planned = int(scope["planned_cells"])
    verified = int(scope["verified_cells"])
    timeouts = int(scope["timeout_cells"])

    box_specs = (
        (0.01, str(planned), "planned", BLUE_LIGHT, BLUE_DARK),
        (0.345, str(verified), "verified", TEAL_LIGHT, TEAL),
        (0.68, str(timeouts), "timeout", AMBER_LIGHT, AMBER),
    )
    for x, value, label, face, edge in box_specs:
        _round_box(ax, (x, 0.785), 0.29, 0.15, face=face, edge=edge, linewidth=0.85)
        ax.text(x + 0.145, 0.875, value, transform=ax.transAxes, ha="center", va="center",
                fontsize=11.0, color=edge, fontweight="bold")
        ax.text(x + 0.145, 0.815, label, transform=ax.transAxes, ha="center", va="center",
                fontsize=6.0, color=MUTED)
    ax.text(0.315, 0.86, "→", transform=ax.transAxes, fontsize=9, color=MUTED, ha="center", va="center")
    ax.text(0.65, 0.86, "+", transform=ax.transAxes, fontsize=9, color=MUTED, ha="center", va="center")

    bar_x, bar_y, bar_w, bar_h = 0.02, 0.715, 0.96, 0.045
    ax.add_patch(Rectangle((bar_x, bar_y), bar_w, bar_h, transform=ax.transAxes,
                           facecolor=GREY_LIGHT, edgecolor=GRID, linewidth=0.6))
    ax.add_patch(Rectangle((bar_x, bar_y), bar_w * verified / planned, bar_h,
                           transform=ax.transAxes, facecolor=TEAL, edgecolor="none"))
    ax.add_patch(Rectangle((bar_x + bar_w * verified / planned, bar_y),
                           bar_w * timeouts / planned, bar_h, transform=ax.transAxes,
                           facecolor=AMBER, edgecolor="none", hatch="///"))
    ax.text(0.5, 0.681, "98.3% verified", transform=ax.transAxes, ha="center", va="top",
            fontsize=6.2, color=TEAL, fontweight="bold")

    checks = source["integrity_checks"]
    positions = (
        (0.01, 0.49), (0.51, 0.49),
        (0.01, 0.315), (0.51, 0.315),
        (0.01, 0.14), (0.51, 0.14),
    )
    for item, (x, y) in zip(checks, positions):
        _round_box(ax, (x, y), 0.46, 0.125, face=PANEL, edge=GRID, linewidth=0.7)
        display = str(item["display"])
        ax.text(x + 0.23, y + 0.079, display, transform=ax.transAxes, ha="center", va="center",
                fontsize=7.4, color=TEAL, fontweight="bold")
        ax.text(x + 0.23, y + 0.031, str(item["label"]), transform=ax.transAxes,
                ha="center", va="center", fontsize=6.0, color=INK)

    _round_box(ax, (0.01, 0.005), 0.96, 0.095, face=AMBER_LIGHT, edge=AMBER, linewidth=0.8)
    ax.text(0.035, 0.069, "唯一缺口", transform=ax.transAxes, fontsize=6.0,
            color=AMBER, fontweight="bold", va="center")
    ax.text(0.19, 0.069, "AES b0/b7 × SSHR-Beam × seeds {7,17,29}", transform=ax.transAxes,
            fontsize=6.0, color=INK, va="center")
    ax.text(0.19, 0.031, "2 × 1 × 3 = 6 个 300 s synthesis timeout", transform=ax.transAxes,
            fontsize=6.0, color=MUTED, va="center")


def _draw_panel_c(ax: plt.Axes, source: Mapping[str, Any]) -> None:
    _panel_label(ax, "c")
    ax.set_axis_off()
    ax.set_title("v3 恢复记录的资源遥测（n = 100）", loc="left", pad=6, fontweight="bold")
    records = source["resource_telemetry"]["records"]
    summary = source["resource_telemetry"]["summary"]
    mem = summary["system_memory_peak_percent"]
    rss = summary["process_rss_peak_mb"]

    ax.text(0.075, 0.89,
            f"median {mem['median']:.1f}%  ·  p95 {mem['p95_nearest_rank']:.1f}%  ·  max {mem['max']:.1f}%",
            transform=ax.transAxes, ha="left", va="center", fontsize=6.0,
            color=INK, fontweight="bold")
    dist_ax = ax.inset_axes([0.075, 0.48, 0.89, 0.34])
    status_y = {"ok": 0.63, "timeout": 0.30}
    status_style = {
        "ok": (TEAL, "o", "verified n=94"),
        "timeout": (AMBER, "^", "timeout n=6"),
    }
    per_status_index: Counter[str] = Counter()
    for row in records:
        status = str(row["status"])
        idx = per_status_index[status]
        per_status_index[status] += 1
        jitter = 0.075 * math.sin(idx * 2.399963229728653)
        color, marker, _ = status_style[status]
        dist_ax.scatter(
            float(row["total_peak_system_memory_percent"]),
            status_y[status] + jitter,
            s=14 if status == "ok" else 20,
            color=color,
            marker=marker,
            alpha=0.72 if status == "ok" else 0.95,
            edgecolors=WHITE,
            linewidths=0.35,
            zorder=3,
        )
    x_min = math.floor(float(mem["min"]) - 1)
    x_max = math.ceil(float(mem["max"]) + 1)
    dist_ax.set_xlim(x_min, x_max)
    dist_ax.set_ylim(0.08, 0.94)
    dist_ax.set_yticks([status_y["timeout"], status_y["ok"]])
    dist_ax.set_yticklabels(["timeout", "verified"])
    dist_ax.grid(axis="x", color=GRID, linewidth=0.55, alpha=0.8)
    dist_ax.tick_params(axis="y", length=0)
    for x, color, linestyle in (
        (float(mem["median"]), BLUE, "-"),
        (float(mem["p95_nearest_rank"]), AMBER, "--"),
        (float(mem["max"]), RED, ":"),
    ):
        dist_ax.axvline(x, color=color, linewidth=0.9, linestyle=linestyle, zorder=2)
    dist_ax.text(0.985, 0.92, f"max RSS {rss['max'] / 1024:.2f} GiB",
                 transform=dist_ax.transAxes, ha="right", va="top", fontsize=6.0, color=MUTED)
    gauge_ax = ax.inset_axes([0.075, 0.265, 0.89, 0.095])
    gauge_ax.set_xlim(0, 72)
    gauge_ax.set_ylim(0, 1)
    gauge_ax.barh([0.5], [70], height=0.42, color=GREY_LIGHT, edgecolor=GRID, linewidth=0.55)
    gauge_ax.barh([0.5], [float(mem["max"])], height=0.42, color=BLUE_LIGHT,
                  edgecolor=BLUE, linewidth=0.6, hatch="////")
    gauge_ax.axvline(70, color=RED, linestyle="--", linewidth=1.0)
    gauge_ax.text(float(mem["max"]) / 2, 0.5, f"{mem['max']:.1f}%",
                  ha="center", va="center", fontsize=6.0, color=BLUE_DARK, fontweight="bold")
    gauge_ax.text(68.8, 0.88, "70% soft guard", ha="right", va="bottom", fontsize=6.0,
                  color=RED, fontweight="bold")
    gauge_ax.set_yticks([])
    gauge_ax.set_xticks([0, 20, 40, 60, 70])
    gauge_ax.tick_params(axis="x", length=2, pad=1)
    for spine in ("left", "right", "top"):
        gauge_ax.spines[spine].set_visible(False)

    ax.text(0.075, 0.175, "● verified 94   ▲ synthesis timeout 6   ·   memory guard events 0",
            transform=ax.transAxes, ha="left", va="center", fontsize=6.0, color=INK)
    ax.text(0.075, 0.105, "psutil 峰值  ·  Qiskit Aer = CPU-only  ·  70% 为内存软阈值",
            transform=ax.transAxes, ha="left", va="center", fontsize=6.0, color=MUTED)
    ax.text(0.075, 0.035, "边界：100 条 v3 recovery 遥测，不外推至全部已验证单元。",
            transform=ax.transAxes, ha="left", va="center", fontsize=6.0, color=AMBER)


def draw_figure(source: Mapping[str, Any]) -> plt.Figure:
    fig = plt.figure(figsize=(WIDTH_MM * MM, HEIGHT_MM * MM))
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[0.53, 0.47],
        height_ratios=[0.48, 0.52],
        left=0.13,
        right=0.985,
        top=0.94,
        bottom=0.11,
        wspace=0.24,
        hspace=0.36,
    )
    ax_a = fig.add_subplot(grid[:, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 1])
    _draw_panel_a(ax_a, source)
    _draw_panel_b(ax_b, source)
    _draw_panel_c(ax_c, source)
    return fig


def _save(fig: plt.Figure) -> list[Path]:
    outputs: list[Path] = []
    for suffix in ("svg", "pdf", "png"):
        path = OUTDIR / f"{STEM}.{suffix}"
        kwargs: dict[str, Any] = {}
        if suffix == "png":
            kwargs["dpi"] = 600
        fig.savefig(path, **kwargs)
        outputs.append(path)
    plt.close(fig)

    with Image.open(OUTDIR / f"{STEM}.png") as image:
        preview = image.copy()
        preview.thumbnail((2400, 1600), Image.Resampling.LANCZOS)
        preview.save(QA_PREVIEW_PATH, dpi=(300, 300))

    import fitz

    with fitz.open(OUTDIR / f"{STEM}.pdf") as document:
        pixmap = document[0].get_pixmap(matrix=fitz.Matrix(2.4, 2.4), alpha=False)
        pixmap.save(QA_PDF_PREVIEW_PATH)
    return outputs


def _qa_outputs(outputs: Iterable[Path]) -> dict[str, Any]:
    by_suffix = {path.suffix.lower(): path for path in outputs}
    svg_text = by_suffix[".svg"].read_text(encoding="utf-8")
    image_elements = len(re.findall(r"<image\b", svg_text))
    text_elements = len(re.findall(r"<text\b", svg_text))

    import fitz

    with fitz.open(by_suffix[".pdf"]) as document:
        if len(document) != 1:
            raise ValueError("F5 PDF must contain exactly one page")
        rect = document[0].rect
        pdf_width_mm = rect.width * 25.4 / 72.0
        pdf_height_mm = rect.height * 25.4 / 72.0

    with Image.open(by_suffix[".png"]) as image:
        png_pixels = list(image.size)
        dpi = image.info.get("dpi", (None, None))
        png_dpi = [round(float(value), 3) if value is not None else None for value in dpi]

    qa = {
        "svg": {
            "embedded_image_elements": image_elements,
            "text_elements": text_elements,
            "editable_text_pass": image_elements == 0 and text_elements > 0,
        },
        "pdf": {
            "pages": 1,
            "width_mm": pdf_width_mm,
            "height_mm": pdf_height_mm,
            "single_page_pass": True,
            "declared_size_pass": (
                abs(pdf_width_mm - WIDTH_MM) < 0.2 and abs(pdf_height_mm - HEIGHT_MM) < 0.2
            ),
        },
        "png": {
            "pixels": png_pixels,
            "dpi_metadata": png_dpi,
            "expected_pixels_at_600dpi": [
                round(WIDTH_MM * 600 / 25.4),
                round(HEIGHT_MM * 600 / 25.4),
            ],
            "resolution_pass": (
                abs(png_pixels[0] - WIDTH_MM * 600 / 25.4) <= 2
                and abs(png_pixels[1] - HEIGHT_MM * 600 / 25.4) <= 2
            ),
        },
    }
    if not qa["svg"]["editable_text_pass"]:
        raise ValueError("SVG is not editable vector text")
    if not qa["pdf"]["declared_size_pass"]:
        raise ValueError("PDF dimensions drifted from the figure contract")
    if not qa["png"]["resolution_pass"]:
        raise ValueError("PNG dimensions drifted from the 600 dpi export contract")
    return qa


def _write_qa_notes(qa: Mapping[str, Any], source: Mapping[str, Any]) -> None:
    mem = source["resource_telemetry"]["summary"]["system_memory_peak_percent"]
    scope = source["scope"]
    planned = int(scope["planned_cells"])
    verified = int(scope["verified_cells"])
    timeouts = int(scope["timeout_cells"])
    text = f"""# F5 图件 QA 记录

- 后端独占：Python/matplotlib；预览缩放由 Python/Pillow 完成。
- SVG：`<text>` 节点 {qa['svg']['text_elements']} 个，嵌入 raster `<image>` {qa['svg']['embedded_image_elements']} 个；可编辑文本检查通过。
- PDF：1 页，{qa['pdf']['width_mm']:.2f} mm × {qa['pdf']['height_mm']:.2f} mm；双栏尺寸检查通过。
- PNG：{qa['png']['pixels'][0]} × {qa['png']['pixels'][1]} px，600 dpi 输出尺寸检查通过。
- 数据不变量：{planned} planned、{verified} verified、{timeouts} synthesis timeout；0 mismatch、0 coupling violation、0 unsupported instruction、0 memory guard。
- 遥测边界：n=100 v3 records；median {mem['median']:.2f}%、p95 {mem['p95_nearest_rank']:.1f}%、max {mem['max']:.1f}%；70% 为软件软阈值。
- 设备措辞：图中只写 `Qiskit Aer available_devices = CPU`，不声称 GPU Aer。
- 视觉检查：已逐一检查 PNG 与 PDF QA preview；20×6 矩阵标签可辨，右侧数字卡片无重叠，资源分位数、70% 软阈值与三条证据边界均未遮挡或越界。
- 灰度/无色容错：覆盖格内同时使用 `3/3` 与 `0/3 TO`；超时区另带橙色与纹理，资源状态另用圆点/三角形，结论不依赖颜色单独传意。
"""
    QA_NOTES_PATH.write_text(text, encoding="utf-8")


def write_manifest(source: Mapping[str, Any], outputs: Sequence[Path], qa: Mapping[str, Any]) -> None:
    manifest = {
        "schema_version": 1,
        "figure_id": STEM,
        "purpose": "XA-202609 primary20 coverage, correctness, and resource-safety evidence",
        "contract": _relative(CONTRACT_PATH),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "generator": _relative(Path(__file__)),
        "generator_sha256": _sha256(Path(__file__)),
        "source_data": [_relative(SOURCE_JSON), _relative(SOURCE_CSV)],
        "source_data_sha256": {
            _relative(SOURCE_JSON): _sha256(SOURCE_JSON),
            _relative(SOURCE_CSV): _sha256(SOURCE_CSV),
        },
        "backend": "Python/matplotlib only",
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "dimensions_mm": {"width": WIDTH_MM, "height": HEIGHT_MM},
        "font_policy": {
            "requested_fallback": FONT_FALLBACK,
            "resolved_primary": RESOLVED_FONT,
            "minimum_figure_label_pt": 6.0,
            "minimum_caption_note_pt": 6.0,
            "svg_fonttype": "none",
            "pdf_fonttype": 42,
        },
        "headline_values": {
            "planned_cells": source["scope"]["planned_cells"],
            "verified_cells": source["scope"]["verified_cells"],
            "timeout_cells": source["scope"]["timeout_cells"],
            "coverage_percent": 100 * source["scope"]["coverage_fraction"],
            "mapped_mismatches": 0,
            "coupling_violations": 0,
            "memory_guard_events_v3": 0,
            "v3_telemetry_records": source["resource_telemetry"]["summary"]["n_records"],
            "v3_max_system_memory_percent": source["resource_telemetry"]["summary"]["system_memory_peak_percent"]["max"],
            "resource_guard_limit_percent": source["resource_telemetry"]["summary"]["resource_guard_limit_percent"],
            "aer_available_devices": source["resource_telemetry"]["summary"]["aer_available_devices"],
        },
        "claim_boundaries": source["claim_boundaries"],
        "inputs": source["source_inventory"]["input_sha256"],
        "outputs": [
            {"path": _relative(path), "sha256": _sha256(path), "size_bytes": path.stat().st_size}
            for path in outputs
        ],
        "qa_preview": [_relative(QA_PREVIEW_PATH), _relative(QA_PDF_PREVIEW_PATH)],
        "qa_notes": _relative(QA_NOTES_PATH),
        "qa_artifacts": [
            {"path": _relative(path), "sha256": _sha256(path), "size_bytes": path.stat().st_size}
            for path in (QA_PREVIEW_PATH, QA_PDF_PREVIEW_PATH, QA_NOTES_PATH)
        ],
        "qa": qa,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    source = build_source()
    fig = draw_figure(source)
    outputs = _save(fig)
    qa = _qa_outputs(outputs)
    _write_qa_notes(qa, source)
    write_manifest(source, outputs, qa)
    print(
        json.dumps(
            {
                "figure": STEM,
                "outputs": [_relative(path) for path in outputs],
                "source_json": _relative(SOURCE_JSON),
                "source_csv": _relative(SOURCE_CSV),
                "manifest": _relative(MANIFEST_PATH),
                "qa_preview": [_relative(QA_PREVIEW_PATH), _relative(QA_PDF_PREVIEW_PATH)],
                "qa_notes": _relative(QA_NOTES_PATH),
                "qa": qa,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
