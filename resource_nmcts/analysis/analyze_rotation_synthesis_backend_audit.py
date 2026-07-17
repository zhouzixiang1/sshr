#!/usr/bin/env python3
"""Audit rotation-synthesis backend availability and the current sequence gap.

The phase/Rz branch deliberately stays at the logical layer.  This audit makes
the remaining rotation-synthesis boundary machine-checkable: it records whether
high-precision Clifford+T synthesis backends are available locally, summarizes
the internal source-derived sequence smoke test, and lists the tight-tolerance
targets that remain open.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

SUMMARY_OUT = RESULTS / "summary_rotation_synthesis_backend_audit.csv"
ANALYSIS_OUT = RESULTS / "analysis_rotation_synthesis_backend_audit.md"
MANIFEST_OUT = RESULTS / "manifest_rotation_synthesis_backend_audit.json"
TABLE_OUT = TABLES / "rotation_synthesis_backend_audit.tex"

SEQUENCE_MANIFEST = RESULTS / "manifest_phase_rotation_sequence_smoke_audit.json"
SEQUENCE_ROWS = RESULTS / "summary_phase_rotation_sequence_smoke_audit.csv"

FIELDS = [
    "item",
    "status",
    "availability",
    "evidence",
    "supported_claim",
    "excluded_claim",
    "next_action",
]

COMMAND_BACKENDS = ("gridsynth", "newsynth", "pgridsynth")
PYTHON_BACKENDS = ("pyzx", "qiskit", "cirq")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def command_probe() -> dict[str, str]:
    return {name: (shutil.which(name) or "") for name in COMMAND_BACKENDS}


def python_probe() -> dict[str, bool]:
    return {name: importlib.util.find_spec(name) is not None for name in PYTHON_BACKENDS}


def boolish(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "pass"}


def tight_failure_ids(rows: list[dict[str, str]]) -> list[str]:
    return [row.get("target_id", "") for row in rows if row.get("status") == "pass" and not boolish(row.get("tight_pass", ""))]


def row(
    item: str,
    status: str,
    availability: str,
    evidence: str,
    supported_claim: str,
    excluded_claim: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "item": item,
        "status": status,
        "availability": availability,
        "evidence": evidence,
        "supported_claim": supported_claim,
        "excluded_claim": excluded_claim,
        "next_action": next_action,
    }


def build_rows() -> list[dict[str, str]]:
    manifest = read_json(SEQUENCE_MANIFEST)
    seq_rows = read_csv(SEQUENCE_ROWS)
    command_paths = command_probe()
    python_modules = python_probe()
    available_commands = [name for name, path in command_paths.items() if path]
    available_modules = [name for name, ok in python_modules.items() if ok]
    failures = tight_failure_ids(seq_rows)

    smoke_pass = int(manifest.get("smoke_pass_count", -1)) if manifest else -1
    tight_pass = int(manifest.get("tight_pass_count", -1)) if manifest else -1
    total = int(manifest.get("rows", -1)) if manifest else -1
    max_error = manifest.get("max_achieved_error", "missing") if manifest else "missing"
    backend = manifest.get("backend", "missing") if manifest else "missing"
    sequence_ok = bool(manifest) and int(manifest.get("needs_revision_count", 1)) == 0 and smoke_pass >= 20

    return [
        row(
            "Internal source-derived sequence smoke",
            "pass" if sequence_ok else "needs revision",
            backend,
            f"smoke={smoke_pass}/{total}; tight={tight_pass}/{total}; max_error={max_error}",
            "The project emits and verifies concrete Clifford+T strings for source-derived Rz targets at coarse tolerance.",
            "This does not certify high-precision or optimal rotation synthesis.",
            "Rerun analyze_phase_rotation_sequence_smoke_audit.py if the sequence manifest is missing or stale.",
        ),
        row(
            "External command-line high-precision backends",
            "pass",
            "available=" + ",".join(available_commands) if available_commands else "none available",
            "; ".join(f"{name}={path or 'missing'}" for name, path in command_paths.items()),
            "The manuscript can state whether a gridsynth-style backend was actually present in this environment.",
            "Missing command-line backends mean the current package cannot claim a reproduced Ross--Selinger/gridsynth flow.",
            "Install and record a deterministic high-precision rotation synthesizer before upgrading the phase/Rz claim.",
        ),
        row(
            "Python synthesis SDK backends",
            "pass",
            "available=" + ",".join(available_modules) if available_modules else "none available",
            "; ".join(f"{name}={'available' if ok else 'missing'}" for name, ok in python_modules.items()),
            "The package records that no hidden Python SDK supplied high-precision rotation synthesis.",
            "The internal beam smoke remains the only sequence emitter unless one of these backends is added and audited.",
            "If pyzx, qiskit, or cirq is added later, bind it to a deterministic emitted-sequence verifier.",
        ),
        row(
            "Tight-tolerance diagnostic",
            "pass" if sequence_ok and len(failures) == max(0, total - tight_pass) else "needs revision",
            f"{tight_pass}/{total} tight pass",
            "tight_failed_targets=" + (",".join(failures) if failures else "none"),
            "The remaining gap is explicitly measured, not hidden behind the coarse smoke result.",
            "The phase/Rz branch is still a logical proxy and should not be used as a final Clifford+T compiler claim.",
            "Use this failure list as the target set for future high-precision synthesis work.",
        ),
    ]


def tex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )


def latex_evidence(text: str) -> str:
    if text.startswith("tight_failed_targets="):
        payload = text.split("=", 1)[1]
        count = 0 if payload == "none" else len([item for item in payload.split(",") if item])
        return f"{count} tight failures listed in CSV"
    return text.replace("max_error", "max error")


def latex_short(text: str) -> str:
    """Use readable labels in narrow LaTeX columns while preserving CSV detail."""
    return text.replace("_", " ")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Rotation-Synthesis Backend Audit",
        "",
        "This audit records the local high-precision rotation-synthesis boundary for the phase/Rz branch.",
        "",
        "## Status counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "| item | status | availability | evidence | supported claim | excluded claim |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in rows:
        lines.append(
            "| {item} | {status} | {availability} | {evidence} | {supported} | {excluded} |".format(
                item=item["item"],
                status=item["status"],
                availability=item["availability"],
                evidence=item["evidence"],
                supported=item["supported_claim"],
                excluded=item["excluded_claim"],
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.24\linewidth}>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.29\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Item & Availability & Evidence & Boundary \\",
        r"\midrule",
    ]
    for item in rows:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                tex_escape(item["item"]),
                tex_escape(latex_short(item["availability"])),
                tex_escape(latex_evidence(item["evidence"])),
                tex_escape(item["excluded_claim"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    command_paths = command_probe()
    python_modules = python_probe()
    status_counts = {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})}
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": status_counts,
        "needs_revision_count": status_counts.get("needs revision", 0),
        "command_backends": command_paths,
        "python_backends": python_modules,
        "high_precision_backend_available": any(command_paths.values()) or any(python_modules.values()),
        "sequence_manifest": "results/manifest_phase_rotation_sequence_smoke_audit.json",
        "outputs": {
            "summary": "results/summary_rotation_synthesis_backend_audit.csv",
            "analysis": "results/analysis_rotation_synthesis_backend_audit.md",
            "manifest": "results/manifest_rotation_synthesis_backend_audit.json",
            "table": "paper_latex/tables/rotation_synthesis_backend_audit.tex",
        },
        "boundary": "No official high-precision Ross--Selinger/gridsynth backend was available unless explicitly listed in command_backends or python_backends.",
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY_OUT, rows)
    write_markdown(ANALYSIS_OUT, rows)
    write_latex(TABLE_OUT, rows)
    write_manifest(MANIFEST_OUT, rows)
    revisions = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} rotation-synthesis backend audit row(s)")
    return 1 if revisions else 0


if __name__ == "__main__":
    raise SystemExit(main())
