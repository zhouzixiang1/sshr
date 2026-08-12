#!/usr/bin/env python3
"""Independently verify an XA-202609 competition-demo output directory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_aes_bidirectional_bundle import verify_aes_bundle  # noqa: E402


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_outer_checksums(root: Path) -> bool:
    for line in (root / "checksums.sha256").read_text(
        encoding="utf-8"
    ).splitlines():
        expected, relative = line.split("  ", 1)
        path = (root / relative).resolve()
        path.relative_to(root)
        if not path.is_file() or _sha256(path) != expected:
            return False
    return True


def verify_demo_output(output: str | Path) -> dict[str, Any]:
    root = Path(output).expanduser().resolve()
    errors: list[str] = []
    required = {
        "input.json",
        "report.json",
        "report.md",
        "execution.log",
        "demo_manifest.json",
        "checksums.sha256",
    }
    if not root.is_dir():
        return {"schema_version": "xa.competition-demo-verifier.v1", "ok": False,
                "checks": {}, "errors": [f"not a directory: {root}"]}
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        return {"schema_version": "xa.competition-demo-verifier.v1", "ok": False,
                "checks": {}, "errors": [f"missing files: {missing}"]}

    try:
        input_record = _json(root / "input.json")
        report = _json(root / "report.json")
        manifest = _json(root / "demo_manifest.json")
        evidence = (root / manifest["evidence_bundle"]).resolve()
        evidence.relative_to(root)
        run = _json(evidence / "run.json")
        summary = _json(evidence / "summary.json")
        rows = _jsonl(evidence / "raw.jsonl")
        evidence_verification = verify_aes_bundle(evidence)
    except Exception as exc:
        return {"schema_version": "xa.competition-demo-verifier.v1", "ok": False,
                "checks": {}, "errors": [f"read/parse failure: {exc}"]}

    bit0 = {
        row["variant"]: row
        for row in rows
        if row["output_bit"] == 0
    }
    qaoa = bit0.get("qaoa_shot")
    classical = bit0.get("classical_greedy")
    qaoa_direct = bool(
        qaoa
        and qaoa["scheduler"]["qaoa_attempted"]
        and qaoa["scheduler"]["qaoa_succeeded"]
        and not qaoa["scheduler"]["qaoa_repaired"]
        and not qaoa["scheduler"]["qaoa_fallback"]
    )
    qaoa_success = (
        sum(endpoint["success_count"] for endpoint in qaoa["noisy_endpoints"])
        if qaoa else None
    )
    classical_success = (
        sum(endpoint["success_count"] for endpoint in classical["noisy_endpoints"])
        if classical else None
    )
    try:
        checks = {
            "outer_checksums": _check_outer_checksums(root),
            "manifest_file_hashes": all(
                _sha256(root / item["relative_path"]) == item["sha256"]
                and (root / item["relative_path"]).stat().st_size
                == item["size_bytes"]
                for item in manifest["files"]
            ),
            "evidence_checksums_bound": _sha256(evidence / "checksums.sha256")
            == manifest["evidence_checksums_sha256"],
            "evidence_bundle_verified": bool(evidence_verification["ok"]),
            "input_contract": input_record == {
                "schema_version": "xa.competition-demo-input.v1",
                "case": "aes_sbox_bit0",
                "synthesizer": "foundation_nmcts",
                "scheduler": "qaoa_diversity",
                "hardware": "superconducting_noise",
                "seed": input_record["seed"],
                "workers": input_record["workers"],
            }
            and input_record["seed"] >= 0
            and input_record["workers"] > 0,
            "tiny_nonperformance_scope": summary["scope"]["tiny"] is True
            and summary["scope"]["performance_evidence"] is False
            and report["scope"]["performance_evidence"] is False,
            "full_aes_logical_contract": len(rows) == 16
            and summary["aes_family_full_domain_verified"]
            and all(
                row["plan_anf_ok"]
                and row["circuit_anf_ok"]
                and row["oracle_ok"]
                and row["reversible_oracle_all_targets_ok"]
                for row in rows
            ),
            "qaoa_direct_non_fallback": qaoa_direct
            and report["quantum_for_ai"]["direct_non_fallback"] is True,
            "report_matches_scheduler": bool(qaoa and classical)
            and report["quantum_for_ai"]["qaoa_selected_indices"]
            == qaoa["scheduler"]["selected_indices"]
            and report["quantum_for_ai"]["classical_selected_indices"]
            == classical["scheduler"]["selected_indices"]
            and report["quantum_for_ai"]["objective_regret"]
            == qaoa["scheduler"]["diagnostics"]["objective_regret"],
            "report_matches_native_and_noise": bool(qaoa and classical)
            and report["native_and_noise"]["native_gate_count"]
            == qaoa["native"]["native_gate_count"]
            and report["native_and_noise"]["native_two_qubit_gate_count"]
            == qaoa["native"]["two_qubit_gate_count"]
            and report["native_and_noise"]["qaoa_success"] == qaoa_success
            and report["native_and_noise"]["classical_success"]
            == classical_success,
            "actual_noisy_simulation_not_hardware": all(
                endpoint["actual_noisy_simulation"]
                and endpoint["hardware_execution"] is False
                and endpoint["task_contract_ok"]
                for row in rows
                for endpoint in row["noisy_endpoints"]
            )
            and report["native_and_noise"]["hardware_execution"] is False,
            "no_advantage_claim": report["scope"]["quantum_advantage_claimed"]
            is False
            and summary["scope"]["quantum_advantage_claimed"] is False
            and "not performance evidence" in report["claim_boundary"],
            "run_identity": report["evidence_run_id"] == run["run_id"],
        }
    except Exception as exc:
        errors.append(f"contract evaluation failure: {exc}")
        checks = {}
    for name, passed in checks.items():
        if not passed:
            errors.append(f"check failed: {name}")
    return {
        "schema_version": "xa.competition-demo-verifier.v1",
        "checks": checks,
        "errors": errors,
        "ok": bool(checks) and all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = verify_demo_output(args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
