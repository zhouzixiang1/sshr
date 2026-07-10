# Paired Method Comparison

Target: `recursive-screen Resource-NMCTS` from `/tmp/resource_nmcts_recursive_screen_n20_resource/raw_giga_highdim_resource.csv` method `and_resource_nmcts`.
Baseline: `direct ANF` from `resource_nmcts_experiment/results/raw_giga_highdim_resource.csv` method `direct_anf`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 5 | 0 | 1 | 20138.000 | 42944.000 | -39.84% |
| CNOT | 6 | 2 | 4 | 0 | 31480.500 | 19600.333 | +28.69% |
| depth | 6 | 2 | 4 | 0 | 31480.500 | 19600.333 | +28.69% |
| peak_ancilla | 6 | 0 | 5 | 1 | 2.833 | 1.000 | +125.00% |
| score | 6 | 5 | 1 | 0 | 21988.519 | 44037.625 | -37.10% |
| time_s | 6 | 0 | 6 | 0 | 60.512 | 10.524 | +474.86% |
