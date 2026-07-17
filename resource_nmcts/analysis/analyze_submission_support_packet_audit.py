#!/usr/bin/env python3
"""Audit the public cover-letter, venue, and declaration support packet.

This audit checks the human-facing files that are used immediately before
journal upload: cover letter template, author declarations template, venue
brief, final checklist, handoff notes, metadata template, and editor/reviewer
briefs.  It verifies that these files preserve the logical-layer claim
boundary, expose author-gated fields, and point to the reproducible package
checks without reading or generating private author metadata.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"

COVER = SUBMISSION_PACKAGE / "cover_letter_template.md"
DECLARATIONS = SUBMISSION_PACKAGE / "author_declarations_template.md"
VENUE = SUBMISSION_PACKAGE / "target_venue_brief.md"
TARGET_POLICY_CHECKLIST_ZH = SUBMISSION_PACKAGE / "TARGET_VENUE_POLICY_CHECKLIST_zh.md"
CHECKLIST = SUBMISSION_PACKAGE / "submission_checklist.md"
FINAL_HANDOFF = SUBMISSION_PACKAGE / "FINAL_SUBMISSION_HANDOFF_zh.md"
README = SUBMISSION_PACKAGE / "README.md"
ARTIFACT_GUIDE = SUBMISSION_PACKAGE / "artifact_reproduction_guide.md"
AUTHOR_PACKET = SUBMISSION_PACKAGE / "AUTHOR_INPUT_REQUIRED.md"
AUTHOR_QUESTIONNAIRE_ZH = SUBMISSION_PACKAGE / "AUTHOR_METADATA_QUESTIONNAIRE_zh.md"
AUTHOR_MINIMAL_FORM_ZH = SUBMISSION_PACKAGE / "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md"
LAST_MILE_ACTION_CARD_ZH = SUBMISSION_PACKAGE / "LAST_MILE_ACTION_CARD_zh.md"
METADATA_ANSWERS_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_answers_template.json"
METADATA_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_template.json"
EDITOR_BRIEF = SUBMISSION_PACKAGE / "editor_screening_brief.md"
REVIEWER_BRIEF = SUBMISSION_PACKAGE / "reviewer_concern_brief.md"
COMPARISON_HANDOFF_ZH = SUBMISSION_PACKAGE / "COMPARISON_HANDOFF_zh.md"
COMPARISON_SIGNIFICANCE_ZH = SUBMISSION_PACKAGE / "COMPARISON_SIGNIFICANCE_MATRIX_zh.md"

CLAIM_SCOPE = RESULTS / "manifest_claim_scope_lint.json"
COMPARISON_PROTOCOL = RESULTS / "manifest_comparison_protocol_audit.json"
COMPARISON_TARGET_VALIDITY = RESULTS / "manifest_comparison_target_validity_audit.json"
COMPARISON_ANSWER_SCORECARD = RESULTS / "manifest_comparison_answer_scorecard.json"
COMPARISON_ROUTE_DECISION = RESULTS / "manifest_comparison_route_decision_audit.json"
COMPARISON_REFERENCE_INTEGRITY = RESULTS / "manifest_comparison_support_reference_integrity.json"
NOVELTY_SCORECARD = RESULTS / "manifest_novelty_comparison_scorecard.json"
BENCHMARK_SUITE = RESULTS / "manifest_benchmark_suite_audit.json"
BENCHMARK_FUNCTION_DIVERSITY = RESULTS / "manifest_benchmark_function_diversity_audit.json"
EDITORIAL_SCREENING = RESULTS / "manifest_editorial_screening_audit.json"
METADATA_CLOSURE = RESULTS / "manifest_submission_metadata_closure_path.json"
METADATA_ANSWER_TEMPLATE_COVERAGE = RESULTS / "manifest_metadata_answer_template_coverage.json"
TEXT_PREVIEW = RESULTS / "manifest_submission_text_preview.json"
ANONYMOUS_REVIEW = RESULTS / "manifest_anonymous_review_readiness.json"
TARGET_VENUE_DECISION = RESULTS / "manifest_target_venue_decision_audit.json"
TARGET_VENUE_POLICY = RESULTS / "manifest_target_venue_policy_checklist.json"
AUTHOR_QUESTIONNAIRE_COVERAGE = RESULTS / "manifest_author_questionnaire_coverage.json"
AUTHOR_MINIMAL_FORM_COVERAGE = RESULTS / "manifest_author_minimal_form_coverage.json"


@dataclass(frozen=True)
class PacketSpec:
    item: str
    upload_risk: str
    files: tuple[Path, ...]
    tokens: tuple[str, ...]
    manifest_path: Path | None
    manifest_key: str
    expected: object
    supported_use: str
    boundary: str


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def token_hits(files: tuple[Path, ...], tokens: tuple[str, ...]) -> tuple[int, list[str]]:
    combined = "\n".join(read_text(path) for path in files)
    missing = [token for token in tokens if token not in combined]
    return len(tokens) - len(missing), missing


def manifest_ok(path: Path | None, key: str, expected: object) -> tuple[bool, str]:
    if path is None:
        return True, "not_applicable"
    manifest = read_json(path)
    if not manifest:
        return False, f"{rel(path)} missing_or_invalid"
    actual = manifest.get(key)
    if isinstance(expected, int) and isinstance(actual, list):
        actual_cmp: object = len(actual)
    else:
        actual_cmp = actual
    return actual_cmp == expected, f"{rel(path)}::{key}={actual_cmp}"


def specs() -> list[PacketSpec]:
    return [
        PacketSpec(
            item="Cover letter preserves logical-layer scope",
            upload_risk="Cover-letter prose could accidentally frame the paper as a hardware compiler.",
            files=(COVER,),
            tokens=(
                "logical-layer synthesis",
                "does not claim hardware mapping",
                "resource-constrained search",
                "rebuild_submission_package.sh",
            ),
            manifest_path=CLAIM_SCOPE,
            manifest_key="unresolved_count",
            expected=0,
            supported_use="The cover letter can introduce the manuscript without overclaiming hardware mapping or physical execution.",
            boundary="The cover letter still needs author, editor, reviewer, and prior-dissemination fields before upload.",
        ),
        PacketSpec(
            item="Cover letter exposes the comparison envelope",
            upload_risk="Editor may see only a narrow SSHR comparison or miss external-toolchain evidence.",
            files=(COVER,),
            tokens=(
                "177 traditional functions",
                "ESOP",
                "SSHR-H/SSHR-I",
                "mockturtle",
                "CirKit",
                "RevKit CLI exact-oracle",
                "complete truth-table bridge",
            ),
            manifest_path=COMPARISON_PROTOCOL,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The cover letter summarizes layered baselines and directs editors to the comparison evidence.",
            boundary="It should not be read as universal dominance over every synthesis or compilation method.",
        ),
        PacketSpec(
            item="Novelty/comparison scorecard is visible",
            upload_risk="Reviewer-facing comparison meaning could be scattered across too many tables and briefs.",
            files=(CHECKLIST, EDITOR_BRIEF, REVIEWER_BRIEF),
            tokens=(
                "Novelty/comparison scorecard",
                "Why the Comparison Is Meaningful",
                "Is this only an SSHR variant?",
                "Does the method dominate every resource?",
            ),
            manifest_path=NOVELTY_SCORECARD,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The support packet gives editors and reviewers a compact route from comparison questions to evidence and limitations.",
            boundary="The scorecard indexes existing evidence; it does not add a new metric or broaden the logical-layer claim.",
        ),
        PacketSpec(
            item="Comparison target validity audit is visible",
            upload_risk="Reviewer may not know which comparisons are primary benchmarks, external probes, controls, or counterpoints.",
            files=(CHECKLIST, README),
            tokens=(
                "Comparison target validity audit",
                "analyze_comparison_target_validity_audit.py",
            ),
            manifest_path=COMPARISON_TARGET_VALIDITY,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The support packet gives reviewers a direct route from comparison targets to role labels and excluded claims.",
            boundary="The validity audit classifies existing comparisons; it does not convert secondary probes into full hardware-mapped baselines.",
        ),
        PacketSpec(
            item="Comparison route decision audit is visible",
            upload_risk="Reviewer may know the baseline names but still read all comparator families as one universal leaderboard.",
            files=(ARTIFACT_GUIDE, README, COMPARISON_SIGNIFICANCE_ZH),
            tokens=(
                "analysis_comparison_route_decision_audit.md",
                "analyze_comparison_route_decision_audit.py",
                "comparison-route decision",
                "比较路线",
            ),
            manifest_path=COMPARISON_ROUTE_DECISION,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The support packet maps each reviewer-facing claim to the comparator family that can answer it and the over-claim that remains excluded.",
            boundary="The route audit indexes existing comparison evidence; it does not add a new result or broaden the logical-layer claim.",
        ),
        PacketSpec(
            item="Benchmark-suite audit is visible from reviewer entrypoints",
            upload_risk="Reviewers could see comparison outcomes without the benchmark-slice composition and representativeness boundary.",
            files=(ARTIFACT_GUIDE, README, CHECKLIST),
            tokens=(
                "analysis_benchmark_suite_audit.md",
                "analyze_benchmark_suite_audit.py",
                "Benchmark-suite composition audit",
                "benchmark-suite composition state",
            ),
            manifest_path=BENCHMARK_SUITE,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="Reviewer-facing entrypoints expose which benchmark suites, n scopes, verification routes, and representativeness boundaries support the comparisons.",
            boundary="The benchmark-suite audit describes existing evidence; it does not expand coverage to all Boolean functions or hardware-mapped benchmarks.",
        ),
        PacketSpec(
            item="Benchmark function-diversity audit is visible",
            upload_risk="Reviewers could accept the suite counts but still question whether the compared functions are structurally narrow.",
            files=(ARTIFACT_GUIDE, README, CHECKLIST),
            tokens=(
                "analysis_benchmark_function_diversity_audit.md",
                "analyze_benchmark_function_diversity_audit.py",
                "Benchmark function-diversity audit",
                "function-diversity state",
            ),
            manifest_path=BENCHMARK_FUNCTION_DIVERSITY,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="Reviewer-facing entrypoints expose function-family, density, degree, ANF-term, profile, and term-count diversity behind the comparison targets.",
            boundary="The function-diversity audit is descriptive evidence over existing rows; it does not imply distributional coverage of all Boolean functions.",
        ),
        PacketSpec(
            item="Chinese comparison handoff is visible",
            upload_risk="Author-side upload text or reviewer replies could overstate SSHR, ROS, RevKit, or AI/MCTS claims.",
            files=(README, AUTHOR_PACKET, FINAL_HANDOFF, COMPARISON_HANDOFF_ZH, COMPARISON_SIGNIFICANCE_ZH),
            tokens=(
                "COMPARISON_HANDOFF_zh.md",
                "COMPARISON_SIGNIFICANCE_MATRIX_zh.md",
                "主比较对象",
                "二级外部探针",
                "反例边界",
                "比较矩阵",
                "AI/MCTS 口径",
                "审稿问答口径",
                "不能说",
                "logical-layer",
                "weighted-score",
                "hardware mapping",
            ),
            manifest_path=COMPARISON_TARGET_VALIDITY,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The author-facing Chinese handoff keeps comparison, novelty, and excluded-claim language aligned before upload or reviewer response.",
            boundary="It is a navigation and wording guide over existing evidence; it does not add experiments or replace author/venue metadata.",
        ),
        PacketSpec(
            item="Chinese comparison significance matrix is visible",
            upload_risk="The author may know the baseline names but not which conclusion each comparison can legitimately support.",
            files=(README, CHECKLIST, FINAL_HANDOFF, REVIEWER_BRIEF, COMPARISON_SIGNIFICANCE_ZH),
            tokens=(
                "COMPARISON_SIGNIFICANCE_MATRIX_zh.md",
                "比较对象与意义矩阵",
                "同任务主基线",
                "SSHR 小函数对照",
                "外部逻辑工具链",
                "精确可逆综合对照",
                "AI/MCTS 因果消融",
                "禁止扩展的说法",
                "hardware mapping",
                "full ROS reproduction",
            ),
            manifest_path=COMPARISON_ANSWER_SCORECARD,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The author can map each baseline family to its role, supported conclusion, invalid conclusion, and evidence entry point before drafting upload text or rebuttals.",
            boundary="The matrix summarizes existing verified comparison evidence; it does not introduce a new result or broaden the comparison scope.",
        ),
        PacketSpec(
            item="Comparison evidence entrypoints resolve",
            upload_risk="Author-facing comparison handoffs could cite stale evidence filenames that cannot be opened during upload preparation or reviewer response drafting.",
            files=(COMPARISON_HANDOFF_ZH, COMPARISON_SIGNIFICANCE_ZH, REVIEWER_BRIEF),
            tokens=(
                "analysis_comparison_answer_scorecard.md",
                "analysis_comparison_target_validity_audit.md",
                "analysis_search_control_baseline_audit.md",
                "COMPARISON_SIGNIFICANCE_MATRIX_zh.md",
            ),
            manifest_path=COMPARISON_REFERENCE_INTEGRITY,
            manifest_key="missing_count",
            expected=0,
            supported_use="The comparison handoff now has a machine-checked path from each cited evidence file or table name to an existing artifact.",
            boundary="This checks evidence-entrypoint integrity; it does not add new experiments or strengthen any comparison claim beyond the referenced artifacts.",
        ),
        PacketSpec(
            item="Author declarations keep private fields explicit",
            upload_risk="Declarations could be mistaken as complete or private author metadata could be committed.",
            files=(DECLARATIONS, AUTHOR_PACKET, AUTHOR_QUESTIONNAIRE_ZH, AUTHOR_MINIMAL_FORM_ZH, METADATA_ANSWERS_TEMPLATE, METADATA_TEMPLATE),
            tokens=(
                "AUTHOR INPUT REQUIRED",
                "AUTHOR_METADATA_QUESTIONNAIRE_zh.md",
                "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md",
                "submission_metadata_answers.json",
                "submission_metadata.json",
                "generated_author_declarations.md",
                "Competing Interests",
                "Data Availability",
                "Code Availability",
                "AI-Assisted Writing or Coding Statement",
            ),
            manifest_path=METADATA_CLOSURE,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The declarations packet is a structured intake path with a short answer file rather than a hidden or implicit author task.",
            boundary="Final authorship, funding, conflicts, archive links, and AI disclosure remain human-gated.",
        ),
        PacketSpec(
            item="Chinese metadata questionnaire maps human inputs",
            upload_risk="The final author/venue gate could remain too abstract for the author to fill in one pass.",
            files=(AUTHOR_QUESTIONNAIRE_ZH, AUTHOR_MINIMAL_FORM_ZH, METADATA_ANSWERS_TEMPLATE, README, CHECKLIST, AUTHOR_PACKET),
            tokens=(
                "AUTHOR_METADATA_QUESTIONNAIRE_zh.md",
                "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md",
                "submission_metadata_answers_template.json",
                "make_submission_metadata_from_answers.py",
                "target_venue.name",
                "authors[].name",
                "corresponding_author.email",
                "author_contributions.methodology",
                "funding.statement",
                "competing_interests.statement",
                "data_availability.archive_link_or_doi",
                "code_availability.commit_hash",
                "ai_assistance.statement",
                "preprint_and_prior_submission.preprint_url_or_doi",
                "cover_letter.suggested_reviewers",
                "permissions.third_party_material_confirmed",
                "validate_submission_metadata.py",
            ),
            manifest_path=AUTHOR_QUESTIONNAIRE_COVERAGE,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The author can answer a Chinese field-by-field questionnaire and transfer the answers to the ignored private metadata JSON.",
            boundary="The questionnaire is an intake guide only; it does not contain, infer, or commit private author values.",
        ),
        PacketSpec(
            item="Minimal response form covers required metadata fields",
            upload_risk="The author may use only the short response form and accidentally omit a required private field.",
            files=(AUTHOR_MINIMAL_FORM_ZH, README, CHECKLIST, AUTHOR_PACKET),
            tokens=(
                "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md",
                "target_venue.*",
                "authors[]",
                "corresponding_author.*",
                "author_contributions.*",
                "funding.*",
                "data_availability.*",
                "code_availability.*",
                "preprint_and_prior_submission.*",
                "cover_letter.*",
                "permissions.*",
                "validate_submission_metadata.py",
            ),
            manifest_path=AUTHOR_MINIMAL_FORM_COVERAGE,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The concise Chinese response form is machine-checked against every required metadata path before authors transfer answers to ignored private JSON.",
            boundary="The short form still contains prompts only; real author and venue values remain private and human-provided.",
        ),
        PacketSpec(
            item="Minimal response-form coverage is visible from reviewer entrypoints",
            upload_risk="The short author form could be present but its machine-checked required-field coverage could be hard to find.",
            files=(ARTIFACT_GUIDE, README, CHECKLIST),
            tokens=(
                "analysis_author_minimal_form_coverage.md",
                "analyze_author_minimal_form_coverage.py",
                "Author minimal response-form coverage",
                "author minimal response-form coverage state",
            ),
            manifest_path=AUTHOR_MINIMAL_FORM_COVERAGE,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The public guide, README, and checklist now point to the machine check proving the concise author-intake form covers every required metadata path.",
            boundary="This only audits public prompts; private author and venue values remain outside the repository.",
        ),
        PacketSpec(
            item="Last-mile action card is visible",
            upload_risk="The package could be machine-complete but still hard for the author to turn into a real venue upload.",
            files=(LAST_MILE_ACTION_CARD_ZH, README, CHECKLIST, FINAL_HANDOFF, AUTHOR_PACKET),
            tokens=(
                "LAST_MILE_ACTION_CARD_zh.md",
                "最后一步行动卡",
                "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md",
                "submission_metadata_answers.json",
                "submission_metadata.json",
                "verify_submission_package.sh",
                "does not claim hardware mapping",
                "not full ROS reproduction",
            ),
            manifest_path=METADATA_CLOSURE,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The author has a one-page Chinese execution card that turns the remaining human metadata gate into a short ordered checklist.",
            boundary="The action card is public navigation only; it does not contain, infer, or commit private author or venue values.",
        ),
        PacketSpec(
            item="Short answer template covers metadata fields",
            upload_risk="The public JSON answer template could omit a required private field even if the longer questionnaire mentions it.",
            files=(METADATA_ANSWERS_TEMPLATE, AUTHOR_PACKET, README, CHECKLIST),
            tokens=(
                "AUTHOR INPUT REQUIRED",
                "target_venue.name",
                "authors",
                "corresponding_author",
                "funding",
                "competing_interests",
                "data_availability",
                "code_availability",
                "ai_assistance",
                "cover_letter",
            ),
            manifest_path=METADATA_ANSWER_TEMPLATE_COVERAGE,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The tracked short-answer JSON template is machine-checked against every required private metadata path before authors fill the ignored answer file.",
            boundary="The template contains placeholders only; real author and venue values remain private and human-provided.",
        ),
        PacketSpec(
            item="Venue policy gate is visible before upload",
            upload_risk="Target venue style, anonymous review, AI disclosure, or archive policy could be missed.",
            files=(VENUE, TARGET_POLICY_CHECKLIST_ZH, CHECKLIST, AUTHOR_PACKET),
            tokens=(
                "target_venue.name",
                "target_venue.manuscript_type",
                "anonymous_review_required",
                "ai_disclosure_policy_checked",
                "Target venue decision audit",
                "TARGET_VENUE_POLICY_CHECKLIST_zh.md",
                "recommended_first_choice",
                "fit_score",
                "source_url",
                "ACM Transactions on Quantum Computing",
                "Quantum",
                "IEEE Transactions on Quantum Engineering",
                "TCAD",
            ),
            manifest_path=TARGET_VENUE_DECISION,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The venue-choice step is concrete enough for the author to fill the private metadata file.",
            boundary="The audit does not choose the journal; it only checks that the choice is explicit and policy-gated.",
        ),
        PacketSpec(
            item="Target-venue policy checklist is actionable",
            upload_risk="The author could choose a venue but miss the specific metadata fields implied by the venue policy.",
            files=(TARGET_POLICY_CHECKLIST_ZH, README, FINAL_HANDOFF, CHECKLIST),
            tokens=(
                "目标期刊政策核对表",
                "ACM TQC",
                "Quantum",
                "target_venue.formatting_policy_checked",
                "target_venue.ai_disclosure_policy_checked",
                "authors[]",
                "author_contributions.*",
                "data_availability.*",
                "code_availability.*",
                "validate_submission_metadata.py",
            ),
            manifest_path=TARGET_VENUE_POLICY,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The policy checklist maps public ACM TQC, Quantum, and archive/license gates to the private metadata fields that must be filled before upload.",
            boundary="It records public policy entry points and author actions; it does not fill private metadata or guarantee a venue decision.",
        ),
        PacketSpec(
            item="Private preview path remains safe",
            upload_risk="Generated cover-letter/declaration previews could leak private metadata into Git or the payload.",
            files=(DECLARATIONS, README, FINAL_HANDOFF),
            tokens=(
                "generated_cover_letter.md",
                "generated_submission_text.md",
                "private",
                "ignored by Git",
                "validate_submission_metadata.py",
            ),
            manifest_path=TEXT_PREVIEW,
            manifest_key="private_outputs_are_git_ignored",
            expected=True,
            supported_use="Authors can generate private submission-system text after filling metadata without committing it.",
            boundary="Tracked audit outputs remain public and redacted; private generated Markdown files stay ignored.",
        ),
        PacketSpec(
            item="Anonymous-review fork is not conflated with author version",
            upload_risk="A double-blind venue could receive author-labeled material or non-anonymous links.",
            files=(FINAL_HANDOFF, CHECKLIST, DECLARATIONS),
            tokens=(
                "double-blind",
                "anonymous_review_required",
                "anonymous review link",
                "author-labeled",
            ),
            manifest_path=ANONYMOUS_REVIEW,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The support packet separates the current author-labeled manuscript from the venue-dependent anonymous path.",
            boundary="Anonymous-review policy and anonymous archive links still require target-venue input.",
        ),
        PacketSpec(
            item="Editor and reviewer triage is aligned",
            upload_risk="Cover letter, editor brief, and reviewer brief could emphasize different claims or boundaries.",
            files=(COVER, EDITOR_BRIEF, REVIEWER_BRIEF),
            tokens=(
                "comparison boundaries",
                "Recommended Editorial Reading Path",
                "Baseline comparability audit",
                "Search-control baseline audit",
                "No claim of universal",
            ),
            manifest_path=EDITORIAL_SCREENING,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The editor-facing and reviewer-facing triage path points to the same bounded evidence package.",
            boundary="Triage briefs are navigation aids, not acceptance guarantees.",
        ),
        PacketSpec(
            item="Upload checklist cites terminal verifiers",
            upload_risk="Final upload could skip the one-command package verifier or the support-packet audit.",
            files=(CHECKLIST, README, FINAL_HANDOFF),
            tokens=(
                "rebuild_submission_package.sh",
                "verify_submission_package.sh",
                "analysis_submission_package_verifier.md",
                "analysis_submission_support_packet_audit.md",
            ),
            manifest_path=None,
            manifest_key="",
            expected=0,
            supported_use="The public handoff points authors to the same terminal checks used by the repository.",
            boundary="The checklist cannot replace final venue-system proof review.",
        ),
    ]


def evaluate(spec: PacketSpec) -> dict[str, str]:
    missing_files = [rel(path) for path in spec.files if not path.exists()]
    hits, missing_tokens = token_hits(spec.files, spec.tokens)
    ok, manifest_evidence = manifest_ok(spec.manifest_path, spec.manifest_key, spec.expected)
    status = "pass" if not missing_files and hits == len(spec.tokens) and ok else "needs revision"
    evidence = (
        f"files_missing={missing_files or 'none'}; "
        f"tokens={hits}/{len(spec.tokens)}; "
        f"missing_tokens={missing_tokens or 'none'}; "
        f"manifest={manifest_evidence}"
    )
    return {
        "item": spec.item,
        "status": status,
        "upload_risk": spec.upload_risk,
        "evidence": evidence,
        "supported_use": spec.supported_use,
        "boundary": spec.boundary,
        "next_action": "No action needed." if status == "pass" else "Restore missing support-packet anchors or rerun upstream audits.",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "upload_risk", "evidence", "supported_use", "boundary", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Submission Support Packet Audit",
        "",
        "This audit checks the public cover-letter, declaration, venue, checklist, handoff, and editor/reviewer support packet before final author metadata is filled.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "## Packet Matrix", "", "| item | status | upload risk | evidence | supported use | boundary |", "|---|---|---|---|---|---|"])
    for row in rows:
        safe = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append("| {item} | {status} | {upload_risk} | {evidence} | {supported_use} | {boundary} |".format(**safe))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}p{0.11\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.25\linewidth}}",
        r"\toprule",
        r"Support-packet item & Status & Supported use & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["item"]),
                    tex_escape(row["status"]),
                    tex_escape(row["supported_use"]),
                    tex_escape(row["boundary"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
        "needs_revision_count": failures,
        "outputs": {
            "summary": "results/summary_submission_support_packet_audit.csv",
            "analysis": "results/analysis_submission_support_packet_audit.md",
            "manifest": "results/manifest_submission_support_packet_audit.json",
            "table": "paper_latex/tables/submission_support_packet_audit.tex",
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = [evaluate(spec) for spec in specs()]
    write_csv(RESULTS / "summary_submission_support_packet_audit.csv", rows)
    write_markdown(RESULTS / "analysis_submission_support_packet_audit.md", rows)
    write_latex(TABLES / "submission_support_packet_audit.tex", rows)
    write_manifest(RESULTS / "manifest_submission_support_packet_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} submission support packet audit rows")
    if failures:
        print(f"warning: {failures} submission support packet row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
