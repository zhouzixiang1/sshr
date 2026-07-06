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
| learned_prior | and_pareto_resource_nmcts | 177 | 40.77 | 83.93 | 88.70 | 1.97 | 49.83 | 2.995 |
| learned_prior | and_resource_nmcts | 177 | 45.74 | 93.49 | 98.49 | 1.89 | 55.21 | 0.314 |
| no_prior | and_affine_nmcts | 177 | 46.42 | 95.48 | 100.13 | 1.89 | 55.99 | 0.145 |
| no_prior | and_pareto_resource_nmcts | 177 | 40.99 | 84.23 | 89.21 | 2.00 | 50.14 | 1.879 |
| no_prior | and_resource_nmcts | 177 | 46.24 | 94.35 | 99.48 | 1.90 | 55.79 | 0.168 |

## Paired Learned-Prior Comparison

| method | metric | pairs | learned wins | learned losses | ties | mean learned | mean no prior | mean relative |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| and_affine_nmcts | T | 177 | 22 | 0 | 155 | 45.88 | 46.42 | -1.65% |
| and_affine_nmcts | CNOT | 177 | 33 | 2 | 142 | 94.36 | 95.48 | -1.61% |
| and_affine_nmcts | depth | 177 | 33 | 5 | 139 | 98.92 | 100.13 | -1.64% |
| and_affine_nmcts | peak_ancilla | 177 | 1 | 0 | 176 | 1.88 | 1.89 | -0.20% |
| and_affine_nmcts | score | 177 | 42 | 0 | 135 | 55.37 | 55.99 | -1.47% |
| and_affine_nmcts | time_s | 177 | 3 | 174 | 0 | 0.286 | 0.145 | +91.22% |
| and_resource_nmcts | T | 177 | 21 | 0 | 156 | 45.74 | 46.24 | -1.49% |
| and_resource_nmcts | CNOT | 177 | 31 | 3 | 143 | 93.49 | 94.35 | -1.28% |
| and_resource_nmcts | depth | 177 | 32 | 5 | 140 | 98.49 | 99.48 | -1.39% |
| and_resource_nmcts | peak_ancilla | 177 | 2 | 0 | 175 | 1.89 | 1.90 | -0.39% |
| and_resource_nmcts | score | 177 | 41 | 0 | 136 | 55.21 | 55.79 | -1.34% |
| and_resource_nmcts | time_s | 177 | 1 | 176 | 0 | 0.314 | 0.168 | +87.31% |
| and_pareto_resource_nmcts | T | 177 | 9 | 0 | 168 | 40.77 | 40.99 | -0.78% |
| and_pareto_resource_nmcts | CNOT | 177 | 19 | 3 | 155 | 83.93 | 84.23 | -0.53% |
| and_pareto_resource_nmcts | depth | 177 | 21 | 5 | 151 | 88.70 | 89.21 | -0.83% |
| and_pareto_resource_nmcts | peak_ancilla | 177 | 5 | 0 | 172 | 1.97 | 2.00 | -0.98% |
| and_pareto_resource_nmcts | score | 177 | 29 | 0 | 148 | 49.83 | 50.14 | -0.78% |
| and_pareto_resource_nmcts | time_s | 177 | 1 | 176 | 0 | 2.995 | 1.879 | +67.44% |
