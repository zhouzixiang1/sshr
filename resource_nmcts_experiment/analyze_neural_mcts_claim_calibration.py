#!/usr/bin/env python3
"""Calibrate the title-level Neural/MCTS claim against generated evidence.

The manuscript title and abstract use a strong method identity: neural
Monte Carlo tree search for resource-constrained Boolean-oracle synthesis.
This audit checks that the title-level terms remain supported by the actual
ablation evidence and by explicit exclusions of stronger claims.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
REVIEWER_BRIEF = THIS_DIR / "submission_package" / "reviewer_concern_brief.md"
EDITOR_BRIEF = THIS_DIR / "submission_package" / "editor_screening_brief.md"

SUMMARY = RESULTS / "summary_neural_mcts_claim_calibration.csv"
ANALYSIS = RESULTS / "analysis_neural_mcts_claim_calibration.md"
MANIFEST = RESULTS / "manifest_neural_mcts_claim_calibration.json"
TABLE = TABLES / "neural_mcts_claim_calibration.tex"

SEARCH_CONTROL_MANIFEST = RESULTS / "manifest_search_control_baseline_audit.json"
SEARCH_CONTROL_SUMMARY = RESULTS / "summary_search_control_baseline_audit.csv"
LEARNED_CONTROL_MANIFEST = RESULTS / "manifest_learned_control_audit.json"
LEARNED_CONTROL_SUMMARY = RESULTS / "summary_learned_control_audit.csv"
BITFLIP_RANDOM_MANIFEST = RESULTS / "manifest_bitflip_random_prior_control.json"
FRONTIER_RANDOM_MANIFEST = RESULTS / "manifest_frontier_random_depth_control.json"
ALGORITHM_CONTRACT_MANIFEST = RESULTS / "manifest_algorithm_contract.json"
SEARCH_BUDGET_MANIFEST = RESULTS / "manifest_search_budget_contract.json"
CLAIM_SCOPE_MANIFEST = RESULTS / "manifest_claim_scope_lint.json"
THREATS_MANIFEST = RESULTS / "manifest_threats_to_validity_audit.json"
SCHEDULE_PROXY_MANIFEST = RESULTS / "manifest_schedule_proxy_audit.json"
ULTRA_SCALE_MANIFEST = RESULTS / "manifest_screen_scale_ultra_scale64_stress.json"
ULTRA_PROFILE_MANIFEST = RESULTS / "manifest_screen_scale_ultra_scale64_resource_profile.json"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def manifest_revision_count(path: Path) -> int:
    manifest = read_json(path)
    if not manifest:
        return -1
    if "needs_revision_count" in manifest:
        return int(manifest.get("needs_revision_count", -1))
    if "unresolved_count" in manifest:
        return int(manifest.get("unresolved_count", -1))
    return -1


def manifest_rows(path: Path) -> int:
    manifest = read_json(path)
    if not manifest:
        return -1
    for key in ("rows", "profile_rows", "raw_rows", "required_boundary_count"):
        if key in manifest:
            return int(manifest.get(key, -1))
    return -1


def token_present(text: str, token: str) -> bool:
    return token.lower() in text.lower()


def status_from(condition: bool) -> str:
    return "pass" if condition else "needs revision"


def missing_tokens(text: str, tokens: tuple[str, ...]) -> list[str]:
    return [token for token in tokens if not token_present(text, token)]


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def build_rows() -> list[dict[str, str]]:
    paper = read_text(PAPER)
    support = read_text(REVIEWER_BRIEF) + "\n" + read_text(EDITOR_BRIEF)
    search_control = read_text(SEARCH_CONTROL_SUMMARY)
    learned_control = read_text(LEARNED_CONTROL_SUMMARY)

    learned_manifest = read_json(LEARNED_CONTROL_MANIFEST)
    promoted = int(learned_manifest.get("promoted_count", -1)) if learned_manifest else -1
    limited = int(learned_manifest.get("limited_count", -1)) if learned_manifest else -1
    not_promoted = int(learned_manifest.get("not_promoted_count", -1)) if learned_manifest else -1

    specs = [
        {
            "claim_anchor": "Neural component in the title",
            "evidence_gate": (
                f"learned-control rows={manifest_rows(LEARNED_CONTROL_MANIFEST)}, "
                f"promoted={promoted}, limited={limited}, not_promoted={not_promoted}"
            ),
            "condition": (
                manifest_revision_count(LEARNED_CONTROL_MANIFEST) == 0
                and promoted >= 4
                and limited >= 2
                and not_promoted >= 1
                and not missing_tokens(paper, ("Learned-control evidence audit", "limited diagnostics"))
                and not missing_tokens(support, ("Is the AI contribution overstated?", "bounded controls"))
            ),
            "allowed_claim": "Neural policies and learned gates are bounded ranking, pruning, or budget-allocation controls with promoted and limited evidence classes.",
            "excluded_claim": "Do not claim that deep learning alone explains the resource reduction.",
            "evidence_files": (
                LEARNED_CONTROL_MANIFEST,
                LEARNED_CONTROL_SUMMARY,
                REVIEWER_BRIEF,
            ),
        },
        {
            "claim_anchor": "MCTS component in the title",
            "evidence_gate": (
                f"search-control rows={manifest_rows(SEARCH_CONTROL_MANIFEST)}, "
                f"needs_revision={manifest_revision_count(SEARCH_CONTROL_MANIFEST)}"
            ),
            "condition": (
                manifest_revision_count(SEARCH_CONTROL_MANIFEST) == 0
                and "Resource-NMCTS over no-MCTS portfolio" in search_control
                and "Pareto Resource-NMCTS over no-MCTS portfolio" in search_control
                and not missing_tokens(paper, ("no-\\mcts{} portfolio", "Pareto archive"))
            ),
            "allowed_claim": "MCTS and Pareto search add measured, non-degrading increments over strengthened deterministic portfolios.",
            "excluded_claim": "Do not attribute the full improvement to MCTS alone.",
            "evidence_files": (
                SEARCH_CONTROL_MANIFEST,
                SEARCH_CONTROL_SUMMARY,
                PAPER,
            ),
        },
        {
            "claim_anchor": "Causal search-control isolation",
            "evidence_gate": (
                f"bit-flip random rows={manifest_rows(BITFLIP_RANDOM_MANIFEST)}, "
                f"frontier random rows={manifest_rows(FRONTIER_RANDOM_MANIFEST)}"
            ),
            "condition": (
                manifest_revision_count(BITFLIP_RANDOM_MANIFEST) == 0
                and manifest_revision_count(FRONTIER_RANDOM_MANIFEST) == 0
                and not missing_tokens(paper, ("random-prior", "random-depth", "same candidate"))
                and not missing_tokens(support, ("random controls", "ranking, pruning, or budget-allocation"))
            ),
            "allowed_claim": "Same-budget and same-candidate random controls support ranking and budget-allocation claims.",
            "excluded_claim": "Do not use random-control rows as speed, hardware-scheduling, or deep-RL-only evidence.",
            "evidence_files": (
                BITFLIP_RANDOM_MANIFEST,
                FRONTIER_RANDOM_MANIFEST,
                REVIEWER_BRIEF,
            ),
        },
        {
            "claim_anchor": "Resource-constrained objective",
            "evidence_gate": (
                f"schedule-proxy rows={manifest_rows(SCHEDULE_PROXY_MANIFEST)}, "
                f"needs_revision={manifest_revision_count(SCHEDULE_PROXY_MANIFEST)}"
            ),
            "condition": (
                manifest_revision_count(SCHEDULE_PROXY_MANIFEST) == 0
                and not missing_tokens(paper, ("logical-resource", "T-count", "CNOT", "ancilla"))
                and not missing_tokens(support, ("not universal dominance", "tradeoffs"))
            ),
            "allowed_claim": "The score and schedule-proxy evidence support resource-constrained logical-layer optimization with visible tradeoffs.",
            "excluded_claim": "Do not turn weighted-score wins into all-resource or hardware-mapped dominance.",
            "evidence_files": (
                SCHEDULE_PROXY_MANIFEST,
                RESULTS / "analysis_multimetric_pareto_tradeoff.md",
                REVIEWER_BRIEF,
            ),
        },
        {
            "claim_anchor": "Verified workflow rather than learned correctness",
            "evidence_gate": (
                f"algorithm rows={manifest_rows(ALGORITHM_CONTRACT_MANIFEST)}, "
                f"budget rows={manifest_rows(SEARCH_BUDGET_MANIFEST)}"
            ),
            "condition": (
                manifest_revision_count(ALGORITHM_CONTRACT_MANIFEST) == 0
                and manifest_revision_count(SEARCH_BUDGET_MANIFEST) == 0
                and not missing_tokens(paper, ("semantic correctness", "search budget", "verification"))
            ),
            "allowed_claim": "Learning controls action order, pruning, or budget; correctness comes from GF(2), emitted-circuit, truth-table, and phase verifiers.",
            "excluded_claim": "Do not imply that a neural model certifies circuit semantics.",
            "evidence_files": (
                ALGORITHM_CONTRACT_MANIFEST,
                SEARCH_BUDGET_MANIFEST,
                PAPER,
            ),
        },
        {
            "claim_anchor": "Large-scale claim boundary",
            "evidence_gate": (
                f"ultra stress rows={manifest_rows(ULTRA_SCALE_MANIFEST)}, "
                f"profile rows={manifest_rows(ULTRA_PROFILE_MANIFEST)}"
            ),
            "condition": (
                manifest_revision_count(ULTRA_SCALE_MANIFEST) == 0
                and manifest_revision_count(ULTRA_PROFILE_MANIFEST) == 0
                and not missing_tokens(paper, ("$n=48,56,64$", "complete truth-table bridge", "symbolic"))
            ),
            "allowed_claim": "Large instances are supported by symbolic term-set/emitted-circuit checks and smaller complete truth-table bridge slices.",
            "excluded_claim": "Do not claim exhaustive truth-table benchmarking or optimality for all large n.",
            "evidence_files": (
                ULTRA_SCALE_MANIFEST,
                ULTRA_PROFILE_MANIFEST,
                RESULTS / "analysis_scaling_resource_audit.md",
            ),
        },
        {
            "claim_anchor": "Logical-layer boundary",
            "evidence_gate": (
                f"claim-scope unresolved={manifest_revision_count(CLAIM_SCOPE_MANIFEST)}, "
                f"threat rows={manifest_rows(THREATS_MANIFEST)}"
            ),
            "condition": (
                manifest_revision_count(CLAIM_SCOPE_MANIFEST) == 0
                and manifest_revision_count(THREATS_MANIFEST) == 0
                and not missing_tokens(paper, ("logical-layer", "not a hardware-mapped"))
                and not missing_tokens(support, ("logical-layer", "hardware mapping"))
            ),
            "allowed_claim": "The paper is a logical-layer synthesis study.",
            "excluded_claim": "Do not claim routing, native-gate scheduling, noise, or magic-state-factory resources.",
            "evidence_files": (
                CLAIM_SCOPE_MANIFEST,
                THREATS_MANIFEST,
                REVIEWER_BRIEF,
            ),
        },
    ]

    rows: list[dict[str, str]] = []
    for spec in specs:
        rows.append(
            {
                "claim_anchor": spec["claim_anchor"],
                "status": status_from(bool(spec["condition"])),
                "evidence_gate": spec["evidence_gate"],
                "allowed_claim": spec["allowed_claim"],
                "excluded_claim": spec["excluded_claim"],
                "evidence_files": "; ".join(rel(path) for path in spec["evidence_files"]),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "claim_anchor",
        "status",
        "evidence_gate",
        "allowed_claim",
        "excluded_claim",
        "evidence_files",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Neural/MCTS Claim Calibration",
        "",
        "This audit checks whether the title-level neural MCTS framing is supported by the current evidence and bounded by explicit exclusions.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| claim anchor | status | evidence gate | allowed claim | excluded claim |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {claim_anchor} | {status} | {evidence_gate} | {allowed_claim} | {excluded_claim} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
        .replace("{", r"\{")
        .replace("}", r"\}")
    )


def latex_cell(text: str) -> str:
    text = latex_escape(text)
    replacements = {
        "Resource-NMCTS": r"\method{}",
        "MCTS": r"\mcts{}",
        "T-count": r"T-count",
        "CNOT": r"CNOT",
        "GF(2)": r"GF(2)",
        "large n": r"large $n$",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.24\linewidth}}",
        r"\toprule",
        r"Claim anchor & Evidence gate & Allowed interpretation & Excluded interpretation \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["claim_anchor"]),
                latex_cell(row["evidence_gate"]),
                latex_cell(row["allowed_claim"]),
                latex_cell(row["excluded_claim"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    paper = read_text(PAPER)
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "table": rel(TABLE),
        "table_anchor_present": r"\label{tab:neural-mcts-claim-calibration}" in paper,
        "claim_anchors": [row["claim_anchor"] for row in rows],
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    revisions = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} neural/MCTS claim-calibration rows")
    if revisions:
        print(f"warning: {revisions} neural/MCTS claim-calibration row(s) need revision")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
