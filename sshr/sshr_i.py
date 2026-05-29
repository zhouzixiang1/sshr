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

TIMEOUT_SECONDS = 120


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


def _solve_ilp_gurobi(
    parallelotopes: List[Parallelotope],
    all_minterms: List[int],
    onset: List[int],
    costs: List[float],
    timeout: float,
) -> List[int]:
    """Return list of selected parallelotope indices using Gurobi."""
    import gurobipy as gp
    from gurobipy import GRB

    onset_set = set(onset)
    m = len(parallelotopes)
    N = len(all_minterms)
    minterm_idx = {v: i for i, v in enumerate(all_minterms)}

    model = gp.Model()
    model.setParam("OutputFlag", 0)
    model.setParam("TimeLimit", timeout)

    x = model.addVars(m, vtype=GRB.BINARY, name="x")
    V = model.addVars(N, vtype=GRB.INTEGER, lb=0, name="V")
    y = model.addVars(N, vtype=GRB.INTEGER, lb=0, name="y")
    z = model.addVars(N, vtype=GRB.INTEGER, lb=0, name="z")

    # C1: V_j = sum_i x_i * e_ij
    for j, minterm in enumerate(all_minterms):
        covering = [i for i, p in enumerate(parallelotopes) if minterm in p.vertices()]
        model.addConstr(V[j] == gp.quicksum(x[i] for i in covering), name=f"C1_{j}")

    for j, minterm in enumerate(all_minterms):
        if minterm in onset_set:
            # C2: V_j = 2*y_j + 1  (odd)
            model.addConstr(V[j] == 2 * y[j] + 1, name=f"C2_{j}")
        else:
            # C3: V_j = 2*z_j  (even)
            model.addConstr(V[j] == 2 * z[j], name=f"C3_{j}")

    obj = gp.quicksum(costs[i] * x[i] for i in range(m))
    model.setObjective(obj, GRB.MINIMIZE)
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

    def build_base_model():
        mdl = gp.Model()
        mdl.setParam("OutputFlag", 0)
        mdl.setParam("TimeLimit", timeout / 2)
        xv = mdl.addVars(m, vtype=GRB.BINARY, name="x")
        Vv = mdl.addVars(N, vtype=GRB.INTEGER, lb=0, name="V")
        yv = mdl.addVars(N, vtype=GRB.INTEGER, lb=0, name="y")
        zv = mdl.addVars(N, vtype=GRB.INTEGER, lb=0, name="z")
        for j, minterm in enumerate(all_minterms):
            covering = [i for i, p in enumerate(parallelotopes) if minterm in p.vertices()]
            mdl.addConstr(Vv[j] == gp.quicksum(xv[i] for i in covering))
        for j, minterm in enumerate(all_minterms):
            if minterm in onset_set:
                mdl.addConstr(Vv[j] == 2 * yv[j] + 1)
            else:
                mdl.addConstr(Vv[j] == 2 * zv[j])
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
) -> List[int]:
    """Solve WP-SCP using Gurobi. Raises RuntimeError if gurobipy is not available."""
    try:
        return _solve_ilp_gurobi(parallelotopes, all_minterms, onset, costs, timeout)
    except ImportError:
        raise RuntimeError(
            "gurobipy is required for SSHR-I. Install it with:\n"
            "  pip install gurobipy   (needs a Gurobi license)"
        )


def sshr_i(
    bf: BooleanFunction,
    objective: str = "cnot",  # "cnot" or "t"
    timeout: float = TIMEOUT_SECONDS,
) -> QuantumCircuit:
    """
    Synthesize a quantum oracle for Boolean function `bf` using SSHR-I.

    Parameters
    ----------
    bf        : BooleanFunction
    objective : "cnot" minimizes CNOT count; "t" minimizes T-count
    timeout   : ILP time limit in seconds

    Returns
    -------
    QuantumCircuit  (n+1 qubits)
    """
    n = bf.n
    circuit = QuantumCircuit(n + 1)

    onset = bf.onset
    if not onset:
        return circuit

    all_minterms = list(range(1 << n))
    offset = bf.offset

    # Enumerate all parallelotopes reachable from on-set AND off-set
    # (the ILP can use any subset; vertices don't need to be all on-set)
    # Per paper: S = all parallelotopes in the hypercube (vertices in {0,1}^n).
    # In practice we limit to parallelotopes whose vertices overlap with on-set.
    parallelotopes = enumerate_parallelotopes(list(range(1 << n)), n)
    # Also add single-minterm (dim-0) fallbacks
    from parallelotope import Parallelotope as _P
    seen_vsets = {p.vertices() for p in parallelotopes}
    for v in all_minterms:
        s = frozenset([v])
        if s not in seen_vsets:
            parallelotopes.append(_P(v, []))
            seen_vsets.add(s)

    # Filter: keep only parallelotopes that intersect on-set (otherwise useless)
    onset_set = set(onset)
    parallelotopes = [p for p in parallelotopes if p.vertices() & onset_set]

    if not parallelotopes:
        # Fallback: cover each minterm individually
        for v in onset:
            p0 = _P(v, [])
            circuit.add_block(synth_block(p0, n))
        return circuit

    # Compute costs
    if objective == "cnot":
        costs = [float(block_cnot_cost(p, n)) for p in parallelotopes]
        selected_indices = _solve_ilp(parallelotopes, all_minterms, onset, costs, timeout)
    else:
        # T-objective: two-stage (1) minimize T with relative-phase Toffoli,
        # (2) fix T budget and minimize CNOT
        t_costs = [float(block_t_cost_rp(p, n)) for p in parallelotopes]
        cnot_costs = [float(block_cnot_cost(p, n)) for p in parallelotopes]
        selected_indices = _solve_ilp_gurobi_t_then_cnot(
            parallelotopes, all_minterms, onset, t_costs, cnot_costs, timeout
        )
        if not selected_indices:
            selected_indices = _solve_ilp_gurobi(
                parallelotopes, all_minterms, onset, t_costs, timeout
            )

    if not selected_indices:
        # ILP failed / timeout with no solution: fall back to SSHR-H
        from sshr_h import sshr_h
        return sshr_h(bf)

    for i in selected_indices:
        block = synth_block(parallelotopes[i], n)
        circuit.add_block(block)

    return circuit
