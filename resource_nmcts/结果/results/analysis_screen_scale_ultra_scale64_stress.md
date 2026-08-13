# Ultra-Scale n=48/56/64 Stress Audit

This audit checks the newly generated term-set stress slice beyond the main n=20--40 envelope.
It remains a logical-layer symbolic test: no truth-table enumeration or hardware mapping is claimed.

## Verification

- raw rows: 480
- functions: 48
- n values: 48, 56, 64
- plan ANF verified rows: 480/480
- emitted-circuit ANF verified rows: 480/480
- max plan mismatches: 0
- max circuit mismatches: 0
- max circuit wire terms: 282

## Comparisons

| scope | target | baseline | role | pairs | score W/L/T | mean score | mean time | mean T |
|---|---|---|---|---:|---:|---:|---:|---:|
| n=48/56/64 | screen_depth4 | screen_depth2 | deterministic deep screen | 48 | 24/0/24 | -1.81% | +488.77% | -1.85% |
| n=48/56/64 | adaptive_all_depth | screen_depth2 | quality ceiling | 48 | 24/0/24 | -1.81% | +809.95% | -1.85% |
| n=48/56/64 | depth_frontier_policy | screen_depth2 | learned frontier vs cheap depth-2 | 48 | 10/0/38 | -0.84% | +244.67% | -0.85% |
| n=48/56/64 | depth_frontier_policy | screen_depth4 | learned frontier vs deepest screen | 48 | 0/14/34 | +1.02% | -35.99% | +1.04% |
| n=48/56/64 | depth_frontier_policy | adaptive_all_depth | learned frontier vs full measured frontier | 48 | 0/14/34 | +1.02% | -61.61% | +1.04% |
| n=48 | depth_frontier_policy | adaptive_all_depth | per-n learned boundary | 16 | 0/1/15 | +0.07% | -53.13% | +0.07% |
| n=48 | screen_depth4 | screen_depth2 | per-n deterministic depth gain | 16 | 6/0/10 | -1.07% | +494.86% | -1.09% |
| n=56 | depth_frontier_policy | adaptive_all_depth | per-n learned boundary | 16 | 0/6/10 | +1.14% | -60.06% | +1.17% |
| n=56 | screen_depth4 | screen_depth2 | per-n deterministic depth gain | 16 | 10/0/6 | -2.23% | +591.40% | -2.28% |
| n=64 | depth_frontier_policy | adaptive_all_depth | per-n learned boundary | 16 | 0/7/9 | +1.85% | -71.64% | +1.88% |
| n=64 | screen_depth4 | screen_depth2 | per-n deterministic depth gain | 16 | 8/0/8 | -2.13% | +380.03% | -2.17% |

## Interpretation

- Depth-4 and all-depth screens still reduce score relative to cheap depth-2 on many ultra-scale rows, but their planning cost is much higher.
- The learned depth-frontier policy is a bounded budget controller: it saves time against the full measured frontier, while accepting a small score gap on this harder n=48--64 slice.
- These rows extend the symbolic verification envelope; they do not replace complete truth-table bridge checks.
