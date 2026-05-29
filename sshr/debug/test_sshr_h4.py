"""Test ceiling-threshold: need ceil(R * |P|) vertices in A."""
import sys, math
sys.path.insert(0, '.')
from bool_func import BooleanFunction, QuantumCircuit, mct_cost
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block


def sshr_h_ceil(bf, R=3/4):
    """Full-universe S, ceiling threshold: need >= ceil(R * |P|) in A."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    S = enumerate_parallelotopes(list(range(1 << n)), n)

    while A:
        selected = False
        for P in S:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0: continue
            if isz >= math.ceil(R * len(verts)):  # ceiling threshold
                circuit.add_block(synth_block(P, n))
                A ^= verts
                selected = True
                break
        if not selected:
            for m in list(A):
                circuit.add_block(synth_block(Parallelotope(m, []), n))
            A = set()
    return circuit


def sshr_h_majority(bf, R=3/4):
    """Full-universe, select P if |A ∩ P| > |P| / 2 (strict majority) AND P is maximal."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    S = enumerate_parallelotopes(list(range(1 << n)), n)

    while A:
        selected = False
        for P in S:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0: continue
            if isz / len(verts) >= R and isz == len(verts):  # ONLY full coverage
                circuit.add_block(synth_block(P, n))
                A ^= verts
                selected = True
                break
        if not selected:
            # Allow partial for dim-1 only
            for P in S:
                if P.dim != 1: continue
                verts = P.vertices()
                isz = len(verts & A)
                if isz == len(verts):
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
evaluate(lambda bf: __import__('sshr_h').sshr_h(bf), 3, "Current dynamic")
evaluate(sshr_h_ceil, 3, "Universe + ceil threshold")
evaluate(sshr_h_majority, 3, "Universe + full-only then partial dim-1")
print("  Paper Table IV: X=1100, CNOT=560, 2MCT=220, 3MCT=128 | T=3588, C=3672, anc=128")
