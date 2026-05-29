"""Test combined: full-universe with tie-breaking by cost (prefer lower CNOT/T)."""
import sys
sys.path.insert(0, '.')
from bool_func import BooleanFunction, QuantumCircuit, mct_cost
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block, block_cnot_cost


def sshr_h_v3(bf, R=3/4):
    """Full-universe, singleton fallback, sort by dim desc then by CNOT cost asc."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    all_ps = enumerate_parallelotopes(list(range(1 << n)), n)
    # sort: higher dim first, then lower cnot_cost
    S = sorted(all_ps, key=lambda p: (-p.dim, block_cnot_cost(p, n)))

    while A:
        selected = False
        for P in S:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0: continue
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


def sshr_h_v4(bf, R=3/4):
    """Full-universe, singleton fallback, prefer higher intersection count (most A-coverage)."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    all_ps = enumerate_parallelotopes(list(range(1 << n)), n)

    while A:
        selected = False
        # Among all P with ratio >= R, pick the one with most vertices in A (greedy max coverage)
        best_P = None
        best_key = (-1, 0)  # (dim, isz)
        for P in all_ps:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0: continue
            if isz / len(verts) >= R:
                key = (P.dim, isz)
                if key > best_key:
                    best_key = key
                    best_P = P
        if best_P is not None:
            circuit.add_block(synth_block(best_P, n))
            A ^= best_P.vertices()
        else:
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
evaluate(lambda bf: __import__('sshr_h').sshr_h(bf), 3, "Current dynamic")
evaluate(sshr_h_v3, 3, "Universe + sort by cnot_cost")
evaluate(sshr_h_v4, 3, "Universe + max coverage greedy")
print("  Paper Table IV: X=1100, CNOT=560, 2MCT=220, 3MCT=128 | T=3588, C=3672, anc=128")
