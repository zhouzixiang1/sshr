"""
Investigate the n=4 SSHR-I gap.
Key question: does using a different cost metric in the ILP explain the gap?
Try: minimize only MCT CNOT cost (ignore CNOT chain), vs current (include chains).
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block, block_cnot_cost, block_t_cost
from npn_reps_n4 import NPN_REPS_N4

def _set_bits(mask):
    bits = []
    pos = 0
    while mask:
        if mask & 1: bits.append(pos)
        mask >>= 1; pos += 1
    return bits

def block_mct_cnot_only(p, n):
    """Cost = only the MCT gate CNOT, ignoring CNOT chain."""
    covered = 0
    for alpha in p.basis: covered |= alpha
    common_bits = _set_bits(((1 << n) - 1) & ~covered)
    n_inner = sum(len(_set_bits(alpha)) - 1 for alpha in p.basis if _set_bits(alpha))
    n_controls = n_inner + len(common_bits)
    if n_controls == 0: return 0
    if n_controls == 1: return 1
    return mct_cost(n_controls)["CNOT"]

def gate_stats(circ):
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == "MCT":
            c = mct_cost(len(g.controls))
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return T, C, anc

def sshr_i_custom(bf, cost_fn, timeout=60):
    """SSHR-I with custom cost function for ILP objective."""
    import gurobipy as gp
    from gurobipy import GRB

    n = bf.n
    from bool_func import QuantumCircuit
    circuit = QuantumCircuit(n + 1)
    onset = bf.onset
    if not onset: return circuit

    all_minterms = list(range(1 << n))
    parallelotopes = enumerate_parallelotopes(all_minterms, n)
    seen_vsets = {p.vertices() for p in parallelotopes}
    for v in all_minterms:
        s = frozenset([v])
        if s not in seen_vsets:
            parallelotopes.append(Parallelotope(v, []))
    onset_set = set(onset)
    parallelotopes = [p for p in parallelotopes if p.vertices() & onset_set]
    if not parallelotopes: return circuit

    costs = [float(cost_fn(p, n)) for p in parallelotopes]
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

    for j, minterm in enumerate(all_minterms):
        covering = [i for i, p in enumerate(parallelotopes) if minterm in p.vertices()]
        model.addConstr(V[j] == gp.quicksum(x[i] for i in covering))
    for j, minterm in enumerate(all_minterms):
        if minterm in onset_set:
            model.addConstr(V[j] == 2 * y[j] + 1)
        else:
            model.addConstr(V[j] == 2 * z[j])

    model.setObjective(gp.quicksum(costs[i] * x[i] for i in range(m)), GRB.MINIMIZE)
    model.optimize()

    if model.SolCount == 0: return circuit
    selected = [i for i in range(m) if x[i].X > 0.5]
    for i in selected:
        circuit.add_block(synth_block(parallelotopes[i], n))
    return circuit

print("Investigating n=4 SSHR-I gap: different cost functions")
print("Paper reference: T=6028, CNOT=4696, Anc=212")
print()

for label, cost_fn in [
    ("block_cnot_cost (current)", block_cnot_cost),
    ("mct_cnot_only (no chains)", block_mct_cnot_only),
]:
    T4, C4, anc4 = 0, 0, 0
    t0 = time.time()
    for tt in NPN_REPS_N4:
        bf = BooleanFunction(4, tt)
        if not bf.onset: continue
        circ = sshr_i_custom(bf, cost_fn, timeout=60)
        t, c, a = gate_stats(circ)
        T4 += t; C4 += c; anc4 += a
    dt = time.time() - t0
    print(f"{label}:")
    print(f"  T={T4} CNOT={C4} Anc={anc4} ({dt:.0f}s)")
    print(f"  T off: {abs(T4-6028)/6028*100:.1f}%, CNOT off: {abs(C4-4696)/4696*100:.1f}%")
    print()
