# Sparse Depth-4 Gate

The gate predicts whether depth-4 Boolean-ring screening should run after depth-2 has been evaluated.
It is compared with the deterministic sparse depth-2/4 frontier and with a depth-2-only baseline.

- train examples: 96
- validation examples: 48
- held-out test examples: 48
- train n: 16,20,24; test n: 28,40
- validation loss: 0.0463; validation accuracy at 0.5: 0.938
- selected threshold: 0.005312
- max validation false skips: 0
- max validation mean score gap: 0.0500%
- validation threshold safety factor: 0.1

| split | pairs | run depth-4 | false skips | score W/L/T vs sparse | mean score vs sparse | mean time vs sparse | score W/L/T vs depth-2 | mean score vs depth-2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 96 | 78 | 0 | 0/0/96 | +0.00% | -10.17% | 75/0/21 | -4.08% |
| valid | 48 | 38 | 0 | 0/0/48 | +0.00% | -12.01% | 34/0/14 | -3.27% |
| test | 48 | 32 | 0 | 0/0/48 | +0.00% | -17.39% | 23/0/25 | -1.77% |

Interpretation:

- The gate is a learned budget controller for the sparse depth frontier, not a hardware scheduler.
- False skips are the key risk because they skip a depth-4 run that would have improved score.
- The deterministic sparse depth-2/4 frontier remains the quality reference; the learned gate trades some quality for additional planning-time reduction if false skips occur.
