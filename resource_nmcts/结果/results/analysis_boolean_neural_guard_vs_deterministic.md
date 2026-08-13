# Paired Method Comparison

Target: `Boolean-linear neural guard` from `results/raw_boolean_neural_highdim.csv` method `and_fprm_boolean_linear_pair_deep_ai_guard`.
Baseline: `Boolean-linear deterministic` from `results/raw_boolean_neural_highdim.csv` method `and_fprm_boolean_linear_pair_deep`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 24 | 4 | 0 | 20 | 3673.667 | 3676.000 | -0.13% |
| CNOT | 24 | 3 | 1 | 20 | 6359.500 | 6360.292 | -0.06% |
| depth | 24 | 3 | 1 | 20 | 6359.625 | 6360.417 | -0.06% |
| peak_ancilla | 24 | 0 | 1 | 23 | 3.458 | 3.417 | +1.39% |
| score | 24 | 4 | 0 | 20 | 4054.872 | 4057.164 | -0.12% |
| time_s | 24 | 0 | 24 | 0 | 63.527 | 30.148 | +94.49% |
