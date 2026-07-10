"""
Training-data collector for the candidate pruner.

For each Boolean function in a (truncated) enumeration:
  1. Enumerate all candidate parallelotopes in the full hypercube.
  2. Run a teacher solver (SSHR-I ILP, beam search, or SSHR-H heuristic).
  3. Identify which candidates were used in the teacher's solution.
  4. Encode every candidate's per-feature vector via
     :func:`src.data.feature_encoder.candidate_features`.
  5. Append one row per (function, candidate) to a CSV.

The CSV is written incrementally so partial runs survive crashes.

CLI
---
::

    python -m src.data.data_collector --n 3 --teacher ilp --max-functions 16
    python -m src.data.data_collector --n 4 --teacher beam --max-functions 222

The default ``out_csv`` for ``n``/``teacher``/``objective`` is
``<repo_root>/data/ilp/n{n}_{teacher}_{objective}.csv``.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import warnings
from typing import Any, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Make sshr_core / data importable when run as a script
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_ROOT = os.path.dirname(_THIS_DIR)         # .../gnn-sshr/src
_REPO_ROOT = os.path.dirname(_SRC_ROOT)        # .../gnn-sshr
for _p in (_SRC_ROOT, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Robust imports: try src.* first, then bare module names.
try:                                                                   # pragma: no cover
    from src.sshr_core.bool_func import BooleanFunction
    from src.sshr_core.parallelotope import Parallelotope
    from src.sshr_core.parallelotope_enum import enumerate_parallelotopes
    from src.sshr_core.block_synth import block_cnot_cost, block_t_cost
    from src.data.feature_encoder import candidate_features, FEATURE_NAMES
except Exception:                                                      # pragma: no cover
    from sshr_core.bool_func import BooleanFunction
    from sshr_core.parallelotope import Parallelotope
    from sshr_core.parallelotope_enum import enumerate_parallelotopes
    from sshr_core.block_synth import block_cnot_cost, block_t_cost
    try:
        from data.feature_encoder import candidate_features, FEATURE_NAMES
    except Exception:                                                  # pragma: no cover
        from src.data.feature_encoder import candidate_features, FEATURE_NAMES  # type: ignore


_LOG = logging.getLogger("gnn_sshr.data_collector")
if not _LOG.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    _LOG.addHandler(_h)
_LOG.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _block_key(p: Parallelotope) -> Tuple[int, Tuple[int, ...]]:
    """Canonical key matching a block back to a candidate."""
    return (int(p.v0), tuple(sorted(int(b) for b in p.basis)))


def _build_universe_candidates(n: int) -> List[Parallelotope]:
    """Full hypercube candidates (dim>=1 + dim-0 singletons)."""
    full = list(range(1 << n))
    cands = enumerate_parallelotopes(full, n, include_singletons=False)
    # Append singletons explicitly (so cand_idx range is stable / matches engine).
    for v in full:
        cands.append(Parallelotope(v, []))
    return cands


def _truth_tables_for(n: int, max_functions: int, use_npn_reps: bool = False) -> List[int]:
    """Return the list of truth-table integers to iterate.

    For n == 4 prefer ``NPN_REPS_N4`` (NPN representatives) when importable.
    Otherwise iterate ``range(1, min(2**(2**n), max_functions + 1))``.

    If ``use_npn_reps`` is True and n == 4, iterate all 222 NPN reps without
    truncation by ``max_functions``.
    """
    if n == 4:
        try:
            try:
                from src.sshr_core.npn_reps_n4 import NPN_REPS_N4
            except Exception:                                         # pragma: no cover
                from sshr_core.npn_reps_n4 import NPN_REPS_N4
            reps = [tt for tt in NPN_REPS_N4 if tt != 0]
            if use_npn_reps:
                return reps
            return reps[:max_functions]
        except Exception as exc:                                      # pragma: no cover
            _LOG.warning("Could not import NPN_REPS_N4 (%s); falling back to range.", exc)

    upper = min(1 << (1 << n), max_functions + 1)
    return list(range(1, upper))


# ---------------------------------------------------------------------------
# Teachers
# ---------------------------------------------------------------------------

def _run_ilp_teacher(
    bf: BooleanFunction,
    objective: str,
    timeout: int,
) -> Tuple[List[Parallelotope], float]:
    """Run SSHR-I ILP and return ``(chosen_blocks, total_cost)``.

    Replicates the candidate construction inside ``sshr_i._ilp_core`` so the
    selected indices map cleanly back to Parallelotope objects.
    """
    try:
        try:
            from src.sshr_core.sshr_i import (
                _solve_ilp_gurobi,
                _solve_ilp_gurobi_t_then_cnot,
                block_t_cost_rp,
            )
        except Exception:                                             # pragma: no cover
            from sshr_core.sshr_i import (
                _solve_ilp_gurobi,
                _solve_ilp_gurobi_t_then_cnot,
                block_t_cost_rp,
            )
    except Exception as exc:                                          # pragma: no cover
        raise RuntimeError(f"Cannot import sshr_i (gurobipy missing?): {exc}") from exc

    n = bf.n
    onset = bf.onset
    if not onset:
        return [], 0.0
    onset_set = set(onset)
    all_minterms = list(range(1 << n))

    parallelotopes = enumerate_parallelotopes(all_minterms, n)
    seen_vsets = {p.vertices() for p in parallelotopes}
    for v in all_minterms:
        s = frozenset([v])
        if s not in seen_vsets:
            parallelotopes.append(Parallelotope(v, []))
            seen_vsets.add(s)
    parallelotopes = [p for p in parallelotopes if p.vertices() & onset_set]
    if not parallelotopes:
        return [], float("inf")

    if objective == "cnot":
        costs = [float(block_cnot_cost(p, n)) for p in parallelotopes]
        selected = _solve_ilp_gurobi(
            parallelotopes, all_minterms, onset, costs, float(timeout)
        )
    elif objective == "t":
        t_costs = [float(block_t_cost_rp(p, n)) for p in parallelotopes]
        c_costs = [float(block_cnot_cost(p, n)) for p in parallelotopes]
        selected = _solve_ilp_gurobi_t_then_cnot(
            parallelotopes, all_minterms, onset, t_costs, c_costs, float(timeout)
        )
        if not selected:
            selected = _solve_ilp_gurobi(
                parallelotopes, all_minterms, onset, t_costs, float(timeout)
            )
    else:
        raise ValueError(f"Unsupported objective {objective!r}")

    if not selected:
        return [], float("inf")

    chosen = [parallelotopes[i] for i in selected]
    if objective == "cnot":
        total_cost = float(sum(block_cnot_cost(p, n) for p in chosen))
    else:
        total_cost = float(sum(block_t_cost_rp(p, n) for p in chosen))
    return chosen, total_cost


def _run_beam_teacher(
    bf: BooleanFunction,
    beam_width: int = 8,
    objective: str = "cnot",
) -> Tuple[List[Parallelotope], float]:
    """Run SSHR-Beam and return ``(chosen_blocks, total_cost)``.

    Replicates the public ``sshr_beam`` driver so the action path is captured
    before being flattened into a :class:`QuantumCircuit`.
    """
    try:
        from src.sshr_core.sshr_beam import _BeamEngine
    except Exception:                                                 # pragma: no cover
        from sshr_core.sshr_beam import _BeamEngine

    n = bf.n
    onset = bf.onset
    if not onset:
        return [], 0.0

    engine = _BeamEngine(n, objective)
    A0 = 0
    for v in onset:
        A0 |= 1 << v

    uid = [0]
    branch = 5

    def new_state(A_mask: int, cost: float, path: List[int]) -> tuple:
        lb = engine.greedy_lb(A_mask)
        uid[0] += 1
        return (cost + lb, uid[0], A_mask, cost, list(path))

    beam: List[tuple] = [new_state(A0, 0.0, [])]
    max_steps = max(1, bin(A0).count("1")) + 1

    best_record: Optional[tuple] = None
    for _ in range(max_steps):
        complete = [s for s in beam if s[2] == 0]
        if complete:
            best_record = min(complete, key=lambda s: s[3])
            break

        all_next: List[tuple] = []
        for s in beam:
            _, _, A_mask, cost_so_far, path = s
            if A_mask == 0:
                all_next.append(s)
                continue
            actions = engine.top_k_actions(A_mask, branch)
            if not actions:
                A_remaining = A_mask
                total_cost = cost_so_far
                extended_path = list(path)
                while A_remaining:
                    v = (A_remaining & -A_remaining).bit_length() - 1
                    singleton_idx = len(engine.all_p) - (1 << n) + v
                    extended_path.append(singleton_idx)
                    total_cost += engine.costs_list[singleton_idx]
                    A_remaining ^= (1 << v)
                all_next.append(new_state(0, total_cost, extended_path))
                continue

            for orig_idx, action_cost in actions:
                bm = engine.bitmasks_list[orig_idx]
                new_A = A_mask ^ bm
                new_cost = cost_so_far + action_cost
                all_next.append(new_state(new_A, new_cost, path + [orig_idx]))

        if not all_next:
            break
        all_next.sort(key=lambda s: (s[0], s[1]))
        beam = all_next[:beam_width]

    if best_record is None:
        best_record = min(beam, key=lambda s: s[3])

    chosen = [engine.all_p[i] for i in best_record[4]]
    return chosen, float(best_record[3])


def _run_h_teacher(bf: BooleanFunction) -> Tuple[List[Parallelotope], float]:
    """Run SSHR-H greedy heuristic and return ``(chosen_blocks, total_cost)``.

    Replicates the algorithm in ``sshr_h.sshr_h`` while accumulating the chosen
    parallelotopes directly (the public function only returns a flattened
    :class:`QuantumCircuit`).
    """
    try:
        from src.sshr_core.sshr_h import _full_hypercube_parallelotopes
    except Exception:                                                 # pragma: no cover
        from sshr_core.sshr_h import _full_hypercube_parallelotopes

    n = bf.n
    R = 3 / 4
    A = set(bf.onset)
    chosen: List[Parallelotope] = []
    if not A:
        return [], 0.0

    S = _full_hypercube_parallelotopes(n)
    while A:
        candidates = [
            P for P in S
            if len(P.vertices() & A) / len(P.vertices()) >= R
        ]
        if not candidates:
            break
        pick = candidates[0]
        chosen.append(pick)
        A ^= pick.vertices()

    for v in list(A):
        chosen.append(Parallelotope(v, []))

    total_cost = float(sum(block_cnot_cost(p, n) for p in chosen))
    return chosen, total_cost


# ---------------------------------------------------------------------------
# Single-function row builder
# ---------------------------------------------------------------------------

def _rows_for_function(
    func_id: int,
    bf: BooleanFunction,
    candidates: Sequence[Parallelotope],
    chosen_blocks: Sequence[Parallelotope],
    total_cost: float,
    feature_matrix: np.ndarray,
) -> List[dict]:
    """Build per-candidate row dicts for a single Boolean function."""
    n = bf.n
    chosen_keys = {_block_key(p) for p in chosen_blocks}
    on_size = len(bf.onset)
    hex_width = max(1, (1 << n) // 4)
    tt_hex = f"{bf.truth_table:0{hex_width}X}"

    rows: List[dict] = []
    for i, cand in enumerate(candidates):
        row: dict = {
            "func_id": int(func_id),
            "n": int(n),
            "truth_table_hex": tt_hex,
            "num_candidates": len(candidates),
            "on_size": int(on_size),
            "optimal_cost": float(total_cost),
            "cand_idx": int(i),
            "cand_dim": int(len(cand.basis)),
            "cand_size": int(1 << len(cand.basis)),
            "label": int(_block_key(cand) in chosen_keys),
        }
        for j, name in enumerate(FEATURE_NAMES):
            row[name] = float(feature_matrix[i, j])
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Incremental CSV writer
# ---------------------------------------------------------------------------

def _csv_columns() -> List[str]:
    base = [
        "func_id",
        "n",
        "truth_table_hex",
        "num_candidates",
        "on_size",
        "optimal_cost",
        "cand_idx",
        "cand_dim",
        "cand_size",
        "label",
    ]
    return base + list(FEATURE_NAMES)


def _flush_rows(rows: List[dict], out_csv: str, header_written: bool) -> bool:
    if not rows:
        return header_written
    df = pd.DataFrame(rows, columns=_csv_columns())
    mode = "a" if header_written else "w"
    df.to_csv(out_csv, mode=mode, header=not header_written, index=False)
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def collect(
    n: int,
    teacher: str = "ilp",
    max_functions: int = 32,
    out_csv: Optional[str] = None,
    objective: str = "cnot",
    timeout: int = 60,
    seed: int = 0,
    flush_every: int = 4,
    use_npn_reps: bool = False,
) -> pd.DataFrame:
    """Collect labeled candidate-ranking training data.

    Parameters
    ----------
    n : int
        Number of input variables.
    teacher : {'ilp', 'beam', 'h'}
        Which teacher solver to use.  ``'ilp'`` requires a working Gurobi
        installation.
    max_functions : int
        Truncate the function enumeration to at most this many entries.
    out_csv : str, optional
        Output CSV path.  Defaults to
        ``<repo>/data/ilp/n{n}_{teacher}_{objective}.csv``.
    objective : {'cnot', 't'}
        Cost objective propagated to ILP/beam teachers.
    timeout : int
        Per-function ILP time-limit (seconds).  Ignored by beam / h.
    seed : int
        Reserved for reproducibility (unused for deterministic teachers).
    flush_every : int
        Append rows to disk every ``flush_every`` functions.

    Returns
    -------
    pandas.DataFrame
        DataFrame of every appended row.
    """
    teacher = teacher.lower()
    if teacher not in {"ilp", "beam", "h"}:
        raise ValueError(f"Unknown teacher {teacher!r}; expected 'ilp', 'beam', or 'h'.")
    if objective not in {"cnot", "t"}:
        raise ValueError(f"Unknown objective {objective!r}; expected 'cnot' or 't'.")

    np.random.seed(int(seed))

    if out_csv is None:
        default_dir = os.path.join(_REPO_ROOT, "data", "ilp")
        os.makedirs(default_dir, exist_ok=True)
        out_csv = os.path.join(default_dir, f"n{n}_{teacher}_{objective}.csv")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(out_csv)) or ".", exist_ok=True)

    # Remove an existing file so each call starts clean.
    if os.path.exists(out_csv):
        os.remove(out_csv)

    truth_tables = _truth_tables_for(n, max_functions, use_npn_reps=use_npn_reps)
    candidates = _build_universe_candidates(n)
    _LOG.info(
        "collect(n=%d, teacher=%s, objective=%s, num_funcs=%d, num_candidates=%d) -> %s",
        n, teacher, objective, len(truth_tables), len(candidates), out_csv,
    )

    pending: List[dict] = []
    all_rows: List[dict] = []
    header_written = False
    success = 0
    failed = 0

    t_start = time.time()
    for func_id, tt in enumerate(truth_tables):
        bf = BooleanFunction(n, int(tt))
        if not bf.onset:
            _LOG.info("[%d] tt=0x%X has empty on-set; skipping.", func_id, tt)
            continue

        try:
            if teacher == "ilp":
                chosen, total_cost = _run_ilp_teacher(bf, objective, timeout)
            elif teacher == "beam":
                chosen, total_cost = _run_beam_teacher(bf, beam_width=8, objective=objective)
            else:
                chosen, total_cost = _run_h_teacher(bf)
        except Exception as exc:
            warnings.warn(f"Teacher {teacher!r} failed on tt=0x{tt:X}: {exc}")
            _LOG.warning("Teacher %s failed on tt=0x%X (%s); skipping.", teacher, tt, exc)
            failed += 1
            continue

        if not chosen:
            _LOG.warning("Teacher %s produced no blocks for tt=0x%X; skipping.", teacher, tt)
            failed += 1
            continue

        feats = candidate_features(bf, candidates)
        rows = _rows_for_function(
            func_id=func_id,
            bf=bf,
            candidates=candidates,
            chosen_blocks=chosen,
            total_cost=total_cost,
            feature_matrix=feats,
        )
        pending.extend(rows)
        all_rows.extend(rows)
        success += 1

        if (success % max(1, flush_every)) == 0:
            header_written = _flush_rows(pending, out_csv, header_written)
            pending = []

    if pending:
        header_written = _flush_rows(pending, out_csv, header_written)

    elapsed = time.time() - t_start
    _LOG.info(
        "Done: %d ok / %d failed in %.1fs (%d rows). CSV: %s",
        success, failed, elapsed, len(all_rows), out_csv,
    )

    columns = _csv_columns()
    if all_rows:
        return pd.DataFrame(all_rows, columns=columns)
    return pd.DataFrame(columns=columns)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect labeled candidate-ranking training data.",
    )
    parser.add_argument("--n", type=int, required=True, help="Number of input variables.")
    parser.add_argument(
        "--teacher",
        choices=("ilp", "beam", "h"),
        default="ilp",
        help="Teacher solver to run for each function.",
    )
    parser.add_argument(
        "--max-functions",
        type=int,
        default=32,
        help="Truncate the function enumeration to this many entries.",
    )
    parser.add_argument(
        "--out-csv",
        default=None,
        help="Output CSV path. Defaults to <repo>/data/ilp/n{n}_{teacher}_{objective}.csv",
    )
    parser.add_argument(
        "--objective",
        choices=("cnot", "t"),
        default="cnot",
        help="Cost objective for ILP / beam teachers.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Per-function timeout in seconds (ILP only).",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed.")
    parser.add_argument(
        "--flush-every",
        type=int,
        default=4,
        help="Append rows to disk every K functions.",
    )
    parser.add_argument(
        "--use-npn-reps",
        action="store_true",
        help="When n==4, iterate all 222 NPN representatives without max_functions truncation.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    df = collect(
        n=args.n,
        teacher=args.teacher,
        max_functions=args.max_functions,
        out_csv=args.out_csv,
        objective=args.objective,
        timeout=args.timeout,
        seed=args.seed,
        flush_every=args.flush_every,
        use_npn_reps=args.use_npn_reps,
    )
    print(f"Wrote {len(df)} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
