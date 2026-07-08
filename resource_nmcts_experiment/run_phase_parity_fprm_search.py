#!/usr/bin/env python3
"""Fixed-polarity phase-parity search for Boolean phase oracles.

The baseline ``run_phase_parity_baseline.py`` expands the ordinary ANF of
``f(x)`` into parity-phase gadgets.  This script searches fixed-polarity
Reed-Muller forms ``g(z)=f(z xor p)`` and translates the resulting parity
phases back to the original variables.  A nonzero polarity changes both the
monomial set and the phase spectrum, so the problem becomes a concrete
phase/Rz-aware search instead of a pure cost reinterpretation.

All verification is exact in rational multiples of pi and is performed up to a
global phase, which is the natural equivalence for phase oracles.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable

from anf_utils import anf_monomials, shifted_function
from bool_func import BooleanFunction
from run_phase_parity_baseline import (
    RESULTS,
    RZ_LAMBDAS,
    SYNTH_T_PER_RZ,
    TABLES,
    evaluate_phase,
    is_clifford_angle,
    is_t_like_angle,
    load_csv,
    normalize_angle_pi,
    phase_polynomial_from_anf,
    score_from_counts,
    synth_score,
    unique_truth_rows,
    write_csv,
)


DEFAULT_RANK_METRICS = ["score", "score_rz1", "score_synth_tperrz30"]


@dataclass(frozen=True)
class CandidateStats:
    name: str
    n: int
    truth_table_hex: str
    method: str
    rank_metric: str
    polarity: int
    candidate_polarities: int
    anf_terms: int
    shifted_constant_term: int
    global_phase_pi: Fraction
    parity_gadgets: int
    rz_total: int
    rz_clifford: int
    rz_t_like: int
    rz_non_clifford: int
    rz_max_denominator: int
    T: int
    CNOT: int
    gates: int
    depth: int
    explicit_ancilla: int
    peak_ancilla: int
    score: float
    verified_up_to_global_phase: bool
    time_s: float


def translate_shifted_angles(
    terms: Iterable[int], polarity: int
) -> tuple[int, Fraction, dict[int, Fraction]]:
    """Return x-variable phase angles for ANF terms of f(x xor p).

    If a shifted parity mask has odd overlap with ``polarity``, then
    parity_z(mask) = 1 - parity_x(mask).  The coefficient is negated and the
    original coefficient becomes part of the global phase.
    """
    shifted_constant, z_angles = phase_polynomial_from_anf(terms)
    global_phase = Fraction(shifted_constant, 1)
    x_angles: defaultdict[int, Fraction] = defaultdict(Fraction)

    for mask, angle in z_angles.items():
        if (int(mask) & int(polarity)).bit_count() % 2:
            global_phase += angle
            x_angles[mask] -= angle
        else:
            x_angles[mask] += angle

    normalized: dict[int, Fraction] = {}
    for mask, angle in x_angles.items():
        reduced = normalize_angle_pi(angle)
        if reduced:
            normalized[mask] = reduced
    return shifted_constant, normalize_angle_pi(global_phase), normalized


def verify_phase_truth_up_to_global(
    n: int, truth_table: int, angles: dict[int, Fraction]
) -> tuple[bool, Fraction]:
    """Check whether phase angles equal the truth function up to a constant."""
    expected_delta: Fraction | None = None
    for x in range(1 << n):
        target = Fraction((truth_table >> x) & 1, 1)
        delta = normalize_angle_pi(evaluate_phase(angles, x) - target)
        if expected_delta is None:
            expected_delta = delta
        elif delta != expected_delta:
            return False, expected_delta
    return True, expected_delta if expected_delta is not None else Fraction(0)


def stats_for_polarity(
    row: dict[str, str],
    polarity: int,
    *,
    method: str,
    rank_metric: str,
    candidate_polarities: int,
) -> CandidateStats:
    started = time.time()
    n = int(row["n"])
    truth = int(row["truth_table_hex"], 16)
    bf = BooleanFunction(n, truth)
    shifted = shifted_function(bf, polarity)
    terms = anf_monomials(shifted)
    shifted_constant, global_phase, angles = translate_shifted_angles(terms, polarity)
    verified, observed_delta = verify_phase_truth_up_to_global(n, truth, angles)
    if verified:
        # evaluate_phase(angles, x) = f(x) - global_phase modulo 2
        # so the observed delta is the negative global phase.
        verified = normalize_angle_pi(global_phase + observed_delta) == 0

    cnot = gates = depth = 0
    rz_clifford = rz_t_like = rz_non_clifford = 0
    max_denominator = 1
    for mask, angle in angles.items():
        width = int(mask).bit_count()
        ladder = 2 * max(0, width - 1)
        cnot += ladder
        gates += ladder + 1
        depth += ladder + 1
        max_denominator = max(max_denominator, angle.denominator)
        if is_clifford_angle(angle):
            rz_clifford += 1
        elif is_t_like_angle(angle):
            rz_t_like += 1
        else:
            rz_non_clifford += 1

    score = score_from_counts(rz_t_like, cnot, depth, gates, 0)
    return CandidateStats(
        name=row["name"],
        n=n,
        truth_table_hex=row["truth_table_hex"],
        method=method,
        rank_metric=rank_metric,
        polarity=polarity,
        candidate_polarities=candidate_polarities,
        anf_terms=len(terms),
        shifted_constant_term=shifted_constant,
        global_phase_pi=global_phase,
        parity_gadgets=len(angles),
        rz_total=len(angles),
        rz_clifford=rz_clifford,
        rz_t_like=rz_t_like,
        rz_non_clifford=rz_non_clifford,
        rz_max_denominator=max_denominator,
        T=rz_t_like,
        CNOT=cnot,
        gates=gates,
        depth=depth,
        explicit_ancilla=0,
        peak_ancilla=0,
        score=score,
        verified_up_to_global_phase=verified,
        time_s=time.time() - started,
    )


def stats_to_row(stats: CandidateStats) -> dict[str, object]:
    base: dict[str, object] = {
        "name": stats.name,
        "n": stats.n,
        "method": stats.method,
        "rank_metric": stats.rank_metric,
        "polarity": stats.polarity,
        "polarity_hex": f"0x{stats.polarity:x}",
        "polarity_weight": int(stats.polarity).bit_count(),
        "candidate_polarities": stats.candidate_polarities,
        "T": stats.T,
        "CNOT": stats.CNOT,
        "depth": stats.depth,
        "gates": stats.gates,
        "explicit_ancilla": stats.explicit_ancilla,
        "peak_ancilla": stats.peak_ancilla,
        "n_qubits": stats.n,
        "score": stats.score,
        "score_lower_bound": stats.score,
        "time_s": stats.time_s,
        "anf_terms": stats.anf_terms,
        "shifted_constant_term": stats.shifted_constant_term,
        "global_phase_pi_num": stats.global_phase_pi.numerator,
        "global_phase_pi_den": stats.global_phase_pi.denominator,
        "global_phase_pi": f"{stats.global_phase_pi.numerator}/{stats.global_phase_pi.denominator}",
        "parity_gadgets": stats.parity_gadgets,
        "rz_total": stats.rz_total,
        "rz_clifford": stats.rz_clifford,
        "rz_t_like": stats.rz_t_like,
        "rz_non_clifford": stats.rz_non_clifford,
        "rz_max_denominator": stats.rz_max_denominator,
        "phase_ops": stats.T + stats.rz_non_clifford,
        "ct_supported": int(stats.rz_non_clifford == 0),
        "verified_up_to_global_phase": stats.verified_up_to_global_phase,
        "correct": "phase oracle verified up to global phase" if stats.verified_up_to_global_phase else "",
        "skipped": "",
        "error": "" if stats.verified_up_to_global_phase else "phase verification failed",
        "truth_table_hex": stats.truth_table_hex,
    }
    for lam in RZ_LAMBDAS:
        base[f"score_rz{lam:g}"] = stats.score + lam * stats.rz_non_clifford
    for t_per_rz in SYNTH_T_PER_RZ:
        base[f"score_synth_tperrz{t_per_rz}"] = synth_score(base, t_per_rz)
    return base


def metric_value(row: dict[str, object], metric: str) -> float:
    return float(row[metric])


def selection_key(row: dict[str, object], rank_metric: str) -> tuple[float, ...]:
    """Tie-break selection by stable, resource-relevant secondary metrics."""
    return (
        metric_value(row, rank_metric),
        metric_value(row, "score_synth_tperrz30"),
        metric_value(row, "score_rz1"),
        metric_value(row, "score"),
        metric_value(row, "rz_non_clifford"),
        metric_value(row, "rz_total"),
        metric_value(row, "CNOT"),
        metric_value(row, "depth"),
        metric_value(row, "polarity_weight"),
        metric_value(row, "polarity"),
    )


def select_best_rows(row: dict[str, str], rank_metrics: list[str]) -> list[dict[str, object]]:
    n = int(row["n"])
    total = 1 << n
    candidates_by_metric: dict[str, list[dict[str, object]]] = {metric: [] for metric in rank_metrics}
    for polarity in range(total):
        # Build a stats object once, then stamp each rank-specific method name.
        stats = stats_for_polarity(
            row,
            polarity,
            method="phase_parity_fprm_candidate",
            rank_metric="candidate",
            candidate_polarities=total,
        )
        base = stats_to_row(stats)
        for metric in rank_metrics:
            ranked = dict(base)
            ranked["method"] = method_name(metric)
            ranked["rank_metric"] = metric
            candidates_by_metric[metric].append(ranked)

    out = []
    for metric, candidates in candidates_by_metric.items():
        out.append(min(candidates, key=lambda item: selection_key(item, metric)))
    return out


def method_name(rank_metric: str) -> str:
    safe = rank_metric.replace("score_synth_tperrz", "tperrz").replace("score_", "")
    safe = safe.replace(".", "p")
    return f"phase_parity_fprm_opt_{safe}"


def rel(new: float, base: float) -> float:
    return (new - base) / max(abs(base), 1.0)


def compare_pairs(pairs: list[tuple[float, float]]) -> dict[str, object]:
    wins = losses = ties = 0
    relatives: list[float] = []
    for target, baseline in pairs:
        if target < baseline - 1e-9:
            wins += 1
        elif target > baseline + 1e-9:
            losses += 1
        else:
            ties += 1
        relatives.append(rel(target, baseline))
    return {
        "items": len(pairs),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": statistics.mean(relatives) if relatives else 0.0,
    }


def usable_by_name(rows: list[dict[str, object] | dict[str, str]]) -> dict[str, dict[str, object] | dict[str, str]]:
    out: dict[str, dict[str, object] | dict[str, str]] = {}
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        out[str(row["name"])] = row
    return out


def comparable_metric(row: dict[str, object] | dict[str, str], metric: str) -> float:
    if metric in row:
        return float(row[metric])
    if metric == "score_rz1.5":
        return float(row["score"]) + 1.5 * float(row["rz_non_clifford"])
    if metric.startswith("score_synth_tperrz"):
        t_per_rz = int(metric.removeprefix("score_synth_tperrz"))
        return synth_score(row, t_per_rz)
    raise KeyError(metric)


def build_summary(
    fprm_rows: list[dict[str, object]],
    anf_rows: list[dict[str, str]],
    revkit_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    anf = usable_by_name(anf_rows)
    revkit = usable_by_name(revkit_rows)
    metrics = [
        "score",
        "score_rz1",
        "score_rz1.5",
        "score_synth_tperrz30",
        "rz_non_clifford",
        "rz_total",
        "CNOT",
        "depth",
    ]
    rows_by_method: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in fprm_rows:
        if not row.get("error"):
            rows_by_method[str(row["method"])].append(row)

    summary: list[dict[str, object]] = []
    for method, method_rows in sorted(rows_by_method.items()):
        for baseline_label, baseline_rows in [
            ("phase_parity_anf", anf),
            ("external_revkit_oracle_synth", revkit),
        ]:
            for metric in metrics:
                pairs: list[tuple[float, float]] = []
                for row in method_rows:
                    base = baseline_rows.get(str(row["name"]))
                    if base is None:
                        continue
                    try:
                        pairs.append((comparable_metric(row, metric), comparable_metric(base, metric)))
                    except KeyError:
                        continue
                if pairs:
                    summary.append(
                        {
                            "target": method,
                            "baseline": baseline_label,
                            "metric": metric,
                            **compare_pairs(pairs),
                        }
                    )

        if method_rows:
            summary.append(
                {
                    "target": method,
                    "baseline": "self",
                    "metric": "resource_means",
                    "items": len(method_rows),
                    "wins": "",
                    "losses": "",
                    "ties": "",
                    "mean_relative": "",
                    "mean_T": statistics.mean(float(row["T"]) for row in method_rows),
                    "mean_CNOT": statistics.mean(float(row["CNOT"]) for row in method_rows),
                    "mean_depth": statistics.mean(float(row["depth"]) for row in method_rows),
                    "mean_score": statistics.mean(float(row["score"]) for row in method_rows),
                    "mean_rz_non_clifford": statistics.mean(float(row["rz_non_clifford"]) for row in method_rows),
                    "mean_rz_total": statistics.mean(float(row["rz_total"]) for row in method_rows),
                    "nonzero_polarity_rows": sum(1 for row in method_rows if int(row["polarity"]) != 0),
                    "mean_polarity_weight": statistics.mean(float(row["polarity_weight"]) for row in method_rows),
                }
            )
    return summary


def pct(value: float) -> str:
    return f"{value:+.2%}"


def latex_pct(value: float) -> str:
    return pct(value).replace("%", r"\%")


def latex_escape(text: str) -> str:
    replacements = {
        "_": r"\_",
        "%": r"\%",
        "&": r"\&",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def write_latex(path: Path, summary: list[dict[str, object]]) -> None:
    focus = [
        ("phase_parity_fprm_opt_score", "phase_parity_anf", "score", "FPRM-score vs ANF"),
        ("phase_parity_fprm_opt_rz1", "phase_parity_anf", "score_rz1", "FPRM-Rz1 vs ANF"),
        (
            "phase_parity_fprm_opt_tperrz30",
            "phase_parity_anf",
            "score_synth_tperrz30",
            r"FPRM-$T/R_z=30$ vs ANF",
        ),
        (
            "phase_parity_fprm_opt_tperrz30",
            "external_revkit_oracle_synth",
            "score_synth_tperrz30",
            r"FPRM-$T/R_z=30$ vs RevKit",
        ),
        (
            "phase_parity_fprm_opt_tperrz30",
            "external_revkit_oracle_synth",
            "rz_non_clifford",
            r"FPRM non-Clifford Rz vs RevKit",
        ),
        (
            "phase_parity_fprm_opt_tperrz30",
            "external_revkit_oracle_synth",
            "CNOT",
            "FPRM CNOT vs RevKit",
        ),
    ]
    lookup = {
        (row["target"], row["baseline"], row["metric"]): row
        for row in summary
        if row["baseline"] != "self"
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{lrrr}\n")
        f.write("\\toprule\n")
        f.write("Comparison & Items & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for key in focus:
            row = lookup.get(key[:3])
            if row is None:
                continue
            label = key[3]
            rendered = label if "$" in label else latex_escape(label)
            wlt = f"{row['wins']}/{row['losses']}/{row['ties']}"
            f.write(f"{rendered} & {row['items']} & {wlt} & {latex_pct(float(row['mean_relative']))} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def summary_row(
    summary: list[dict[str, object]], target: str, baseline: str, metric: str
) -> dict[str, object] | None:
    for row in summary:
        if row["target"] == target and row["baseline"] == baseline and row["metric"] == metric:
            return row
    return None


def write_analysis(
    path: Path,
    fprm_rows: list[dict[str, object]],
    summary: list[dict[str, object]],
    rank_metrics: list[str],
) -> None:
    usable = [row for row in fprm_rows if not row.get("error")]
    verified = sum(1 for row in fprm_rows if str(row.get("verified_up_to_global_phase")) == "True")
    lines = [
        "# Phase-Parity FPRM Polarity Search",
        "",
        "This run exhaustively searches fixed-polarity Reed-Muller forms for",
        "each benchmark function and translates shifted parity phases back to",
        "the original variables.  Verification is exact up to global phase.",
        "",
        f"- rows: {len(fprm_rows)}",
        f"- usable rows: {len(usable)}",
        f"- verified up to global phase: {verified}/{len(fprm_rows)}",
        f"- rank metrics: {', '.join(rank_metrics)}",
    ]
    for method in sorted({str(row["method"]) for row in usable}):
        rows = [row for row in usable if row["method"] == method]
        if not rows:
            continue
        lines.extend(
            [
                "",
                f"## {method}",
                "",
                f"- rows: {len(rows)}",
                f"- nonzero polarity selections: {sum(1 for row in rows if int(row['polarity']) != 0)}/{len(rows)}",
                f"- mean polarity weight: {statistics.mean(float(row['polarity_weight']) for row in rows):.2f}",
                f"- mean lower-bound score: {statistics.mean(float(row['score']) for row in rows):.2f}",
                f"- mean CNOT: {statistics.mean(float(row['CNOT']) for row in rows):.2f}",
                f"- mean depth: {statistics.mean(float(row['depth']) for row in rows):.2f}",
                f"- mean total Rz: {statistics.mean(float(row['rz_total']) for row in rows):.2f}",
                f"- mean non-Clifford Rz: {statistics.mean(float(row['rz_non_clifford']) for row in rows):.2f}",
                f"- max angle denominator: {max(int(row['rz_max_denominator']) for row in rows)}",
                "",
                "| baseline | metric | items | W/L/T | mean relative |",
                "|---|---|---:|---:|---:|",
            ]
        )
        for baseline in ["phase_parity_anf", "external_revkit_oracle_synth"]:
            for metric in [
                "score",
                "score_rz1",
                "score_synth_tperrz30",
                "rz_non_clifford",
                "rz_total",
                "CNOT",
                "depth",
            ]:
                row = summary_row(summary, method, baseline, metric)
                if row is None:
                    continue
                lines.append(
                    f"| {baseline} | {metric} | {row['items']} | "
                    f"{row['wins']}/{row['losses']}/{row['ties']} | {pct(float(row['mean_relative']))} |"
                )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Fixed-polarity search changes the phase polynomial itself, not only the reported cost model.",
            "- The selected polarity is rank-metric dependent, so lower-bound and synthesized-Rz objectives should be reported separately.",
            "- This remains a logic-layer phase-oracle emitter; it does not yet output approximate rotation sequences or perform hardware mapping.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(
    path: Path,
    args: argparse.Namespace,
    rows: list[dict[str, object]],
    started: float,
    rank_metrics: list[str],
) -> None:
    payload = {
        "input": str(args.input),
        "anf_baseline": str(args.anf_baseline),
        "revkit": str(args.revkit),
        "raw_out": str(args.raw_out),
        "summary": str(args.summary),
        "analysis": str(args.analysis),
        "latex_out": str(args.latex_out),
        "max_n": args.max_n,
        "rank_metrics": rank_metrics,
        "rows": len(rows),
        "verified_rows": sum(1 for row in rows if str(row.get("verified_up_to_global_phase")) == "True"),
        "elapsed_s": time.time() - started,
        "claim_boundary": "Exhaustive fixed-polarity phase-oracle search up to max_n; logic-layer Rz resource model; not hardware mapping.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_rank_metrics(raw: str) -> list[str]:
    metrics = [item.strip() for item in raw.split(",") if item.strip()]
    return metrics or list(DEFAULT_RANK_METRICS)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RESULTS / "raw_traditional_resource.csv")
    parser.add_argument("--anf-baseline", type=Path, default=RESULTS / "raw_phase_parity_anf.csv")
    parser.add_argument("--revkit", type=Path, default=RESULTS / "raw_revkit_oracle_synth_traditional.csv")
    parser.add_argument("--max-n", type=int, default=6)
    parser.add_argument("--rank-metrics", default=",".join(DEFAULT_RANK_METRICS))
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_phase_parity_fprm.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_phase_parity_fprm.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_phase_parity_fprm.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "phase_parity_fprm.tex")
    parser.add_argument("--manifest", type=Path, default=RESULTS / "manifest_phase_parity_fprm.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    started = time.time()
    rank_metrics = parse_rank_metrics(args.rank_metrics)
    rows: list[dict[str, object]] = []
    for truth_row in unique_truth_rows(args.input, args.max_n):
        rows.extend(select_best_rows(truth_row, rank_metrics))

    write_csv(args.raw_out, rows)
    summary = build_summary(rows, load_csv(args.anf_baseline), load_csv(args.revkit))
    write_csv(args.summary, summary)
    write_analysis(args.analysis, rows, summary, rank_metrics)
    write_latex(args.latex_out, summary)
    write_manifest(args.manifest, args, rows, started, rank_metrics)

    print(f"elapsed {time.time() - started:.2f}s")
    print(f"rows {len(rows)}")
    print(f"verified {sum(1 for row in rows if str(row.get('verified_up_to_global_phase')) == 'True')}/{len(rows)}")
    print(f"wrote {args.raw_out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.analysis}")
    print(f"wrote {args.latex_out}")
    print(f"wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
