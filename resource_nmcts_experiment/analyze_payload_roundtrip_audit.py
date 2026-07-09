#!/usr/bin/env python3
"""Round-trip audit for the deterministic submission payload archive.

This terminal audit opens the generated tarball, checks that the payload
manifest and archive contents agree, verifies every archived file hash, rejects
unsafe or private paths, and confirms deterministic tar metadata.  It does not
modify the payload archive.
"""
from __future__ import annotations

import csv
import json
import sys
import tarfile
from pathlib import Path

from make_submission_payload_archive import ARCHIVE, PAYLOAD_ROOT, THIS_DIR


RESULTS = THIS_DIR / "results"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"
PRIVATE_BASENAMES = {
    "submission_metadata.json",
    "generated_author_declarations.md",
    "generated_availability_statements.md",
    "generated_cover_letter.md",
    "generated_submission_text.md",
}
REQUIRED_PAYLOAD_PATHS = {
    "paper_latex/resource_nmcts_submission_v1.tex",
    "paper_latex/resource_nmcts_submission_v1.pdf",
    "paper_latex/resource_nmcts_submission_anonymous.tex",
    "paper_latex/resource_nmcts_submission_anonymous.pdf",
    "paper_latex/references.bib",
    "rebuild_submission_package.sh",
    "verify_submission_package.sh",
    "submission_package/README.md",
    "submission_package/AUTHOR_INPUT_REQUIRED.md",
    "submission_package/submission_checklist.md",
    "results/analysis_submission_archive_manifest.md",
    "results/analysis_submission_traceability_audit.md",
}
REVIEWER_ENTRYPOINT_PATHS = {
    "submission_package/artifact_reproduction_guide.md",
    "submission_package/editor_screening_brief.md",
    "submission_package/reviewer_concern_brief.md",
    "submission_package/target_venue_brief.md",
    "results/analysis_artifact_rerun_registry.md",
    "results/analysis_reproducibility_audit.md",
    "results/analysis_figure_asset_audit.md",
}
COMPARISON_PROTOCOL_PATHS = {
    "analyze_comparison_protocol_audit.py",
    "results/analysis_comparison_protocol_audit.md",
    "results/summary_comparison_protocol_audit.csv",
    "results/manifest_comparison_protocol_audit.json",
    "results/analysis_baseline_claim_matrix.md",
    "results/analysis_comparison_evidence_matrix.md",
    "results/analysis_baseline_comparability_audit.md",
    "results/analysis_counterpoint_claim_boundary.md",
    "results/analysis_paired_statistical_evidence.md",
    "results/analysis_multimetric_pareto_tradeoff.md",
}
HEADLINE_NUMERIC_PATHS = {
    "analyze_headline_numeric_consistency.py",
    "results/analysis_headline_numeric_consistency.md",
    "results/summary_headline_numeric_consistency.csv",
    "results/manifest_headline_numeric_consistency.json",
}
CITATION_SUPPORT_PATHS = {
    "analyze_citation_support_audit.py",
    "results/analysis_citation_support_audit.md",
    "results/summary_citation_support_audit.csv",
    "results/manifest_citation_support_audit.json",
}
AUTHOR_INPUT_CLOSURE_PATHS = {
    "analyze_author_input_closure_audit.py",
    "results/analysis_author_input_closure_audit.md",
    "results/summary_author_input_closure_audit.csv",
    "results/manifest_author_input_closure_audit.json",
}
SOURCE_PATH_PRIVACY_PATHS = {
    "analyze_source_path_privacy_audit.py",
}
PAYLOAD_EXTRACTION_SMOKE_PATHS = {
    "analyze_payload_extraction_smoke_audit.py",
}
PAYLOAD_VERIFIER_SMOKE_PATHS = {
    "analyze_payload_verifier_smoke_audit.py",
}


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def safe_payload_path(path: str) -> bool:
    if path.startswith("/") or path.startswith("../") or "/../" in path:
        return False
    if path == "." or path.endswith("/"):
        return False
    parts = path.split("/")
    return "__MACOSX" not in parts and ".DS_Store" not in parts


def load_archive_members() -> tuple[list[tarfile.TarInfo], dict[str, bytes], str]:
    if not ARCHIVE.exists():
        return [], {}, "archive missing"
    try:
        members: list[tarfile.TarInfo] = []
        payload: dict[str, bytes] = {}
        with tarfile.open(ARCHIVE, "r:gz") as tar:
            for member in tar.getmembers():
                members.append(member)
                if not member.isfile():
                    continue
                extracted = tar.extractfile(member)
                payload[member.name] = extracted.read() if extracted is not None else b""
        return members, payload, ""
    except Exception as exc:
        return [], {}, f"{type(exc).__name__}: {exc}"


def build_rows() -> list[dict[str, str]]:
    manifest = read_json(PAYLOAD_MANIFEST)
    manifest_files = manifest.get("files", []) if manifest else []
    members, payload, archive_error = load_archive_members()
    rows: list[dict[str, str]] = []

    rows.append(
        row(
            "Payload archive readable",
            "pass" if not archive_error and members else "needs revision",
            f"archive={rel(ARCHIVE)}; members={len(members)}; error={archive_error or 'none'}.",
            "Regenerate the payload archive if it cannot be opened by Python tarfile.",
        )
    )

    archive_paths = sorted(path.removeprefix(f"{PAYLOAD_ROOT}/") for path in payload if path.startswith(f"{PAYLOAD_ROOT}/"))
    manifest_paths: list[str] = []
    manifest_sha: dict[str, str] = {}
    if isinstance(manifest_files, list):
        for item in manifest_files:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", ""))
            manifest_paths.append(path)
            manifest_sha[path] = str(item.get("sha256", ""))
    manifest_paths = sorted(manifest_paths)

    missing_from_archive = sorted(set(manifest_paths) - set(archive_paths))
    extra_in_archive = sorted(set(archive_paths) - set(manifest_paths))
    rows.append(
        row(
            "Payload manifest round-trip",
            "pass" if manifest and not missing_from_archive and not extra_in_archive else "needs revision",
            f"manifest_files={len(manifest_paths)}; archive_files={len(archive_paths)}; missing={missing_from_archive[:5] or 'none'}; extra={extra_in_archive[:5] or 'none'}.",
            "Regenerate make_submission_payload_archive.py outputs if manifest and archive contents diverge.",
        )
    )

    import hashlib

    mismatches: list[str] = []
    for path in manifest_paths:
        data = payload.get(f"{PAYLOAD_ROOT}/{path}")
        if data is None:
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest != manifest_sha.get(path):
            mismatches.append(path)
    rows.append(
        row(
            "Payload per-file SHA256",
            "pass" if not mismatches else "needs revision",
            f"checked={len(manifest_paths) - len(missing_from_archive)}; mismatches={mismatches[:5] or 'none'}.",
            "Regenerate the payload archive and manifest if any archived file digest differs from the manifest.",
        )
    )

    unsafe = sorted(name for name in payload if not name.startswith(f"{PAYLOAD_ROOT}/") or not safe_payload_path(name.removeprefix(f"{PAYLOAD_ROOT}/")))
    private_hits = sorted(path for path in archive_paths if Path(path).name in PRIVATE_BASENAMES)
    rows.append(
        row(
            "Payload path hygiene",
            "pass" if not unsafe and not private_hits else "needs revision",
            f"unsafe_paths={unsafe[:5] or 'none'}; private_hits={private_hits or 'none'}.",
            "Remove unsafe, platform-generated, or private files from the payload inputs.",
        )
    )

    required_missing = sorted(REQUIRED_PAYLOAD_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload required artifacts",
            "pass" if not required_missing else "needs revision",
            f"required={len(REQUIRED_PAYLOAD_PATHS)}; missing={required_missing or 'none'}.",
            "Ensure the uploadable archive includes manuscript, bibliography, rebuild/verify scripts, handoff docs, and submission audits.",
        )
    )

    entry_missing = sorted(REVIEWER_ENTRYPOINT_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload reviewer entrypoints",
            "pass" if not entry_missing else "needs revision",
            f"reviewer_entries={len(REVIEWER_ENTRYPOINT_PATHS)}; missing={entry_missing or 'none'}.",
            "Ensure the uploadable archive includes reviewer-facing guide, editor/reviewer briefs, venue brief, registry, and reproducibility audit.",
        )
    )

    comparison_missing = sorted(COMPARISON_PROTOCOL_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload comparison protocol evidence",
            "pass" if not comparison_missing else "needs revision",
            f"comparison_protocol_files={len(COMPARISON_PROTOCOL_PATHS)}; missing={comparison_missing or 'none'}.",
            "Ensure the uploadable archive includes the comparison protocol audit plus its claim, evidence, comparability, counterpoint, statistical, and tradeoff sources.",
        )
    )

    headline_missing = sorted(HEADLINE_NUMERIC_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload headline numeric evidence",
            "pass" if not headline_missing else "needs revision",
            f"headline_numeric_files={len(HEADLINE_NUMERIC_PATHS)}; missing={headline_missing or 'none'}.",
            "Ensure the uploadable archive includes the headline numeric audit script and generated CSV/Markdown/JSON evidence.",
        )
    )

    citation_missing = sorted(CITATION_SUPPORT_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload citation support evidence",
            "pass" if not citation_missing else "needs revision",
            f"citation_support_files={len(CITATION_SUPPORT_PATHS)}; missing={citation_missing or 'none'}.",
            "Ensure the uploadable archive includes the citation support audit script and generated CSV/Markdown/JSON evidence.",
        )
    )

    author_input_missing = sorted(AUTHOR_INPUT_CLOSURE_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload author-input closure evidence",
            "pass" if not author_input_missing else "needs revision",
            f"author_input_closure_files={len(AUTHOR_INPUT_CLOSURE_PATHS)}; missing={author_input_missing or 'none'}.",
            "Ensure the uploadable archive includes the author-input closure audit script and generated CSV/Markdown/JSON evidence.",
        )
    )

    source_path_missing = sorted(SOURCE_PATH_PRIVACY_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload source/path privacy executable",
            "pass" if not source_path_missing else "needs revision",
            f"source_path_privacy_scripts={len(SOURCE_PATH_PRIVACY_PATHS)}; missing={source_path_missing or 'none'}; terminal_outputs_excluded=3.",
            "Ensure the uploadable archive includes source/path privacy audit code; generated terminal outputs are intentionally excluded and reproduced by the extracted-payload smoke test.",
        )
    )

    extraction_smoke_missing = sorted(PAYLOAD_EXTRACTION_SMOKE_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload extraction smoke executable",
            "pass" if not extraction_smoke_missing else "needs revision",
            f"payload_extraction_smoke_scripts={len(PAYLOAD_EXTRACTION_SMOKE_PATHS)}; missing={extraction_smoke_missing or 'none'}; terminal_outputs_excluded=3.",
            "Ensure the uploadable archive includes the extraction smoke audit code; generated terminal outputs are intentionally excluded and regenerated from the source tree.",
        )
    )

    verifier_smoke_missing = sorted(PAYLOAD_VERIFIER_SMOKE_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload verifier smoke executable",
            "pass" if not verifier_smoke_missing else "needs revision",
            f"payload_verifier_smoke_scripts={len(PAYLOAD_VERIFIER_SMOKE_PATHS)}; missing={verifier_smoke_missing or 'none'}; terminal_outputs_excluded=3.",
            "Ensure the uploadable archive includes the verifier smoke audit code; generated terminal outputs are intentionally excluded and regenerated from the source tree.",
        )
    )

    metadata_bad: list[str] = []
    for member in members:
        if not member.name.startswith(f"{PAYLOAD_ROOT}/"):
            metadata_bad.append(f"{member.name}:root")
        if member.mtime != 0:
            metadata_bad.append(f"{member.name}:mtime={member.mtime}")
        if member.uid != 0 or member.gid != 0:
            metadata_bad.append(f"{member.name}:uidgid={member.uid}/{member.gid}")
        if member.uname or member.gname:
            metadata_bad.append(f"{member.name}:names")
        if member.isfile():
            expected_mode = 0o755 if member.name.endswith(".sh") else 0o644
            if member.mode != expected_mode:
                metadata_bad.append(f"{member.name}:mode={oct(member.mode)}")
    rows.append(
        row(
            "Payload deterministic tar metadata",
            "pass" if not metadata_bad else "needs revision",
            f"members_checked={len(members)}; metadata_issues={metadata_bad[:5] or 'none'}.",
            "Keep tar member mtime/uid/gid/user/group/mode normalized for deterministic payloads.",
        )
    )

    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Payload Round-Trip Audit",
        "",
        "This terminal audit opens the reviewer/upload tarball and checks manifest agreement, per-file hashes, path hygiene, required artifacts, and deterministic tar metadata.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | evidence | next action |", "|---|---|---|---|"])
    for item in rows:
        lines.append(
            "| {item} | {status} | {evidence} | {next_action} |".format(
                **{key: value.replace("|", "\\|") for key, value in item.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "archive": rel(ARCHIVE),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "required_payload_paths": sorted(REQUIRED_PAYLOAD_PATHS),
        "reviewer_entrypoint_paths": sorted(REVIEWER_ENTRYPOINT_PATHS),
        "comparison_protocol_paths": sorted(COMPARISON_PROTOCOL_PATHS),
        "headline_numeric_paths": sorted(HEADLINE_NUMERIC_PATHS),
        "citation_support_paths": sorted(CITATION_SUPPORT_PATHS),
        "author_input_closure_paths": sorted(AUTHOR_INPUT_CLOSURE_PATHS),
        "payload_extraction_smoke_paths": sorted(PAYLOAD_EXTRACTION_SMOKE_PATHS),
        "payload_verifier_smoke_paths": sorted(PAYLOAD_VERIFIER_SMOKE_PATHS),
        "private_basenames": sorted(PRIVATE_BASENAMES),
        "rows": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_payload_roundtrip_audit.csv"),
            "analysis": rel(RESULTS / "analysis_payload_roundtrip_audit.md"),
            "manifest": rel(RESULTS / "manifest_payload_roundtrip_audit.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_payload_roundtrip_audit.csv", rows)
    write_markdown(RESULTS / "analysis_payload_roundtrip_audit.md", rows)
    write_manifest(RESULTS / "manifest_payload_roundtrip_audit.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} payload round-trip audit row(s)")
    if failures:
        print(f"warning: {failures} payload round-trip row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
