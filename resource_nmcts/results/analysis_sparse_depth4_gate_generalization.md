# Sparse Depth-4 Gate Generalization Audit

The trained sparse depth-4 gate is evaluated without retraining on independent generated term sets.
The deterministic sparse depth-2/4 frontier remains the quality reference.

- model: `models/sparse_depth4_gate.pt`
- checkpoint train n: 16,20,24; checkpoint test n: 28,40
- audit seeds: 20260801,20260802,20260803
- audit n: 24,28,32,40; per n per seed: 12
- threshold: 0.005312
- total audit pairs: 144
- total false skips: 0
- seed false skips: min 0, max 0

| scope | pairs | run depth-4 | false skips | score W/L/T vs sparse | mean score vs sparse | mean time vs sparse | score W/L/T vs depth-2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| all | 144 | 106 | 0 | 0/0/144 | +0.00% | -13.43% | 94/0/50 |
| seed=20260801 | 48 | 33 | 0 | 0/0/48 | +0.00% | -15.73% | 30/0/18 |
| seed=20260802 | 48 | 37 | 0 | 0/0/48 | +0.00% | -11.60% | 31/0/17 |
| seed=20260803 | 48 | 36 | 0 | 0/0/48 | +0.00% | -12.95% | 33/0/15 |
| n=24 | 36 | 29 | 0 | 0/0/36 | +0.00% | -9.88% | 27/0/9 |
| n=28 | 36 | 27 | 0 | 0/0/36 | +0.00% | -12.98% | 24/0/12 |
| n=32 | 36 | 23 | 0 | 0/0/36 | +0.00% | -18.19% | 21/0/15 |
| n=40 | 36 | 27 | 0 | 0/0/36 | +0.00% | -12.66% | 22/0/14 |

Interpretation:

- This audit tests deployment stability of the learned budget gate, not a new quality frontier.
- A zero false-skip row means the gate did not skip any depth-4 case that would have improved over depth 2 under the current score.
- Mean time is measured relative to evaluating both depth 2 and depth 4 in the deterministic sparse frontier.
