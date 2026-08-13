# Neural Prior Ablation

Rows: 1062; usable: 1062; errors: 0; skipped: 0.

The learned-prior rows come from a matched `traditional_resource` rerun
with `models/action_scorer_rollout_logical_and.pt`.  The no-prior rows
rerun the same functions and methods with an absent model path, so the
search keeps the heuristic PUCT/action prior but removes the learned
action scorer.

## Mean Resources

| variant | method | functions | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| learned_prior | and_affine_nmcts | 177 | 45.88 | 94.36 | 98.92 | 1.88 | 55.37 | 0.286 |
| learned_prior | and_pareto_resource_nmcts | 177 | 40.43 | 83.04 | 88.00 | 2.03 | 49.56 | 3.983 |
| learned_prior | and_resource_nmcts | 177 | 43.91 | 89.85 | 94.51 | 1.92 | 53.22 | 0.410 |
| no_prior | and_affine_nmcts | 177 | 46.42 | 95.48 | 100.13 | 1.89 | 55.99 | 0.145 |
| no_prior | and_pareto_resource_nmcts | 177 | 40.66 | 83.29 | 88.49 | 2.06 | 49.86 | 3.562 |
| no_prior | and_resource_nmcts | 177 | 44.32 | 90.46 | 95.32 | 1.94 | 53.70 | 0.342 |

## Paired Learned-Prior Comparison

| method | metric | pairs | learned wins | learned losses | ties | mean learned | mean no prior | mean relative |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| and_affine_nmcts | T | 177 | 22 | 0 | 155 | 45.88 | 46.42 | -1.65% |
| and_affine_nmcts | CNOT | 177 | 33 | 2 | 142 | 94.36 | 95.48 | -1.61% |
| and_affine_nmcts | depth | 177 | 33 | 5 | 139 | 98.92 | 100.13 | -1.64% |
| and_affine_nmcts | peak_ancilla | 177 | 1 | 0 | 176 | 1.88 | 1.89 | -0.20% |
| and_affine_nmcts | score | 177 | 42 | 0 | 135 | 55.37 | 55.99 | -1.47% |
| and_affine_nmcts | time_s | 177 | 3 | 174 | 0 | 0.286 | 0.145 | +91.22% |
| and_resource_nmcts | T | 177 | 17 | 0 | 160 | 43.91 | 44.32 | -1.19% |
| and_resource_nmcts | CNOT | 177 | 27 | 5 | 145 | 89.85 | 90.46 | -0.95% |
| and_resource_nmcts | depth | 177 | 31 | 4 | 142 | 94.51 | 95.32 | -1.21% |
| and_resource_nmcts | peak_ancilla | 177 | 3 | 0 | 174 | 1.92 | 1.94 | -0.59% |
| and_resource_nmcts | score | 177 | 39 | 0 | 138 | 53.22 | 53.70 | -1.10% |
| and_resource_nmcts | time_s | 177 | 54 | 123 | 0 | 0.410 | 0.342 | +55.11% |
| and_pareto_resource_nmcts | T | 177 | 9 | 0 | 168 | 40.43 | 40.66 | -0.78% |
| and_pareto_resource_nmcts | CNOT | 177 | 19 | 3 | 155 | 83.04 | 83.29 | -0.47% |
| and_pareto_resource_nmcts | depth | 177 | 21 | 5 | 151 | 88.00 | 88.49 | -0.81% |
| and_pareto_resource_nmcts | peak_ancilla | 177 | 5 | 0 | 172 | 2.03 | 2.06 | -0.98% |
| and_pareto_resource_nmcts | score | 177 | 29 | 0 | 148 | 49.56 | 49.86 | -0.78% |
| and_pareto_resource_nmcts | time_s | 177 | 37 | 140 | 0 | 3.983 | 3.562 | +18.77% |
