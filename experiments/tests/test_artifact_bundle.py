"""Integrity, path-safety and overwrite tests for XA evidence bundles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.artifacts import ArtifactBundleWriter, verify_bundle


def _bundle(path: Path) -> Path:
    writer = ArtifactBundleWriter(path)
    writer.add_json("run", "run.json", {"run_id": "tiny", "seed": 7})
    writer.add_text("raw", "raw/events.jsonl", '{"value":1}\n')
    writer.finalize(bundle_metadata={"track": "p0-freeze"})
    return path


def test_bundle_roundtrip_and_manifest_are_verified(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path / "tiny")
    result = verify_bundle(bundle, required_roles=("run", "raw"))

    assert result.ok, result.errors
    assert {ref.role for ref in result.artifacts} == {"run", "raw"}
    manifest = json.loads((bundle / "artifacts.manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "xa.artifact-bundle.v1"
    assert [item["relative_path"] for item in manifest["artifacts"]] == [
        "raw/events.jsonl",
        "run.json",
    ]


def test_bundle_detects_tampering_and_unlisted_files(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path / "tiny")
    (bundle / "run.json").write_text("{}\n", encoding="utf-8")
    result = verify_bundle(bundle)
    assert not result.ok
    assert any("mismatch" in error for error in result.errors)

    extra = bundle / "surprise.txt"
    extra.write_text("unlisted", encoding="utf-8")
    result = verify_bundle(bundle)
    assert any("unlisted artifact files" in error for error in result.errors)


@pytest.mark.parametrize("unsafe", ["/absolute.json", "../escape.json", "a/../b.json", "a\\b.json"])
def test_bundle_rejects_unsafe_paths(tmp_path: Path, unsafe: str) -> None:
    writer = ArtifactBundleWriter(tmp_path / unsafe.replace("/", "_").replace("\\", "_"))
    with pytest.raises(ValueError):
        writer.add_json("unsafe", unsafe, {})


def test_bundle_rejects_duplicate_roles_paths_and_overwrite(tmp_path: Path) -> None:
    bundle = tmp_path / "tiny"
    writer = ArtifactBundleWriter(bundle)
    writer.add_json("run", "run.json", {})
    with pytest.raises(ValueError, match="duplicate artifact role"):
        writer.add_json("run", "other.json", {})
    with pytest.raises(ValueError, match="duplicate artifact path"):
        writer.add_json("other", "run.json", {})
    writer.finalize()

    with pytest.raises(FileExistsError):
        ArtifactBundleWriter(bundle)
