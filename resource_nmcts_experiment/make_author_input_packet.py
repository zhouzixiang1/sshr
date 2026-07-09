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
MINIMAL_FORM = SUBMISSION_PACKAGE / "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md"
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
        "For a compact matrix of baseline roles, supported claims, excluded claims, and",
        "evidence entry points, use `submission_package/COMPARISON_SIGNIFICANCE_MATRIX_zh.md`.",
        "",
        "If you want a Chinese field-by-field intake checklist, use",
        "`submission_package/AUTHOR_METADATA_QUESTIONNAIRE_zh.md` before filling",
        "`submission_package/submission_metadata.json`.  The questionnaire maps each",
        "human answer to the corresponding JSON path and does not contain private values.",
        "For the shortest possible reply format, use",
        "`submission_package/AUTHOR_MINIMAL_RESPONSE_FORM_zh.md`; it compresses the same",
        "remaining author/venue gate into ten answer groups.",
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
            "- `submission_package/COMPARISON_SIGNIFICANCE_MATRIX_zh.md` as the Chinese comparison-role matrix before editing cover-letter, response, or venue-system claim text.",
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


def write_minimal_form() -> None:
    lines = [
        "# 最小作者回复表",
        "",
        "用途：把最终投稿前仍需作者确认的信息压缩成一张可回复清单。请不要把真实私人信息写进 tracked 文件；把答案填入被 Git 忽略的 `submission_package/submission_metadata.json`，或直接把本表答案发回后再由工具写入私有 JSON。",
        "",
        "推荐流程：",
        "",
        "```bash",
        "/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_starter.py --write-private",
        "$EDITOR submission_package/submission_metadata.json",
        "./rebuild_submission_package.sh",
        "./verify_submission_package.sh",
        "```",
        "",
        "## 1. 目标 venue 与审稿政策",
        "",
        "- JSON path: `target_venue.*`",
        "- 请回答：目标期刊/会议、稿件类型、是否双盲、是否已核对格式/参考文献/字数/补充材料/AI disclosure 政策。",
        "- 可接受简答：`ACM Transactions on Quantum Computing; regular article; anonymous review: no/yes; all policies checked: yes/no/not applicable`。",
        "",
        "## 2. 作者与通讯作者",
        "",
        "- JSON path: `authors[]`, `corresponding_author.*`",
        "- 请回答：作者顺序、姓名、ORCID、单位、邮箱、通讯作者、通讯地址。",
        "- ORCID 没有时请明确写 `no ORCID` 或 `not applicable`，不要留空。",
        "",
        "## 3. CRediT 或等价贡献",
        "",
        "- JSON path: `author_contributions.*`",
        "- 请回答：conceptualization, methodology, software, validation, formal analysis, investigation, data curation, writing original draft, writing review/editing, visualization, supervision, funding acquisition 分别是谁。",
        "- 目标 venue 不要求 CRediT 时，也请给出等价贡献说明。",
        "",
        "## 4. 经费、致谢、利益冲突",
        "",
        "- JSON path: `funding.*`, `acknowledgements.statement`, `competing_interests.statement`",
        "- 请回答：基金声明和基金号；致谢或 no acknowledgements；利益冲突声明或 none-declared wording。",
        "",
        "## 5. 数据与代码可用性",
        "",
        "- JSON path: `data_availability.*`, `code_availability.*`",
        "- 已可自动预填：`code_availability.repository_url`, `code_availability.commit_hash`, `code_availability.environment_notes`。",
        "- 请回答：最终公开 archive DOI/URL，双盲匿名链接（如需），访问限制，代码 license，最终 Data/Code Availability 正文。",
        "- 如果某项没有，请写 `none` 或 `not applicable`，不要留空。",
        "",
        "## 6. AI assistance disclosure",
        "",
        "- JSON path: `ai_assistance.statement`",
        "- 请回答：目标 venue 是否要求 AI disclosure；若要求，给出最终文字；若不要求，写 `No disclosure required by the target venue` 或等价表述。",
        "",
        "## 7. 预印本、既往投稿、相关稿件",
        "",
        "- JSON path: `preprint_and_prior_submission.*`",
        "- 请回答：是否有 preprint DOI/URL、是否有既往投稿历史、是否有相关在投/已投稿件，以及投稿系统要求的完整声明。",
        "",
        "## 8. Cover letter 与审稿人建议",
        "",
        "- JSON path: `cover_letter.*`",
        "- 请回答：目标编辑/栏目、建议审稿人、回避审稿人、给编辑的 routing statement。",
        "- 没有建议或回避审稿人时请写 `none`。",
        "",
        "## 9. 权限确认",
        "",
        "- JSON path: `permissions.*`",
        "- 请确认：本文图表是否均来自本地脚本和实验 artifact；是否没有未授权第三方图表、表格、长引文或受版权限制材料。",
        "",
        "## 10. 不要改的科学口径",
        "",
        "- 写投稿系统文本或 cover letter 前，先读 `COMPARISON_HANDOFF_zh.md` 和 `COMPARISON_SIGNIFICANCE_MATRIX_zh.md`。",
        "- 本文只主张 `logical-layer quantum Boolean oracle synthesis`。",
        "- 不写成 hardware mapping、routing、native-gate scheduling、noise model、magic-state-factory resource estimate。",
        "- 不把 ROS-style LUT proxy 写成 full official ROS SAT garbage-management reproduction。",
        "- 不把 weighted-score 胜出写成对所有 T/CNOT/depth/ancilla 指标的全面支配。",
        "",
        "## 填完后必须跑",
        "",
        "```bash",
        "/opt/anaconda3/envs/mcts-qoracle/bin/python validate_submission_metadata.py",
        "/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_text_preview.py",
        "./rebuild_submission_package.sh",
        "./verify_submission_package.sh",
        "rg -n \"needs author input|needs revision\" results/analysis_submission_readiness_audit.md results/analysis_submission_metadata_audit.md results/analysis_submission_metadata_validator.md",
        "```",
    ]
    MINIMAL_FORM.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, str]]) -> None:
    needs = [row for row in rows if row.get("status") != "pass"]
    validator_rows = read_rows(VALIDATOR_SUMMARY)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "source": rel(SUMMARY),
        "output": rel(OUTPUT),
        "minimal_form": rel(MINIMAL_FORM),
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
    write_minimal_form()
    write_manifest(rows)
    print(f"wrote {rel(OUTPUT)} and {rel(MINIMAL_FORM)} with {sum(1 for row in rows if row.get('status') != 'pass')} author-input rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
