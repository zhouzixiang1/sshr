# Paired Method Comparison

Target: `deeper-screen Resource-NMCTS` from `/tmp/resource_nmcts_screen_deeper_resource_n20/raw_giga_highdim_resource.csv` method `and_resource_nmcts`.
Baseline: `direct ANF` from `resource_nmcts_experiment/results/raw_giga_highdim_resource.csv` method `direct_anf`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 5 | 0 | 1 | 19535.333 | 42944.000 | -41.57% |
| CNOT | 6 | 2 | 4 | 0 | 30542.500 | 19600.333 | +25.23% |
| depth | 6 | 2 | 4 | 0 | 30542.500 | 19600.333 | +25.23% |
| peak_ancilla | 6 | 0 | 5 | 1 | 3.000 | 1.000 | +141.67% |
| score | 6 | 5 | 1 | 0 | 21331.242 | 44037.625 | -38.86% |
| time_s | 6 | 0 | 6 | 0 | 79.554 | 10.524 | +655.56% |
