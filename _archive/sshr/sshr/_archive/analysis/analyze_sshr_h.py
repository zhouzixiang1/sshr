"""深度解析 SSHR-H 启发式复现结果"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h
from parallelotope_enum import enumerate_parallelotopes
from block_synth import block_cnot_cost, block_t_cost

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

n = 3
print("=" * 65)
print("1. n=3 全集：按 on-set 大小分组统计（我们 vs 论文）")
print("=" * 65)
by = {}
for tt in range(1, 256):
    bf = BooleanFunction(n, tt)
    circ = sshr_h(bf)
    raw, dc = gc(circ)
    k = len(bf.onset)
    if k not in by:
        by[k] = {"T": 0, "CNOT": 0, "cnt": 0, "m1": 0, "m2": 0, "m3": 0, "gates": 0}
    by[k]["T"] += dc["T"]; by[k]["CNOT"] += dc["CNOT"]
    by[k]["cnt"] += 1; by[k]["gates"] += len(circ.gates)
    by[k]["m1"] += raw.get("1-MCT", 0)
    by[k]["m2"] += raw.get("2-MCT", 0)
    by[k]["m3"] += raw.get("3-MCT", 0)

print(f"{'|A|':>4} {'#fn':>4} {'总T':>6} {'均T':>5} {'总CNOT_eq':>10} {'均C':>5} {'1-MCT':>6} {'2-MCT':>6} {'3-MCT':>6} {'均门数':>6}")
tT = tC = t2 = t3 = 0
for k in sorted(by):
    d = by[k]; c = d["cnt"]
    tT += d["T"]; tC += d["CNOT"]; t2 += d["m2"]; t3 += d["m3"]
    print(f"{k:>4} {c:>4} {d['T']:>6} {d['T']/c:>5.1f} {d['CNOT']:>10} {d['CNOT']/c:>5.1f} "
          f"{d['m1']:>6} {d['m2']:>6} {d['m3']:>6} {d['gates']/c:>6.2f}")
print(f"{'合计':>4} {'255':>4} {tT:>6} {'':>5} {tC:>10} {'':>5} {'':>6} {t2:>6} {t3:>6}")
print(f"{'论文':>4} {'255':>4} {'3588':>6} {'':>5} {'3672':>10} {'':>5} {'':>6} {'220':>6} {'128':>6}")
print(f"{'差值':>4} {'':>4} {tT-3588:>+6} {'':>5} {tC-3672:>+10} {'':>5} {'':>6} {t2-220:>+6} {t3-128:>+6}")

# ── 2. 追踪具体函数的决策过程 ──
print("\n" + "=" * 65)
print("2. 追踪两个典型函数的决策过程（R=3/4 阈值）")
print("=" * 65)

for tt, label in [(0x96, "XOR-like 0x96"), (0x6B, "0x6B")]:
    bf = BooleanFunction(n, tt)
    onset = sorted(bf.onset)
    print(f"\n  f=0x{tt:02X}  onset={onset}  (|A|={len(onset)})")
    A = set(bf.onset)
    step = 0
    while A:
        S = enumerate_parallelotopes(list(A), n)
        chosen = None
        for P in S:
            verts = P.vertices()
            inter = len(verts & A)
            ratio = inter / len(verts)
            if ratio >= 0.75:
                chosen = P; break
        if not chosen and S:
            chosen = max(S, key=lambda P: len(P.vertices() & A) / len(P.vertices()))
        if chosen:
            step += 1
            verts = chosen.vertices()
            inter = len(verts & A)
            ratio = inter / len(verts)
            ct = block_cnot_cost(chosen, n)
            tt2 = block_t_cost(chosen, n)
            print(f"    步{step}: dim={chosen.dim} verts={sorted(verts)} ∩A={inter}/{len(verts)}"
                  f"={ratio:.2f}  CNOT_eq={ct}  T={tt2}")
            A ^= verts
        else:
            for m in list(A):
                print(f"    步{step+1}: 孤立点 {m} → 3-MCT  T=16")
            break
    circ = sshr_h(bf)
    raw2, dc2 = gc(circ)
    print(f"    总计: T={dc2['T']}  CNOT_eq={dc2['CNOT']}  gates={raw2}")

# ── 3. 2-MCT 来源分析（哪些 onset 结构导致使用 Toffoli）──
print("\n" + "=" * 65)
print("3. 2-MCT 使用来源分析（Toffoli = dim-1 parallelotope）")
print("=" * 65)
only2 = []; both = []; only3 = []
for tt in range(1, 256):
    bf = BooleanFunction(n, tt)
    circ = sshr_h(bf)
    raw2, _ = gc(circ)
    m2 = raw2.get("2-MCT", 0); m3 = raw2.get("3-MCT", 0)
    if m2 > 0 and m3 == 0:
        only2.append((tt, m2, sorted(bf.onset)))
    elif m2 > 0 and m3 > 0:
        both.append((tt, m2, m3, sorted(bf.onset)))
    elif m3 > 0:
        only3.append((tt, m3, sorted(bf.onset)))

print(f"只用 2-MCT（无 3-MCT）：{len(only2)} 个函数")
print(f"同时用 2-MCT 和 3-MCT：{len(both)} 个函数")
print(f"只用 3-MCT（无 2-MCT）：{len(only3)} 个函数")

from collections import Counter
cnt2 = Counter(m2 for _, m2, _ in only2)
print(f"\n  '只用2-MCT'函数中，2-MCT 个数分布:")
for c in sorted(cnt2):
    print(f"    {c} 个 2-MCT: {cnt2[c]} 个函数  (T贡献={c*7}×{cnt2[c]}={c*7*cnt2[c]})")
print(f"\n  示例（只用2-MCT的函数，onset={only2[:3]}...）")

# ── 4. n=4 的 tie-breaking 效应分析 ──
print("\n" + "=" * 65)
print("4. n=4 NPN reps：维度使用分布对比")
print("=" * 65)
try:
    from npn_reps_n4 import NPN_REPS_N4
    n4 = 4
    fns4 = [BooleanFunction(n4, tt) for tt in NPN_REPS_N4 if tt != 0]
    dim_hist = {}
    tT4 = tC4 = 0
    for bf in fns4:
        circ = sshr_h(bf)
        raw2, dc2 = gc(circ)
        tT4 += dc2["T"]; tC4 += dc2["CNOT"]
        for k in range(1, n4+1):
            key = f"{k+1}-MCT"  # dim=k → (n-k)-MCT → controls=n-k... actually MCT controls = n-k
            # Actually: k-dim parallelotope → (n-k) controls MCT
            pass
        for g in circ.gates:
            if g.type == "MCT":
                nc = len(g.controls)
                dim = n4 - nc  # approximate (inner bits may add complexity)
                dim_hist[nc] = dim_hist.get(nc, 0) + 1

    print(f"n=4 (221 NPN reps) 总计: T={tT4}  CNOT_eq={tC4}")
    print(f"论文:                      T=7391   CNOT_eq=6540")
    print(f"差值:                      T={tT4-7391:+d} ({(tT4-7391)/7391*100:+.1f}%)  CNOT={tC4-6540:+d} ({(tC4-6540)/6540*100:+.1f}%)")
    print(f"\nMCT 控制位数分布（我们）:")
    for nc in sorted(dim_hist):
        print(f"  {nc}-control MCT ({4-nc}D parallelotope): {dim_hist[nc]} 次")
    print(f"\n论文参考: 2-MCT=249, 3-MCT=218, 4-MCT=90")
except Exception as e:
    print(f"跳过（{e}）")

# ── 5. n=5,6 为何我们反而更好 ──
print("\n" + "=" * 65)
print("5. 高维（n=5,6）我们更优的核心原因")
print("=" * 65)
import random
rng = random.Random(42)
n5 = 5; N5 = 1 << n5
sample5 = []
for _ in range(50):
    k = rng.randint(1, N5 // 2)
    mints = set(rng.sample(range(N5), k))
    sample5.append(BooleanFunction(n5, sum(1 << i for i in mints)))

dim_usage5 = {}; tT5 = tC5 = 0
for bf in sample5:
    circ = sshr_h(bf)
    raw2, dc2 = gc(circ)
    tT5 += dc2["T"]; tC5 += dc2["CNOT"]
    for key in raw2:
        if key.endswith("-MCT"):
            dim_usage5[key] = dim_usage5.get(key, 0) + raw2[key]

print(f"n=5 (50样本) 总T={tT5}  总CNOT_eq={tC5}")
print(f"MCT 类型分布（平行多面体维度越高=控制位越少=代价越低）:")
for key in sorted(dim_usage5, key=lambda x: int(x.split("-")[0])):
    nc = int(key.split("-")[0])
    dim = n5 - nc
    print(f"  {key} (dim={dim} parallelotope): {dim_usage5[key]} 次")
