"""
ESOP synthesis via ILP (exact minimum XOR-sum-of-products).

Uses the same WP-SCP ILP framework as SSHR-I, but with all 3^n
possible product-term cubes as candidate subsets instead of parallelotopes.

A cube (care_mask, value) covers all x where (x & care_mask) == value.
The corresponding MCT gate has len(care_mask set bits) controls.

This gives the optimal ESOP baseline to compare against SSHR.
"""
from __future__ import annotations
from typing import List, Tuple
from bool_func import BooleanFunction, QuantumCircuit, mct_cost


def _enumerate_cubes(n: int) -> List[Tuple[int, int]]:
    """
    Enumerate all 3^n cubes in {0,1}^n.
    Returns (care_mask, value) pairs where free vars have care_mask bit=0.
    """
    cubes = []
    N = 1 << n
    # care_mask iterates over all 2^n subsets of variables
    for care_mask in range(N):
        # For each care_mask, value iterates over all 2^popcount(care_mask) assignments
        free_bits = [(N-1) & ~care_mask]  # not used directly
        for value in range(N):
            if (value & ~care_mask) != 0:
                continue  # value must only have bits set where care_mask is set
            # cube covers all x with (x & care_mask) == value
            cubes.append((care_mask, value))
    return cubes


def _cube_vertices(care_mask: int, value: int, n: int) -> frozenset:
    """Return frozenset of all minterms covered by this cube."""
    N = 1 << n
    free_mask = ((N - 1) & ~care_mask)
    # Base = value, iterate over all combinations of free bits
    verts = set()
    free_bit_positions = [b for b in range(n) if not ((care_mask >> b) & 1)]
    for i in range(1 << len(free_bit_positions)):
        v = value
        for j, b in enumerate(free_bit_positions):
            if (i >> j) & 1:
                v |= (1 << b)
        verts.add(v)
    return frozenset(verts)


def _cube_mct_cost(care_mask: int, n: int) -> dict:
    """Cost of MCT gate for a cube with given care_mask."""
    k = bin(care_mask).count("1")  # number of controlled bits
    if k == 0:
        return {"T": 0, "CNOT": 0, "ancilla": 0}  # X gate only
    return mct_cost(k)


def esop_ilp(
    bf: BooleanFunction,
    objective: str = "cnot",
    timeout: float = 120,
) -> QuantumCircuit:
    """
    Exact ESOP synthesis using ILP (Gurobi).
    Returns QuantumCircuit implementing bf as ESOP.
    """
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    onset = bf.onset
    if not onset:
        return circuit

    all_minterms = list(range(1 << n))
    onset_set = set(onset)

    # Enumerate cubes and filter to those intersecting on-set
    all_cubes = _enumerate_cubes(n)
    cubes = []
    verts_list = []
    for care_mask, value in all_cubes:
        verts = _cube_vertices(care_mask, value, n)
        if verts & onset_set:
            cubes.append((care_mask, value))
            verts_list.append(verts)

    # Compute costs
    if objective == "cnot":
        costs = [float(_cube_mct_cost(cm, n)["CNOT"]) for cm, v in cubes]
    else:
        costs = [float(_cube_mct_cost(cm, n)["T"]) for cm, v in cubes]

    # Solve ILP (same WP-SCP formulation) using Gurobi only
    import gurobipy as gp
    from gurobipy import GRB

    m = len(cubes)
    N = len(all_minterms)

    model = gp.Model()
    model.setParam("OutputFlag", 0)
    model.setParam("TimeLimit", timeout)

    x = model.addVars(m, vtype=GRB.BINARY, name="x")
    V = model.addVars(N, vtype=GRB.INTEGER, lb=0, name="V")
    y = model.addVars(N, vtype=GRB.INTEGER, lb=0, name="y")
    z = model.addVars(N, vtype=GRB.INTEGER, lb=0, name="z")

    for j, mint in enumerate(all_minterms):
        covering = [i for i, verts in enumerate(verts_list) if mint in verts]
        model.addConstr(V[j] == gp.quicksum(x[i] for i in covering))

    for j, mint in enumerate(all_minterms):
        if mint in onset_set:
            model.addConstr(V[j] == 2 * y[j] + 1)
        else:
            model.addConstr(V[j] == 2 * z[j])

    model.setObjective(gp.quicksum(costs[i] * x[i] for i in range(m)), GRB.MINIMIZE)
    model.optimize()

    selected = [i for i in range(m) if model.SolCount > 0 and x[i].X > 0.5]

    output_qubit = n
    for i in selected:
        care_mask, value = cubes[i]
        controls = [b for b in range(n) if (care_mask >> b) & 1]
        x_wrap = [b for b in controls if not ((value >> b) & 1)]
        for b in x_wrap:
            circuit.add_x(b)
        circuit.add_mct(controls, output_qubit)
        for b in x_wrap:
            circuit.add_x(b)

    return circuit
