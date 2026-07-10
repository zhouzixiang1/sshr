# Paired Method Comparison

Target: `deeper-screen Resource-NMCTS` from `/tmp/resource_nmcts_screen_deeper_resource_n20/raw_giga_highdim_resource.csv` method `and_resource_nmcts`.
Baseline: `depth-1 recursive-screen Resource-NMCTS` from `resource_nmcts_experiment/results/raw_giga_recursive_screen_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 5 | 0 | 1 | 19535.333 | 20138.000 | -3.22% |
| CNOT | 6 | 5 | 0 | 1 | 30542.500 | 31480.500 | -2.67% |
| depth | 6 | 5 | 0 | 1 | 30542.500 | 31480.500 | -2.67% |
| peak_ancilla | 6 | 0 | 1 | 5 | 3.000 | 2.833 | +5.56% |
| score | 6 | 5 | 0 | 1 | 21331.242 | 21988.519 | -3.13% |
| time_s | 6 | 0 | 6 | 0 | 79.554 | 60.512 | +29.31% |
