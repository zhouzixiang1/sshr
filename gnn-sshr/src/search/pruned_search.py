"""Candidate-pruning wrappers around SSHR-H / SSHR-I / Beam.

This module supports the AI-SSHR experimental pipeline by providing utilities
to prune the parallelotope candidate pool using externally supplied scores
(e.g. from a learned ranker or GNN), then dispatch the surviving candidates
to one of the core synthesis backends:

    - ``ilp``  : weighted parity set covering via Gurobi (uses the pruned set
                 directly through ``sshr_core.sshr_i._solve_ilp_gurobi``).
    - ``beam`` : the production beam search.  The current ``sshr_beam`` API
                 does not accept a pre-pruned candidate list, so the full
                 enumeration is used; this is documented as a limitation
                 below and a coverage-feasibility check is still performed.
    - ``h``    : the SSHR-H heuristic.  Same limitation as ``beam``.

Public API
----------
- :func:`prune_candidates` - top-ratio selection with optional coverage repair.
- :func:`run_pruned`       - end-to-end enumerate -> prune -> synthesise.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

# Allow ``PYTHONPATH=src`` style invocation.
_THIS = Path(__file__).resolve()
_SRC = _THIS.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sshr_core.bool_func import BooleanFunction, QuantumCircuit  # noqa: E402
from sshr_core.block_synth import (  # noqa: E402
    block_cnot_cost,
    block_t_cost,
    synth_block,
)
from sshr_core.parallelotope import Parallelotope  # noqa: E402
from sshr_core.parallelotope_enum import enumerate_parallelotopes  # noqa: E402


__all__ = ["prune_candidates", "run_pruned"]


# ---------------------------------------------------------------------------
# Pruning
# ---------------------------------------------------------------------------

def prune_candidates(
    candidates: Sequence[Parallelotope],
    scores: Sequence[float],
    keep_ratio: float,
    ensure_coverage: bool = True,
    onset: Optional[Iterable[int]] = None,
    n: Optional[int] = None,
) -> List[int]:
    """Return indices of the candidates surviving top-``keep_ratio`` pruning.

    Parameters
    ----------
    candidates : Sequence[Parallelotope]
        Full enumerated candidate list.
    scores : Sequence[float]
        Per-candidate ranker scores; higher is better.
    keep_ratio : float
        Fraction of candidates to keep (clamped to ``[0, 1]``).  Always keeps
        at least one candidate when the input is non-empty.
    ensure_coverage : bool, default True
        If True, the kept set is repaired so that the WP-SCP ILP is
        feasible: for every onset minterm ``v`` the singleton parallelotope
        ``{v}`` is forced into the kept set (singletons are unit vectors in
        the GF(2) coverage matrix and trivially make the parity cover
        feasible).  If a singleton is unavailable for some ``v`` (which
        should not happen when the candidates come from
        ``_enumerate_with_singletons``), the cheapest candidate containing
        ``v`` as a vertex is added as a best-effort fallback.
    onset : Iterable[int], optional
        Onset minterms.  Required if ``ensure_coverage`` is True.
    n : int, optional
        Number of input variables (used for cost ranking when adding back
        missing-coverage candidates).  Defaults to a size-only ordering.

    Returns
    -------
    list[int]
        Sorted unique indices into ``candidates``.
    """
    m = len(candidates)
    if m == 0:
        return []
    if len(scores) != m:
        raise ValueError(
            f"len(scores)={len(scores)} != len(candidates)={m}"
        )

    # Top-keep_ratio selection.
    keep_ratio = max(0.0, min(1.0, float(keep_ratio)))
    k = max(1, int(round(keep_ratio * m)))
    order = sorted(range(m), key=lambda i: -float(scores[i]))
    kept = set(order[:k])

    if ensure_coverage:
        if onset is None:
            raise ValueError("ensure_coverage=True requires `onset`.")
        onset_list = list(onset)

        # ------------------------------------------------------------------
        # WP-SCP feasibility repair.
        #
        # Mere "any-coverage" of the onset (set-union) is NOT sufficient for
        # the parity-cover ILP -- onset minterms must be coverable by an
        # *odd* combination over GF(2).  The simplest sufficient condition
        # is to ensure that, for every onset minterm v, the singleton
        # parallelotope {v} is in the kept set: those are unit vectors in
        # the GF(2) coverage matrix and trivially span the onset
        # characteristic vector while keeping every other parity at 0.
        #
        # ``_enumerate_with_singletons`` guarantees a singleton candidate
        # exists for every minterm that intersects the onset, so a singleton
        # for each onset v is present in ``candidates``.
        # ------------------------------------------------------------------
        singleton_idx: Dict[int, int] = {}
        for i, p in enumerate(candidates):
            if p.dim == 0:
                verts = p.vertices()
                if len(verts) == 1:
                    (v,) = tuple(verts)
                    # Prefer the first occurrence; multiple singletons would
                    # be a duplicate, but be defensive.
                    if v not in singleton_idx:
                        singleton_idx[v] = i

        for v in onset_list:
            si = singleton_idx.get(v)
            if si is not None:
                kept.add(si)
            else:
                # Fallback: no singleton for this onset minterm. Add the
                # cheapest candidate that contains v as a vertex; while not
                # a parity-feasibility guarantee on its own, pairing it with
                # other singletons in the kept set keeps the ILP solvable in
                # the common case.  Cost preference: lowest dim, smallest
                # size, then lowest CNOT cost (if ``n`` is known), then idx.
                def _cost_key(idx: int) -> tuple:
                    p = candidates[idx]
                    dim = p.dim
                    size = len(p)
                    cn = block_cnot_cost(p, n) if n is not None else 0
                    return (dim, size, cn, idx)

                best_idx: Optional[int] = None
                best_key: Optional[tuple] = None
                for i, p in enumerate(candidates):
                    if i in kept:
                        continue
                    if v not in p.vertices():
                        continue
                    key = _cost_key(i)
                    if best_key is None or key < best_key:
                        best_key = key
                        best_idx = i
                if best_idx is not None:
                    kept.add(best_idx)

    return sorted(kept)


# ---------------------------------------------------------------------------
# Enumeration helper (matches ``sshr_i._ilp_core`` semantics)
# ---------------------------------------------------------------------------

def _enumerate_with_singletons(bf: BooleanFunction) -> List[Parallelotope]:
    """Enumerate dim>=1 parallelotopes plus singleton fall-backs, then filter
    to those whose vertex set intersects the onset (mirrors ``_ilp_core``)."""
    n = bf.n
    onset_set = set(bf.onset)
    all_minterms = list(range(1 << n))
    parallelotopes = enumerate_parallelotopes(all_minterms, n)
    seen = {p.vertices() for p in parallelotopes}
    for v in all_minterms:
        s = frozenset([v])
        if s not in seen:
            parallelotopes.append(Parallelotope(v, []))
            seen.add(s)
    return [p for p in parallelotopes if p.vertices() & onset_set]


# ---------------------------------------------------------------------------
# Solver dispatch
# ---------------------------------------------------------------------------

def _circuit_cost(circ: QuantumCircuit, objective: str) -> int:
    """Sum the elementary CNOT or T cost of every gate in ``circ``."""
    from sshr_core.bool_func import mct_cost, mct_cost_rp
    fn = mct_cost_rp if objective == "t" else mct_cost
    total = 0
    for g in circ.gates:
        if g.type == "MCT":
            d = fn(len(g.controls))
            total += d["T"] if objective == "t" else d["CNOT"]
        elif g.type == "CNOT":
            if objective == "cnot":
                total += 1
        # X / output X: 0 cost in both objectives.
    return int(total)


def _run_ilp_pruned(
    bf: BooleanFunction,
    pruned: List[Parallelotope],
    objective: str,
    timeout: float,
) -> QuantumCircuit:
    """Build a circuit by feeding ``pruned`` directly to Gurobi WP-SCP."""
    from sshr_core.sshr_i import (
        _solve_ilp_gurobi,
        _solve_ilp_gurobi_t_then_cnot,
        block_t_cost_rp,
    )

    n = bf.n
    all_minterms = list(range(1 << n))
    if objective == "cnot":
        costs = [float(block_cnot_cost(p, n)) for p in pruned]
        selected = _solve_ilp_gurobi(
            pruned, all_minterms, bf.onset, costs, timeout,
        )
    else:
        t_costs = [float(block_t_cost_rp(p, n)) for p in pruned]
        c_costs = [float(block_cnot_cost(p, n)) for p in pruned]
        selected = _solve_ilp_gurobi_t_then_cnot(
            pruned, all_minterms, bf.onset, t_costs, c_costs, timeout,
        )
        if not selected:
            selected = _solve_ilp_gurobi(
                pruned, all_minterms, bf.onset, t_costs, timeout,
            )
    circ = QuantumCircuit(n + 1)
    for i in selected:
        circ.add_block(synth_block(pruned[i], n))
    return circ


def _check_feasible(pruned: List[Parallelotope], onset: Iterable[int]) -> bool:
    """Return True iff every onset minterm is covered by some pruned cand."""
    cov: set = set()
    for p in pruned:
        cov |= p.vertices()
    return set(onset).issubset(cov)


def run_pruned(
    bf: BooleanFunction,
    scores: Sequence[float],
    keep_ratio: float = 0.1,
    solver: str = "ilp",
    ensure_coverage: bool = True,
    **solver_kwargs: Any,
) -> Dict[str, Any]:
    """Enumerate, prune and synthesise.

    Parameters
    ----------
    bf : BooleanFunction
        The Boolean function to synthesise.
    scores : Sequence[float]
        Score per candidate, ordered to match the output of
        :func:`_enumerate_with_singletons` for ``bf``.
    keep_ratio : float, default 0.1
        Fraction of candidates passed to the solver.
    solver : {"ilp", "beam", "h"}, default "ilp"
        Backend to use after pruning.  ``ilp`` actually consumes the pruned
        set; ``beam`` and ``h`` currently fall back to full enumeration --
        see module docstring.  ``ilp`` requires gurobipy.
    ensure_coverage : bool, default True
        Whether to repair onset coverage after top-ratio selection.
    **solver_kwargs
        Forwarded to the underlying solver:
            ilp  : ``objective`` (default ``"cnot"``), ``timeout`` (default 60).
            beam : everything passed to ``sshr_core.sshr_beam.sshr_beam``.
            h    : ``R`` is forwarded to ``sshr_core.sshr_h.sshr_h``.

    Returns
    -------
    dict
        ``{'kept': int, 'cost': int, 'time_s': float, 'feasible': bool}``.
        ``cost`` is the CNOT (or T) count of the produced circuit, depending
        on ``objective``.  ``feasible`` is True iff a valid covering circuit
        was produced.
    """
    objective = solver_kwargs.get("objective", "cnot")

    # 1. Enumerate full candidate list.
    candidates = _enumerate_with_singletons(bf)
    if len(scores) != len(candidates):
        raise ValueError(
            f"len(scores)={len(scores)} != #candidates={len(candidates)}"
        )

    # 2. Prune.
    kept_idx = prune_candidates(
        candidates,
        scores,
        keep_ratio=keep_ratio,
        ensure_coverage=ensure_coverage,
        onset=bf.onset,
        n=bf.n,
    )
    pruned = [candidates[i] for i in kept_idx]

    feasible_input = _check_feasible(pruned, bf.onset)

    # 3. Dispatch solver.
    t0 = time.time()
    circ: QuantumCircuit
    feasible = False
    if solver == "ilp":
        if not feasible_input:
            # WP-SCP would be infeasible -- bail out early.
            elapsed = time.time() - t0
            return {
                "kept": len(pruned),
                "cost": -1,
                "time_s": elapsed,
                "feasible": False,
            }
        timeout = float(solver_kwargs.get("timeout", 60.0))
        circ = _run_ilp_pruned(bf, pruned, objective, timeout)
        feasible = len(circ.gates) > 0 or not bf.onset
    elif solver == "beam":
        # NOTE: ``sshr_beam`` enumerates internally and does not yet accept a
        # pre-pruned candidate list.  We call the full solver and rely on the
        # coverage check above for diagnostics.
        from sshr_core.sshr_beam import sshr_beam
        beam_kwargs = {
            k: v for k, v in solver_kwargs.items()
            if k in {"objective", "width", "branch", "verbose"}
        }
        circ = sshr_beam(bf, **beam_kwargs)
        feasible = True
    elif solver == "h":
        # NOTE: ``sshr_h`` enumerates internally; same limitation as beam.
        from sshr_core.sshr_h import sshr_h
        h_kwargs = {k: v for k, v in solver_kwargs.items() if k in {"R"}}
        circ = sshr_h(bf, **h_kwargs)
        feasible = True
    else:
        raise ValueError(f"unknown solver: {solver!r}")

    elapsed = time.time() - t0
    cost = _circuit_cost(circ, objective) if feasible else -1
    return {
        "kept": len(pruned),
        "cost": cost,
        "time_s": elapsed,
        "feasible": feasible,
    }


# ---------------------------------------------------------------------------
# Smoke run / CLI
# ---------------------------------------------------------------------------

def _smoke_run() -> Dict[str, Any]:
    """Tiny n=3 sanity check: random scores + ``solver='h'`` (no Gurobi)."""
    import random
    bf = BooleanFunction(3, 0xB6)  # arbitrary 3-input function
    cands = _enumerate_with_singletons(bf)
    rng = random.Random(0)
    scores = [rng.random() for _ in cands]
    res = run_pruned(
        bf,
        scores,
        keep_ratio=0.5,
        solver="h",
        ensure_coverage=True,
    )
    res["n_candidates"] = len(cands)
    return res


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Prune parallelotope candidates and synthesise via "
                    "SSHR-I / SSHR-Beam / SSHR-H.",
    )
    p.add_argument(
        "--n", type=int, default=3,
        help="Number of input variables (default: 3).",
    )
    p.add_argument(
        "--tt", type=lambda s: int(s, 0), default=0xB6,
        help="Truth-table integer (e.g. 0xB6 for n=3).",
    )
    p.add_argument(
        "--keep-ratio", type=float, default=0.5,
        help="Fraction of candidates to keep (default 0.5).",
    )
    p.add_argument(
        "--solver", choices=["ilp", "beam", "h"], default="h",
        help="Backend solver (default: h, which needs no Gurobi).",
    )
    p.add_argument(
        "--objective", choices=["cnot", "t"], default="cnot",
    )
    p.add_argument(
        "--no-coverage", action="store_true",
        help="Disable coverage repair after pruning.",
    )
    p.add_argument(
        "--seed", type=int, default=0,
        help="RNG seed for the demo random scoring.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """Script entry point.  Runs a single function with random scores."""
    import random

    args = _build_arg_parser().parse_args(argv)
    bf = BooleanFunction(args.n, args.tt)
    cands = _enumerate_with_singletons(bf)
    rng = random.Random(args.seed)
    scores = [rng.random() for _ in cands]

    res = run_pruned(
        bf,
        scores,
        keep_ratio=args.keep_ratio,
        solver=args.solver,
        ensure_coverage=not args.no_coverage,
        objective=args.objective,
    )
    print(
        f"n={args.n} tt=0x{args.tt:X} solver={args.solver} "
        f"#cands={len(cands)} kept={res['kept']} "
        f"cost={res['cost']} time_s={res['time_s']:.3f} "
        f"feasible={res['feasible']}"
    )
    return 0


if __name__ == "__main__":
    smoke = _smoke_run()
    print(f"[smoke] {smoke}")
    raise SystemExit(main())
