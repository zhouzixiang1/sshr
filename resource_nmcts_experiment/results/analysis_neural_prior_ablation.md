# Neural Prior Ablation

Rows: 1062; usable: 1062; errors: 0; skipped: 0.

The learned-prior rows reuse the main `traditional_resource` run with
`models/action_scorer_rollout_logical_and.pt`.  The no-prior rows rerun
the same functions and methods with an absent model path, so the search
keeps the heuristic PUCT/action prior but removes the learned action scorer.

## Mean Resources

| variant | method | functions | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| learned_prior | and_affine_nmcts | 177 | 45.88 | 94.36 | 98.92 | 1.88 | 55.37 | 1.447 |
| learned_prior | and_pareto_resource_nmcts | 177 | 41.45 | 85.34 | 90.22 | 2.01 | 50.66 | 1.879 |
| learned_prior | and_resource_nmcts | 177 | 45.74 | 93.49 | 98.49 | 1.89 | 55.21 | 1.602 |
| no_prior | and_affine_nmcts | 177 | 46.42 | 95.48 | 100.13 | 1.89 | 55.99 | 0.132 |
| no_prior | and_pareto_resource_nmcts | 177 | 41.67 | 85.79 | 90.86 | 2.04 | 50.99 | 1.574 |
| no_prior | and_resource_nmcts | 177 | 46.24 | 94.35 | 99.48 | 1.90 | 55.79 | 0.154 |

## Paired Learned-Prior Comparison

| method | metric | pairs | learned wins | learned losses | ties | mean learned | mean no prior | mean relative |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| and_affine_nmcts | T | 177 | 22 | 0 | 155 | 45.88 | 46.42 | -1.65% |
| and_affine_nmcts | CNOT | 177 | 33 | 2 | 142 | 94.36 | 95.48 | -1.61% |
| and_affine_nmcts | depth | 177 | 33 | 5 | 139 | 98.92 | 100.13 | -1.64% |
| and_affine_nmcts | peak_ancilla | 177 | 1 | 0 | 176 | 1.88 | 1.89 | -0.20% |
| and_affine_nmcts | score | 177 | 42 | 0 | 135 | 55.37 | 55.99 | -1.47% |
| and_affine_nmcts | time_s | 177 | 0 | 177 | 0 | 1.447 | 0.132 | +853.43% |
| and_resource_nmcts | T | 177 | 21 | 0 | 156 | 45.74 | 46.24 | -1.49% |
| and_resource_nmcts | CNOT | 177 | 31 | 3 | 143 | 93.49 | 94.35 | -1.28% |
| and_resource_nmcts | depth | 177 | 32 | 5 | 140 | 98.49 | 99.48 | -1.39% |
| and_resource_nmcts | peak_ancilla | 177 | 2 | 0 | 175 | 1.89 | 1.90 | -0.39% |
| and_resource_nmcts | score | 177 | 41 | 0 | 136 | 55.21 | 55.79 | -1.34% |
| and_resource_nmcts | time_s | 177 | 0 | 177 | 0 | 1.602 | 0.154 | +814.58% |
| and_pareto_resource_nmcts | T | 177 | 9 | 0 | 168 | 41.45 | 41.67 | -0.78% |
| and_pareto_resource_nmcts | CNOT | 177 | 23 | 4 | 150 | 85.34 | 85.79 | -0.70% |
| and_pareto_resource_nmcts | depth | 177 | 26 | 5 | 146 | 90.22 | 90.86 | -0.98% |
| and_pareto_resource_nmcts | peak_ancilla | 177 | 6 | 0 | 171 | 2.01 | 2.04 | -1.18% |
| and_pareto_resource_nmcts | score | 177 | 34 | 0 | 143 | 50.66 | 50.99 | -0.82% |
| and_pareto_resource_nmcts | time_s | 177 | 9 | 168 | 0 | 1.879 | 1.574 | +22.04% |
