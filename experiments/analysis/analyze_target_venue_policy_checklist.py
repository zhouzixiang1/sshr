#!/usr/bin/env python3
"""Generate an author-facing target-venue policy checklist.

This script does not contact publisher websites at rebuild time.  It records
the public policy entry points checked for the current submission package and
maps those requirements to the private ``submission_metadata.json`` fields that
the author must fill before upload.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"
OUTPUT = SUBMISSION_PACKAGE / "TARGET_VENUE_POLICY_CHECKLIST_zh.md"

CHECKED_DATE = "2026-07-09"


@dataclass(frozen=True)
class PolicyRow:
    venue: str
    item: str
    metadata_paths: tuple[str, ...]
    public_source: str
    source_note: str
    author_action: str
    boundary: str


ROWS = (
    PolicyRow(
        venue="ACM Transactions on Quantum Computing",
        item="Submission route and manuscript type",
        metadata_paths=("target_venue.name", "target_venue.manuscript_type"),
        public_source="https://dl.acm.org/journal/tqc/author-guidelines",
        source_note="ACM TQC author guidelines route authors through the ACM journal submission workflow for Transactions on Quantum Computing.",
        author_action="Confirm ACM TQC as the final target and choose the manuscript type expected by the submission system.",
        boundary="This records the upload route only; it does not select the journal on behalf of the author.",
    ),
    PolicyRow(
        venue="ACM Transactions on Quantum Computing",
        item="ACM template and TAPS-compatible LaTeX discipline",
        metadata_paths=(
            "target_venue.formatting_policy_checked",
            "target_venue.reference_style_checked",
            "target_venue.supplementary_material_policy_checked",
        ),
        public_source="https://www.acm.org/publications/authors/submissions",
        source_note="ACM's submissions page points authors to the Primary Article Templates and approved LaTeX package discipline for TAPS compatibility.",
        author_action="Confirm the ACM primary-article template version, reference style, package restrictions, and supplementary-material handling before upload.",
        boundary="The current ACM/TQC smoke draft proves a review-format path compiles; final ACM metadata, rights, CCS, and keywords still require author review.",
    ),
    PolicyRow(
        venue="ACM Transactions on Quantum Computing",
        item="Authorship, ORCID, corresponding author, and conflicts",
        metadata_paths=(
            "authors[]",
            "corresponding_author.*",
            "author_contributions.*",
            "competing_interests.statement",
        ),
        public_source="https://www.acm.org/publications/policies/new-acm-policy-on-authorship",
        source_note="ACM authorship policy requires accountable named authors, valid ORCIDs before eRights completion, one corresponding author, and conflict declarations.",
        author_action="Fill author order, affiliations, ORCIDs, corresponding author, contributions, and competing-interest wording in the private metadata JSON.",
        boundary="These are private author decisions and cannot be inferred from the repository.",
    ),
    PolicyRow(
        venue="ACM Transactions on Quantum Computing",
        item="AI assistance disclosure",
        metadata_paths=("target_venue.ai_disclosure_policy_checked", "ai_assistance.statement"),
        public_source="https://www.acm.org/publications/policies/frequently-asked-questions",
        source_note="ACM FAQ separates generative AI content creation, which requires disclosure, from basic grammar/spelling assistance, which generally does not.",
        author_action="Choose the exact disclosure wording for any AI-assisted writing, code, bibliographic, figure, or calculation use, or record that no disclosure is required for the actual use case.",
        boundary="The checklist does not decide whether the author's actual tool use crosses ACM's disclosure threshold.",
    ),
    PolicyRow(
        venue="ACM Transactions on Quantum Computing",
        item="Prior publication and preprint status",
        metadata_paths=("preprint_and_prior_submission.*",),
        public_source="https://www.acm.org/publications/policies/new-acm-policy-on-authorship",
        source_note="ACM policy distinguishes arXiv-style preprints from simultaneous submission to another publication venue.",
        author_action="Record any arXiv/preprint URL and certify that the manuscript is not under review elsewhere unless the selected venue explicitly permits it.",
        boundary="Prior-submission history is author-specific and must not be guessed.",
    ),
    PolicyRow(
        venue="Quantum",
        item="ArXiv or quant-ph route",
        metadata_paths=(
            "target_venue.name",
            "target_venue.manuscript_type",
            "preprint_and_prior_submission.preprint_url_or_doi",
        ),
        public_source="https://quantum-journal.org/instructions/authors/",
        source_note="Quantum asks authors to supply an arXiv reference for a preprint posted to, or cross-listed with, quant-ph.",
        author_action="If Quantum is selected, post or cross-list the manuscript to quant-ph and record the arXiv identifier before journal submission.",
        boundary="This is only needed if Quantum becomes the selected venue.",
    ),
    PolicyRow(
        venue="Quantum",
        item="Author contribution and AI statement",
        metadata_paths=("author_contributions.*", "ai_assistance.statement"),
        public_source="https://quantum-journal.org/instructions/authors/",
        source_note="Quantum states that author contribution statements are mandatory and AI/LLM use scope should be disclosed in that statement.",
        author_action="Prepare the contribution statement and include any AI/LLM use scope, including grammar checking, reformatting, text, image, bibliography, code, or calculation assistance.",
        boundary="The contribution statement must reflect the actual author roles.",
    ),
    PolicyRow(
        venue="Quantum",
        item="Cover letter, editor, referee, and exclusivity checks",
        metadata_paths=(
            "cover_letter.target_editor",
            "cover_letter.suggested_reviewers",
            "cover_letter.excluded_reviewers",
            "preprint_and_prior_submission.prior_submission_history",
        ),
        public_source="https://quantum-journal.org/instructions/authors/",
        source_note="Quantum says cover letters are not necessary, asks for suggested referees/editors through Scholastica, and requires the work not be concurrently submitted elsewhere.",
        author_action="If Quantum is selected, prepare suggested editors/referees or avoidance lists and confirm no concurrent journal submission.",
        boundary="Editor/referee choices and prior-submission status are author decisions.",
    ),
    PolicyRow(
        venue="Any selected venue",
        item="Data, code, archive, license, and anonymous-review links",
        metadata_paths=(
            "data_availability.*",
            "code_availability.*",
            "target_venue.anonymous_review_required",
        ),
        public_source="submission_package/dist/resource_nmcts_submission_payload.tar.gz",
        source_note="The repository already builds a reproducible payload archive, SHA256 sidecar, public handoff, and anonymous-review path.",
        author_action="Create final public archive links or anonymous review links as required, choose the code license wording, and paste final availability text into private metadata.",
        boundary="The repo can generate the package, but final DOI/URL/license choices remain outside the tracked source.",
    ),
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def row_dict(item: PolicyRow) -> dict[str, str]:
    return {
        "venue": item.venue,
        "item": item.item,
        "metadata_paths": "; ".join(item.metadata_paths),
        "public_source": item.public_source,
        "source_note": item.source_note,
        "author_action": item.author_action,
        "boundary": item.boundary,
        "status": "pass" if item.public_source and item.metadata_paths and item.author_action else "needs revision",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["venue", "item", "metadata_paths", "public_source", "source_note", "author_action", "boundary", "status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_analysis(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Target Venue Policy Checklist Audit",
        "",
        f"Checked date: {CHECKED_DATE}",
        "",
        "This audit records public policy entry points for the remaining author/venue gate. It does not fill private author metadata.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| venue | item | metadata paths | public source | status |",
            "|---|---|---|---|---|",
        ]
    )
    for item in rows:
        safe = {key: value.replace("|", "\\|") for key, value in item.items()}
        lines.append("| {venue} | {item} | `{metadata_paths}` | {public_source} | {status} |".format(**safe))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_public_checklist(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# 目标期刊政策核对表",
        "",
        f"核对日期：{CHECKED_DATE}",
        "",
        "用途：在最终上传前，把首选 ACM TQC 与备选 Quantum 的公开政策入口映射到私有 `submission_metadata.json` 字段。不要在本 tracked 文件中填写真实作者信息。",
        "",
        "推荐用法：先选定目标期刊，再按本表把答案写入被 Git 忽略的 `submission_package/submission_metadata.json`，随后运行 `./rebuild_submission_package.sh` 和 `./verify_submission_package.sh`。",
        "",
        "## 必须先确认的总原则",
        "",
        "- 本文当前只主张 logical-layer quantum Boolean oracle synthesis。",
        "- 若选择 ACM TQC，当前已有 `paper_latex/resource_nmcts_submission_acm_tqc.tex`、review-stage CCS/keywords 和已通过的 ACM/TQC format smoke，但正式 ACM metadata、rights、ORCID、conflict、AI disclosure 与最终 archive 链接仍需作者确认。",
        "- 若选择 Quantum，通常需要 arXiv/quant-ph 路线、贡献声明和 AI/LLM 使用范围说明。",
        "- Data/code archive DOI、匿名审稿链接、license、funding、acknowledgements、conflict、prior submission 都不能从代码自动推断。",
        "",
        "## 核对矩阵",
        "",
        "| venue | policy item | fill in private JSON | author action | source | boundary |",
        "|---|---|---|---|---|---|",
    ]
    for item in rows:
        safe = {key: value.replace("|", "\\|") for key, value in item.items()}
        lines.append(
            "| {venue} | {item} | `{metadata_paths}` | {author_action} | {public_source} | {boundary} |".format(**safe)
        )
    lines.extend(
        [
            "",
            "## 填完后必须验证",
            "",
            "```bash",
            "/opt/anaconda3/envs/mcts-qoracle/bin/python validate_submission_metadata.py",
            "/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_text_preview.py",
            "./rebuild_submission_package.sh",
            "./verify_submission_package.sh",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "checked_date": CHECKED_DATE,
        "rows": len(rows),
        "venues": sorted({row["venue"] for row in rows}),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "outputs": {
            "summary": rel(RESULTS / "summary_target_venue_policy_checklist.csv"),
            "analysis": rel(RESULTS / "analysis_target_venue_policy_checklist.md"),
            "manifest": rel(RESULTS / "manifest_target_venue_policy_checklist.json"),
            "public_checklist": rel(OUTPUT),
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = [row_dict(item) for item in ROWS]
    write_csv(RESULTS / "summary_target_venue_policy_checklist.csv", rows)
    write_analysis(RESULTS / "analysis_target_venue_policy_checklist.md", rows)
    write_public_checklist(OUTPUT, rows)
    write_manifest(RESULTS / "manifest_target_venue_policy_checklist.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} target-venue policy checklist row(s)")
    if failures:
        print(f"warning: {failures} target-venue policy checklist row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
