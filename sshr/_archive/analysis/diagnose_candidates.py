"""
诊断：为什么所有 tie-breaking 都没有效果？
核心假设：候选集生成方式（enumerate_parallelotopes(list(A), n)）
         限制了所有顶点必须在 A 内，导致大量本可利用的 parallelotope 被排除。
论文可能：从全超立方体枚举，ratio ≥ 3/4 即可，允许 off-set 顶点进入 A（XOR 语义）。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bool_func import BooleanFunction, mct_cost, QuantumCircuit
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block, block_cnot_cost, block_t_cost


def gc(circ):
    raw = {}; T = CNOT = 0
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            raw[f"{k}-MCT"] = raw.get(f"{k}-MCT", 0) + 1
            c = mct_cost(k); T += c["T"]; CNOT += c["CNOT"]
        elif g.type == "CNOT":
            CNOT += 1
    return raw, {"T": T, "CNOT": CNOT}


# ── 关键诊断：onset={0,1,2,3,5,6,7} ──────────────────────────────────────────
print("=" * 65)
print("诊断：onset={0,1,2,3,5,6,7}（off-set={4}）的候选集差异")
print("=" * 65)

n = 3
A = {0, 1, 2, 3, 5, 6, 7}
all_pts = list(range(1 << n))

print("\n[当前实现] enumerate_parallelotopes(list(A), n)——顶点全在 A 内：")
S_in_A = enumerate_parallelotopes(list(A), n)
for p in S_in_A:
    verts = p.vertices()
    inter = len(verts & A)
    ratio = inter / len(verts)
    print(f"  dim={p.dim} {sorted(verts)} ratio={ratio:.2f} T={block_t_cost(p,n)} CNOT={block_cnot_cost(p,n)}"
          f"  {'✓ R≥3/4' if ratio >= 0.75 else ''}")

print(f"\n[全超立方体] enumerate_parallelotopes(all_pts, n)——ratio≥3/4 的额外候选：")
S_full = enumerate_parallelotopes(all_pts, n)
seen = {p.vertices() for p in S_in_A}
extras = []
for p in S_full:
    verts = p.vertices()
    inter = len(verts & A)
    ratio = inter / len(verts)
    if ratio >= 0.75 and verts not in seen:
        extras.append(p)
        off_verts = verts - A
        print(f"  dim={p.dim} {sorted(verts)} ratio={ratio:.2f} T={block_t_cost(p,n)} "
              f"off-set顶点={sorted(off_verts)}")

if not extras:
    print("  （无额外候选）")


# ── 实现全超立方体版 SSHR-H ──────────────────────────────────────────────────
print("\n" + "=" * 65)
print("实现对比：当前 vs 全超立方体候选集（SSHR-H-full）")
print("=" * 65)

# 预计算全超立方体的所有 parallelotopes（每个 n 只算一次）
_FULL_CACHE = {}
def get_full_parallelotopes(n):
    if n not in _FULL_CACHE:
        _FULL_CACHE[n] = enumerate_parallelotopes(list(range(1 << n)), n)
    return _FULL_CACHE[n]


def sshr_h_full(bf, R=0.75, sort_key=None):
    """从全超立方体枚举候选，ratio 阈值过滤，XOR 更新"""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit

    S_all = get_full_parallelotopes(n)
    max_iter = 20 * len(A) + 200

    for _ in range(max_iter):
        if not A:
            break

        candidates = [P for P in S_all
                      if len(P.vertices() & A) / len(P.vertices()) >= R]

        if not candidates:
            best_ratio = max((len(P.vertices() & A) / len(P.vertices()) for P in S_all), default=0)
            candidates = [P for P in S_all
                          if abs(len(P.vertices() & A) / len(P.vertices()) - best_ratio) < 1e-9]
        if not candidates:
            break

        if sort_key:
            candidates.sort(key=lambda P: sort_key(P, A, n))

        chosen = candidates[0]
        circuit.add_block(synth_block(chosen, n))
        A ^= chosen.vertices()

    for m in list(A):
        p0 = Parallelotope(m, [])
        circuit.add_block(synth_block(p0, n))
    return circuit


def sshr_h_original(bf, R=0.75):
    """当前实现（从当前 A 枚举）"""
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    A = set(bf.onset)
    if not A:
        return circuit
    max_iter = 10 * len(A) + 100
    for _ in range(max_iter):
        if not A:
            break
        S = enumerate_parallelotopes(list(A), n)
        chosen = None
        for P in S:
            if len(P.vertices() & A) / len(P.vertices()) >= R:
                chosen = P; break
        if not chosen and S:
            chosen = max(S, key=lambda P: len(P.vertices() & A) / len(P.vertices()))
        if not chosen:
            break
        circuit.add_block(synth_block(chosen, n))
        A ^= chosen.vertices()
    for m in list(A):
        p0 = Parallelotope(m, [])
        circuit.add_block(synth_block(p0, n))
    return circuit


# sort_key 变体
def key_min_t(P, A, n): return block_t_cost(P, n)
def key_dim_t(P, A, n): return (-P.dim, block_t_cost(P, n))
def key_coverage_t(P, A, n): return (-len(P.vertices() & A), block_t_cost(P, n))
def key_ratio_t(P, A, n): return (-len(P.vertices() & A)/len(P.vertices()), block_t_cost(P, n))


PAPER = {3: {"T": 3588, "CNOT": 3672, "2mct": 220, "3mct": 128},
         4: {"T": 7391, "CNOT": 6540, "2mct": 249, "3mct": 218, "4mct": 90}}

import time
from npn_reps_n4 import NPN_REPS_N4

for n in [3, 4]:
    if n == 3:
        fns = [BooleanFunction(n, tt) for tt in range(1, 256)]
    else:
        fns = [BooleanFunction(n, tt) for tt in NPN_REPS_N4 if tt != 0]

    paper = PAPER[n]
    print(f"\nn={n}  ({len(fns)} 函数)  论文: T={paper['T']}  CNOT={paper['CNOT']}")
    print(f"{'方法':<35} {'T':>7} {'ΔT%':>7} {'CNOT':>7} {'ΔCNOT%':>8} {'2-MCT':>6} {'3-MCT':>6} {'4-MCT':>6}")
    print("-" * 80)

    # 当前实现
    tT = tC = t2 = t3 = t4 = 0
    for bf in fns:
        raw, dc = gc(sshr_h_original(bf))
        tT += dc["T"]; tC += dc["CNOT"]
        t2 += raw.get("2-MCT",0); t3 += raw.get("3-MCT",0); t4 += raw.get("4-MCT",0)
    dT = (tT-paper["T"])/paper["T"]*100; dC = (tC-paper["CNOT"])/paper["CNOT"]*100
    print(f"{'当前（A内枚举）':<35} {tT:>7} {dT:>+6.1f}% {tC:>7} {dC:>+7.1f}% {t2:>6} {t3:>6} {t4:>6}")

    # 全超立方体变体
    variants = [
        ("全超+默认排序",        None),
        ("全超+min_T",          key_min_t),
        ("全超+dim→T",          key_dim_t),
        ("全超+coverage→T",     key_coverage_t),
        ("全超+ratio→T",        key_ratio_t),
    ]
    for vname, sk in variants:
        t0 = time.time()
        tT = tC = t2 = t3 = t4 = 0
        for bf in fns:
            raw, dc = gc(sshr_h_full(bf, sort_key=sk))
            tT += dc["T"]; tC += dc["CNOT"]
            t2 += raw.get("2-MCT",0); t3 += raw.get("3-MCT",0); t4 += raw.get("4-MCT",0)
        dT = (tT-paper["T"])/paper["T"]*100; dC = (tC-paper["CNOT"])/paper["CNOT"]*100
        dt = time.time()-t0
        print(f"{vname:<35} {tT:>7} {dT:>+6.1f}% {tC:>7} {dC:>+7.1f}% {t2:>6} {t3:>6} {t4:>6}  [{dt:.1f}s]")

    print(f"{'论文':<35} {paper['T']:>7} {'0.0%':>7} {paper['CNOT']:>7} {'0.0%':>8} "
          f"{paper['2mct']:>6} {paper.get('3mct','?'):>6} {paper.get('4mct','?'):>6}")
