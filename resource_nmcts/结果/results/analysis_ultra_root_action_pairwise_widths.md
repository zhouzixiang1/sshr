# High-dimensional root-action oracle analysis

This diagnostic evaluates whether high-dimensional CNOT-only linear-pair
root actions contain useful ranking headroom beyond the cheap heuristic.
Each action is scored by building actual greedy child plans, so the
oracle rows are a bounded one-step teacher signal rather than a global
reversible-circuit optimum.

Model for optional neural ordering: `resource_nmcts_experiment/models/linear_action_scorer_root_pairwise.pt`.

Rows: 254; errors: 0; incorrect: 0.

## Mean resources

| method | functions | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|---:|
| root_beam4_oracle_eval | 23 | 5744.1739 | 9136.1304 | 9136.3478 | 3.3913 | 6286.8878 | 0.062961 |
| root_direct | 24 | 6047.6667 | 9491.1250 | 9491.3333 | 2.2917 | 6608.7017 | 5.707462 |
| root_heuristic_top1 | 23 | 5750.0870 | 9143.7391 | 9143.9565 | 3.3913 | 6293.2415 | 0.025640 |
| root_neural_top12 | 23 | 5742.9565 | 9133.3043 | 9133.5217 | 3.3913 | 6285.5067 | 0.000507 |
| root_neural_top4 | 23 | 5743.8261 | 9134.9565 | 9135.1739 | 3.3913 | 6286.4741 | 0.000478 |
| root_neural_top8 | 23 | 5742.9565 | 9133.4348 | 9133.6522 | 3.3913 | 6285.5143 | 0.000529 |
| root_oracle12 | 23 | 5742.9565 | 9133.3478 | 9133.5652 | 3.3913 | 6285.5096 | 0.165330 |
| root_oracle24 | 23 | 5742.2609 | 9133.3043 | 9133.5217 | 3.3913 | 6284.8128 | 0.259275 |
| root_union_h4_n12 | 23 | 5742.9565 | 9133.2609 | 9133.4783 | 3.3913 | 6285.5039 | 0.000460 |
| root_union_h4_n4 | 23 | 5743.3043 | 9134.4783 | 9134.6957 | 3.3913 | 6285.9239 | 0.000427 |
| root_union_h4_n8 | 23 | 5742.9565 | 9133.3478 | 9133.5652 | 3.3913 | 6285.5087 | 0.000432 |

## Pairwise comparisons

| target | baseline | metric | W/L/T | mean relative |
|---|---|---|---:|---:|
| root_beam4_oracle_eval | root_heuristic_top1 | score | 10/0/13 | -0.27% |
| root_beam4_oracle_eval | root_heuristic_top1 | T | 10/0/13 | -0.29% |
| root_beam4_oracle_eval | root_heuristic_top1 | CNOT | 9/1/13 | -0.11% |
| root_oracle12 | root_beam4_oracle_eval | score | 7/0/16 | -0.09% |
| root_oracle12 | root_beam4_oracle_eval | T | 4/0/19 | -0.09% |
| root_oracle12 | root_beam4_oracle_eval | CNOT | 6/1/16 | -0.15% |
| root_oracle24 | root_beam4_oracle_eval | score | 7/0/16 | -0.18% |
| root_oracle24 | root_beam4_oracle_eval | T | 7/0/16 | -0.19% |
| root_oracle24 | root_beam4_oracle_eval | CNOT | 5/1/17 | -0.12% |
| root_oracle24 | root_heuristic_top1 | score | 16/0/7 | -0.45% |
| root_oracle24 | root_heuristic_top1 | T | 16/0/7 | -0.48% |
| root_oracle24 | root_heuristic_top1 | CNOT | 13/2/8 | -0.23% |
| root_neural_top12 | root_beam4_oracle_eval | score | 6/1/16 | -0.06% |
| root_neural_top12 | root_beam4_oracle_eval | T | 4/0/19 | -0.05% |
| root_neural_top12 | root_beam4_oracle_eval | CNOT | 5/2/16 | -0.13% |
| root_oracle24 | root_neural_top12 | score | 3/0/20 | -0.12% |
| root_oracle24 | root_neural_top12 | T | 3/0/20 | -0.14% |
| root_oracle24 | root_neural_top12 | CNOT | 1/2/20 | +0.01% |
| root_neural_top4 | root_beam4_oracle_eval | score | 4/2/17 | +0.05% |
| root_neural_top4 | root_beam4_oracle_eval | T | 3/2/18 | +0.05% |
| root_neural_top4 | root_beam4_oracle_eval | CNOT | 3/3/17 | +0.00% |
| root_oracle24 | root_neural_top4 | score | 5/0/18 | -0.23% |
| root_oracle24 | root_neural_top4 | T | 5/0/18 | -0.24% |
| root_oracle24 | root_neural_top4 | CNOT | 4/0/19 | -0.12% |
| root_neural_top8 | root_beam4_oracle_eval | score | 5/1/17 | -0.06% |
| root_neural_top8 | root_beam4_oracle_eval | T | 4/0/19 | -0.05% |
| root_neural_top8 | root_beam4_oracle_eval | CNOT | 4/2/17 | -0.12% |
| root_oracle24 | root_neural_top8 | score | 3/0/20 | -0.12% |
| root_oracle24 | root_neural_top8 | T | 3/0/20 | -0.14% |
| root_oracle24 | root_neural_top8 | CNOT | 1/1/21 | -0.00% |
| root_union_h4_n12 | root_beam4_oracle_eval | score | 6/0/17 | -0.06% |
| root_union_h4_n12 | root_beam4_oracle_eval | T | 4/0/19 | -0.05% |
| root_union_h4_n12 | root_beam4_oracle_eval | CNOT | 5/1/17 | -0.14% |
| root_oracle24 | root_union_h4_n12 | score | 3/0/20 | -0.12% |
| root_oracle24 | root_union_h4_n12 | T | 3/0/20 | -0.14% |
| root_oracle24 | root_union_h4_n12 | CNOT | 1/2/20 | +0.02% |
| root_union_h4_n4 | root_beam4_oracle_eval | score | 4/0/19 | -0.02% |
| root_union_h4_n4 | root_beam4_oracle_eval | T | 3/0/20 | -0.02% |
| root_union_h4_n4 | root_beam4_oracle_eval | CNOT | 3/1/19 | -0.04% |
| root_oracle24 | root_union_h4_n4 | score | 4/0/19 | -0.16% |
| root_oracle24 | root_union_h4_n4 | T | 4/0/19 | -0.17% |
| root_oracle24 | root_union_h4_n4 | CNOT | 3/0/20 | -0.09% |
| root_union_h4_n8 | root_beam4_oracle_eval | score | 5/0/18 | -0.06% |
| root_union_h4_n8 | root_beam4_oracle_eval | T | 4/0/19 | -0.05% |
| root_union_h4_n8 | root_beam4_oracle_eval | CNOT | 4/1/18 | -0.13% |
| root_oracle24 | root_union_h4_n8 | score | 3/0/20 | -0.12% |
| root_oracle24 | root_union_h4_n8 | T | 3/0/20 | -0.14% |
| root_oracle24 | root_union_h4_n8 | CNOT | 1/1/21 | +0.01% |

## Interpretation

- `root_beam4_oracle_eval` measures the best action available inside the current heuristic top-4 window after true child evaluation.
- `root_oracle12` and `root_oracle24` measure how much extra quality is available if a wider root-action set can be ranked correctly.
- `root_union_h4_nK` keeps the deterministic heuristic top-4 actions and adds neural top-K actions, so it measures whether the learned ranker adds useful candidates without discarding the current heuristic window.
- Positive headroom here is a supervised target for a stronger high-dimensional learned root-action ranker; it should not be presented as a final synthesis optimum.
