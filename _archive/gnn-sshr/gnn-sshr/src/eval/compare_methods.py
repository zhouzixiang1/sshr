"""End-to-end CNOT comparison harness for SSHR methods.

Produces a markdown table aligned to the paper's Table V/VI/VII for a
given variable count ``n``.  The harness compares:

1. ``paper_sshr_h``      -- Table V SSHR-H reference numbers.
2. ``paper_sshr_i_cnot`` -- Table VI SSHR-I CNOT-objective reference numbers.
3. ``paper_xag``         -- Table V XAG baseline reference numbers.
4. ``our_sshr_h``        -- :func:`sshr_core.sshr_h.sshr_h` over the test set.
5. ``our_sshr_beam``     -- :func:`sshr_core.sshr_beam.sshr_beam` (CNOT, w=20).
6. ``rule_pruned_ilp``   -- top-20% prune via a simple rule-based ranker, ILP.
7. ``lgb_pruned_ilp``    -- top-20% prune via a LightGBM ranker, ILP.
8. ``gnn_pruned_ilp``    -- top-20% prune via the GNN ``CandidatePruner``, ILP.

ILP rows (6/7/8) require Gurobi (``gurobipy``).  When Gurobi is not
importable they are reported as ``skipped (no Gurobi)`` rather than
crashing the run, so the script can be invoked from either env.

CLI
---
::

    python -m eval.compare_methods --n 3 \
        --csv data/ilp/n3_ilp_cnot.csv \
        --lgb-ckpt results/models/lgbm_n3_smoke.txt \
        --out results/tables/p0_baselines_n3.md
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# sys.path: support both ``PYTHONPATH=src`` and direct file invocation.
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_SRC = _THIS.parent.parent  # .../src
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sshr_core.bool_func import BooleanFunction  # noqa: E402
from sshr_core import paper_data  # noqa: E402

# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------
try:
    import gurobipy  # noqa: F401
    HAS_GUROBI = True
except ImportError:
    HAS_GUROBI = False


# ---------------------------------------------------------------------------
# Row schema
# ---------------------------------------------------------------------------

EVAL_SCHEMA: Tuple[str, ...] = (
    "method",
    "n",
    "T",
    "CNOT",
    "Anc",
    "gain_vs_paper_sshr_h_cnot",  # percentage; +ve == better than paper SSHR-H
    "n_evaluated",
    "n_skipped",
    "time_s",
    "note",
)


@dataclass
class Row:
    method: str
    n: int
    T: Optional[int] = None
    CNOT: Optional[int] = None
    Anc: Optional[int] = None
    gain_vs_paper_sshr_h_cnot: Optional[float] = None
    n_evaluated: int = 0
    n_skipped: int = 0
    time_s: float = 0.0
    note: str = ""
    # per-function feasibility map: truth_table (int) -> cost dict {T, CNOT, ancilla}
    # NOT emitted in to_dict / EVAL_SCHEMA; used for common-subset re-aggregation.
    per_func: Dict[int, Dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: d[k] for k in EVAL_SCHEMA}


# ---------------------------------------------------------------------------
# Test-set construction
# ---------------------------------------------------------------------------

def _truth_tables_from_csv(csv_path: Path, n: int) -> List[int]:
    """Return distinct truth tables (in CSV order) parsed from a data CSV."""
    seen: set = set()
    tts: List[int] = []
    with csv_path.open("r", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if "truth_table_hex" not in row:
                continue
            try:
                row_n = int(row.get("n", n))
            except ValueError:
                row_n = n
            if row_n != n:
                continue
            tt = int(row["truth_table_hex"], 16)
            if tt in seen:
                continue
            seen.add(tt)
            tts.append(tt)
    return tts


def build_test_set(n: int, csv_path: Optional[Path]) -> List[BooleanFunction]:
    """Build the test set used for the ``our_*`` and ``*_pruned_*`` rows.

    For ``n=3`` we default to all 256 truth tables when no CSV is given.
    For ``n=4`` we use the 222 NPN representatives.  Otherwise we require
    a CSV to enumerate the test set explicitly.
    """
    if csv_path is not None and csv_path.exists():
        tts = _truth_tables_from_csv(csv_path, n)
        if tts:
            return [BooleanFunction(n, tt) for tt in tts]

    if n == 3:
        return [BooleanFunction(3, tt) for tt in range(256)]
    if n == 4:
        from sshr_core.npn_reps_n4 import NPN_REPS_N4  # noqa: WPS433
        return [BooleanFunction(4, tt) for tt in NPN_REPS_N4]

    raise ValueError(
        f"No test set available for n={n} without a CSV (looked at {csv_path!r}).",
    )


# ---------------------------------------------------------------------------
# Method 1-3: paper reference rows
# ---------------------------------------------------------------------------

def _paper_row(method: str, table: dict, n: int) -> Row:
    if n not in table:
        return Row(
            method=method, n=n,
            note=f"not present in paper table",
        )
    T, C, anc = table[n]
    return Row(
        method=method, n=n,
        T=int(T), CNOT=int(C), Anc=int(anc),
        n_evaluated=0, time_s=0.0,
        note="paper reference",
    )


# ---------------------------------------------------------------------------
# Method 4-5: our SSHR-H / SSHR-Beam
# ---------------------------------------------------------------------------

def _aggregate_costs(circuits_costs: Iterable[Dict[str, int]]) -> Tuple[int, int, int]:
    """Sum T, CNOT, and ancilla across functions (paper Table V convention)."""
    T = 0
    C = 0
    anc = 0
    for d in circuits_costs:
        T += int(d.get("T", 0))
        C += int(d.get("CNOT", 0))
        anc += int(d.get("ancilla", 0))
    return T, C, anc


def run_our_sshr_h(test_set: Sequence[BooleanFunction], n: int) -> Row:
    from sshr_core.sshr_h import sshr_h  # noqa: WPS433

    t0 = time.time()
    costs: List[Dict[str, int]] = []
    for bf in test_set:
        circ = sshr_h(bf)
        costs.append(circ.cost())
    T, C, anc = _aggregate_costs(costs)
    return Row(
        method="our_sshr_h", n=n, T=T, CNOT=C, Anc=anc,
        n_evaluated=len(test_set), time_s=time.time() - t0,
    )


def run_our_sshr_beam(
    test_set: Sequence[BooleanFunction],
    n: int,
    width: int = 20,
) -> Row:
    from sshr_core.sshr_beam import sshr_beam  # noqa: WPS433

    t0 = time.time()
    costs: List[Dict[str, int]] = []
    for bf in test_set:
        circ = sshr_beam(bf, objective="cnot", width=width)
        costs.append(circ.cost())
    T, C, anc = _aggregate_costs(costs)
    return Row(
        method="our_sshr_beam", n=n, T=T, CNOT=C, Anc=anc,
        n_evaluated=len(test_set), time_s=time.time() - t0,
        note=f"width={width}",
    )


# ---------------------------------------------------------------------------
# Pruned ILP helpers
# ---------------------------------------------------------------------------

def _circuit_from_pruned_run(bf: BooleanFunction, scores: Sequence[float],
                             keep_ratio: float, timeout: float) -> Tuple[Optional[Dict[str, int]], str]:
    """Run pruned ILP for a single bf, return (cost_dict_or_None, note)."""
    from search.pruned_search import (  # noqa: WPS433
        _enumerate_with_singletons,
        prune_candidates,
    )
    from sshr_core.bool_func import QuantumCircuit  # noqa: WPS433
    from sshr_core.block_synth import synth_block, block_cnot_cost  # noqa: WPS433
    from sshr_core.sshr_i import _solve_ilp_gurobi  # noqa: WPS433

    n = bf.n
    candidates = _enumerate_with_singletons(bf)
    if len(scores) != len(candidates):
        return None, f"score-length mismatch ({len(scores)} vs {len(candidates)})"

    kept_idx = prune_candidates(
        candidates, list(scores),
        keep_ratio=keep_ratio,
        ensure_coverage=True,
        onset=bf.onset,
        n=n,
    )
    pruned = [candidates[i] for i in kept_idx]
    onset_set = set(bf.onset)
    covered: set = set()
    for p in pruned:
        covered |= p.vertices()
    if not onset_set.issubset(covered):
        return None, "infeasible (onset not covered)"

    costs = [float(block_cnot_cost(p, n)) for p in pruned]
    all_minterms = list(range(1 << n))
    t0 = time.time()
    selected = _solve_ilp_gurobi(pruned, all_minterms, bf.onset, costs, timeout)
    elapsed = time.time() - t0
    if elapsed > timeout + 1.0:
        # _solve_ilp_gurobi may have timed out internally; treat empty
        # selection as failure.
        if not selected and bf.onset:
            return None, f"ilp timeout (>{timeout}s)"
    if not selected and bf.onset:
        return None, "ilp infeasible / no solution"

    circ = QuantumCircuit(n + 1)
    for idx in selected:
        circ.add_block(synth_block(pruned[idx], n))
    return circ.cost(), ""


def _run_pruned_ilp_method(
    method: str,
    test_set: Sequence[BooleanFunction],
    n: int,
    score_fn,
    keep_ratio: float = 0.20,
    timeout: float = 15.0,
    note_prefix: str = "",
) -> Row:
    """Generic driver: ``score_fn(bf)`` returns per-candidate scores."""
    if not HAS_GUROBI:
        return Row(
            method=method, n=n,
            n_evaluated=0, n_skipped=len(test_set),
            note="skipped (no Gurobi)",
        )

    t0 = time.time()
    costs: List[Dict[str, int]] = []
    skipped = 0
    skip_notes: List[str] = []
    per_func: Dict[int, Dict[str, int]] = {}
    for bf in test_set:
        try:
            scores = score_fn(bf)
        except Exception as exc:  # noqa: BLE001 - score-time failure
            skipped += 1
            skip_notes.append(f"score-error: {exc}")
            continue
        cost_dict, note = _circuit_from_pruned_run(
            bf, scores, keep_ratio=keep_ratio, timeout=timeout,
        )
        if cost_dict is None:
            skipped += 1
            if note:
                skip_notes.append(note)
            continue
        costs.append(cost_dict)
        per_func[int(bf.truth_table)] = dict(cost_dict)

    T, C, anc = _aggregate_costs(costs)
    note = note_prefix
    if skipped:
        # Keep the note compact: just count categories.
        unique_notes = sorted({n for n in skip_notes if n})
        if unique_notes:
            note = (note + "; " if note else "") + f"skip={skipped} ({unique_notes[0]}{'...' if len(unique_notes) > 1 else ''})"
        else:
            note = (note + "; " if note else "") + f"skip={skipped}"
    return Row(
        method=method, n=n,
        T=T if costs else None,
        CNOT=C if costs else None,
        Anc=anc if costs else None,
        n_evaluated=len(costs),
        n_skipped=skipped,
        time_s=time.time() - t0,
        note=note,
        per_func=per_func,
    )


# ---------------------------------------------------------------------------
# Method 6: rule-based ranker
# ---------------------------------------------------------------------------

def _rule_scores(bf: BooleanFunction) -> List[float]:
    """Hand-coded ranker: cand_dim - 0.1 * off_overlap.

    Higher score == more attractive candidate.  Mirrors ``cand_dim`` /
    ``off_overlap`` columns used by the LightGBM features.
    """
    from search.pruned_search import _enumerate_with_singletons  # noqa: WPS433

    cands = _enumerate_with_singletons(bf)
    offset = set(range(1 << bf.n)) - set(bf.onset)
    out: List[float] = []
    for p in cands:
        verts = p.vertices()
        off_overlap = sum(1 for v in verts if v in offset)
        out.append(float(p.dim) - 0.1 * float(off_overlap))
    return out


# ---------------------------------------------------------------------------
# Method 7: LightGBM ranker
# ---------------------------------------------------------------------------

def _lgb_score_fn(ckpt_path: Path):
    from models.lightgbm_pruner import LightGBMPruner  # noqa: WPS433
    from data.feature_encoder import candidate_features, FEATURE_NAMES  # noqa: WPS433
    from search.pruned_search import _enumerate_with_singletons  # noqa: WPS433

    pruner = LightGBMPruner.load(str(ckpt_path))
    feature_cols = pruner.feature_cols_ or list(FEATURE_NAMES)

    import pandas as pd

    def score(bf: BooleanFunction) -> List[float]:
        cands = _enumerate_with_singletons(bf)
        feats = candidate_features(bf, cands)
        df = pd.DataFrame(feats, columns=list(FEATURE_NAMES))
        # Restrict / re-order to model feature_cols.
        df = df[feature_cols]
        return list(map(float, pruner.predict(df, feature_cols)))

    return score


# ---------------------------------------------------------------------------
# Method 8: GNN candidate pruner
# ---------------------------------------------------------------------------

def _gnn_score_fn(ckpt_path: Path):
    """Lazy-loaded GNN scorer.  Raises a clear error if torch / pyg missing."""
    import torch
    from models.candidate_pruner import CandidatePruner, dict_to_hetero  # noqa: WPS433
    from data.graph_builder import build_bipartite_graph  # noqa: WPS433
    from search.pruned_search import _enumerate_with_singletons  # noqa: WPS433

    state = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    if isinstance(state, dict) and "state_dict" in state:
        state_dict = state["state_dict"]
        cfg = state.get("config", {}) or {}
    elif isinstance(state, dict) and "model_state" in state:
        state_dict = state["model_state"]
        cfg = state.get("config", {}) or {}
    else:
        state_dict = state
        cfg = {}

    model = CandidatePruner(
        parity_in_dim=cfg.get("parity_in_dim", 5),
        cand_in_dim=cfg.get("cand_in_dim", 8),
        hidden=cfg.get("hidden", 128),
        num_layers=cfg.get("num_layers", cfg.get("layers", 3)),
        dropout=cfg.get("dropout", 0.1),
    )
    model.load_state_dict(state_dict)
    model.eval()

    @torch.no_grad()
    def score(bf: BooleanFunction) -> List[float]:
        cands = _enumerate_with_singletons(bf)
        graph = build_bipartite_graph(bf, cands)
        data = dict_to_hetero(graph)
        out = model(data).cpu().numpy().tolist()
        return [float(x) for x in out]

    return score


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def render_markdown(rows: List[Row], n: int) -> str:
    header = (
        "| Method | T | CNOT | Anc | gain_vs_paper_sshr_h_cnot (%) | n_evaluated | n_skipped | time_s | note |\n"
        "|---|---|---|---|---|---|---|---|---|"
    )
    lines = [f"# Method comparison @ n={n}", "", header]
    for row in rows:
        gain = row.gain_vs_paper_sshr_h_cnot
        gain_str = "-" if gain is None else f"{gain:+.2f}"
        lines.append(
            "| {method} | {T} | {CNOT} | {Anc} | {gain} | {ne} | {ns} | {ts} | {note} |".format(
                method=row.method,
                T=_fmt(row.T),
                CNOT=_fmt(row.CNOT),
                Anc=_fmt(row.Anc),
                gain=gain_str,
                ne=row.n_evaluated,
                ns=row.n_skipped,
                ts=f"{row.time_s:.2f}" if row.time_s else "-",
                note=row.note or "",
            )
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Gain calculation
# ---------------------------------------------------------------------------

def _attach_gain(rows: List[Row], n: int) -> None:
    """Set ``gain_vs_paper_sshr_h_cnot`` on every row (in-place)."""
    paper = paper_data.TABLE_V_SSHR_H.get(n)
    if not paper:
        return
    paper_cnot = paper[1]
    if paper_cnot <= 0:
        return
    for row in rows:
        if row.CNOT is None:
            row.gain_vs_paper_sshr_h_cnot = None
            continue
        row.gain_vs_paper_sshr_h_cnot = (paper_cnot - row.CNOT) / paper_cnot * 100.0


# ---------------------------------------------------------------------------
# Common-subset re-aggregation
# ---------------------------------------------------------------------------

PRUNED_METHODS: Tuple[str, ...] = ("rule_pruned_ilp", "lgb_pruned_ilp", "gnn_pruned_ilp")


def compute_common_subset(rows: List[Row]) -> set:
    """Intersection of feasible truth-tables across pruned methods.

    Includes a pruned method only if it has at least one feasible func; this
    avoids degenerating to the empty set when a method was skipped (no Gurobi
    or no checkpoint).
    """
    feasible_sets: List[set] = []
    for row in rows:
        if row.method not in PRUNED_METHODS:
            continue
        if not row.per_func:
            continue
        feasible_sets.append(set(row.per_func.keys()))
    if not feasible_sets:
        return set()
    common = feasible_sets[0]
    for s in feasible_sets[1:]:
        common = common & s
    return common


def reaggregate_on_subset(rows: List[Row], common: set, n: int) -> List[Row]:
    """Return a new list of Rows re-aggregated on the common subset.

    Paper / heuristic rows that don't have per-function data are passed
    through unchanged (with a note indicating they are not subset-restricted).
    """
    out: List[Row] = []
    for row in rows:
        if row.method not in PRUNED_METHODS or not row.per_func:
            new = Row(
                method=row.method, n=row.n,
                T=row.T, CNOT=row.CNOT, Anc=row.Anc,
                n_evaluated=row.n_evaluated,
                n_skipped=row.n_skipped,
                time_s=row.time_s,
                note=row.note,
            )
            out.append(new)
            continue
        sub_costs = [row.per_func[tt] for tt in common if tt in row.per_func]
        if not sub_costs:
            out.append(Row(
                method=row.method, n=row.n,
                n_evaluated=0,
                n_skipped=len(common),
                note=(row.note + "; " if row.note else "") + "no overlap with common subset",
            ))
            continue
        T, C, anc = _aggregate_costs(sub_costs)
        out.append(Row(
            method=row.method, n=row.n,
            T=T, CNOT=C, Anc=anc,
            n_evaluated=len(sub_costs),
            n_skipped=len(common) - len(sub_costs),
            time_s=row.time_s,
            note=(row.note + "; " if row.note else "") + f"common-subset|S|={len(common)}",
        ))
    return out


def write_per_function_diff_csv(rows: List[Row], common: set, csv_path: Path, n: int) -> None:
    """Write per-function (gnn vs lgb) diff CSV restricted to the common subset."""
    gnn_row = next((r for r in rows if r.method == "gnn_pruned_ilp"), None)
    lgb_row = next((r for r in rows if r.method == "lgb_pruned_ilp"), None)
    if gnn_row is None or lgb_row is None:
        return
    gnn_pf = gnn_row.per_func
    lgb_pf = lgb_row.per_func
    pair_subset = (set(gnn_pf.keys()) & set(lgb_pf.keys()))
    if common:
        pair_subset = pair_subset & common
    if not pair_subset:
        return
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    hex_width = max(1, (1 << n) // 4)
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "func_id", "truth_table_hex",
            "gnn_cnot", "lgb_cnot", "diff_gnn_minus_lgb",
        ])
        for func_id, tt in enumerate(sorted(pair_subset)):
            gnn_c = int(gnn_pf[tt].get("CNOT", 0))
            lgb_c = int(lgb_pf[tt].get("CNOT", 0))
            writer.writerow([
                func_id,
                f"0x{tt:0{hex_width}X}",
                gnn_c, lgb_c, gnn_c - lgb_c,
            ])


# ---------------------------------------------------------------------------
# Top-level driver
# ---------------------------------------------------------------------------

def compare_methods(
    n: int,
    csv_path: Optional[Path] = None,
    lgb_ckpt: Optional[Path] = None,
    gnn_ckpt: Optional[Path] = None,
    keep_ratio: float = 0.20,
    timeout: float = 15.0,
    beam_width: int = 20,
) -> List[Row]:
    """Run all eight methods and return the rows in EVAL_SCHEMA order."""
    test_set = build_test_set(n, csv_path)

    rows: List[Row] = []

    # 1-3: paper reference rows.
    rows.append(_paper_row("paper_sshr_h", paper_data.TABLE_V_SSHR_H, n))
    rows.append(_paper_row("paper_sshr_i_cnot", paper_data.TABLE_VI_SSHR_I_CNOT, n))
    rows.append(_paper_row("paper_xag", paper_data.TABLE_V_XAG, n))

    # 4-5: our heuristics.
    rows.append(run_our_sshr_h(test_set, n))
    rows.append(run_our_sshr_beam(test_set, n, width=beam_width))

    # 6: rule-pruned ILP.
    rows.append(_run_pruned_ilp_method(
        "rule_pruned_ilp", test_set, n,
        score_fn=_rule_scores,
        keep_ratio=keep_ratio,
        timeout=timeout,
        note_prefix=f"keep={keep_ratio:g}",
    ))

    # 7: LGB-pruned ILP.
    if lgb_ckpt is not None and Path(lgb_ckpt).exists():
        if HAS_GUROBI:
            try:
                lgb_fn = _lgb_score_fn(Path(lgb_ckpt))
            except Exception as exc:  # noqa: BLE001
                rows.append(Row(
                    method="lgb_pruned_ilp", n=n,
                    n_skipped=len(test_set),
                    note=f"load-error: {exc}",
                ))
            else:
                rows.append(_run_pruned_ilp_method(
                    "lgb_pruned_ilp", test_set, n,
                    score_fn=lgb_fn,
                    keep_ratio=keep_ratio,
                    timeout=timeout,
                    note_prefix=f"keep={keep_ratio:g}",
                ))
        else:
            rows.append(Row(
                method="lgb_pruned_ilp", n=n,
                n_skipped=len(test_set),
                note="skipped (no Gurobi)",
            ))
    else:
        rows.append(Row(
            method="lgb_pruned_ilp", n=n,
            n_skipped=len(test_set),
            note="skipped (no --lgb-ckpt)",
        ))

    # 8: GNN-pruned ILP.
    if gnn_ckpt is not None and Path(gnn_ckpt).exists():
        if HAS_GUROBI:
            try:
                gnn_fn = _gnn_score_fn(Path(gnn_ckpt))
            except Exception as exc:  # noqa: BLE001
                rows.append(Row(
                    method="gnn_pruned_ilp", n=n,
                    n_skipped=len(test_set),
                    note=f"load-error: {exc}",
                ))
            else:
                rows.append(_run_pruned_ilp_method(
                    "gnn_pruned_ilp", test_set, n,
                    score_fn=gnn_fn,
                    keep_ratio=keep_ratio,
                    timeout=timeout,
                    note_prefix=f"keep={keep_ratio:g}",
                ))
        else:
            rows.append(Row(
                method="gnn_pruned_ilp", n=n,
                n_skipped=len(test_set),
                note="skipped (no Gurobi)",
            ))
    else:
        rows.append(Row(
            method="gnn_pruned_ilp", n=n,
            n_skipped=len(test_set),
            note="skipped (no --gnn-ckpt)",
        ))

    _attach_gain(rows, n)
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval.compare_methods",
        description=(
            "End-to-end CNOT comparison across paper baselines, our "
            "heuristics, and pruned-ILP variants (rule / LightGBM / GNN)."
        ),
    )
    parser.add_argument("--n", type=int, required=True, help="Number of variables.")
    parser.add_argument(
        "--csv", type=Path, default=None,
        help="Optional CSV (one row per (function, candidate)) supplying the test-set truth tables.",
    )
    parser.add_argument(
        "--lgb-ckpt", type=Path, default=None,
        help="LightGBM model file (results/models/lgbm_n{n}_smoke.txt). Skipped if missing.",
    )
    parser.add_argument(
        "--gnn-ckpt", type=Path, default=None,
        help="GNN CandidatePruner checkpoint. Skipped if missing.",
    )
    parser.add_argument(
        "--out", type=Path, required=True,
        help="Output markdown path (e.g. results/tables/p0_baselines_n3.md).",
    )
    parser.add_argument(
        "--keep-ratio", type=float, default=0.20,
        help="Top-fraction of candidates the rankers keep (default 0.20).",
    )
    parser.add_argument(
        "--ilp-timeout", type=float, default=15.0,
        help="Per-function ILP timeout in seconds (default 15).",
    )
    parser.add_argument(
        "--beam-width", type=int, default=20,
        help="Beam width for our_sshr_beam (default 20).",
    )
    parser.add_argument(
        "--json-out", type=Path, default=None,
        help="Optional path to also emit rows as JSON (matching EVAL_SCHEMA).",
    )
    parser.add_argument(
        "--require-common-subset", action="store_true",
        help=(
            "After running all methods, intersect the feasible func sets "
            "across pruned methods (rule/lgb/gnn) and emit a second markdown "
            "section with totals re-aggregated on the common subset. Also "
            "writes results/tables/p0_per_function_diff_n{n}.csv."
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    rows = compare_methods(
        n=args.n,
        csv_path=args.csv,
        lgb_ckpt=args.lgb_ckpt,
        gnn_ckpt=args.gnn_ckpt,
        keep_ratio=args.keep_ratio,
        timeout=args.ilp_timeout,
        beam_width=args.beam_width,
    )

    md = render_markdown(rows, args.n)

    if args.require_common_subset:
        common = compute_common_subset(rows)
        sub_rows = reaggregate_on_subset(rows, common, args.n)
        _attach_gain(sub_rows, args.n)
        sub_md = render_markdown(sub_rows, args.n)
        # Replace the leading H1 of the subset section so the two sections
        # are clearly distinguished in the same .md file.
        sub_md = sub_md.replace(
            f"# Method comparison @ n={args.n}",
            f"# Common-feasible subset (|S|={len(common)}) @ n={args.n}",
            1,
        )
        md = md + "\n" + sub_md
        diff_csv = args.out.parent / f"p0_per_function_diff_n{args.n}.csv"
        write_per_function_diff_csv(rows, common, diff_csv, args.n)
        print(f"[ok] common subset |S|={len(common)}")
        print(f"[ok] per-func diff csv: {diff_csv}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md)

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps([r.to_dict() for r in rows], indent=2, default=float)
        )

    print(md)
    print(f"[ok] markdown written: {args.out}")
    if not HAS_GUROBI:
        print("[note] gurobipy not importable -- ILP rows reported as skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
