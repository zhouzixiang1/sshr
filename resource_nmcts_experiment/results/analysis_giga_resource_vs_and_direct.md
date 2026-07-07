# Paired Method Comparison

Target: `Resource-NMCTS updated` from `results/raw_giga_boolean_neural_resource.csv` method `and_resource_nmcts`.
Baseline: `AND-direct ANF` from `results/raw_giga_boolean_neural_resource.csv` method `and_direct_anf`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 5 | 0 | 1 | 20138.000 | 21516.667 | -9.43% |
| CNOT | 6 | 5 | 0 | 1 | 31480.500 | 33635.667 | -8.61% |
| depth | 6 | 5 | 0 | 1 | 31480.500 | 33635.667 | -8.61% |
| peak_ancilla | 6 | 0 | 5 | 1 | 2.833 | 1.667 | +61.11% |
| score | 6 | 5 | 0 | 1 | 21988.519 | 23491.152 | -9.04% |
| time_s | 6 | 0 | 6 | 0 | 61.579 | 10.741 | +473.22% |
