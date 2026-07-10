#!/usr/bin/env python3
"""Affine-linear phase-parity search for Boolean phase oracles.

``run_phase_parity_fprm_search.py`` searches translations
``g(z)=f(z xor p)``.  This script adds an invertible linear preconditioner:

    h(y) = f(B^{-1} y),  g(z) = h(z xor p),  z = Bx xor p.

The phase polynomial is synthesized in ``z`` variables and translated back to
parity masks over the original ``x`` variables.  The transform is therefore an
algebraic rewrite of the phase polynomial, not a hardware-mapping claim and not
an added CNOT wrapper.  Verification is exact up to global phase.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
from src.affine_search import candidate_transforms, identity_rows, transform_function
from src.anf_utils import anf_monomials, shifted_function
from src.sshr_lib.bool_func import BooleanFunction
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
from run_phase_parity_fprm_search import (
    DEFAULT_RANK_METRICS,
    comparable_metric,
    compare_pairs,
    latex_pct,
    method_name as fprm_method_name,
    pct,
    selection_key as fprm_selection_key,
    usable_by_name,
)
@dataclass(frozen=True)
class CandidateStats:
    name: str
    n: int
    truth_table_hex: str
    method: str
    rank_metric: str
    transform_index: int
    transform_rows: tuple[int, ...]
    polarity: int
    candidate_transforms: int
    candidate_polarities: int
    candidate_affine_forms: int
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


def transform_mask(rows: Sequence[int], mask: int) -> int:
    """Translate a parity mask over y=B x variables back to x variables."""
    out = 0
    remaining = int(mask)
    while remaining:
        bit = (remaining & -remaining).bit_length() - 1
        out ^= int(rows[bit])
        remaining &= remaining - 1
    return out


def translate_affine_shifted_angles(
    terms: Iterable[int],
    rows: Sequence[int],
    polarity: int,
) -> tuple[int, Fraction, dict[int, Fraction]]:
    """Return x-variable phase angles for ANF terms of f(B^{-1}(z xor p))."""
    shifted_constant, z_angles = phase_polynomial_from_anf(terms)
    global_phase = Fraction(shifted_constant, 1)
    x_angles: defaultdict[int, Fraction] = defaultdict(Fraction)

    for z_mask, angle in z_angles.items():
        x_mask = transform_mask(rows, int(z_mask))
        if (int(z_mask) & int(polarity)).bit_count() % 2:
            global_phase += angle
            x_angles[x_mask] -= angle
        else:
            x_angles[x_mask] += angle

    normalized: dict[int, Fraction] = {}
    for mask, angle in x_angles.items():
        reduced = normalize_angle_pi(angle)
        if reduced:
            normalized[mask] = reduced
    return shifted_constant, normalize_angle_pi(global_phase), normalized


def verify_phase_truth_up_to_global(
    n: int, truth_table: int, global_phase: Fraction, angles: dict[int, Fraction]
) -> bool:
    observed_delta: Fraction | None = None
    for x in range(1 << n):
        target = Fraction((truth_table >> x) & 1, 1)
        delta = normalize_angle_pi(evaluate_phase(angles, x) - target)
        if observed_delta is None:
            observed_delta = delta
        elif delta != observed_delta:
            return False
    return normalize_angle_pi(global_phase + (observed_delta or Fraction(0))) == 0


def count_angles(angles: dict[int, Fraction]) -> dict[str, float]:
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
    return {
        "parity_gadgets": len(angles),
        "rz_total": len(angles),
        "rz_clifford": rz_clifford,
        "rz_t_like": rz_t_like,
        "rz_non_clifford": rz_non_clifford,
        "rz_max_denominator": max_denominator,
        "T": rz_t_like,
        "CNOT": cnot,
        "gates": gates,
        "depth": depth,
        "explicit_ancilla": 0,
        "peak_ancilla": 0,
        "score": score,
    }


def method_name(rank_metric: str) -> str:
    return fprm_method_name(rank_metric).replace("phase_parity_fprm", "phase_parity_affine_fprm")


def stats_to_row(stats: CandidateStats) -> dict[str, object]:
    transform_rows_hex = ";".join(f"0x{row:x}" for row in stats.transform_rows)
    transform_weight = sum(int(row).bit_count() for row in stats.transform_rows)
    nonidentity = stats.transform_rows != identity_rows(stats.n)
    base: dict[str, object] = {
        "name": stats.name,
        "n": stats.n,
        "method": stats.method,
        "rank_metric": stats.rank_metric,
        "transform_index": stats.transform_index,
        "transform_rows_hex": transform_rows_hex,
        "transform_weight": transform_weight,
        "transform_nonidentity": int(nonidentity),
        "polarity": stats.polarity,
        "polarity_hex": f"0x{stats.polarity:x}",
        "polarity_weight": int(stats.polarity).bit_count(),
        "candidate_transforms": stats.candidate_transforms,
        "candidate_polarities": stats.candidate_polarities,
        "candidate_affine_forms": stats.candidate_affine_forms,
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


def selection_key(row: dict[str, object], rank_metric: str) -> tuple[float, ...]:
    return (
        float(row[rank_metric]),
        float(row["score_synth_tperrz30"]),
        float(row["score_rz1"]),
        float(row["score"]),
        float(row["rz_non_clifford"]),
        float(row["rz_total"]),
        float(row["CNOT"]),
        float(row["depth"]),
        float(row["transform_nonidentity"]),
        float(row["polarity_weight"]),
        float(row["transform_index"]),
        float(row["polarity"]),
    )


def select_best_rows(
    row: dict[str, str],
    rank_metrics: list[str],
    *,
    seed: int,
    transform_budget: int,
) -> list[dict[str, object]]:
    started = time.time()
    n = int(row["n"])
    truth = int(row["truth_table_hex"], 16)
    bf = BooleanFunction(n, truth)
    transforms = candidate_transforms(n, seed + n * 10_000, transform_budget)
    candidate_polarities = 1 << n
    candidates_by_metric: dict[str, list[dict[str, object]]] = {metric: [] for metric in rank_metrics}

    for transform_index, transform in enumerate(transforms):
        transformed = transform_function(bf, transform.rows)
        for polarity in range(candidate_polarities):
            shifted = shifted_function(transformed, polarity)
            terms = anf_monomials(shifted)
            shifted_constant, global_phase, angles = translate_affine_shifted_angles(
                terms, transform.rows, polarity
            )
            counts = count_angles(angles)
            base_stats = CandidateStats(
                name=row["name"],
                n=n,
                truth_table_hex=row["truth_table_hex"],
                method="phase_parity_affine_fprm_candidate",
                rank_metric="candidate",
                transform_index=transform_index,
                transform_rows=tuple(transform.rows),
                polarity=polarity,
                candidate_transforms=len(transforms),
                candidate_polarities=candidate_polarities,
                candidate_affine_forms=len(transforms) * candidate_polarities,
                anf_terms=len(terms),
                shifted_constant_term=shifted_constant,
                global_phase_pi=global_phase,
                verified_up_to_global_phase=False,
                time_s=0.0,
                **counts,
            )
            base = stats_to_row(base_stats)
            for metric in rank_metrics:
                ranked = dict(base)
                ranked["method"] = method_name(metric)
                ranked["rank_metric"] = metric
                candidates_by_metric[metric].append(ranked)

    selected: list[dict[str, object]] = []
    elapsed = time.time() - started
    for metric, candidates in candidates_by_metric.items():
        best = dict(min(candidates, key=lambda item: selection_key(item, metric)))
        rows = tuple(int(part, 16) for part in str(best["transform_rows_hex"]).split(";"))
        transformed = transform_function(bf, rows)
        shifted = shifted_function(transformed, int(best["polarity"]))
        terms = anf_monomials(shifted)
        shifted_constant, global_phase, angles = translate_affine_shifted_angles(terms, rows, int(best["polarity"]))
        best["verified_up_to_global_phase"] = verify_phase_truth_up_to_global(n, truth, global_phase, angles)
        best["correct"] = (
            "phase oracle verified up to global phase" if best["verified_up_to_global_phase"] else ""
        )
        best["error"] = "" if best["verified_up_to_global_phase"] else "phase verification failed"
        best["time_s"] = elapsed / max(1, len(rank_metrics))
        selected.append(best)
    return selected


def fprm_baseline_method(target_method: str) -> str:
    return str(target_method).replace("phase_parity_affine_fprm", "phase_parity_fprm")


def build_fprm_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        out[str(row["method"])][str(row["name"])] = row
    return out


def build_summary(
    affine_rows: list[dict[str, object]],
    anf_rows: list[dict[str, str]],
    fprm_rows: list[dict[str, str]],
    revkit_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    anf = usable_by_name(anf_rows)
    fprm = build_fprm_lookup(fprm_rows)
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
    for row in affine_rows:
        if not row.get("error"):
            rows_by_method[str(row["method"])].append(row)

    summary: list[dict[str, object]] = []
    for method, method_rows in sorted(rows_by_method.items()):
        baselines: list[tuple[str, dict[str, dict[str, object] | dict[str, str]]]] = [
            ("phase_parity_anf", anf),
            (fprm_baseline_method(method), fprm.get(fprm_baseline_method(method), {})),
            ("external_revkit_oracle_synth", revkit),
        ]
        for baseline_label, baseline_rows in baselines:
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
                    "mean_rz_non_clifford": statistics.mean(
                        float(row["rz_non_clifford"]) for row in method_rows
                    ),
                    "mean_rz_total": statistics.mean(float(row["rz_total"]) for row in method_rows),
                    "nonidentity_transform_rows": sum(
                        1 for row in method_rows if int(row["transform_nonidentity"]) != 0
                    ),
                    "nonzero_polarity_rows": sum(1 for row in method_rows if int(row["polarity"]) != 0),
                    "mean_polarity_weight": statistics.mean(float(row["polarity_weight"]) for row in method_rows),
                    "mean_candidate_affine_forms": statistics.mean(
                        float(row["candidate_affine_forms"]) for row in method_rows
                    ),
                }
            )
    return summary


def summary_row(
    summary: list[dict[str, object]], target: str, baseline: str, metric: str
) -> dict[str, object] | None:
    for row in summary:
        if row["target"] == target and row["baseline"] == baseline and row["metric"] == metric:
            return row
    return None


def write_latex(path: Path, summary: list[dict[str, object]]) -> None:
    focus = [
        (
            "phase_parity_affine_fprm_opt_tperrz30",
            "phase_parity_fprm_opt_tperrz30",
            "score_synth_tperrz30",
            r"Affine-FPRM-$T/R_z=30$ vs FPRM",
        ),
        (
            "phase_parity_affine_fprm_opt_tperrz30",
            "phase_parity_anf",
            "score_synth_tperrz30",
            r"Affine-FPRM-$T/R_z=30$ vs ANF",
        ),
        (
            "phase_parity_affine_fprm_opt_tperrz30",
            "external_revkit_oracle_synth",
            "score_synth_tperrz30",
            r"Affine-FPRM-$T/R_z=30$ vs RevKit",
        ),
        (
            "phase_parity_affine_fprm_opt_tperrz30",
            "phase_parity_fprm_opt_tperrz30",
            "rz_non_clifford",
            r"Affine-FPRM non-Clifford Rz vs FPRM",
        ),
        (
            "phase_parity_affine_fprm_opt_score",
            "phase_parity_fprm_opt_score",
            "score",
            r"Affine-FPRM-score vs FPRM",
        ),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{lrrr}\n")
        f.write("\\toprule\n")
        f.write("Comparison & Items & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for target, baseline, metric, label in focus:
            row = summary_row(summary, target, baseline, metric)
            if row is None:
                continue
            wlt = f"{row['wins']}/{row['losses']}/{row['ties']}"
            f.write(f"{label} & {row['items']} & {wlt} & {latex_pct(float(row['mean_relative']))} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def write_analysis(
    path: Path,
    affine_rows: list[dict[str, object]],
    summary: list[dict[str, object]],
    rank_metrics: list[str],
    transform_budget: int,
) -> None:
    usable = [row for row in affine_rows if not row.get("error")]
    verified = sum(1 for row in affine_rows if str(row.get("verified_up_to_global_phase")) == "True")
    lines = [
        "# Phase-Parity Affine-FPRM Search",
        "",
        "This run searches fixed-polarity phase-parity forms after a bounded set",
        "of invertible linear input transforms.  The selected phase polynomial is",
        "translated back to original input parity masks, so the transform is an",
        "algebraic phase-polynomial rewrite rather than a hardware mapping step.",
        "",
        f"- rows: {len(affine_rows)}",
        f"- usable rows: {len(usable)}",
        f"- verified up to global phase: {verified}/{len(affine_rows)}",
        f"- rank metrics: {', '.join(rank_metrics)}",
        f"- transform budget per function: {transform_budget}",
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
                f"- nonidentity transform selections: {sum(1 for row in rows if int(row['transform_nonidentity']) != 0)}/{len(rows)}",
                f"- nonzero polarity selections: {sum(1 for row in rows if int(row['polarity']) != 0)}/{len(rows)}",
                f"- mean candidate affine forms: {statistics.mean(float(row['candidate_affine_forms']) for row in rows):.1f}",
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
        for baseline in ["phase_parity_anf", fprm_baseline_method(method), "external_revkit_oracle_synth"]:
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
            "- The identity transform is included, so affine-FPRM is score-nondegrading relative to fixed-polarity FPRM under the same rank metric.",
            "- Nonidentity transform selections indicate that linear preconditioning changes parity-gadget cancellation, not only tie-breaking.",
            "- This remains a logic-layer phase-oracle emitter; it does not output approximate rotation sequences or perform hardware mapping.",
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
        "fprm_baseline": str(args.fprm_baseline),
        "revkit": str(args.revkit),
        "raw_out": str(args.raw_out),
        "summary": str(args.summary),
        "analysis": str(args.analysis),
        "latex_out": str(args.latex_out),
        "max_n": args.max_n,
        "seed": args.seed,
        "transform_budget": args.transform_budget,
        "rank_metrics": rank_metrics,
        "rows": len(rows),
        "verified_rows": sum(1 for row in rows if str(row.get("verified_up_to_global_phase")) == "True"),
        "elapsed_s": time.time() - started,
        "claim_boundary": "Bounded affine-linear plus fixed-polarity phase-oracle search; logic-layer Rz resource model; not hardware mapping.",
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
    parser.add_argument("--fprm-baseline", type=Path, default=RESULTS / "raw_phase_parity_fprm.csv")
    parser.add_argument("--revkit", type=Path, default=RESULTS / "raw_revkit_oracle_synth_traditional.csv")
    parser.add_argument("--max-n", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260708)
    parser.add_argument("--transform-budget", type=int, default=32)
    parser.add_argument("--rank-metrics", default=",".join(DEFAULT_RANK_METRICS))
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_phase_parity_affine.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_phase_parity_affine.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_phase_parity_affine.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "phase_parity_affine.tex")
    parser.add_argument("--manifest", type=Path, default=RESULTS / "manifest_phase_parity_affine.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    started = time.time()
    rank_metrics = parse_rank_metrics(args.rank_metrics)
    rows: list[dict[str, object]] = []
    truth_rows = unique_truth_rows(args.input, args.max_n)
    for index, truth_row in enumerate(truth_rows, 1):
        rows.extend(
            select_best_rows(
                truth_row,
                rank_metrics,
                seed=args.seed,
                transform_budget=args.transform_budget,
            )
        )
        print(f"{index}/{len(truth_rows)} {truth_row['name']}", flush=True)

    write_csv(args.raw_out, rows)
    summary = build_summary(
        rows,
        load_csv(args.anf_baseline),
        load_csv(args.fprm_baseline),
        load_csv(args.revkit),
    )
    write_csv(args.summary, summary)
    write_analysis(args.analysis, rows, summary, rank_metrics, args.transform_budget)
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
