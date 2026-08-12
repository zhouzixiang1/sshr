#!/usr/bin/env python3
"""Run the offline XA-202609 AES Boolean-Oracle competition demo.

The demo intentionally executes a reduced all-coordinate contract smoke and
then presents AES S-box output bit 0 as the worked case.  It exercises the
equivariant learned-policy root scorer, direct shot-based QAOA scheduling,
logical semantic verification, synthetic superconducting native mapping, and
seeded noisy trajectories.  Tiny-demo numbers are never performance evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_aes_bidirectional_bundle import verify_aes_bundle  # noqa: E402
from scripts.verify_demo_output import verify_demo_output  # noqa: E402


DEMO_SCHEMA = "xa.competition-demo.v1"
DEMO_RUN_ID = "xa-demo-aes-sbox-bit0"


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


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )


def _portable_execution_log(command: list[str], stdout: str) -> str:
    """Render a reproducible log without leaking the local checkout path."""
    text = "$ " + " ".join(command) + "\n" + stdout
    return text.replace(str(PROJECT_ROOT), "${PROJECT_ROOT}")


def _selected_row(
    rows: list[dict[str, Any]], output_bit: int, variant: str
) -> dict[str, Any]:
    matches = [
        row
        for row in rows
        if row["output_bit"] == output_bit and row["variant"] == variant
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one row for bit={output_bit}, variant={variant}; "
            f"found {len(matches)}"
        )
    return matches[0]


def _build_report(
    *,
    input_record: dict[str, Any],
    run: dict[str, Any],
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    classical = _selected_row(rows, 0, "classical_greedy")
    qaoa = _selected_row(rows, 0, "qaoa_shot")
    qaoa_diag = qaoa["scheduler"]["diagnostics"]
    classical_diag = classical["scheduler"]["diagnostics"]
    classical_success = sum(
        endpoint["success_count"] for endpoint in classical["noisy_endpoints"]
    )
    qaoa_success = sum(
        endpoint["success_count"] for endpoint in qaoa["noisy_endpoints"]
    )
    classical_shots = sum(
        endpoint["shots"] for endpoint in classical["noisy_endpoints"]
    )
    qaoa_shots = sum(endpoint["shots"] for endpoint in qaoa["noisy_endpoints"])
    direct_qaoa = bool(
        qaoa["scheduler"]["qaoa_attempted"]
        and qaoa["scheduler"]["qaoa_succeeded"]
        and not qaoa["scheduler"]["qaoa_repaired"]
        and not qaoa["scheduler"]["qaoa_fallback"]
    )
    return {
        "schema_version": DEMO_SCHEMA,
        "case": input_record["case"],
        "display_coordinate": 0,
        "evidence_run_id": run["run_id"],
        "ai_for_quantum": {
            "learned_policy_active": bool(qaoa["learned_policy_active_at_root"]),
            "learned_value_enabled": bool(qaoa["learned_value_enabled"]),
            "plan_anf_ok": bool(qaoa["plan_anf_ok"]),
            "circuit_anf_ok": bool(qaoa["circuit_anf_ok"]),
            "oracle_ok": bool(qaoa["oracle_ok"]),
            "reversible_oracle_all_targets_ok": bool(
                qaoa["reversible_oracle_all_targets_ok"]
            ),
            "logical_resource_score": qaoa["logical_resource_score"],
            "logical_qasm3_sha256": qaoa["logical_qasm3_sha256"],
        },
        "quantum_for_ai": {
            "backend": summary["scope"]["qaoa_backend"],
            "direct_non_fallback": direct_qaoa,
            "candidate_count": qaoa["scheduler"]["candidate_count"],
            "budget_effective": qaoa["scheduler"]["budget_effective"],
            "classical_selected_indices": classical["scheduler"][
                "selected_indices"
            ],
            "qaoa_selected_indices": qaoa["scheduler"]["selected_indices"],
            "classical_objective": classical_diag["objective"],
            "qaoa_objective": qaoa_diag["effective_objective"],
            "exact_objective": qaoa_diag["exact_objective"],
            "objective_regret": qaoa_diag["objective_regret"],
        },
        "native_and_noise": {
            "profile": qaoa["native"]["profile_name"],
            "gate_set": qaoa["native"]["native_gate_set"],
            "native_gate_count": qaoa["native"]["native_gate_count"],
            "native_two_qubit_gate_count": qaoa["native"][
                "two_qubit_gate_count"
            ],
            "coupling_ok": bool(qaoa["native"]["coupling_ok"]),
            "actual_noisy_simulation": all(
                endpoint["actual_noisy_simulation"]
                for endpoint in qaoa["noisy_endpoints"]
            ),
            "classical_success": classical_success,
            "classical_shots": classical_shots,
            "qaoa_success": qaoa_success,
            "qaoa_shots": qaoa_shots,
            "hardware_execution": False,
        },
        "scope": {
            "tiny_contract_smoke": True,
            "performance_evidence": False,
            "full_aes_family_logically_verified": bool(
                summary["aes_family_full_domain_verified"]
            ),
            "native_equivalence": summary["scope"]["native_equivalence_scope"],
            "quantum_advantage_claimed": False,
        },
        "claim_boundary": (
            "This reduced offline demo proves the execution and verification "
            "contract only. Its numeric values are not performance evidence. "
            "The native/noisy path uses a synthetic heavy-hex-like profile and "
            "seeded simulation, not calibrated hardware; no quantum speedup or "
            "quantum-advantage claim is made."
        ),
    }


def _report_markdown(report: dict[str, Any]) -> str:
    ai = report["ai_for_quantum"]
    q4ai = report["quantum_for_ai"]
    native = report["native_and_noise"]
    semantic_ok = all(
        ai[key]
        for key in (
            "plan_anf_ok",
            "circuit_anf_ok",
            "oracle_ok",
            "reversible_oracle_all_targets_ok",
        )
    )
    return f"""# XA-202609 双向智能编译演示

## AI for Quantum

- AES S-box output bit 0 由置换等变 learned policy 实际参与根候选排序；
  learned value 明确关闭。
- Plan ANF、Circuit ANF、完整 Oracle 与 `256 × 2` 可逆语义验证：
  `{'全部通过' if semantic_ok else '未通过'}`。
- 逻辑资源分数：`{ai['logical_resource_score']:.6f}`；逻辑 QASM SHA-256：
  `{ai['logical_qasm3_sha256']}`。

## Quantum for AI

- 直接 QAOA、无 repair/fallback：
  `{'是' if q4ai['direct_non_fallback'] else '否'}`。
- 冻结候选池 `K={q4ai['candidate_count']}`、预算 `B={q4ai['budget_effective']}`；
  greedy 选择 `{q4ai['classical_selected_indices']}`，QAOA 选择
  `{q4ai['qaoa_selected_indices']}`。
- 本次 tiny smoke 的 QAOA objective / exact objective：
  `{q4ai['qaoa_objective']:.6f} / {q4ai['exact_objective']:.6f}`；regret：
  `{q4ai['objective_regret']:.6f}`。

## 原生映射与含噪执行

- profile：`{native['profile']}`；原生门集：
  `{', '.join(native['gate_set'])}`。
- 原生总门：`{native['native_gate_count']}`；双比特门：
  `{native['native_two_qubit_gate_count']}`；coupling 检查：
  `{'通过' if native['coupling_ok'] else '未通过'}`。
- classical / QAOA noisy success：`{native['classical_success']}/{native['classical_shots']}`
  与 `{native['qaoa_success']}/{native['qaoa_shots']}`。

## 结论边界

本缩小演示只证明执行与验证契约，不把 tiny 数字作为性能证据。原生/含噪路径
使用 synthetic heavy-hex-like profile 与 seeded simulation，不是真机校准；
不主张量子加速或量子优势。
"""


def _manifest(output: Path, evidence_bundle: Path) -> dict[str, Any]:
    files = []
    for name, role in (
        ("input.json", "input"),
        ("report.json", "machine_report"),
        ("report.md", "human_report"),
        ("execution.log", "execution_log"),
    ):
        path = output / name
        files.append(
            {
                "relative_path": name,
                "role": role,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "schema_version": "xa.competition-demo-manifest.v1",
        "files": files,
        "evidence_bundle": str(evidence_bundle.relative_to(output)),
        "evidence_checksums_sha256": _sha256(
            evidence_bundle / "checksums.sha256"
        ),
    }


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("aes_sbox_bit0",), required=True)
    parser.add_argument(
        "--synthesizer", choices=("foundation_nmcts",), required=True
    )
    parser.add_argument(
        "--scheduler", choices=("qaoa_diversity",), required=True
    )
    parser.add_argument(
        "--hardware", choices=("superconducting_noise",), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=930000)
    parser.add_argument(
        "--workers", type=int, default=max(1, min(4, os.cpu_count() or 1))
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    if args.seed < 0 or args.workers <= 0:
        raise ValueError("seed must be non-negative and workers must be positive")
    output = args.output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(
            f"demo output must be empty; choose a new path or clear it: {output}"
        )
    output.mkdir(parents=True, exist_ok=True)
    evidence_root = output / "evidence"
    input_record = {
        "schema_version": "xa.competition-demo-input.v1",
        "case": args.case,
        "synthesizer": args.synthesizer,
        "scheduler": args.scheduler,
        "hardware": args.hardware,
        "seed": args.seed,
        "workers": args.workers,
    }
    _write_json(output / "input.json", input_record)

    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_aes_bidirectional_pilot.py"),
        "--tiny",
        "--solver-seed",
        str(args.seed),
        "--scheduler-seed-base",
        str(args.seed),
        "--noise-seed-base",
        str(args.seed),
        "--workers",
        str(args.workers),
        "--out-dir",
        str(evidence_root),
        "--run-id",
        DEMO_RUN_ID,
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    (output / "execution.log").write_text(
        _portable_execution_log(command, completed.stdout),
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"AES demo pipeline failed with exit code {completed.returncode}; "
            f"see {output / 'execution.log'}"
        )

    evidence_bundle = evidence_root / DEMO_RUN_ID
    independent = verify_aes_bundle(evidence_bundle)
    if not independent["ok"]:
        raise RuntimeError(
            f"AES demo evidence verification failed: {independent['errors']}"
        )
    run = _json(evidence_bundle / "run.json")
    summary = _json(evidence_bundle / "summary.json")
    rows = _jsonl(evidence_bundle / "raw.jsonl")
    report = _build_report(
        input_record=input_record,
        run=run,
        summary=summary,
        rows=rows,
    )
    _write_json(output / "report.json", report)
    (output / "report.md").write_text(
        _report_markdown(report), encoding="utf-8"
    )
    manifest = _manifest(output, evidence_bundle)
    _write_json(output / "demo_manifest.json", manifest)
    checksum_names = [
        "input.json",
        "report.json",
        "report.md",
        "execution.log",
        "demo_manifest.json",
    ]
    (output / "checksums.sha256").write_text(
        "".join(f"{_sha256(output / name)}  {name}\n" for name in checksum_names),
        encoding="utf-8",
    )
    verification = verify_demo_output(output)
    _write_json(output / "verification.json", verification)
    if not verification["ok"]:
        raise RuntimeError(f"demo output verification failed: {verification['errors']}")
    print(f"demo_output={output}")
    print(f"evidence_bundle={evidence_bundle}")
    print("qaoa_direct_non_fallback=true")
    print("hardware_execution=false")
    print("performance_evidence=false")
    print("verification_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
