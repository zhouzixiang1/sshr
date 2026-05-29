"""
Algorithm 3: SSHR-I — ILP-based synthesis via Weighted Parity Set Covering.

Formulates the synthesis as a Weighted Parity Set Covering Problem (WP-SCP):
  - Variables x_i ∈ {0,1}: whether parallelotope P_i is selected
  - Each minterm in on-set must be covered ODD number of times
  - Each minterm in off-set must be covered EVEN number of times
  - Minimize total CNOT cost (or T-count, depending on `objective`)

Solver priority:
  1. Gurobi (gurobipy) — commercial, fastest
  2. PuLP + CBC/GLPK — open source fallback
  3. OR-Tools CP-SAT — open source fallback

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


def _solve_ilp_pulp(
    parallelotopes: List[Parallelotope],
    all_minterms: List[int],
    onset: List[int],
    costs: List[float],
    timeout: float,
) -> List[int]:
    """Return list of selected parallelotope indices using PuLP (CBC solver)."""
    import pulp

    onset_set = set(onset)
    m = len(parallelotopes)
    N = len(all_minterms)

    prob = pulp.LpProblem("WP_SCP", pulp.LpMinimize)

    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(m)]
    V = [pulp.LpVariable(f"V_{j}", lowBound=0, cat="Integer") for j in range(N)]
    y = [pulp.LpVariable(f"y_{j}", lowBound=0, cat="Integer") for j in range(N)]
    z = [pulp.LpVariable(f"z_{j}", lowBound=0, cat="Integer") for j in range(N)]

    # Objective
    prob += pulp.lpSum(costs[i] * x[i] for i in range(m))

    # C1
    for j, minterm in enumerate(all_minterms):
        covering = [i for i, p in enumerate(parallelotopes) if minterm in p.vertices()]
        prob += (V[j] == pulp.lpSum(x[i] for i in covering))

    # C2 / C3
    for j, minterm in enumerate(all_minterms):
        if minterm in onset_set:
            prob += (V[j] == 2 * y[j] + 1)
        else:
            prob += (V[j] == 2 * z[j])

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=int(timeout))
    prob.solve(solver)

    if pulp.LpStatus[prob.status] not in ("Optimal", "Not Solved"):
        # try to extract partial solution
        pass
    return [i for i in range(m) if pulp.value(x[i]) is not None and pulp.value(x[i]) > 0.5]


def _solve_ilp_highs(
    parallelotopes: List[Parallelotope],
    all_minterms: List[int],
    onset: List[int],
    costs: List[float],
    timeout: float,
) -> List[int]:
    """Return list of selected parallelotope indices using HiGHS (no size limit)."""
    import highspy

    onset_set = set(onset)
    P = len(parallelotopes)
    M = len(all_minterms)
    m_idx = {v: i for i, v in enumerate(all_minterms)}

    h = highspy.Highs()
    h.silent()
    h.setOptionValue('time_limit', timeout)

    # Variables: x[0..P-1] binary, V[P..P+M-1] integer, y/z[P+M..P+2M-1] integer
    h.addBinaries(P)
    h.addIntegrals(M)
    h.addIntegrals(M)
    for j in range(M):
        h.changeColBounds(P + j, 0, float(P))      # V_j bounds
        h.changeColBounds(P + M + j, 0, float(P))  # y/z_j bounds

    # Objective: min sum cost[i] * x[i]
    for i in range(P):
        h.changeColCost(i, costs[i])

    # Build covering index: for each minterm j, which parallelotopes cover it?
    covers: dict = {j: [] for j in range(M)}
    for i, p in enumerate(parallelotopes):
        for v in p.vertices():
            j = m_idx.get(v)
            if j is not None:
                covers[j].append(i)

    for j, mint in enumerate(all_minterms):
        # C1: sum_{i covers j} x_i - V_j = 0
        inds = covers[j] + [P + j]
        vals = [1.0] * len(covers[j]) + [-1.0]
        h.addRow(0.0, 0.0, len(inds), inds, vals)

        # C2/C3: V_j - 2*(y/z)_j = 1 (onset) or 0 (offset)
        rhs = 1.0 if mint in onset_set else 0.0
        h.addRow(rhs, rhs, 2, [P + j, P + M + j], [1.0, -2.0])

    h.minimize()

    status = str(h.getModelStatus())
    if 'Infeasible' in status or 'NotSet' in status:
        return []

    # Extract solution (binary vars)
    sol = [h.getInfoValue('primal_solution_status')[1]]
    try:
        vals_out = [h.val(i) for i in range(P)]
    except Exception:
        vals_out = [h.getInfoValue('objective_function_value')[1]]
        return []

    return [i for i in range(P) if vals_out[i] > 0.5]


def _solve_ilp(
    parallelotopes: List[Parallelotope],
    all_minterms: List[int],
    onset: List[int],
    costs: List[float],
    timeout: float,
) -> List[int]:
    """Try Gurobi first, then HiGHS, then PuLP."""
    try:
        return _solve_ilp_gurobi(parallelotopes, all_minterms, onset, costs, timeout)
    except ImportError:
        pass
    except Exception as e:
        # Gurobi model too large for restricted license → fall through to HiGHS
        if 'too large' in str(e).lower() or 'size' in str(e).lower():
            pass
        else:
            raise
    try:
        return _solve_ilp_highs(parallelotopes, all_minterms, onset, costs, timeout)
    except ImportError:
        pass
    try:
        return _solve_ilp_pulp(parallelotopes, all_minterms, onset, costs, timeout)
    except ImportError:
        pass
    raise RuntimeError(
        "No ILP solver found. Install gurobipy, highspy, or pulp:\n"
        "  pip install gurobipy   (needs Gurobi license)\n"
        "  pip install highspy    (free, no size limit)\n"
        "  pip install pulp"
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
        try:
            selected_indices = _solve_ilp_gurobi_t_then_cnot(
                parallelotopes, all_minterms, onset, t_costs, cnot_costs, timeout
            )
        except Exception:
            selected_indices = _solve_ilp(parallelotopes, all_minterms, onset, t_costs, timeout)

    if not selected_indices:
        # ILP failed / timeout with no solution: fall back to SSHR-H
        from sshr_h import sshr_h
        return sshr_h(bf)

    for i in selected_indices:
        block = synth_block(parallelotopes[i], n)
        circuit.add_block(block)

    return circuit
