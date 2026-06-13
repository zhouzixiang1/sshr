"""Test iterative pruning at n=5: compare SSHR-H, full ILP, standard pruned ILP, and iterative pruned ILP."""
import sys
import time

sys.path.insert(0, "/Users/zhouzixiang/Desktop/tzb/claude/sshr")
sys.path.insert(0, "/Users/zhouzixiang/Desktop/tzb/claude/ai_sshr_experiment")

from bool_func import BooleanFunction, mct_cost
from feature_extractor import ensure_sshr_on_path

ensure_sshr_on_path()

from ai_pruned_ilp import ai_pruned_ilp, iterative_pruned_ilp
from sshr_h import sshr_h
from sshr_i import sshr_i
import random

rng = random.Random(42)
N = 1 << 5
fns = []
while len(fns) < 15:
    k = rng.randint(1, N // 2)
    tt = sum(1 << i for i in rng.sample(range(N), k))
    bf = BooleanFunction(5, tt)
    if bf.onset:
        fns.append(bf)


def cnot_count(circ):
    total = 0
    for g in circ.gates:
        if g.type == "MCT":
            total += mct_cost(len(g.controls))["CNOT"]
        elif g.type == "CNOT":
            total += 1
    return total


# Baselines
print("Computing baselines...")
h_cnots = []
for bf in fns:
    circ = sshr_h(bf)
    h_cnots.append(cnot_count(circ))
print(f"SSHR-H: avg CNOT={sum(h_cnots)/len(h_cnots):.1f}")

# Full ILP on subset
print("\nFull ILP (5 fns, 60s each)...")
ilp_cnots = []
for bf in fns[:5]:
    circ = sshr_i(bf, objective="cnot", timeout=60)
    ilp_cnots.append(cnot_count(circ))
print(f"Full ILP (5 fns): avg CNOT={sum(ilp_cnots)/len(ilp_cnots):.1f}")

# Standard AI-Pruned ILP
print("\nStandard AI-Pruned ILP (ratio=0.8)...")
t0 = time.time()
pruned_cnots = []
for bf in fns:
    circ = ai_pruned_ilp(bf, "cnot", timeout=60, keep_ratio=0.8, keep_min=200)
    pruned_cnots.append(cnot_count(circ))
print(
    f"Standard pruned: avg CNOT={sum(pruned_cnots)/len(pruned_cnots):.1f}, time={time.time()-t0:.1f}s"
)

# Iterative pruning
for rounds, ratio in [(2, 0.3), (3, 0.3), (2, 0.5)]:
    print(f"\nIterative (rounds={rounds}, init_ratio={ratio})...")
    t0 = time.time()
    iter_cnots = []
    for bf in fns:
        circ = iterative_pruned_ilp(
            bf,
            "cnot",
            timeout=60,
            initial_keep_ratio=ratio,
            max_rounds=rounds,
        )
        iter_cnots.append(cnot_count(circ))
    print(
        f"Iterative: avg CNOT={sum(iter_cnots)/len(iter_cnots):.1f}, time={time.time()-t0:.1f}s"
    )
