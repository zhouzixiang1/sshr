# Paired Method Comparison

Target: `gate holdout adaptive screen` from `results/raw_gate_holdout_resource.csv` method `and_boolean_linear_pair_screen_adaptive`.
Baseline: `gate holdout full Resource` from `results/raw_gate_holdout_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 16 | 0 | 4 | 12 | 27459.750 | 27408.250 | +7.54% |
| CNOT | 16 | 0 | 4 | 12 | 42825.375 | 42780.500 | +3.40% |
| depth | 16 | 0 | 4 | 12 | 42825.500 | 42780.625 | +3.40% |
| peak_ancilla | 16 | 0 | 0 | 16 | 3.625 | 3.625 | +0.00% |
| score | 16 | 0 | 4 | 12 | 29976.055 | 29921.996 | +7.07% |
| time_s | 16 | 16 | 0 | 0 | 22.514 | 194.780 | -84.27% |
