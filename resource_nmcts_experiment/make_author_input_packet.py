#!/usr/bin/env python3
"""Generate a concise author-input handoff packet.

The metadata audit is machine-readable and detailed.  This packet is the
human-facing companion placed directly in `submission_package/`: it tells the
author exactly which fields remain manual, where to fill them, and which checks
to rerun afterward.  It intentionally does not include private values.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"
SUMMARY = RESULTS / "summary_submission_metadata_audit.csv"
VALIDATOR_SUMMARY = RESULTS / "summary_submission_metadata_validator.csv"
ANONYMOUS_REVIEW_MANIFEST = RESULTS / "manifest_anonymous_review_readiness.json"
OUTPUT = SUBMISSION_PACKAGE / "AUTHOR_INPUT_REQUIRED.md"
MANIFEST = RESULTS / "manifest_author_input_packet.json"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_packet(rows: list[dict[str, str]]) -> None:
    needs = [row for row in rows if row.get("status") != "pass"]
    validator_rows = read_rows(VALIDATOR_SUMMARY)
    validator_revisions = [row for row in validator_rows if row.get("status") == "needs revision"]
    validator_author_input = [row for row in validator_rows if row.get("status") == "needs author input"]
    anonymous_manifest = read_json(ANONYMOUS_REVIEW_MANIFEST)
    anonymous_counts = anonymous_manifest.get("status_counts", {}) if anonymous_manifest else {}
    lines = [
        "# Author Input Required",
        "",
        "This packet lists the remaining author- and venue-specific fields that cannot be inferred from code, experiments, or generated artifacts.",
        "",
        "Do not fill private author metadata into tracked files unless the target venue requires it.  The preferred private intake path is:",
        "",
        "```bash",
        "/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_starter.py --write-private",
        "$EDITOR submission_package/submission_metadata.json",
        "./rebuild_submission_package.sh",
        "./verify_submission_package.sh",
        "```",
        "",
        "Use `cp submission_package/submission_metadata_template.json submission_package/submission_metadata.json`",
        "instead if you prefer a completely blank template.  `submission_metadata.json`",
        "is ignored by Git so private author metadata is not committed accidentally.",
        "When the metadata file is complete, the rebuild also creates ignored private previews:",
        "`generated_author_declarations.md`, `generated_availability_statements.md`,",
        "`generated_cover_letter.md`, and `generated_submission_text.md`.",
        "Before generating final upload text, `validate_submission_metadata.py` checks common",
        "format issues without writing private values to tracked files.",
        "",
        "Before editing venue-specific claims, cover-letter language, or reviewer replies, read",
        "`submission_package/COMPARISON_HANDOFF_zh.md`.  It gives the Chinese author-facing",
        "answer to what the method is compared against, why the comparison set is meaningful,",
        "and which stronger claims must not be made.",
        "",
        "If you want a Chinese field-by-field intake checklist, use",
        "`submission_package/AUTHOR_METADATA_QUESTIONNAIRE_zh.md` before filling",
        "`submission_package/submission_metadata.json`.  The questionnaire maps each",
        "human answer to the corresponding JSON path and does not contain private values.",
        "",
        "## Current Gate",
        "",
        f"- metadata rows needing author input: {len(needs)}",
        f"- metadata validator rows needing author input: {len(validator_author_input)}",
        f"- metadata validator rows needing revision: {len(validator_revisions)}",
        f"- anonymous-review rows needing author input: {anonymous_counts.get('needs author input', 0)}",
        f"- anonymous-review rows needing revision: {anonymous_counts.get('needs revision', 0)}",
        "- research, experiment, manuscript, archive, payload, and verifier checks are handled by the generated audits.",
        "- final goal closure should not be marked complete until these fields are filled and the rebuild/verifier pass again.",
        "",
        "## Required Actions",
        "",
    ]
    if not rows:
        lines.extend(
            [
                "- Metadata audit summary is missing.  Run `./rebuild_submission_package.sh` first.",
                "",
            ]
        )
    else:
        for idx, row in enumerate(needs, start=1):
            lines.extend(
                [
                    f"{idx}. **{row.get('item', 'Unknown item')}**",
                    f"   - source: `{row.get('source', '')}`",
                    f"   - required fields: {row.get('required_fields', '')}",
                    f"   - evidence: {row.get('evidence', '')}",
                    f"   - next action: {row.get('next_action', '')}",
                    "",
                ]
            )
    lines.extend(
        [
            "## Files To Update After Author Decisions",
            "",
            "- `submission_package/AUTHOR_METADATA_QUESTIONNAIRE_zh.md` as the Chinese field-by-field intake guide.",
            "- `submission_package/submission_metadata.json` for the private structured intake.",
            "- `submission_package/generated_*.md` private previews, generated automatically from the structured intake and intentionally ignored by Git.",
            "- `submission_package/author_declarations_template.md` if the venue wants declarations in prose form.",
            "- `submission_package/cover_letter_template.md` after the target venue and routing details are known.",
            "- `submission_package/submission_checklist.md` after venue formatting, reference style, word limit, supplementary-material policy, and AI-disclosure policy are confirmed.",
            "- `paper_latex/resource_nmcts_submission_v1.tex` only if the selected venue requires author names, declarations, formatting conversion, or final availability links inside the manuscript source.",
            "- A venue-specific anonymous manuscript copy and anonymous artifact links if `target_venue.anonymous_review_required` is yes.",
            "",
            "## Final Checks After Filling Metadata",
            "",
            "```bash",
            "./rebuild_submission_package.sh",
            "./verify_submission_package.sh",
            "rg -n \"needs author input|needs revision\" results/analysis_submission_readiness_audit.md results/analysis_submission_metadata_audit.md",
            "```",
            "",
            "Expected terminal state after real author metadata is supplied: no `needs revision` rows, no unresolved author-input rows in the final upload copy, and a passing terminal package verifier.",
        ]
    )
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, str]]) -> None:
    needs = [row for row in rows if row.get("status") != "pass"]
    validator_rows = read_rows(VALIDATOR_SUMMARY)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "source": rel(SUMMARY),
        "output": rel(OUTPUT),
        "metadata_rows": len(rows),
        "needs_author_input": len(needs),
        "metadata_validator_rows": len(validator_rows),
        "metadata_validator_needs_revision": sum(1 for row in validator_rows if row.get("status") == "needs revision"),
        "metadata_validator_needs_author_input": sum(1 for row in validator_rows if row.get("status") == "needs author input"),
        "items": [
            {
                "item": row.get("item", ""),
                "status": row.get("status", ""),
                "source": row.get("source", ""),
                "next_action": row.get("next_action", ""),
            }
            for row in rows
        ],
    }
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = read_rows(SUMMARY)
    write_packet(rows)
    write_manifest(rows)
    print(f"wrote {rel(OUTPUT)} with {sum(1 for row in rows if row.get('status') != 'pass')} author-input rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
