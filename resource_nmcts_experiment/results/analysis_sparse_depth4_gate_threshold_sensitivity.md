# Sparse Depth-4 Gate Threshold Sensitivity

This analysis sweeps the deployment threshold of the trained sparse depth-4 gate on the 144-pair independent-seed audit.
It does not retrain the model or rerun synthesis.

- selected threshold: 0.005312
- selected false skips: 0
- selected time vs sparse: -13.43%
- best zero-false-skip time vs sparse in sweep: -14.92%

| operating point | threshold | run depth-4 | false skips | score W/L/T vs sparse | mean score vs sparse | mean time vs sparse |
|---|---:|---:|---:|---:|---:|---:|
| eager sparse | 0.000000 | 144 | 0 | 0/0/144 | +0.00% | +0.00% |
| selected | 0.005312 | 106 | 0 | 0/0/144 | +0.00% | -13.43% |
| max zero-skip saving | 0.030675 | 102 | 0 | 0/0/144 | +0.00% | -14.92% |
| max one-skip saving | 0.039703 | 101 | 1 | 0/1/143 | +0.01% | -15.49% |
| depth-2 only | 1.000000 | 0 | 94 | 0/94/50 | +2.84% | -77.99% |
