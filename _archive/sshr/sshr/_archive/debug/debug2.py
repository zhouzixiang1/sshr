"""Investigate SSHR-H behavior for n=4 functions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction
from sshr_h import sshr_h
from parallelotope_enum import enumerate_parallelotopes

# How many gates does SSHR-H use for a simple n=4 function?
# f = x3 (onset = {8,9,10,11,12,13,14,15}) — 8 minterms forming a 3D cube
onset = list(range(8, 16))
bf = BooleanFunction(4, sum(1<<x for x in onset))
circ = sshr_h(bf)
print(f"Simple 3D cube {[bin(x) for x in onset]}:")
print(f"  Gates: X={sum(1 for g in circ.gates if g.type=='X')}, CNOT={sum(1 for g in circ.gates if g.type=='CNOT')}, MCT={sum(1 for g in circ.gates if g.type=='MCT')}")
print(f"  Cost: {circ.cost()}")

# Check what parallelotopes are found for this onset
ps = enumerate_parallelotopes(onset, 4)
print(f"\n  Parallelotopes found: {len(ps)}")
for p in sorted(ps, key=lambda x: -x.dim)[:5]:
    print(f"    dim={p.dim}  verts={sorted(p.vertices())}")

# Check function where SSHR-H might degenerate
# f with onset = all 16 minterms
bf_all = BooleanFunction(4, 0xFFFF)
circ_all = sshr_h(bf_all)
print(f"\nAll-ones function:")
print(f"  Gates: {sum(1 for g in circ_all.gates if g.type=='X')} X, {sum(1 for g in circ_all.gates if g.type=='CNOT')} CNOT, {sum(1 for g in circ_all.gates if g.type=='MCT')} MCT")

# Sample 10 random 4-bit functions and show gate counts
import random
rng = random.Random(42)
print("\n10 random 4-bit functions:")
print(f"{'tt':>8}  {'onset':>6}  {'X':>5}  {'CNOT':>5}  {'MCT':>5}")
for tt in rng.sample(range(1, 65535), 10):
    bf = BooleanFunction(4, tt)
    circ = sshr_h(bf)
    X = sum(1 for g in circ.gates if g.type == 'X')
    C = sum(1 for g in circ.gates if g.type == 'CNOT')
    M = sum(1 for g in circ.gates if g.type == 'MCT')
    print(f"0x{tt:04X}  {len(bf.onset):>6}  {X:>5}  {C:>5}  {M:>5}")
