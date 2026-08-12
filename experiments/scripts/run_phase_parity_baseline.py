#!/usr/bin/env python3
"""Phase-polynomial ANF baseline for Boolean phase-oracle synthesis.

The existing Resource-NMCTS emitters synthesize bit-flip oracles with
X/CNOT/MCT gates.  RevKit's ``oracle_synth`` baseline, however, returns an
Rz-phase netlist.  This script adds a concrete internal phase/Rz-aware baseline
instead of only charging RevKit's non-Clifford rotations symbolically.

For each ANF monomial ``prod_{i in S} x_i`` it uses the integer identity

    prod S = 1 / 2^(|S|-1) * sum_{empty != T subset S}
             (-1)^(|T|+1) parity_T(x)

and emits one parity-phase gadget per merged parity mask.  The result is a
phase oracle up to a global phase when the ANF has a constant term.  Resource
counts are logic-layer proxies and do not include hardware mapping.
"""
from __future__ import annotations

# --- project root bootstrap (so this script runs standalone) ---
import sys as _sys
from pathlib import Path as _Path
_PROJ_ROOT = _Path(__file__).resolve().parent.parent
if str(_PROJ_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJ_ROOT))


import argparse
import csv
import json
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from src.anf_utils import anf_monomials
from run_external_baselines import DEFAULT_WEIGHTS


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

RZ_LAMBDAS = [1.0, 1.5, 2.0, 4.0, 10.0]
SYNTH_T_PER_RZ = [30, 60, 100]


@dataclass(frozen=True)
class PhaseParityStats:
    name: str
    n: int
    truth_table_hex: str
    anf_terms: int
    constant_term: int
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


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def unique_truth_rows(path: Path, max_n: int | None) -> list[dict[str, str]]:
    rows = load_csv(path)
    by_name: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("skipped") or row.get("error"):
            continue
        if not row.get("truth_table_hex"):
            continue
        n = int(row["n"])
        if max_n is not None and n > max_n:
            continue
        by_name.setdefault(row["name"], row)
    return sorted(by_name.values(), key=lambda item: (int(item["n"]), item["name"]))


def normalize_angle_pi(frac: Fraction) -> Fraction:
    """Normalize an angle coefficient modulo 2*pi in units of pi."""
    return frac - 2 * (frac // 2)


def add_monomial_phase(acc: defaultdict[int, Fraction], term: int) -> None:
    degree = int(term).bit_count()
    if degree <= 0:
        return
    denom = 1 << (degree - 1)
    sub = term
    while sub:
        sign = 1 if int(sub).bit_count() % 2 else -1
        acc[sub] += Fraction(sign, denom)
        sub = (sub - 1) & term


def phase_polynomial_from_anf(terms: Iterable[int]) -> tuple[int, dict[int, Fraction]]:
    constant = 0
    angles: defaultdict[int, Fraction] = defaultdict(Fraction)
    for raw in terms:
        term = int(raw)
        if term == 0:
            constant ^= 1
        else:
            add_monomial_phase(angles, term)

    normalized: dict[int, Fraction] = {}
    for mask, angle in angles.items():
        reduced = normalize_angle_pi(angle)
        if reduced:
            normalized[mask] = reduced
    return constant, normalized


def evaluate_phase(angles: dict[int, Fraction], x: int) -> Fraction:
    total = Fraction(0)
    for mask, angle in angles.items():
        if (x & mask).bit_count() % 2:
            total += angle
    return normalize_angle_pi(total)


def verify_phase_truth(n: int, truth_table: int, constant: int, angles: dict[int, Fraction]) -> bool:
    for x in range(1 << n):
        expected = ((truth_table >> x) & 1) ^ constant
        if evaluate_phase(angles, x) != expected:
            return False
    return True


def is_clifford_angle(angle: Fraction) -> bool:
    return (angle * 2).denominator == 1


def is_t_like_angle(angle: Fraction) -> bool:
    return not is_clifford_angle(angle) and (angle * 4).denominator == 1


def score_from_counts(T: float, CNOT: float, depth: float, gates: float, peak_ancilla: float) -> float:
    return (
        DEFAULT_WEIGHTS["t"] * T
        + DEFAULT_WEIGHTS["cnot"] * CNOT
        + DEFAULT_WEIGHTS["depth"] * depth
        + DEFAULT_WEIGHTS["gates"] * gates
        + DEFAULT_WEIGHTS["ancilla"] * peak_ancilla
    )


def synth_score(row: dict[str, object], t_per_rz: int) -> float:
    non_clifford = float(row.get("rz_non_clifford", 0) or 0)
    extra_t = t_per_rz * non_clifford
    return score_from_counts(
        float(row["T"]) + extra_t,
        float(row["CNOT"]),
        float(row["depth"]) + extra_t,
        float(row["gates"]) + extra_t,
        float(row["peak_ancilla"]),
    )


def synthesize_phase_parity(row: dict[str, str]) -> PhaseParityStats:
    started = time.time()
    n = int(row["n"])
    truth = int(row["truth_table_hex"], 16)
    # Import lazily to keep module-level imports usable from tests/scripts.
    from src.sshr_lib.bool_func import BooleanFunction

    terms = anf_monomials(BooleanFunction(n, truth))
    constant, angles = phase_polynomial_from_anf(terms)
    verified = verify_phase_truth(n, truth, constant, angles)

    cnot = gates = depth = 0
    rz_clifford = rz_t_like = rz_non_clifford = 0
    max_denominator = 1
    for mask, angle in angles.items():
        width = int(mask).bit_count()
        cnot += 2 * max(0, width - 1)
        gates += 2 * max(0, width - 1) + 1
        depth += 2 * max(0, width - 1) + 1
        max_denominator = max(max_denominator, angle.denominator)
        if is_clifford_angle(angle):
            rz_clifford += 1
        elif is_t_like_angle(angle):
            rz_t_like += 1
        else:
            rz_non_clifford += 1

    score = score_from_counts(rz_t_like, cnot, depth, gates, 0)
    return PhaseParityStats(
        name=row["name"],
        n=n,
        truth_table_hex=row["truth_table_hex"],
        anf_terms=len(terms),
        constant_term=constant,
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


def stats_to_row(stats: PhaseParityStats) -> dict[str, object]:
    base: dict[str, object] = {
        "name": stats.name,
        "n": stats.n,
        "method": "phase_parity_anf",
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
        "constant_term_global_phase": stats.constant_term,
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
        key = f"score_rz{lam:g}"
        base[key] = stats.score + lam * stats.rz_non_clifford
    for t_per_rz in SYNTH_T_PER_RZ:
        base[f"score_synth_tperrz{t_per_rz}"] = synth_score(base, t_per_rz)
    return base


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    preferred = [
        "name",
        "n",
        "method",
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "n_qubits",
        "score",
        "score_lower_bound",
        *[f"score_rz{lam:g}" for lam in RZ_LAMBDAS],
        *[f"score_synth_tperrz{v}" for v in SYNTH_T_PER_RZ],
        "time_s",
        "anf_terms",
        "constant_term_global_phase",
        "parity_gadgets",
        "rz_total",
        "rz_clifford",
        "rz_t_like",
        "rz_non_clifford",
        "rz_max_denominator",
        "phase_ops",
        "ct_supported",
        "verified_up_to_global_phase",
        "correct",
        "skipped",
        "error",
        "truth_table_hex",
    ]
    fieldnames = sorted({key for row in rows for key in row})
    ordered = [key for key in preferred if key in fieldnames]
    ordered.extend(key for key in fieldnames if key not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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


def by_name(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        out[row["name"]] = row
    return out


def f(row: dict[str, object], key: str) -> float:
    return float(row[key])


def build_summary(phase_rows: list[dict[str, object]], revkit_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    revkit = by_name(revkit_rows)
    comparisons: list[tuple[str, list[tuple[float, float]]]] = [
        ("lower_bound_score", []),
        ("score_plus_1_per_rz", []),
        ("score_plus_1p5_per_rz", []),
        ("score_plus_2_per_rz", []),
        ("score_plus_4_per_rz", []),
        ("synth_tperrz30_score", []),
        ("synth_tperrz60_score", []),
        ("non_clifford_rz", []),
        ("total_rz", []),
        ("CNOT", []),
        ("depth", []),
    ]
    lookup = {name: pairs for name, pairs in comparisons}
    for phase in phase_rows:
        rev = revkit.get(str(phase["name"]))
        if rev is None:
            continue
        lookup["lower_bound_score"].append((f(phase, "score"), float(rev["score"])))
        for label, lam in [
            ("score_plus_1_per_rz", 1.0),
            ("score_plus_1p5_per_rz", 1.5),
            ("score_plus_2_per_rz", 2.0),
            ("score_plus_4_per_rz", 4.0),
        ]:
            phase_score = f(phase, "score") + lam * f(phase, "rz_non_clifford")
            rev_score = float(rev["score"]) + lam * float(rev["rz_non_clifford"])
            lookup[label].append((phase_score, rev_score))
        for t_per_rz in [30, 60]:
            lookup[f"synth_tperrz{t_per_rz}_score"].append(
                (f(phase, f"score_synth_tperrz{t_per_rz}"), synth_score(rev, t_per_rz))
            )
        lookup["non_clifford_rz"].append((f(phase, "rz_non_clifford"), float(rev["rz_non_clifford"])))
        lookup["total_rz"].append((f(phase, "rz_total"), float(rev["rz_total"])))
        lookup["CNOT"].append((f(phase, "CNOT"), float(rev["CNOT"])))
        lookup["depth"].append((f(phase, "depth"), float(rev["depth"])))

    summary: list[dict[str, object]] = []
    for metric, pairs in comparisons:
        if not pairs:
            continue
        stats = compare_pairs(pairs)
        summary.append({"target": "phase_parity_anf", "baseline": "external_revkit_oracle_synth", "metric": metric, **stats})

    if phase_rows:
        summary.append(
            {
                "target": "phase_parity_anf",
                "baseline": "self",
                "metric": "resource_means",
                "items": len(phase_rows),
                "wins": "",
                "losses": "",
                "ties": "",
                "mean_relative": "",
                "mean_T": statistics.mean(f(row, "T") for row in phase_rows),
                "mean_CNOT": statistics.mean(f(row, "CNOT") for row in phase_rows),
                "mean_depth": statistics.mean(f(row, "depth") for row in phase_rows),
                "mean_score": statistics.mean(f(row, "score") for row in phase_rows),
                "mean_rz_non_clifford": statistics.mean(f(row, "rz_non_clifford") for row in phase_rows),
                "mean_rz_total": statistics.mean(f(row, "rz_total") for row in phase_rows),
            }
        )
    return summary


def pct(value: float) -> str:
    return f"{value:+.2%}"


def latex_pct(value: float) -> str:
    return pct(value).replace("%", r"\%")


def latex_escape(text: str) -> str:
    return text.replace("_", r"\_")


def write_latex(path: Path, summary: list[dict[str, object]]) -> None:
    labels = {
        "lower_bound_score": "lower-bound score",
        "score_plus_1_per_rz": "score+1/Rz",
        "score_plus_1p5_per_rz": "score+1.5/Rz",
        "score_plus_2_per_rz": "score+2/Rz",
        "synth_tperrz30_score": "$T/R_z=30$ proxy",
        "non_clifford_rz": "non-Clifford Rz",
        "total_rz": "total Rz",
    }
    focus = set(labels)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{lrrrr}\n")
        f.write("\\toprule\n")
        f.write("Metric & Items & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for row in summary:
            metric = str(row["metric"])
            if metric not in focus:
                continue
            wlt = f"{row['wins']}/{row['losses']}/{row['ties']}"
            label = labels[metric]
            rendered = label if "$" in label else latex_escape(label)
            f.write(f"{rendered} & {row['items']} & {wlt} & {latex_pct(float(row['mean_relative']))} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def write_analysis(path: Path, phase_rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    usable = [row for row in phase_rows if not row.get("error")]
    verified = sum(1 for row in phase_rows if str(row.get("verified_up_to_global_phase")) == "True")
    lines = [
        "# Phase-Parity ANF Baseline",
        "",
        "This run emits a concrete parity-phase ANF baseline.  It expands each",
        "ANF monomial into merged parity-phase gadgets using exact rational",
        "coefficients and verifies every function as a phase oracle up to a",
        "global phase.",
        "",
        "This is a phase/Rz-aware internal emitter.  It is not the same target",
        "as the existing bit-flip Resource-NMCTS circuits, and it is still a",
        "logic-layer resource model rather than hardware mapping.",
        "",
        f"- rows: {len(phase_rows)}",
        f"- usable rows: {len(usable)}",
        f"- verified up to global phase: {verified}/{len(phase_rows)}",
    ]
    if usable:
        lines.extend(
            [
                f"- mean lower-bound score: {statistics.mean(f(row, 'score') for row in usable):.2f}",
                f"- mean CNOT: {statistics.mean(f(row, 'CNOT') for row in usable):.2f}",
                f"- mean depth: {statistics.mean(f(row, 'depth') for row in usable):.2f}",
                f"- mean total Rz: {statistics.mean(f(row, 'rz_total') for row in usable):.2f}",
                f"- mean non-Clifford Rz: {statistics.mean(f(row, 'rz_non_clifford') for row in usable):.2f}",
                f"- max angle denominator: {max(int(row['rz_max_denominator']) for row in usable)}",
            ]
        )
    lines.extend(
        [
            "",
            "## Comparison with RevKit `oracle_synth`",
            "",
            "Rows compare the internal phase-parity ANF emitter against RevKit's",
            "Rz-phase lower-bound netlist.  Lower is better for every metric.",
            "",
            "| metric | items | W/L/T | mean relative |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in summary:
        if row["baseline"] != "external_revkit_oracle_synth":
            continue
        lines.append(
            f"| {row['metric']} | {row['items']} | {row['wins']}/{row['losses']}/{row['ties']} | "
            f"{pct(float(row['mean_relative']))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The emitter is exact up to global phase, which is the natural equivalence for phase oracles.",
            "- The lower-bound score charges only T-like Rz rotations; non-Clifford Rz rotations are reported separately.",
            "- If this baseline is poor under lower-bound or synthesized-Rz scoring, that is useful evidence: a naive parity-phase expansion is not enough, and a learned phase/Rz-aware search must reduce parity gadget count or rotation spectrum.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, args: argparse.Namespace, rows: list[dict[str, object]], started: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "input": str(args.input),
        "revkit": str(args.revkit),
        "raw_out": str(args.raw_out),
        "summary": str(args.summary),
        "analysis": str(args.analysis),
        "latex_out": str(args.latex_out),
        "max_n": args.max_n,
        "rows": len(rows),
        "verified_rows": sum(1 for row in rows if str(row.get("verified_up_to_global_phase")) == "True"),
        "elapsed_s": time.time() - started,
        "claim_boundary": "Phase-oracle emitter up to global phase; logic-layer Rz resource model; not hardware mapping.",
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RESULTS / "raw_traditional_resource.csv")
    parser.add_argument("--revkit", type=Path, default=RESULTS / "raw_revkit_oracle_synth_traditional.csv")
    parser.add_argument("--max-n", type=int, default=6)
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_phase_parity_anf.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_phase_parity_anf.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_phase_parity_anf.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "phase_parity_anf.tex")
    parser.add_argument("--manifest", type=Path, default=RESULTS / "manifest_phase_parity_anf.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    started = time.time()
    rows = [stats_to_row(synthesize_phase_parity(row)) for row in unique_truth_rows(args.input, args.max_n)]
    write_csv(args.raw_out, rows)
    summary = build_summary(rows, load_csv(args.revkit))
    write_csv(args.summary, summary)
    write_analysis(args.analysis, rows, summary)
    write_latex(args.latex_out, summary)
    write_manifest(args.manifest, args, rows, started)
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
