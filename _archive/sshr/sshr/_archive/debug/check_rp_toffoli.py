"""
Test: paper's Table VII T=2832 for n=3 explained by relative-phase Toffoli (T=4 per 2MCT).

Hypothesis: for T-objective, paper uses T=4 per k=2 MCT (relative-phase Toffoli)
instead of standard T=7. The final T count is also reported using T=4.

Check: if we use 196 Toffoli gates (as found by our T-obj ILP) with T=4 each:
  T = 196*4 + 128*16 = 784 + 2048 = 2832 ✓ (paper value!)

Also check what CNOT count the T-obj solution actually has with this counting.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i

def gate_stats_rp(circ, rp_toffoli=False):
    """Count gates. If rp_toffoli=True, count 2MCT as T=4 instead of T=7."""
    raw = {}; T, C, anc = 0, 0, 0
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            raw[f"{k}-MCT"] = raw.get(f"{k}-MCT", 0) + 1
            if rp_toffoli and k == 2:
                # Relative-phase Toffoli: T=4, CNOT cost depends on decomp
                # Use T=4, keep CNOT=6 (same circuit structure, just different T count)
                T += 4
                C += mct_cost(k)["CNOT"]
                anc += mct_cost(k)["ancilla"]
            else:
                c = mct_cost(k)
                T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return raw, T, C, anc

# Run T-objective and count with standard vs relative-phase T cost
print("n=3 SSHR-I T-objective: standard T=7 vs relative-phase T=4 for 2MCT")
print("Paper: T=2832, CNOT=3579")
print()

T_std, T_rp, C_std, C_rp = 0, 0, 0, 0
count_2mct = 0; count_3mct = 0

t0 = time.time()
for tt in range(1, 256):
    bf = BooleanFunction(3, tt)
    if not bf.onset: continue
    circ = sshr_i(bf, objective="t", timeout=30)
    raw_std, t_s, c_s, _ = gate_stats_rp(circ, rp_toffoli=False)
    raw_rp,  t_r, c_r, _ = gate_stats_rp(circ, rp_toffoli=True)
    T_std += t_s; T_rp += t_r
    C_std += c_s; C_rp += c_r
    count_2mct += raw_std.get('2-MCT', 0)
    count_3mct += raw_std.get('3-MCT', 0)

dt = time.time() - t0
print(f"Standard (T=7 per 2MCT):        T={T_std} CNOT={C_std} ({dt:.0f}s)")
print(f"Relative-phase (T=4 per 2MCT):  T={T_rp} CNOT={C_rp}")
print(f"Paper T-objective n=3:           T=2832 CNOT=3579")
print()
print(f"Gate counts: 2MCT={count_2mct}, 3MCT={count_3mct}")
print(f"Check: {count_2mct}*4 + {count_3mct}*16 = {count_2mct*4 + count_3mct*16}")
print(f"Check: {count_2mct}*7 + {count_3mct}*16 = {count_2mct*7 + count_3mct*16}")

# Now use T=4 in ILP objective too, and see what circuits we get
print()
print("Now using T=4 (relative-phase) in ILP objective:")
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block
from bool_func import QuantumCircuit
import gurobipy as gp
from gurobipy import GRB

def mct_t_rp(n_controls):
    """T cost of MCT with relative-phase Toffoli for k=2."""
    if n_controls <= 1: return 0
    if n_controls == 2: return 4  # relative-phase
    return mct_cost(n_controls)["T"]

def block_t_cost_rp(p, n):
    covered = 0
    for alpha in p.basis: covered |= alpha
    common_bits = [(n-1) & ~covered]
    n_inner = sum(bin(alpha).count('1') - 1 for alpha in p.basis if alpha)
    n_common = bin(((1<<n)-1) & ~covered).count('1')
    n_controls = n_inner + n_common
    return mct_t_rp(n_controls)

def sshr_i_rp_t(bf, timeout=30):
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    onset = bf.onset
    if not onset: return circuit
    all_minterms = list(range(1 << n))
    ps = enumerate_parallelotopes(all_minterms, n)
    seen = {p.vertices() for p in ps}
    for v in all_minterms:
        s = frozenset([v])
        if s not in seen: ps.append(Parallelotope(v, [])); seen.add(s)
    onset_set = set(onset)
    ps = [p for p in ps if p.vertices() & onset_set]
    if not ps: return circuit
    costs = [float(block_t_cost_rp(p, n)) for p in ps]
    m = len(ps); N = len(all_minterms)
    model = gp.Model(); model.setParam("OutputFlag", 0); model.setParam("TimeLimit", timeout)
    x = model.addVars(m, vtype=GRB.BINARY)
    V = model.addVars(N, vtype=GRB.INTEGER, lb=0)
    y = model.addVars(N, vtype=GRB.INTEGER, lb=0)
    z = model.addVars(N, vtype=GRB.INTEGER, lb=0)
    for j, mt in enumerate(all_minterms):
        cov = [i for i, p in enumerate(ps) if mt in p.vertices()]
        model.addConstr(V[j] == gp.quicksum(x[i] for i in cov))
    for j, mt in enumerate(all_minterms):
        if mt in onset_set: model.addConstr(V[j] == 2*y[j]+1)
        else: model.addConstr(V[j] == 2*z[j])
    model.setObjective(gp.quicksum(costs[i]*x[i] for i in range(m)), GRB.MINIMIZE)
    model.optimize()
    if model.SolCount == 0: return circuit
    for i in range(m):
        if x[i].X > 0.5: circuit.add_block(synth_block(ps[i], n))
    return circuit

T_rp2, C_rp2 = 0, 0; ct2mct = 0; ct3mct = 0
t0 = time.time()
for tt in range(1, 256):
    bf = BooleanFunction(3, tt)
    if not bf.onset: continue
    circ = sshr_i_rp_t(bf, timeout=30)
    raw, T_s, C_s, _ = gate_stats_rp(circ, rp_toffoli=True)
    T_rp2 += T_s; C_rp2 += C_s
    ct2mct += raw.get('2-MCT', 0); ct3mct += raw.get('3-MCT', 0)
dt = time.time() - t0
print(f"ILP with T=4 objective, count T=4: T={T_rp2} CNOT={C_rp2} ({dt:.0f}s)")
print(f"2MCT={ct2mct}, 3MCT={ct3mct}")
print(f"Paper: T=2832, CNOT=3579")
