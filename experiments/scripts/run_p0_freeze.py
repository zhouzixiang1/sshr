#!/usr/bin/env python3
"""Create the first checksum-verified XA-202609 freeze bundle.

This runner is deliberately small.  It proves the end-to-end evidence path
before expensive ablations start: deterministic Boolean inputs, the legacy and
detailed synthesis boundaries, three independent logical verifiers, explicit
source/model hashes, and a bundle that refuses overwrite or path traversal.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.anf_utils import majority_function  # noqa: E402
from src.contracts.artifacts import ArtifactBundleWriter, verify_bundle  # noqa: E402
from src.contracts.codec import canonical_json_bytes, canonical_json_text, sha256_bytes, sha256_file  # noqa: E402
from src.contracts.experiment import ExperimentManifest  # noqa: E402
from src.factor_plan import SearchConfig  # noqa: E402
from src.synthesizers import FOUNDATION_MODEL, synthesize_detailed  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _source_tree_sha256() -> str:
    records = []
    for relative_root in ("src", "scripts", "tests"):
        for path in sorted((PROJECT_ROOT / relative_root).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            records.append(
                {
                    "path": path.relative_to(PROJECT_ROOT).as_posix(),
                    "sha256": sha256_file(path),
                }
            )
    return sha256_bytes(canonical_json_bytes(records))


def _dependency_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for distribution in ("numpy", "torch", "pytest", "pulp"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    return versions


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "xa202609",
        help="parent directory for the new immutable run directory",
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--seed", type=int, default=202609)
    parser.add_argument("--model-path", type=Path, default=FOUNDATION_MODEL)
    parser.add_argument(
        "--skip-foundation",
        action="store_true",
        help="record only the deterministic direct baseline",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    created_at = _utc_now()
    run_id = args.run_id or f"p0-freeze-{created_at.replace(':', '').replace('-', '')}"
    config = SearchConfig(
        candidate_top_k=8,
        mcts_simulations=4,
        neural_mcts_simulations=4,
        max_polarities=4,
    )
    bf = majority_function(4)
    dataset_record = {
        "generator_id": "xa.p0-freeze-majority4.v1",
        "cases": [
            {
                "case_id": "majority4",
                "n_declared": bf.n,
                "truth_table_hex": f"0x{bf.truth_table:04x}",
            }
        ],
        "seeds": [args.seed],
    }
    dataset_record["dataset_sha256"] = sha256_bytes(canonical_json_bytes(dataset_record))

    model_path = args.model_path.expanduser().resolve()
    methods: list[tuple[str, str | None]] = [("direct_anf", None)]
    if not args.skip_foundation:
        if not model_path.is_file():
            raise FileNotFoundError(f"foundation checkpoint not found: {model_path}")
        methods.append(("foundation_nmcts", str(model_path)))

    started = time.time()
    detailed = [
        synthesize_detailed(method, bf, config, seed=args.seed, model_path=path)
        for method, path in methods
    ]
    elapsed = time.time() - started
    raw_records = [result.to_dict() for result in detailed]
    all_oracle_ok = all(item.verification["oracle_truth_table"]["ok"] for item in detailed)
    all_plan_ok = all(
        item.verification["plan_anf"] is None or item.verification["plan_anf"]["ok"]
        for item in detailed
    )
    all_circuit_ok = all(item.verification["circuit_anf"]["ok"] for item in detailed)

    source_status = _git(
        "status",
        "--porcelain=v1",
        "--",
        "resource_nmcts/src",
        "resource_nmcts/scripts",
        "resource_nmcts/tests",
    )
    source_record = {
        "commit_sha": _git("rev-parse", "HEAD"),
        "dirty": bool(source_status),
        "source_tree_sha256": _source_tree_sha256(),
    }
    model_record = None
    if len(methods) > 1:
        model_record = {
            "model_id": model_path.stem,
            "path_hint": (
                model_path.relative_to(PROJECT_ROOT).as_posix()
                if model_path.is_relative_to(PROJECT_ROOT)
                else model_path.name
            ),
            "sha256": sha256_file(model_path),
        }

    expected_artifacts = (
        "run.json",
        "raw.jsonl",
        "summary.json",
        "verifier.json",
        "events.jsonl",
        "stdout.log",
        "stderr.log",
        "artifacts.manifest.json",
        "checksums.sha256",
    )
    summary = {
        "schema_version": "xa.p0-freeze-summary.v1",
        "run_id": run_id,
        "case_count": 1,
        "method_count": len(detailed),
        "all_oracle_ok": all_oracle_ok,
        "all_plan_anf_ok": all_plan_ok,
        "all_circuit_anf_ok": all_circuit_ok,
        "methods": [
            {
                "method": item.requested_method,
                "score_inputs": item.summary["cost"],
                "gates": item.summary["gates"],
                "n_qubits": item.summary["n_qubits"],
            }
            for item in detailed
        ],
    }
    verifier_record = {
        "schema_version": "xa.p0-freeze-verifier.v1",
        "ok": all_oracle_ok and all_plan_ok and all_circuit_ok,
        "checks": {
            "oracle_truth_table_100_percent": all_oracle_ok,
            "plan_anf_100_percent": all_plan_ok,
            "circuit_anf_100_percent": all_circuit_ok,
            "method_count_matches": summary["method_count"] == len(raw_records),
            "dataset_sha_present": len(dataset_record["dataset_sha256"]) == 64,
            "source_sha_present": len(source_record["source_tree_sha256"]) == 64,
            "model_sha_present_or_skipped": model_record is None or len(model_record["sha256"]) == 64,
        },
    }
    verifier_record["ok"] = verifier_record["ok"] and all(verifier_record["checks"].values())
    finished_at = _utc_now()
    manifest = ExperimentManifest(
        run_id=run_id,
        track="p0-freeze",
        experiment="detailed-contract-smoke",
        status="complete" if verifier_record["ok"] else "failed",
        created_at_utc=created_at,
        source=source_record,
        environment={
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "dependencies": _dependency_versions(),
        },
        command={
            "entrypoint": "scripts/run_p0_freeze.py",
            "seed": args.seed,
            "skip_foundation": bool(args.skip_foundation),
        },
        dataset=dataset_record,
        config=asdict(config),
        model=model_record,
        variants=tuple(method for method, _ in methods),
        expected_artifacts=expected_artifacts,
        counts={"cases": 1, "methods": len(methods), "records": len(raw_records)},
        timing={"started_at_utc": created_at, "finished_at_utc": finished_at, "elapsed_s": elapsed},
        claim_boundary=(
            "This freeze bundle verifies the logical synthesis evidence path only; "
            "it does not evidence QAOA, native mapping, noise, or hardware execution."
        ),
    )

    events = [
        {"event": "run_started", "at_utc": created_at, "run_id": run_id},
        {"event": "verification_finished", "at_utc": finished_at, "ok": verifier_record["ok"]},
    ]
    writer = ArtifactBundleWriter(args.out_dir.expanduser().resolve() / run_id)
    writer.add_json("run", "run.json", manifest.to_dict())
    writer.add_text(
        "raw",
        "raw.jsonl",
        "".join(canonical_json_text(record) + "\n" for record in raw_records),
        "application/x-ndjson",
    )
    writer.add_json("summary", "summary.json", summary)
    writer.add_json("verifier", "verifier.json", verifier_record)
    writer.add_text(
        "events",
        "events.jsonl",
        "".join(canonical_json_text(event) + "\n" for event in events),
        "application/x-ndjson",
    )
    writer.add_text("stdout", "stdout.log", "")
    writer.add_text("stderr", "stderr.log", "")
    writer.finalize(bundle_metadata={"run_id": run_id, "track": "p0-freeze"})

    bundle_result = verify_bundle(
        writer.run_dir,
        required_roles=("run", "raw", "summary", "verifier", "events", "stdout", "stderr"),
    )
    if not bundle_result.ok:
        print(json.dumps({"run_id": run_id, "errors": bundle_result.errors}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "run_id": run_id,
                "bundle": writer.run_dir.as_posix(),
                "records": len(raw_records),
                "verification_ok": verifier_record["ok"],
                "bundle_ok": bundle_result.ok,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if verifier_record["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
