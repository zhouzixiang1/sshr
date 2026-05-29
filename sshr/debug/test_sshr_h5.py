"""Test: S from onset ∪ current A (union-growing)."""
import sys
sys.path.insert(0, '.')
from bool_func import BooleanFunction, QuantumCircuit, mct_cost
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block


def sshr_h_union(bf, R=3/4):
    """S enumerated from onset ∪ current A (growing union)."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    universe = set(bf.onset)  # grows as A grows
    S = enumerate_parallelotopes(sorted(universe), n)

    while A:
        # Update S if universe grew
        new_universe = universe | A
        if new_universe != universe:
            universe = new_universe
            S = enumerate_parallelotopes(sorted(universe), n)

        selected = False
        for P in S:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0: continue
            if isz / len(verts) >= R:
                circuit.add_block(synth_block(P, n))
                A ^= verts
                universe |= A  # update universe with new A elements
                S = enumerate_parallelotopes(sorted(universe), n)
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
evaluate(lambda bf: __import__('sshr_h').sshr_h(bf), 3, "Current dynamic (onset only)")
evaluate(sshr_h_union, 3, "Union-growing S")
print("  Paper Table IV: X=1100, CNOT=560, 2MCT=220, 3MCT=128 | T=3588, C=3672, anc=128")
