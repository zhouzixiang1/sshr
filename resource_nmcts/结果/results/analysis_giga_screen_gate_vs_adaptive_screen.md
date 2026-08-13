# Paired Method Comparison

Target: `screen-gated Resource-NMCTS n20` from `results/raw_giga_screen_gate_resource.csv` method `and_resource_nmcts_screen_gate`.
Baseline: `adaptive screen n20` from `results/raw_giga_adaptive_screen_resource.csv` method `and_boolean_linear_pair_screen_adaptive`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 0 | 0 | 6 | 19535.333 | 19535.333 | +0.00% |
| CNOT | 6 | 0 | 0 | 6 | 30542.500 | 30542.500 | +0.00% |
| depth | 6 | 0 | 0 | 6 | 30542.500 | 30542.500 | +0.00% |
| peak_ancilla | 6 | 0 | 0 | 6 | 3.000 | 3.000 | +0.00% |
| score | 6 | 0 | 0 | 6 | 21331.242 | 21331.242 | +0.00% |
| time_s | 6 | 3 | 3 | 0 | 20.712 | 20.668 | -0.04% |
