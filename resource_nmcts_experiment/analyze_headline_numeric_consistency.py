#!/usr/bin/env python3
"""Audit headline manuscript numbers against generated evidence files.

The submission abstract carries many compressed numeric claims.  This audit
recomputes the central claims from CSV evidence where practical and checks that
both author and anonymous LaTeX sources still contain the matching headline
tokens.  It is intentionally narrow: it protects numbers that reviewers are
likely to verify first rather than re-running experiments.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER_DIR = THIS_DIR / "paper_latex"
AUTHOR_TEX = PAPER_DIR / "resource_nmcts_submission_v1.tex"
ANONYMOUS_TEX = PAPER_DIR / "resource_nmcts_submission_anonymous.tex"

RAW_TRADITIONAL = RESULTS / "raw_traditional_resource.csv"
PAIRED_STATS = RESULTS / "summary_paired_statistical_evidence.csv"
WEIGHT_ROBUSTNESS = RESULTS / "summary_weight_robustness.csv"
SPARSE_FRONTIER = RESULTS / "summary_sparse_depth_frontier.csv"
DEPTH4_GATE = RESULTS / "summary_sparse_depth4_gate_threshold_operating_points.csv"
PHASE_RANDOM_CONTROL = RESULTS / "summary_phase_policy_random_control.csv"
EVIDENCE_MATRIX = RESULTS / "summary_comparison_evidence_matrix.csv"
VALIDATION_SOURCE = PAPER_DIR / "figures" / "submission_v36" / "source_data" / "fig5_validation.csv"


@dataclass(frozen=True)
class Claim:
    claim: str
    computed: str
    expected: str
    source: str
    tokens: tuple[str, ...]
    numeric_ok: bool
    evidence_note: str


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def norm_latex(text: str) -> str:
    text = text.replace(r"\%", "%")
    text = text.replace("$", "")
    text = text.replace(r"\leq", "<=")
    text = text.replace(r"\ttable{}", "truth table")
    text = re.sub(r"\\[a-zA-Z]+\{\}", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def float_close(actual: float, expected: float, tol: float = 0.005) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= tol


def pct(value: float) -> str:
    return f"{value:.2f}%"


def wlt(row: dict[str, str]) -> str:
    return f"{int(row['wins'])}/{int(row['losses'])}/{int(row['ties'])}"


def find_row(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    return {}


def valid_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def traditional_pairs(metric: str) -> tuple[int, float]:
    rows = read_csv(RAW_TRADITIONAL)
    by_method: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        if row.get("skipped"):
            continue
        if row.get("correct") and not valid_bool(row["correct"]):
            continue
        by_method.setdefault(row.get("method", ""), {})[row.get("name", "")] = row
    target = by_method.get("and_pareto_resource_nmcts", {})
    baseline = by_method.get("direct_anf", {})
    names = sorted(set(target) & set(baseline))
    rels: list[float] = []
    for name in names:
        base = float(baseline[name][metric])
        tgt = float(target[name][metric])
        if base == 0:
            continue
        rels.append((tgt - base) / base)
    return len(names), 100.0 * sum(rels) / len(rels)


def paired_claims() -> list[Claim]:
    rows = read_csv(PAIRED_STATS)
    specs = [
        ("n<=6 Pareto vs direct ANF", "score", 177, "172/1/4", -67.80, ("177", "67.80%")),
        ("n<=6 Pareto vs ESOP beam", "score", 177, "174/0/3", -36.09, ("174/0/3",)),
        ("n<=6 Pareto vs ESOP-MILP", "score", 177, "167/3/7", -29.84, ("167/3/7",)),
        ("n<=6 Pareto vs SSHR-H", "score", 177, "173/4/0", -41.06, ("173/4/0",)),
        ("ROS-style LUT best-K", "score", 309, "309/0/0", -84.27, ("309/0/0",)),
        ("mockturtle XAG n<=6", "score", 177, "166/11/0", -31.50, ("166/11/0",)),
        ("mockturtle XAG n=14", "score", 64, "64/0/0", -91.49, ("64/0/0",)),
        ("CirKit AIG/MC n<=6", "score", 177, "177/0/0", -62.34, ("177/0/0",)),
        ("CirKit AIG/MC n=14", "score", 64, "64/0/0", -94.46, ("64/0/0",)),
        ("RevKit CLI exact oracle", "score", 177, "173/0/4", -67.28, ("173/0/4",)),
    ]
    claims: list[Claim] = []
    for comparison, metric, pairs, expected_wlt, expected_mean, tokens in specs:
        row = find_row(rows, comparison=comparison, metric=metric)
        actual_pairs = int(row.get("pairs", "-1")) if row else -1
        actual_wlt = wlt(row) if row else "missing"
        actual_mean = float(row.get("mean_relative_pct", "nan")) if row else float("nan")
        numeric_ok = (
            bool(row)
            and actual_pairs == pairs
            and actual_wlt == expected_wlt
            and float_close(actual_mean, expected_mean)
        )
        claims.append(
            Claim(
                claim=f"{comparison} paired score",
                computed=f"pairs={actual_pairs}; W/L/T={actual_wlt}; mean={pct(actual_mean)}",
                expected=f"pairs={pairs}; W/L/T={expected_wlt}; mean={pct(expected_mean)}",
                source="results/summary_paired_statistical_evidence.csv",
                tokens=tokens,
                numeric_ok=numeric_ok,
                evidence_note=f"target={row.get('target_method', 'missing')}; baseline={row.get('baseline_method', 'missing')}"
                if row
                else "missing row",
            )
        )
    return claims


def traditional_t_claim() -> Claim:
    pairs, mean_rel = traditional_pairs("T")
    return Claim(
        claim="n<=6 Pareto vs direct ANF mean T-count reduction",
        computed=f"pairs={pairs}; mean={pct(mean_rel)}",
        expected="pairs=177; mean=-73.92%",
        source="results/raw_traditional_resource.csv",
        tokens=("73.92%",),
        numeric_ok=pairs == 177 and float_close(mean_rel, -73.92),
        evidence_note="Pairwise mean relative T-count over correct non-skipped direct_anf and and_pareto_resource_nmcts rows.",
    )


def sparse_frontier_claim() -> Claim:
    rows = read_csv(SPARSE_FRONTIER)
    bridge = [row for row in rows if row.get("source", "").startswith("truth-bridge")]
    values = sorted(abs(100.0 * float(row["mean_rel_time"])) for row in bridge)
    min_value = values[0] if values else float("nan")
    max_value = values[-1] if values else float("nan")
    all_tied = bool(bridge) and all(row.get("score_wlt") in {"0/0/6", "0/0/72", "0/0/96"} for row in rows)
    numeric_ok = len(bridge) == 3 and float_close(min_value, 24.94) and float_close(max_value, 28.88) and all_tied
    return Claim(
        claim="sparse depth-2/4 frontier bridge time reduction",
        computed=f"bridge_rows={len(bridge)}; time_range={pct(min_value)}--{pct(max_value)}; score_tied={all_tied}",
        expected="bridge_rows=3; time_range=24.94%--28.88%; score_tied=True",
        source="results/summary_sparse_depth_frontier.csv",
        tokens=("24.94--28.88%",),
        numeric_ok=numeric_ok,
        evidence_note="Range is computed from truth-bridge n=23, n=24, and n=25 rows.",
    )


def depth4_gate_claim() -> Claim:
    rows = read_csv(DEPTH4_GATE)
    row = find_row(rows, label="selected")
    pairs = int(row.get("pairs", "-1")) if row else -1
    wlt_score = row.get("score_wlt_vs_sparse", "missing") if row else "missing"
    time_saving = -100.0 * float(row.get("mean_rel_time_vs_sparse", "nan")) if row else float("nan")
    numeric_ok = pairs == 144 and wlt_score == "0/0/144" and float_close(time_saving, 13.43)
    return Claim(
        claim="learned sparse depth-4 gate selected operating point",
        computed=f"pairs={pairs}; score_wlt_vs_sparse={wlt_score}; time_saving={pct(time_saving)}",
        expected="pairs=144; score_wlt_vs_sparse=0/0/144; time_saving=13.43%",
        source="results/summary_sparse_depth4_gate_threshold_operating_points.csv",
        tokens=("144-pair", "13.43%"),
        numeric_ok=numeric_ok,
        evidence_note=f"threshold={row.get('threshold', 'missing') if row else 'missing'}",
    )


def phase_shortlist_claim() -> Claim:
    rows = read_csv(PHASE_RANDOM_CONTROL)
    row = find_row(rows, policy="diverse", topk="512")
    items = int(row.get("functions", "-1")) if row else -1
    mean_rel = 100.0 * float(row.get("mean_relative", "nan")) if row else float("nan")
    # The manuscript rounds this near-zero score delta as within 0.01%.
    within = abs(mean_rel) <= 0.0125
    numeric_ok = items == 38 and within
    return Claim(
        claim="phase diverse top-512 shortlist tracks wide search",
        computed=f"held_out_items={items}; exact_scored=512/8192; mean_delta={pct(mean_rel)}",
        expected="held_out_items=38; exact_scored=512/8192; |mean_delta|<=0.0125%",
        source="results/summary_phase_policy_random_control.csv",
        tokens=("512 of 8192", "0.01%", "T/R_z=30"),
        numeric_ok=numeric_ok,
        evidence_note=f"target_method={row.get('target_method', 'missing') if row else 'missing'}",
    )


def validation_scale_claim() -> Claim:
    rows = read_csv(EVIDENCE_MATRIX)
    verified_total = 0
    bridge_ok = False
    for row in rows:
        value = row.get("verified_rows", "")
        if row.get("evidence_block") == "Complete truth-table bridges":
            bridge_ok = "400/400" in value
        for match in re.finditer(r"(\d+)/\1", value):
            verified_total += int(match.group(1))
    numeric_ok = verified_total == 15762 and bridge_ok
    return Claim(
        claim="headline verification row count",
        computed=f"verified_total={verified_total:,}; bridge_400_400={bridge_ok}",
        expected="verified_total=15,762; bridge_400_400=True",
        source="results/summary_comparison_evidence_matrix.csv",
        tokens=("15,762", "400/400"),
        numeric_ok=numeric_ok,
        evidence_note="Sums all exact X/X verified-row entries in the comparison evidence matrix.",
    )


def build_claims() -> list[Claim]:
    return [
        traditional_t_claim(),
        *paired_claims(),
        phase_shortlist_claim(),
        sparse_frontier_claim(),
        depth4_gate_claim(),
        validation_scale_claim(),
    ]


def token_status(tokens: tuple[str, ...], text: str) -> tuple[bool, str]:
    missing = [token for token in tokens if token not in text]
    return not missing, ",".join(missing) if missing else "none"


def build_rows() -> list[dict[str, str]]:
    author = norm_latex(read_text(AUTHOR_TEX))
    anonymous = norm_latex(read_text(ANONYMOUS_TEX))
    rows: list[dict[str, str]] = []
    for claim in build_claims():
        author_ok, author_missing = token_status(claim.tokens, author)
        anonymous_ok, anonymous_missing = token_status(claim.tokens, anonymous)
        status = "pass" if claim.numeric_ok and author_ok and anonymous_ok else "needs revision"
        rows.append(
            {
                "claim": claim.claim,
                "status": status,
                "computed": claim.computed,
                "expected": claim.expected,
                "source": claim.source,
                "manuscript_tokens": "; ".join(claim.tokens),
                "author_missing_tokens": author_missing,
                "anonymous_missing_tokens": anonymous_missing,
                "evidence_note": claim.evidence_note,
                "next_action": "No action needed."
                if status == "pass"
                else "Regenerate or revise the evidence source and update both author and anonymous abstracts.",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "claim",
        "status",
        "computed",
        "expected",
        "source",
        "manuscript_tokens",
        "author_missing_tokens",
        "anonymous_missing_tokens",
        "evidence_note",
        "next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})}
    lines = [
        "# Headline Numeric Consistency Audit",
        "",
        "This audit recomputes central abstract numbers from generated evidence files and checks that both author and anonymous LaTeX sources contain the corresponding headline tokens.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Claims",
            "",
            "| claim | status | computed | expected | source | manuscript tokens |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['claim']} | {row['status']} | {row['computed']} | {row['expected']} | `{row['source']}` | {row['manuscript_tokens']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts = {
        status: sum(1 for row in rows if row["status"] == status)
        for status in sorted({row["status"] for row in rows})
    }
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "claims": len(rows),
        "needs_revision_count": status_counts.get("needs revision", 0),
        "status_counts": status_counts,
        "source_files": sorted({row["source"] for row in rows}),
        "manuscripts": {
            "author": str(AUTHOR_TEX.relative_to(THIS_DIR)),
            "anonymous": str(ANONYMOUS_TEX.relative_to(THIS_DIR)),
        },
        "outputs": {
            "summary": "results/summary_headline_numeric_consistency.csv",
            "analysis": "results/analysis_headline_numeric_consistency.md",
            "manifest": "results/manifest_headline_numeric_consistency.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_headline_numeric_consistency.csv", rows)
    write_markdown(RESULTS / "analysis_headline_numeric_consistency.md", rows)
    write_manifest(RESULTS / "manifest_headline_numeric_consistency.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} headline numeric consistency row(s)")
    if failures:
        print(f"warning: {failures} headline row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
