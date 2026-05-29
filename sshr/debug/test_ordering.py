"""Test different parallelotope ordering strategies for SSHR-H to match paper."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, QuantumCircuit, mct_cost
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block, block_cnot_cost, block_t_cost


def gate_stats(circ):
    raw = {}; T, C, anc = 0, 0, 0
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            raw[f"{k}-MCT"] = raw.get(f"{k}-MCT", 0) + 1
            c = mct_cost(k)
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return raw, T, C, anc


def sshr_h_variant(bf, R=3/4, sort_key="dim_desc", include_universe=False):
    """Variant of SSHR-H with configurable parallelotope ordering."""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    def get_sorted_s(a_set):
        if include_universe:
            ps = enumerate_parallelotopes(list(range(1 << n)), n)
        else:
            ps = enumerate_parallelotopes(list(a_set), n)

        if sort_key == "dim_desc":
            return ps  # already dim DESC
        elif sort_key == "dim_asc":
            return list(reversed(ps))
        elif sort_key == "cnot_asc":
            return sorted(ps, key=lambda p: block_cnot_cost(p, n))
        elif sort_key == "cnot_desc":
            return sorted(ps, key=lambda p: -block_cnot_cost(p, n))
        elif sort_key == "t_asc":
            return sorted(ps, key=lambda p: block_t_cost(p, n))
        elif sort_key == "coverage_desc":
            # Sort by |A∩P| descending, then dim desc
            return sorted(ps, key=lambda p: (-len(p.vertices() & a_set), -len(p.basis)))
        elif sort_key == "ratio_times_size":
            # Sort by |A∩P| * coverage_ratio (a quality measure)
            def key(p):
                v = p.vertices()
                isz = len(v & a_set)
                if len(v) == 0: return 0
                return -(isz / len(v)) * isz
            return sorted(ps, key=key)
        elif sort_key == "dim_cnot_asc":
            # dim DESC, then CNOT ASC within same dim
            return sorted(ps, key=lambda p: (-len(p.basis), block_cnot_cost(p, n)))
        elif sort_key == "dim_cnot_desc":
            # dim ASC, then CNOT DESC within same dim
            return sorted(ps, key=lambda p: (len(p.basis), -block_cnot_cost(p, n)))
        else:
            return ps

    S = get_sorted_s(A)
    max_iter = 10 * len(A) + len(S) + 100
    iteration = 0

    while A and iteration < max_iter:
        iteration += 1
        made_progress = False
        for P in S:
            verts = P.vertices()
            isz = len(verts & A)
            if isz == 0:
                continue
            if isz / len(verts) >= R:
                circuit.add_block(synth_block(P, n))
                A ^= verts
                S = get_sorted_s(A)
                made_progress = True
                break
        if not made_progress:
            if not S:
                break
            best_P, best_ratio = None, -1.0
            for P in S:
                verts = P.vertices()
                isz = len(verts & A)
                if isz == 0: continue
                ratio = isz / len(verts)
                if ratio > best_ratio:
                    best_ratio = ratio; best_P = P
            if best_P is not None:
                circuit.add_block(synth_block(best_P, n))
                A ^= best_P.vertices()
                S = get_sorted_s(A)
            else:
                for minterm in list(A):
                    circuit.add_block(synth_block(Parallelotope(minterm, []), n))
                A = set()
                break

    for minterm in list(A):
        circuit.add_block(synth_block(Parallelotope(minterm, []), n))
    return circuit


# Paper reference for n=3 (all 256 functions)
# X=1100, CNOT=560, 2MCT=220, 3MCT=128 | T=3588, C=3672, Anc=128
paper_n3 = (1100, 560, 220, 128, 3588, 3672, 128)

strategies = [
    ("dim_desc",         False),
    ("dim_asc",          False),
    ("cnot_asc",         False),
    ("cnot_desc",        False),
    ("t_asc",            False),
    ("coverage_desc",    False),
    ("ratio_times_size", False),
    ("dim_cnot_asc",     False),
    ("dim_cnot_desc",    False),
    ("dim_desc",         True),   # full universe
    ("cnot_asc",         True),   # full universe + cnot_asc
    ("coverage_desc",    True),   # full universe + coverage_desc
]

bfs = [BooleanFunction(3, tt) for tt in range(256)]
print(f"{'Strategy':30s}  {'univ':4}  {'X':>6}  {'CNOT':>6}  {'2MCT':>5}  {'3MCT':>5}  |  {'T':>6}  {'C':>6}  {'Anc':>4}")
print("-"*90)
print(f"{'Paper':30s}  {'  no':4}  {1100:>6}  {560:>6}  {220:>5}  {128:>5}  |  {3588:>6}  {3672:>6}  {128:>4}  <<< TARGET")
print("-"*90)

for sort_key, univ in strategies:
    label = f"{sort_key}{'_universe' if univ else ''}"
    tot = {}; T, C, anc = 0, 0, 0
    for bf in bfs:
        circ = sshr_h_variant(bf, sort_key=sort_key, include_universe=univ)
        raw, t, c, a = gate_stats(circ)
        T += t; C += c; anc += a
        for k, v in raw.items():
            tot[k] = tot.get(k, 0) + v
    x = tot.get('X',0); cn = tot.get('CNOT',0)
    m2 = tot.get('2-MCT',0); m3 = tot.get('3-MCT',0)
    match = "  *** " if (x==1100 and cn==560 and m2==220 and m3==128) else ""
    u = "yes" if univ else " no"
    print(f"{sort_key:30s}  {u:4}  {x:>6}  {cn:>6}  {m2:>5}  {m3:>5}  |  {T:>6}  {C:>6}  {anc:>4}  {match}")
