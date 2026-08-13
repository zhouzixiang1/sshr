# Ultra-Scale n=48/56/64 Resource Profile

This derived audit expands the ultra-scale stress slice from score/time comparisons into raw logical resource means.
It reuses the verified term-set rows and does not rerun synthesis.

## Verification

- raw rows: 480
- functions: 48
- n values: 48, 56, 64
- plan ANF verified rows: 480/480
- emitted-circuit ANF verified rows: 480/480
- max plan mismatches: 0
- max circuit mismatches: 0

## Overall Method Means

| method | rows | score | T | CNOT | depth | peak ancilla | T-depth proxy | ancilla lifetime | time s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct AND | 48 | 1378.11 | 1250.42 | 2002.35 | 2002.38 | 5.0208 | 595.75 | 0.00 | 0.00 |
| Depth-2 screen | 48 | 1202.81 | 1088.83 | 1755.62 | 1755.65 | 5.3750 | 517.81 | 23.19 | 2.80 |
| Depth-4 screen | 48 | 1168.91 | 1057.58 | 1709.42 | 1709.44 | 5.3958 | 503.12 | 29.69 | 27.53 |
| All-depth frontier | 48 | 1168.91 | 1057.58 | 1709.42 | 1709.44 | 5.3958 | 503.12 | 29.69 | 41.27 |
| Learned frontier | 48 | 1182.60 | 1070.25 | 1727.73 | 1727.75 | 5.3750 | 509.08 | 26.54 | 17.11 |

## Overall Pairwise Deltas

| target | baseline | pairs | score W/L/T | score | T | CNOT | depth | T-depth | ancilla lifetime | time |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Depth-4 screen | Depth-2 screen | 48 | 24/0/24 | -1.81% | -1.85% | -1.68% | -1.68% | -1.81% | +20.87% | +488.77% |
| Learned frontier | Depth-2 screen | 48 | 10/0/38 | -0.84% | -0.85% | -0.79% | -0.79% | -0.83% | +10.37% | +244.67% |
| Learned frontier | All-depth frontier | 48 | 0/14/34 | +1.02% | +1.04% | +0.92% | +0.92% | +1.03% | -7.58% | -61.61% |

## Interpretation

- Depth-4 and all-depth screens lower T-count, CNOT, logical depth, and T-depth proxy relative to the cheap depth-2 screen, but they substantially increase planning time and auxiliary lifetime.
- The learned frontier sits between cheap depth-2 and the all-depth ceiling: it improves resource means over depth-2, saves time against all-depth, and accepts a small resource gap to the full frontier.
- This makes the ultra-scale result a resource-frontier and budget-control claim, not a single-metric or hardware-mapped dominance claim.
