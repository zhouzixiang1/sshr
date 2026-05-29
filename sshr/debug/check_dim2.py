"""Check specific n=3 functions that should be single dim-2 (0 2-MCT)."""
import sys
sys.path.insert(0, '.')
from bool_func import BooleanFunction
from sshr_h import sshr_h

# 12 dim-2 parallelotopes in n=3
test = [0x0F, 0xF0, 0x33, 0xCC, 0x55, 0xAA, 0x4B, 0xB4, 0xC3, 0x3C, 0xA5, 0x5A]
# Corresponding onsets:
# 0x0F={0,1,2,3}, 0xF0={4,5,6,7}, 0x33={0,1,4,5}, 0xCC={2,3,6,7}
# 0x55={0,2,4,6}, 0xAA={1,3,5,7}, 0x4B={0,1,3,6}?,
# Let me compute correctly:
# 0xC3 = 11000011 = bits 0,1,6,7 = {0,1,6,7}
# 0x3C = 00111100 = bits 2,3,4,5 = {2,3,4,5}
# 0xA5 = 10100101 = bits 0,2,5,7 = {0,2,5,7}
# 0x5A = 01011010 = bits 1,3,4,6 = {1,3,4,6}

for tt in test:
    bf = BooleanFunction(3, tt)
    circ = sshr_h(bf)
    m2 = sum(1 for g in circ.gates if g.type=='MCT' and len(g.controls)==2)
    m3 = sum(1 for g in circ.gates if g.type=='MCT' and len(g.controls)==3)
    X = sum(1 for g in circ.gates if g.type=='X')
    CN = sum(1 for g in circ.gates if g.type=='CNOT')
    print(f'  0x{tt:02X} onset={sorted(bf.onset)} X={X} CNOT={CN} 2MCT={m2} 3MCT={m3}')

# Check correctness
print("\nVerifying correctness for all n=3:")
fails = 0
for tt in range(256):
    bf = BooleanFunction(3, tt)
    circ = sshr_h(bf)
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        if circ.simulate(bits)[n] != bf.evaluate(x):
            fails += 1
            print(f"  FAIL: tt=0x{tt:02X} x={x}")
            break
print(f"  Correctness failures: {fails}")
