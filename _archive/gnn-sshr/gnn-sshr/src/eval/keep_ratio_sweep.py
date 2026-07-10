"""keep_ratio sweep harness.

For each ratio in ``--ratios`` and each method in {rule, lgb, gnn}, run the
pruned-ILP pipeline against every truth table in the test set and record
totals (T, CNOT, Anc), feasibility (n_skipped) and wallclock.

The harness is a thin wrapper around the public helpers in
:mod:`eval.compare_methods` so it never duplicates pruned_search internals.
The expensive bits (test-set construction, LGB/GNN score functions, the
``_run_pruned_ilp_method`` driver) are imported and reused.

CLI
---
::

    PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.keep_ratio_sweep \\
        --csv data/ilp/n3_ilp_cnot.csv --n 3 \\
        --gnn-ckpt results/models/gnn_pruner_n3.pt \\
        --lgb-ckpt results/models/lgbm_n3.txt \\
        --ratios 0.10,0.15,0.20,0.30,0.50 \\
        --out    results/tables/keep_ratio_sweep_n3.csv \\
        --out-md results/tables/keep_ratio_sweep_n3.md
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# sys.path: support PYTHONPATH=src and direct invocation alike.
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_SRC = _THIS.parent.parent  # .../src
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sshr_core.bool_func import BooleanFunction  # noqa: E402

from eval.compare_methods import (  # noqa: E402
    HAS_GUROBI,
    Row,
    build_test_set,
    _run_pruned_ilp_method,
    _rule_scores,
    _lgb_score_fn,
    _gnn_score_fn,
)


METHODS = ("rule", "lgb", "gnn")

CSV_COLUMNS = (
    "ratio",
    "method",
    "n_evaluated",
    "n_skipped",
    "T_total",
    "CNOT_total",
    "Anc_total",
    "wallclock_s",
)


# ---------------------------------------------------------------------------
# Per-cell evaluation
# ---------------------------------------------------------------------------

def _resolve_score_fn(
    method: str,
    *,
    lgb_ckpt: Optional[Path],
    gnn_ckpt: Optional[Path],
) -> Tuple[Optional[Callable], str]:
    """Return ``(score_fn, error_note)``.  ``score_fn`` is ``None`` if unavailable."""
    if method == "rule":
        return _rule_scores, ""
    if method == "lgb":
        if lgb_ckpt is None or not lgb_ckpt.exists():
            return None, "missing --lgb-ckpt"
        try:
            return _lgb_score_fn(lgb_ckpt), ""
        except Exception as exc:  # noqa: BLE001
            return None, f"load-error: {exc}"
    if method == "gnn":
        if gnn_ckpt is None or not gnn_ckpt.exists():
            return None, "missing --gnn-ckpt"
        try:
            return _gnn_score_fn(gnn_ckpt), ""
        except Exception as exc:  # noqa: BLE001
            return None, f"load-error: {exc}"
    raise ValueError(f"unknown method {method!r}")


def _eval_cell(
    method: str,
    ratio: float,
    test_set: Sequence[BooleanFunction],
    n: int,
    timeout: float,
    score_fn: Optional[Callable],
    err_note: str,
) -> Row:
    method_name = f"{method}_pruned_ilp"
    if score_fn is None:
        return Row(
            method=method_name, n=n,
            n_skipped=len(test_set),
            note=err_note or "score-fn unavailable",
        )
    if not HAS_GUROBI:
        return Row(
            method=method_name, n=n,
            n_skipped=len(test_set),
            note="skipped (no Gurobi)",
        )
    return _run_pruned_ilp_method(
        method_name, test_set, n,
        score_fn=score_fn,
        keep_ratio=ratio,
        timeout=timeout,
        note_prefix=f"keep={ratio:g}",
    )


# ---------------------------------------------------------------------------
# Sweep driver
# ---------------------------------------------------------------------------

def run_sweep(
    n: int,
    csv_path: Optional[Path],
    ratios: Sequence[float],
    *,
    lgb_ckpt: Optional[Path],
    gnn_ckpt: Optional[Path],
    timeout: float = 15.0,
) -> List[Dict]:
    """Run the full sweep and return a list of result dicts (CSV schema)."""
    test_set = build_test_set(n, csv_path)

    # Cache score_fns once; fail-fast notes propagate to every ratio.
    score_cache: Dict[str, Tuple[Optional[Callable], str]] = {
        m: _resolve_score_fn(m, lgb_ckpt=lgb_ckpt, gnn_ckpt=gnn_ckpt)
        for m in METHODS
    }

    results: List[Dict] = []
    for ratio in ratios:
        for method in METHODS:
            score_fn, err_note = score_cache[method]
            t0 = time.time()
            row = _eval_cell(
                method, ratio, test_set, n,
                timeout=timeout,
                score_fn=score_fn,
                err_note=err_note,
            )
            wall = time.time() - t0
            results.append({
                "ratio": ratio,
                "method": method,
                "n_evaluated": row.n_evaluated,
                "n_skipped": row.n_skipped,
                "T_total": "" if row.T is None else int(row.T),
                "CNOT_total": "" if row.CNOT is None else int(row.CNOT),
                "Anc_total": "" if row.Anc is None else int(row.Anc),
                "wallclock_s": f"{wall:.3f}",
                "_note": row.note,
            })
            print(
                f"[{method:>4} r={ratio:.2f}] "
                f"CNOT={row.CNOT} T={row.T} Anc={row.Anc} "
                f"eval={row.n_evaluated} skip={row.n_skipped} "
                f"wall={wall:.2f}s note={row.note}",
                flush=True,
            )
    return results


# ---------------------------------------------------------------------------
# CSV / Markdown rendering
# ---------------------------------------------------------------------------

def _write_csv(rows: List[Dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_COLUMNS})


def _pivot(rows: List[Dict], metric: str) -> Tuple[List[float], List[str], Dict]:
    ratios = sorted({r["ratio"] for r in rows})
    methods = list(METHODS)
    table: Dict[Tuple[float, str], object] = {}
    for r in rows:
        table[(r["ratio"], r["method"])] = r.get(metric, "")
    return ratios, methods, table


def _fmt_cell(v) -> str:
    if v == "" or v is None:
        return "-"
    return str(v)


def _pivot_markdown(rows: List[Dict], metric: str, title: str) -> str:
    ratios, methods, table = _pivot(rows, metric)
    lines = [f"## {title}", ""]
    header = "| ratio | " + " | ".join(methods) + " |"
    sep = "|---|" + "|".join(["---"] * len(methods)) + "|"
    lines += [header, sep]
    for r in ratios:
        cells = [_fmt_cell(table.get((r, m), "")) for m in methods]
        lines.append(f"| {r:.2f} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _recommendation_section(rows: List[Dict], skip_budget: int = 10) -> Tuple[str, Dict]:
    """Pick the ratio per method that minimises CNOT_total subject to
    ``n_skipped <= skip_budget``.  Returns (markdown, picks)."""
    picks: Dict[str, Dict] = {}
    for method in METHODS:
        best: Optional[Dict] = None
        for r in rows:
            if r["method"] != method:
                continue
            if r["n_skipped"] > skip_budget:
                continue
            cnot = r["CNOT_total"]
            if cnot == "" or cnot is None:
                continue
            if best is None or int(cnot) < int(best["CNOT_total"]):
                best = r
        picks[method] = best  # type: ignore[assignment]

    lines = [f"## Recommended operating point (min CNOT s.t. n_skipped <= {skip_budget})", ""]
    lines.append("| method | best_ratio | CNOT_total | T_total | Anc_total | n_skipped | wallclock_s |")
    lines.append("|---|---|---|---|---|---|---|")
    for method in METHODS:
        b = picks.get(method)
        if b is None:
            lines.append(f"| {method} | - | infeasible | - | - | - | - |")
        else:
            lines.append(
                f"| {method} | {b['ratio']:.2f} | {b['CNOT_total']} | {b['T_total']} | "
                f"{b['Anc_total']} | {b['n_skipped']} | {b['wallclock_s']} |"
            )
    return "\n".join(lines) + "\n", picks


def render_markdown(rows: List[Dict], n: int, skip_budget: int = 10) -> Tuple[str, Dict]:
    parts = [f"# keep_ratio sweep @ n={n}", ""]
    parts.append(_pivot_markdown(rows, "CNOT_total", "CNOT_total by ratio x method"))
    parts.append("")
    parts.append(_pivot_markdown(rows, "n_skipped", "n_skipped by ratio x method"))
    parts.append("")
    rec_md, picks = _recommendation_section(rows, skip_budget=skip_budget)
    parts.append(rec_md)
    return "\n".join(parts), picks


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_ratios(spec: str) -> List[float]:
    out = [float(x.strip()) for x in spec.split(",") if x.strip()]
    if not out:
        raise argparse.ArgumentTypeError("--ratios must list at least one value")
    return out


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval.keep_ratio_sweep",
        description="Sweep keep_ratio for rule/LGB/GNN pruners and dump CSV+Markdown.",
    )
    parser.add_argument("--csv", type=Path, required=True,
                        help="Test-set CSV (one row per (function, candidate)).")
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--gnn-ckpt", type=Path, required=False, default=None)
    parser.add_argument("--lgb-ckpt", type=Path, required=False, default=None)
    parser.add_argument("--ratios", type=_parse_ratios, default=[0.10, 0.15, 0.20, 0.30, 0.50])
    parser.add_argument("--out", type=Path, required=True, help="Output CSV path.")
    parser.add_argument("--out-md", type=Path, required=True, help="Output Markdown path.")
    parser.add_argument("--ilp-timeout", type=float, default=15.0)
    parser.add_argument("--skip-budget", type=int, default=10,
                        help="Max n_skipped allowed for the 'recommended' table.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    rows = run_sweep(
        n=args.n,
        csv_path=args.csv,
        ratios=args.ratios,
        lgb_ckpt=args.lgb_ckpt,
        gnn_ckpt=args.gnn_ckpt,
        timeout=args.ilp_timeout,
    )

    _write_csv(rows, args.out)
    md, _picks = render_markdown(rows, args.n, skip_budget=args.skip_budget)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md)

    print(md)
    print(f"[ok] csv  : {args.out}")
    print(f"[ok] md   : {args.out_md}")
    if not HAS_GUROBI:
        print("[note] gurobipy not importable -- ILP rows reported as skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
