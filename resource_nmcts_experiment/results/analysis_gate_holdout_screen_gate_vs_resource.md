# Paired Method Comparison

Target: `gate holdout screen-gated Resource` from `results/raw_gate_holdout_resource.csv` method `and_resource_nmcts_screen_gate`.
Baseline: `gate holdout full Resource` from `results/raw_gate_holdout_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 16 | 0 | 0 | 16 | 27408.250 | 27408.250 | +0.00% |
| CNOT | 16 | 0 | 0 | 16 | 42780.500 | 42780.500 | +0.00% |
| depth | 16 | 0 | 0 | 16 | 42780.625 | 42780.625 | +0.00% |
| peak_ancilla | 16 | 0 | 0 | 16 | 3.625 | 3.625 | +0.00% |
| score | 16 | 0 | 0 | 16 | 29921.996 | 29921.996 | +0.00% |
| time_s | 16 | 11 | 5 | 0 | 164.457 | 194.780 | -36.83% |
