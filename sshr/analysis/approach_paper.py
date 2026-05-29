"""
逼近论文结果：系统测试各种改进策略
核心诊断：全超立方体候选集爆炸的原因是 fallback 选了 ratio<3/4 的候选导致振荡。
修复方案：ratio<3/4 时直接退化到 singleton（dim-0），不从全超立方体选次优候选。
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bool_func import BooleanFunction, mct_cost, QuantumCircuit
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block, block_cnot_cost, block_t_cost
from npn_reps_n4 import NPN_REPS_N4

# ── 代价计算 ──────────────────────────────────────────────────────────────────

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

def totals(fns, synth_fn):
    tT = tC = t1 = t2 = t3 = t4 = 0
    for bf in fns:
        raw, dc = gc(synth_fn(bf))
        tT += dc["T"]; tC += dc["CNOT"]
        t1 += raw.get("1-MCT",0); t2 += raw.get("2-MCT",0)
        t3 += raw.get("3-MCT",0); t4 += raw.get("4-MCT",0)
    return {"T":tT,"CNOT":tC,"1mct":t1,"2mct":t2,"3mct":t3,"4mct":t4}

# ── 预计算全超立方体候选集 ─────────────────────────────────────────────────────
_FULL = {}
def full_S(n):
    if n not in _FULL:
        _FULL[n] = enumerate_parallelotopes(list(range(1 << n)), n)
    return _FULL[n]

# ── sort_key 定义 ──────────────────────────────────────────────────────────────
def sk_none(P, A, n):    return 0
def sk_dim(P, A, n):     return -P.dim
def sk_T(P, A, n):       return block_t_cost(P, n)
def sk_CNOT(P, A, n):    return block_cnot_cost(P, n)
def sk_cov(P, A, n):     return -len(P.vertices() & A)
def sk_dim_T(P, A, n):   return (-P.dim, block_t_cost(P, n))
def sk_dim_C(P, A, n):   return (-P.dim, block_cnot_cost(P, n))
def sk_cov_T(P, A, n):   return (-len(P.vertices() & A), block_t_cost(P, n))
def sk_cov_C(P, A, n):   return (-len(P.vertices() & A), block_cnot_cost(P, n))
def sk_ratio_T(P, A, n):
    return (-len(P.vertices() & A)/len(P.vertices()), block_t_cost(P, n))

# ── 策略 A：当前实现（从 A 枚举，选第一个满足 R 的）──────────────────────────
def sshr_original(bf):
    from sshr_h import sshr_h
    return sshr_h(bf)

# ── 策略 B：从 A 枚举 + 可插拔排序 ──────────────────────────────────────────
def make_sshr_a(sort_key, R=0.75):
    def _synth(bf):
        n = bf.n
        circuit = QuantumCircuit(n + 1)
        A = set(bf.onset)
        if not A: return circuit
        for _ in range(20 * len(A) + 200):
            if not A: break
            S = enumerate_parallelotopes(list(A), n)
            candidates = [P for P in S if len(P.vertices() & A)/len(P.vertices()) >= R]
            if not candidates: break
            candidates.sort(key=lambda P: sort_key(P, A, n))
            chosen = candidates[0]
            circuit.add_block(synth_block(chosen, n))
            A ^= chosen.vertices()
        for m in list(A):
            circuit.add_block(synth_block(Parallelotope(m, []), n))
        return circuit
    return _synth

# ── 策略 C：全超立方体 + 修正（ratio<R 时直接用 singleton）─────────────────
def make_sshr_full(sort_key, R=0.75):
    def _synth(bf):
        n = bf.n
        circuit = QuantumCircuit(n + 1)
        A = set(bf.onset)
        if not A: return circuit
        S = full_S(n)
        while A:
            # 全超立方体中 ratio >= R 的候选
            cands = [P for P in S if len(P.vertices() & A)/len(P.vertices()) >= R]
            if not cands:
                break   # 直接退出，用 singleton 处理剩余
            cands.sort(key=lambda P: sort_key(P, A, n))
            chosen = cands[0]
            circuit.add_block(synth_block(chosen, n))
            A ^= chosen.vertices()
        for m in list(A):
            circuit.add_block(synth_block(Parallelotope(m, []), n))
        return circuit
    return _synth

# ── 策略 D：互补（|onset|>2^(n-1) 时合成 NOT(f) + X）─────────────────────
def make_sshr_with_complement(base_synth):
    def _synth(bf):
        n = bf.n
        half = 1 << (n - 1)
        if len(bf.onset) > half:
            # 合成补函数
            comp_tt = ((1 << (1 << n)) - 1) ^ bf.truth_table
            bf_comp = BooleanFunction(n, comp_tt)
            circ = base_synth(bf_comp)
            # 在输出 qubit 加 X 门（相当于取非）
            circ_out = QuantumCircuit(n + 1)
            circ_out.add_x(n)
            for g in circ.gates:
                if g.type == "MCT": circ_out.add_mct(g.controls, g.target)
                elif g.type == "CNOT": circ_out.add_cnot(g.controls[0], g.target)
                elif g.type == "X": circ_out.add_x(g.target)
            circ_out.add_x(n)
            return circ_out
        return base_synth(bf)
    return _synth

# ── 策略 E：全超 + 互补 ─────────────────────────────────────────────────────
def make_sshr_full_complement(sort_key, R=0.75):
    base = make_sshr_full(sort_key, R)
    return make_sshr_with_complement(base)

# ── 策略 F：全超 + 不同 R 阈值 ──────────────────────────────────────────────
def make_sshr_full_R(R, sort_key=sk_dim_T):
    return make_sshr_full(sort_key, R)

# ── 主程序 ────────────────────────────────────────────────────────────────────
PAPER = {
    3: {"T": 3588, "CNOT": 3672, "2mct": 220, "3mct": 128},
    4: {"T": 7391, "CNOT": 6540, "2mct": 249, "3mct": 218, "4mct": 90},
}

for n in [3, 4]:
    fns = ([BooleanFunction(n, tt) for tt in range(1, 256)]
           if n == 3 else
           [BooleanFunction(n, tt) for tt in NPN_REPS_N4 if tt != 0])
    paper = PAPER[n]

    print(f"\n{'='*80}")
    print(f"n={n}  ({len(fns)} 函数)")
    print(f"论文目标: T={paper['T']}  CNOT={paper['CNOT']}  "
          f"2-MCT={paper['2mct']}  {'3' if n==3 else '4'}-MCT={paper.get('3mct' if n==3 else '4mct','?')}")
    print(f"{'策略':<38} {'T':>7} {'ΔT%':>7} {'CNOT':>7} {'ΔCNOT%':>8} "
          f"{'1-MCT':>6} {'2-MCT':>6} {'3-MCT':>6} {'4-MCT':>6} {'时间':>6}")
    print("-" * 90)

    def show(name, fn):
        t0 = time.time()
        r = totals(fns, fn)
        dt = time.time() - t0
        dT  = (r["T"]   -paper["T"])   /paper["T"]   *100
        dC  = (r["CNOT"]-paper["CNOT"])/paper["CNOT"]*100
        star = " ◀" if abs(dT) < 3 else ""
        print(f"{name:<38} {r['T']:>7} {dT:>+6.1f}% {r['CNOT']:>7} {dC:>+7.1f}% "
              f"{r['1mct']:>6} {r['2mct']:>6} {r['3mct']:>6} {r['4mct']:>6} {dt:>5.1f}s{star}")

    # A：当前
    show("A: 当前实现",            sshr_original)

    # B：A内枚举 + 排序变体
    show("B1: A内+dim→T",         make_sshr_a(sk_dim_T))
    show("B2: A内+dim→CNOT",      make_sshr_a(sk_dim_C))
    show("B3: A内+cov→T",         make_sshr_a(sk_cov_T))
    show("B4: A内+cov→CNOT",      make_sshr_a(sk_cov_C))
    show("B5: A内+ratio→T",       make_sshr_a(sk_ratio_T))
    show("B6: A内+min_T",         make_sshr_a(sk_T))
    show("B7: A内+min_CNOT",      make_sshr_a(sk_CNOT))

    # C：全超（修正版）+ 排序变体
    show("C1: 全超(fix)+默认",     make_sshr_full(sk_none))
    show("C2: 全超(fix)+dim→T",   make_sshr_full(sk_dim_T))
    show("C3: 全超(fix)+dim→CNOT",make_sshr_full(sk_dim_C))
    show("C4: 全超(fix)+cov→T",   make_sshr_full(sk_cov_T))
    show("C5: 全超(fix)+cov→CNOT",make_sshr_full(sk_cov_C))
    show("C6: 全超(fix)+min_T",   make_sshr_full(sk_T))
    show("C7: 全超(fix)+min_CNOT",make_sshr_full(sk_CNOT))

    # D：互补 + 当前实现
    show("D: 互补+当前",           make_sshr_with_complement(sshr_original))

    # E：全超 + 互补
    show("E1: 全超+互补+dim→T",   make_sshr_full_complement(sk_dim_T))
    show("E2: 全超+互补+cov→T",   make_sshr_full_complement(sk_cov_T))
    show("E3: 全超+互补+min_T",   make_sshr_full_complement(sk_T))

    # F：不同 R 阈值
    for R in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        show(f"F: 全超 R={R}",    make_sshr_full_R(R))

    print(f"\n{'论文参考':<38} {paper['T']:>7} {'0.0%':>7} {paper['CNOT']:>7} {'0.0%':>8} "
          f"{'?':>6} {paper['2mct']:>6} {paper.get('3mct','?'):>6} {paper.get('4mct','?'):>6}")
