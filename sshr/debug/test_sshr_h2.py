"""Test SSHR-H with full universe + clean singleton fallback."""
import sys
sys.path.insert(0, '.')
from bool_func import BooleanFunction, QuantumCircuit, mct_cost
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block


def sshr_h_universe_clean(bf, R=3/4):
    """SSHR-H: full-universe S, singleton fallback (no best-ratio)."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    # Full universe parallelotopes, sorted dim-descending, FIXED
    S = enumerate_parallelotopes(list(range(1 << n)), n)

    while A:
        selected = False
        for P in S:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0:
                continue
            if isz / len(verts) >= R:
                circuit.add_block(synth_block(P, n))
                A ^= verts
                selected = True
                break
        if not selected:
            # No P qualifies → handle all remaining as singletons
            for m in list(A):
                circuit.add_block(synth_block(Parallelotope(m, []), n))
            A = set()
    return circuit


def sshr_h_dynamic_singleton(bf, R=3/4):
    """SSHR-H: dynamic S from current A, singleton fallback (no best-ratio)."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    while A:
        S = enumerate_parallelotopes(list(A), n)
        selected = False
        for P in S:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0:
                continue
            if isz / len(verts) >= R:
                circuit.add_block(synth_block(P, n))
                A ^= verts
                selected = True
                break
        if not selected:
            for m in list(A):
                circuit.add_block(synth_block(Parallelotope(m, []), n))
            A = set()
    return circuit


def evaluate(synth_fn, n, label):
    total = {}
    T, C, anc = 0, 0, 0
    for tt in range(1 << (1 << n)):
        bf = BooleanFunction(n, tt)
        circ = synth_fn(bf)
        for g in circ.gates:
            total[g.type] = total.get(g.type, 0) + 1
            if g.type == "MCT":
                k = len(g.controls)
                total[f"{k}-MCT"] = total.get(f"{k}-MCT", 0) + 1
                c = mct_cost(k)
                T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
            elif g.type == "CNOT":
                C += 1
    print(f"  {label}: X={total.get('X',0)}, CNOT={total.get('CNOT',0)}, "
          f"2MCT={total.get('2-MCT',0)}, 3MCT={total.get('3-MCT',0)} | T={T}, C={C}, anc={anc}")


print("=== n=3 SSHR-H variants ===")
evaluate(lambda bf: __import__('sshr_h').sshr_h(bf), 3, "Current (dynamic+best-ratio)")
evaluate(sshr_h_dynamic_singleton, 3, "Dynamic-S + singleton fallback")
evaluate(sshr_h_universe_clean, 3, "Full-universe-S + singleton fallback")
print("  Paper Table IV: X=1100, CNOT=560, 2MCT=220, 3MCT=128 | T=3588, C=3672, anc=128")

# Also verify correctness of best variant
print("\n=== Correctness check ===")
fails = 0
for tt in range(256):
    bf = BooleanFunction(3, tt)
    circ = sshr_h_universe_clean(bf)
    n = 3
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        if circ.simulate(bits)[n] != bf.evaluate(x):
            fails += 1
            break
print(f"  Correctness failures (universe+singleton): {fails}")
