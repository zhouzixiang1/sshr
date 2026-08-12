"""Shared provenance and bundle helpers for small XA diagnostic runners."""

from __future__ import annotations

import importlib.metadata
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.contracts.artifacts import ArtifactBundleWriter, BundleVerification, verify_bundle
from src.contracts.codec import canonical_json_bytes, canonical_json_text, sha256_bytes, sha256_file


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def source_record(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    repo_root = project_root.parent
    project_relative = project_root.relative_to(repo_root)

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()

    records = []
    for relative_root in ("src", "scripts", "tests"):
        for path in sorted((project_root / relative_root).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            records.append(
                {
                    "path": path.relative_to(project_root).as_posix(),
                    "sha256": sha256_file(path),
                }
            )
    source_pathspecs = [
        (project_relative / relative_root).as_posix()
        for relative_root in ("src", "scripts", "tests")
    ]
    dirty_status = git("status", "--porcelain=v1", "--", *source_pathspecs)
    source_tree_sha256 = sha256_bytes(canonical_json_bytes(records))
    tracked_diff = git("diff", "--binary", "HEAD", "--", *source_pathspecs)
    dirty_diff_sha256 = sha256_bytes(
        canonical_json_bytes(
            {
                "status": dirty_status.splitlines(),
                "tracked_diff": tracked_diff,
                # Untracked source files do not appear in `git diff`; binding
                # the complete source tree closes that provenance gap.
                "source_tree_sha256": source_tree_sha256,
            }
        )
    )
    return {
        "commit_sha": git("rev-parse", "HEAD"),
        "dirty": bool(dirty_status),
        "dirty_diff_sha256": dirty_diff_sha256 if dirty_status else None,
        "source_tree_sha256": source_tree_sha256,
    }


def environment_record() -> dict[str, Any]:
    versions: dict[str, str | None] = {}
    for distribution in ("numpy", "torch", "pytest", "pulp"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    torch_threads: int | None = None
    torch_interop_threads: int | None = None
    try:
        import torch

        torch_threads = int(torch.get_num_threads())
        torch_interop_threads = int(torch.get_num_interop_threads())
    except (ImportError, RuntimeError):
        pass
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "logical_cpu_count": os.cpu_count(),
        "torch_threads": torch_threads,
        "torch_interop_threads": torch_interop_threads,
        "dependencies": versions,
    }


def model_record(checkpoint: str | Path, project_root: Path) -> dict[str, str]:
    path = Path(checkpoint).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"checkpoint not found: {path}")
    project_root = project_root.resolve()
    try:
        hint = path.relative_to(project_root).as_posix()
    except ValueError:
        hint = path.name
    return {"model_id": path.stem, "path_hint": hint, "sha256": sha256_file(path)}


def dataset_sha256(dataset_without_sha: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(dataset_without_sha))


def write_pilot_bundle(
    *,
    run_dir: Path,
    run_record: dict[str, Any],
    raw_records: Iterable[dict[str, Any]],
    summary: dict[str, Any],
    verifier: dict[str, Any],
    events: Iterable[dict[str, Any]],
    track: str,
) -> BundleVerification:
    raw_list = list(raw_records)
    event_list = list(events)
    writer = ArtifactBundleWriter(run_dir)
    writer.add_json("run", "run.json", run_record)
    writer.add_text(
        "raw",
        "raw.jsonl",
        "".join(canonical_json_text(record) + "\n" for record in raw_list),
        "application/x-ndjson",
    )
    writer.add_json("summary", "summary.json", summary)
    writer.add_json("verifier", "verifier.json", verifier)
    writer.add_text(
        "events",
        "events.jsonl",
        "".join(canonical_json_text(event) + "\n" for event in event_list),
        "application/x-ndjson",
    )
    writer.add_text("stdout", "stdout.log", "")
    writer.add_text("stderr", "stderr.log", "")
    writer.finalize(bundle_metadata={"run_id": run_record["run_id"], "track": track})
    return verify_bundle(
        run_dir,
        required_roles=("run", "raw", "summary", "verifier", "events", "stdout", "stderr"),
    )
