# Neural Prior Ablation

Rows: 24; usable: 24; errors: 0; skipped: 0.

The learned-prior rows come from a matched `highdim_neural_prior` rerun
with `resource_nmcts_experiment/models/linear_action_scorer_root_pairwise.pt`.  The no-prior rows
rerun the same functions and methods with an absent model path, so the
search keeps the heuristic PUCT/action prior but removes the learned
action scorer.

## Mean Resources

| variant | method | functions | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| learned_prior | and_resource_nmcts | 12 | 3324.67 | 5737.83 | 5739.67 | 3.58 | 3669.55 | 71.290 |
| no_prior | and_resource_nmcts | 12 | 3326.67 | 5736.50 | 5738.33 | 3.50 | 3671.30 | 23.261 |

## Paired Learned-Prior Comparison

| method | metric | pairs | learned wins | learned losses | ties | mean learned | mean no prior | mean relative |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| and_resource_nmcts | T | 12 | 2 | 0 | 10 | 3324.67 | 3326.67 | -0.05% |
| and_resource_nmcts | CNOT | 12 | 0 | 1 | 11 | 5737.83 | 5736.50 | +0.01% |
| and_resource_nmcts | depth | 12 | 0 | 1 | 11 | 5739.67 | 5738.33 | +0.01% |
| and_resource_nmcts | peak_ancilla | 12 | 0 | 1 | 11 | 3.58 | 3.50 | +1.82% |
| and_resource_nmcts | score | 12 | 2 | 0 | 10 | 3669.55 | 3671.30 | -0.05% |
| and_resource_nmcts | time_s | 12 | 0 | 12 | 0 | 71.290 | 23.261 | +179.59% |
