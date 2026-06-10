"""
Algorithm 3: SSHR-I — ILP-based synthesis via Weighted Parity Set Covering.

Formulates the synthesis as a Weighted Parity Set Covering Problem (WP-SCP):
  - Variables x_i ∈ {0,1}: whether parallelotope P_i is selected
  - Each minterm in on-set must be covered ODD number of times
  - Each minterm in off-set must be covered EVEN number of times
  - Minimize total CNOT cost (or T-count, depending on `objective`)

Solver: Gurobi (gurobipy) only. A valid Gurobi license is required.

Time limit: 120 seconds per function (return best solution found).
"""
from __future__ import annotations
from typing import List, Tuple, Optional
import math

from bool_func import BooleanFunction, QuantumCircuit
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block, block_cnot_cost, block_t_cost
from bool_func import mct_cost as _mct_cost

TIMEOUT_SECONDS = 120  # default; sshr_i() uses n-adaptive default (7200 for n>=6)
_TIMEOUT_BY_N = {3: 30, 4: 30, 5: 120}  # n>=6 defaults to 7200


def block_t_cost_rp(p, n: int) -> int:
    """T-count cost using relative-phase Toffoli (T=4 for k=2 MCT)."""
    covered = 0
    for alpha in p.basis:
        covered |= alpha
    common_bits = bin(((1 << n) - 1) & ~covered).count('1')
    n_inner = sum(bin(alpha).count('1') - 1 for alpha in p.basis if alpha)
    n_controls = n_inner + common_bits
    if n_controls < 2:
        return 0
    if n_controls == 2:
        return 4  # relative-phase Toffoli
    return _mct_cost(n_controls)["T"]


def _circuit_cost(circ, objective: str) -> int:
    """Compute CNOT or RP-T cost of a QuantumCircuit."""
    cnot = t = 0
    for g in circ.gates:
        if g.type == 'MCT':
            k = len(g.controls)
            c = _mct_cost(k)
            cnot += c["CNOT"]
            t += 4 if k == 2 else c["T"]
        elif g.type == 'CNOT':
            cnot += 1
    return cnot if objective == "cnot" else t


def _solve_ilp_gurobi(
    parallelotopes: List[Parallelotope],
    all_minterms: List[int],
    onset: List[int],
    costs: List[float],
    timeout: float,
    cutoff: Optional[float] = None,
) -> List[int]:
    """Return list of selected parallelotope indices using Gurobi."""
    import gurobipy as gp
    from gurobipy import GRB

    onset_set = set(onset)
    m = len(parallelotopes)
    N = len(all_minterms)
    minterm_idx = {v: i for i, v in enumerate(all_minterms)}

    # Precompute covering index once: O(sum 2^dim) instead of O(N*m)
    covering_idx: List[List[int]] = [[] for _ in range(N)]
    for i, p in enumerate(parallelotopes):
        for v in p.vertices():
            covering_idx[minterm_idx[v]].append(i)

    # Tight upper bound for parity variables: optimal V_j is empirically ≤ 5;
    # cap at 20 to be safe. This dramatically tightens the LP relaxation vs ub=∞.
    PAR_UB = 20

    model = gp.Model()
    model.setParam("OutputFlag", 0)
    model.setParam("TimeLimit", timeout)
    # Prune any branch whose bound ≥ cutoff+0.5 (integer costs, so ≥ cutoff+1)
    if cutoff is not None:
        model.setParam("Cutoff", cutoff + 0.5)

    x = model.addVars(m, vtype=GRB.BINARY, name="x")
    # V_j eliminated by substitution into parity constraints
    y = model.addVars(N, vtype=GRB.INTEGER, lb=0, ub=PAR_UB, name="y")
    z = model.addVars(N, vtype=GRB.INTEGER, lb=0, ub=PAR_UB, name="z")

    # Parity constraints: sum_i x_i*e_ij = 2*y_j+1 (onset) or 2*z_j (offset)
    for j, minterm in enumerate(all_minterms):
        cover_sum = gp.quicksum(x[i] for i in covering_idx[j])
        if minterm in onset_set:
            model.addConstr(cover_sum - 2 * y[j] == 1)
        else:
            model.addConstr(cover_sum == 2 * z[j])

    model.setObjective(gp.quicksum(costs[i] * x[i] for i in range(m)), GRB.MINIMIZE)
    model.optimize()

    if model.SolCount == 0:
        return []
    return [i for i in range(m) if x[i].X > 0.5]


def _solve_ilp_gurobi_t_then_cnot(
    parallelotopes: List[Parallelotope],
    all_minterms: List[int],
    onset: List[int],
    t_costs: List[float],
    cnot_costs: List[float],
    timeout: float,
) -> List[int]:
    """Two-stage: minimize T first, then minimize CNOT at same optimal T."""
    import gurobipy as gp
    from gurobipy import GRB

    onset_set = set(onset)
    m = len(parallelotopes)
    N = len(all_minterms)
    minterm_idx = {v: i for i, v in enumerate(all_minterms)}

    # Precompute covering index once, shared between both stages
    covering_idx: List[List[int]] = [[] for _ in range(N)]
    for i, p in enumerate(parallelotopes):
        for v in p.vertices():
            covering_idx[minterm_idx[v]].append(i)

    PAR_UB = 20

    def build_base_model():
        mdl = gp.Model()
        mdl.setParam("OutputFlag", 0)
        mdl.setParam("TimeLimit", timeout / 2)
        xv = mdl.addVars(m, vtype=GRB.BINARY, name="x")
        yv = mdl.addVars(N, vtype=GRB.INTEGER, lb=0, ub=PAR_UB, name="y")
        zv = mdl.addVars(N, vtype=GRB.INTEGER, lb=0, ub=PAR_UB, name="z")
        for j, minterm in enumerate(all_minterms):
            cover_sum = gp.quicksum(xv[i] for i in covering_idx[j])
            if minterm in onset_set:
                mdl.addConstr(cover_sum - 2 * yv[j] == 1)
            else:
                mdl.addConstr(cover_sum == 2 * zv[j])
        return mdl, xv

    # Stage 1: minimize T
    model1, x1 = build_base_model()
    model1.setObjective(gp.quicksum(t_costs[i] * x1[i] for i in range(m)), GRB.MINIMIZE)
    model1.optimize()
    if model1.SolCount == 0:
        return []
    opt_t = model1.ObjVal

    # Stage 2: fix T budget, minimize CNOT
    model2, x2 = build_base_model()
    model2.setParam("TimeLimit", timeout / 2)
    model2.addConstr(gp.quicksum(t_costs[i] * x2[i] for i in range(m)) <= opt_t + 0.5)
    model2.setObjective(gp.quicksum(cnot_costs[i] * x2[i] for i in range(m)), GRB.MINIMIZE)
    model2.optimize()
    if model2.SolCount > 0:
        return [i for i in range(m) if x2[i].X > 0.5]
    return [i for i in range(m) if x1[i].X > 0.5]


def _solve_ilp(
    parallelotopes: List[Parallelotope],
    all_minterms: List[int],
    onset: List[int],
    costs: List[float],
    timeout: float,
    cutoff: Optional[float] = None,
) -> List[int]:
    """Solve WP-SCP using Gurobi. Raises RuntimeError if gurobipy is not available."""
    try:
        return _solve_ilp_gurobi(parallelotopes, all_minterms, onset, costs, timeout, cutoff)
    except ImportError:
        raise RuntimeError(
            "gurobipy is required for SSHR-I. Install it with:\n"
            "  pip install gurobipy   (needs a Gurobi license)"
        )


def _ilp_core(
    bf: BooleanFunction,
    objective: str,
    timeout: float,
) -> QuantumCircuit:
    """
    Core ILP synthesis for a single bf (no complement selection).
    Uses SSHR-H result as upper-bound Cutoff and fallback.
    """
    from sshr_h import sshr_h as _sshr_h
    from parallelotope import Parallelotope as _P

    n = bf.n
    if not bf.onset:
        return QuantumCircuit(n + 1)

    h_circ = _sshr_h(bf)
    h_cost = _circuit_cost(h_circ, objective)

    all_minterms = list(range(1 << n))
    onset = bf.onset
    onset_set = set(onset)

    parallelotopes = enumerate_parallelotopes(all_minterms, n)
    seen_vsets = {p.vertices() for p in parallelotopes}
    for v in all_minterms:
        s = frozenset([v])
        if s not in seen_vsets:
            parallelotopes.append(_P(v, []))
            seen_vsets.add(s)
    parallelotopes = [p for p in parallelotopes if p.vertices() & onset_set]

    if not parallelotopes:
        return h_circ

    if objective == "cnot":
        costs = [float(block_cnot_cost(p, n)) for p in parallelotopes]
        selected = _solve_ilp(parallelotopes, all_minterms, onset, costs, timeout, cutoff=h_cost)
    else:
        t_costs = [float(block_t_cost_rp(p, n)) for p in parallelotopes]
        c_costs = [float(block_cnot_cost(p, n)) for p in parallelotopes]
        selected = _solve_ilp_gurobi_t_then_cnot(
            parallelotopes, all_minterms, onset, t_costs, c_costs, timeout
        )
        if not selected:
            selected = _solve_ilp_gurobi(parallelotopes, all_minterms, onset, t_costs, timeout)

    if not selected:
        return h_circ

    circ = QuantumCircuit(n + 1)
    for i in selected:
        circ.add_block(synth_block(parallelotopes[i], n))
    return circ


def sshr_i(
    bf: BooleanFunction,
    objective: str = "cnot",    # "cnot" or "t"
    timeout: float = None,       # None = n-adaptive: 30s(n≤4), 120s(n=5), 7200s(n≥6)
    try_complement: bool = True, # run ILP on both f and NOT(f), each with timeout/2
) -> QuantumCircuit:
    """
    Synthesize a quantum oracle for Boolean function `bf` using SSHR-I.

    Parameters
    ----------
    bf             : BooleanFunction
    objective      : "cnot" minimizes CNOT count; "t" minimizes T-count
    timeout        : ILP time limit in seconds (total budget; split if try_complement=True)
    try_complement : If True, run ILP on both f and NOT(f) (each gets timeout/2),
                     return whichever costs less. X gate on output costs 0 CNOT/T.
                     Exact complement selection — better than SSHR-H heuristic.
                     Set False when input is already an optimal-complement representative
                     (e.g., NPN_REPS_N4 for n=4).

    Returns
    -------
    QuantumCircuit  (n+1 qubits)
    """
    n = bf.n
    if timeout is None:
        timeout = _TIMEOUT_BY_N.get(n, 7200)

    if not bf.onset:
        return QuantumCircuit(n + 1)

    if try_complement:
        # Exact complement selection: run ILP on both f and NOT(f), each with timeout/2
        full_mask = (1 << (1 << n)) - 1
        bf_comp = BooleanFunction(n, bf.truth_table ^ full_mask)

        circ_f = _ilp_core(bf, objective, timeout / 2)

        if bf_comp.onset:
            circ_c = _ilp_core(bf_comp, objective, timeout / 2)
            if _circuit_cost(circ_c, objective) < _circuit_cost(circ_f, objective):
                circ_c.add_x(n)  # X costs 0 CNOT, 0 T
                return circ_c

        return circ_f
    else:
        return _ilp_core(bf, objective, timeout)
