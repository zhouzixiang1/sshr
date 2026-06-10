"""
研究不同 tie-breaking 策略对 n=3,4 结果的影响
目标：逼近论文 n=3: T=3588, CNOT=3672, 2-MCT=220, 3-MCT=128
          n=4: T=7391, CNOT=6540, 2-MCT=249, 3-MCT=218, 4-MCT=90
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bool_func import BooleanFunction, mct_cost, QuantumCircuit
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block, block_cnot_cost, block_t_cost


# ── 代价计算 ─────────────────────────────────────────────────────────────────

def gc(circ):
    raw = {}; T = CNOT = anc = 0
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            raw[f"{k}-MCT"] = raw.get(f"{k}-MCT", 0) + 1
            c = mct_cost(k); T += c["T"]; CNOT += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            CNOT += 1
    return raw, {"T": T, "CNOT": CNOT, "anc": anc}


# ── 通用 SSHR-H，支持可插拔的候选排序函数 ──────────────────────────────────

def sshr_h_custom(bf, R=0.75, sort_key=None, n_lookahead=0):
    """
    sort_key: fn(P, A, n) -> float，越小越优先
    n_lookahead: 0=无预见，1=模拟1步后的代价，2=2步
    """
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

        # 满足阈值的候选
        candidates = [P for P in S
                      if len(P.vertices() & A) / len(P.vertices()) >= R]

        if not candidates:
            # 放宽阈值，取最大 ratio
            best_ratio = max((len(P.vertices() & A) / len(P.vertices()) for P in S), default=0)
            candidates = [P for P in S
                          if abs(len(P.vertices() & A) / len(P.vertices()) - best_ratio) < 1e-9]

        if not candidates:
            break

        # 排序选最优
        if sort_key is not None:
            candidates.sort(key=lambda P: sort_key(P, A, n))

        chosen = candidates[0]
        circuit.add_block(synth_block(chosen, n))
        A ^= chosen.vertices()

    # 残余孤立点
    for m in list(A):
        p0 = Parallelotope(m, [])
        circuit.add_block(synth_block(p0, n))

    return circuit


# ── 各种 sort_key 策略 ───────────────────────────────────────────────────────

def key_original(P, A, n):
    """原始策略：按维度降序（不额外排序，candidates 已是降维顺序）"""
    return (0,)   # 保持原顺序

def key_min_t(P, A, n):
    """优先最小 T 代价"""
    return block_t_cost(P, n)

def key_min_cnot(P, A, n):
    """优先最小 CNOT 代价"""
    return block_cnot_cost(P, n)

def key_max_dim(P, A, n):
    """优先最高维（等维再按 T）"""
    return (-P.dim, block_t_cost(P, n))

def key_max_coverage(P, A, n):
    """优先覆盖最多 A 中的点（绝对数量）"""
    return -len(P.vertices() & A)

def key_max_ratio(P, A, n):
    """优先最高比例（ratio 相同再按 T）"""
    ratio = len(P.vertices() & A) / len(P.vertices())
    return (-ratio, block_t_cost(P, n))

def key_min_t_per_coverage(P, A, n):
    """优先 T/覆盖量 最小（代价效益比）"""
    covered = len(P.vertices() & A)
    t = block_t_cost(P, n)
    return t / covered if covered > 0 else float('inf')

def key_min_cnot_per_coverage(P, A, n):
    """优先 CNOT/覆盖量 最小"""
    covered = len(P.vertices() & A)
    c = block_cnot_cost(P, n)
    return c / covered if covered > 0 else float('inf')

def key_dim_then_t(P, A, n):
    """先最高维，同维再最小 T"""
    return (-P.dim, block_t_cost(P, n))

def key_dim_then_cnot(P, A, n):
    """先最高维，同维再最小 CNOT"""
    return (-P.dim, block_cnot_cost(P, n))

def key_coverage_then_t(P, A, n):
    """先最多覆盖，再最小 T"""
    return (-len(P.vertices() & A), block_t_cost(P, n))

def key_coverage_then_cnot(P, A, n):
    """先最多覆盖，再最小 CNOT"""
    return (-len(P.vertices() & A), block_cnot_cost(P, n))

def key_ratio_then_t(P, A, n):
    """先最高比例，再最小 T"""
    return (-len(P.vertices() & A) / len(P.vertices()), block_t_cost(P, n))

def key_onset_density(P, A, n):
    """高 onset 密度（intersection/total_size 之比 * 覆盖量）再按 T"""
    verts = P.vertices()
    covered = len(verts & A)
    ratio = covered / len(verts)
    return (-ratio * covered, block_t_cost(P, n))


# ── 批量评估 ─────────────────────────────────────────────────────────────────

def evaluate(fns, sort_key, R=0.75, n=3):
    tT = tC = t2 = t3 = t4 = t1 = 0
    for bf in fns:
        circ = sshr_h_custom(bf, R=R, sort_key=sort_key)
        raw, dc = gc(circ)
        tT += dc["T"]; tC += dc["CNOT"]
        t1 += raw.get("1-MCT", 0)
        t2 += raw.get("2-MCT", 0)
        t3 += raw.get("3-MCT", 0)
        t4 += raw.get("4-MCT", 0)
    return {"T": tT, "CNOT": tC, "1mct": t1, "2mct": t2, "3mct": t3, "4mct": t4}


# ── 主程序 ────────────────────────────────────────────────────────────────────

STRATEGIES = [
    ("original（当前）",        None),
    ("min_T",                   key_min_t),
    ("min_CNOT",                key_min_cnot),
    ("max_dim→min_T",           key_dim_then_t),
    ("max_dim→min_CNOT",        key_dim_then_cnot),
    ("max_coverage→min_T",      key_coverage_then_t),
    ("max_coverage→min_CNOT",   key_coverage_then_cnot),
    ("max_ratio→min_T",         key_ratio_then_t),
    ("min_T/coverage",          key_min_t_per_coverage),
    ("min_CNOT/coverage",       key_min_cnot_per_coverage),
    ("onset_density→T",         key_onset_density),
]

PAPER = {
    3: {"T": 3588, "CNOT": 3672, "2mct": 220, "3mct": 128},
    4: {"T": 7391, "CNOT": 6540, "2mct": 249, "3mct": 218, "4mct": 90},
}

for n in [3, 4]:
    if n == 3:
        fns = [BooleanFunction(n, tt) for tt in range(1, 1 << (1 << n))]
    else:
        from npn_reps_n4 import NPN_REPS_N4
        fns = [BooleanFunction(n, tt) for tt in NPN_REPS_N4 if tt != 0]

    paper = PAPER[n]
    mct_key = "4mct" if n == 4 else "3mct"
    mct_paper = paper.get(mct_key, "?")

    print(f"\n{'='*80}")
    print(f"n={n}  ({len(fns)} 函数)   论文目标: T={paper['T']}  CNOT={paper['CNOT']}  "
          f"2-MCT={paper['2mct']}  {mct_key.upper()}={mct_paper}")
    print(f"{'策略':<28} {'T':>7} {'ΔT%':>7} {'CNOT':>7} {'ΔCNOT%':>8} "
          f"{'1-MCT':>6} {'2-MCT':>6} {'3-MCT':>6} {'4-MCT':>6}")
    print("-" * 80)

    for name, sk in STRATEGIES:
        t0 = time.time()
        res = evaluate(fns, sk, n=n)
        dt = time.time() - t0
        dT  = (res["T"]    - paper["T"])    / paper["T"]    * 100
        dC  = (res["CNOT"] - paper["CNOT"]) / paper["CNOT"] * 100
        mark = " ←best" if abs(dT) < 1 else ""
        print(f"{name:<28} {res['T']:>7} {dT:>+6.1f}% {res['CNOT']:>7} {dC:>+7.1f}% "
              f"{res['1mct']:>6} {res['2mct']:>6} {res['3mct']:>6} {res['4mct']:>6}{mark}")

    print(f"\n{'论文参考':<28} {paper['T']:>7} {'0.0%':>7} {paper['CNOT']:>7} {'0.0%':>8} "
          f"{'?':>6} {paper['2mct']:>6} {paper.get('3mct','?'):>6} {paper.get('4mct','?'):>6}")
