"""Test different SSHR-H variants to match paper Table IV n=3."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bool_func import BooleanFunction, QuantumCircuit, mct_cost
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block


def sshr_h_fixed_s(bf, R=3/4):
    """SSHR-H with FIXED S from original onset."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    # Fixed S from ORIGINAL onset
    S = enumerate_parallelotopes(list(A), n)
    max_iter = 10 * len(A) + len(S) + 100

    for _ in range(max_iter):
        if not A:
            break
        made = False
        for P in S:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0:
                continue
            if isz / len(verts) >= R:
                circuit.add_block(synth_block(P, n))
                A ^= verts
                made = True
                break
        if not made:
            # fallback: best ratio
            best_P, best_ratio = None, -1.0
            for P in S:
                verts = P.vertices()
                isz = len(verts & A)
                if isz == 0: continue
                r = isz / len(verts)
                if r > best_ratio:
                    best_ratio = r; best_P = P
            if best_P:
                circuit.add_block(synth_block(best_P, n))
                A ^= best_P.vertices()
            else:
                break

    for m in list(A):
        circuit.add_block(synth_block(Parallelotope(m, []), n))
    return circuit


def sshr_h_full_universe(bf, R=3/4):
    """SSHR-H with S from FULL UNIVERSE (like SSHR-I)."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    # Full universe S — fixed
    S = enumerate_parallelotopes(list(range(1 << n)), n)
    max_iter = 10 * (1 << n) + len(S) + 100

    for _ in range(max_iter):
        if not A:
            break
        made = False
        for P in S:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0:
                continue
            if isz / len(verts) >= R:
                circuit.add_block(synth_block(P, n))
                A ^= verts
                made = True
                break
        if not made:
            best_P, best_ratio = None, -1.0
            for P in S:
                verts = P.vertices()
                isz = len(verts & A)
                if isz == 0: continue
                r = isz / len(verts)
                if r > best_ratio:
                    best_ratio = r; best_P = P
            if best_P:
                circuit.add_block(synth_block(best_P, n))
                A ^= best_P.vertices()
            else:
                break

    for m in list(A):
        circuit.add_block(synth_block(Parallelotope(m, []), n))
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
evaluate(lambda bf: __import__('sshr_h').sshr_h(bf), 3, "Dynamic-S (current)")
evaluate(sshr_h_fixed_s, 3, "Fixed-S (onset)")
evaluate(sshr_h_full_universe, 3, "Full-universe-S")
print("  Paper Table IV: X=1100, CNOT=560, 2MCT=220, 3MCT=128 | T=3588, C=3672, anc=128")
