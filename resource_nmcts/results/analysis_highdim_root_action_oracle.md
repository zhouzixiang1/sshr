# High-dimensional root-action oracle analysis

This diagnostic evaluates whether high-dimensional CNOT-only linear-pair
root actions contain useful ranking headroom beyond the cheap heuristic.
Each action is scored by building actual greedy child plans, so the
oracle rows are a bounded one-step teacher signal rather than a global
reversible-circuit optimum.

Model for optional neural ordering: `/Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment/models/linear_action_scorer_highdim.pt`.

Rows: 62; errors: 0; incorrect: 0.

## Mean resources

| method | functions | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|---:|
| root_beam4_oracle_eval | 10 | 5484.0000 | 8889.0000 | 8889.4000 | 3.9000 | 6013.5630 | 0.140741 |
| root_direct | 12 | 5609.3333 | 8787.3333 | 8787.8333 | 2.4167 | 6129.2625 | 0.566775 |
| root_heuristic_top1 | 10 | 5491.6000 | 8897.2000 | 8897.6000 | 3.9000 | 6021.6340 | 0.047384 |
| root_neural_top4 | 10 | 5485.6000 | 8891.5000 | 8891.9000 | 3.9000 | 6015.3075 | 0.002730 |
| root_oracle12 | 10 | 5478.8000 | 8888.3000 | 8888.7000 | 3.9000 | 6008.3395 | 0.411918 |
| root_oracle24 | 10 | 5478.8000 | 8888.3000 | 8888.7000 | 3.9000 | 6008.3395 | 0.589406 |

## Pairwise comparisons

| target | baseline | metric | W/L/T | mean relative |
|---|---|---|---:|---:|
| root_beam4_oracle_eval | root_heuristic_top1 | score | 5/0/5 | -0.25% |
| root_beam4_oracle_eval | root_heuristic_top1 | T | 4/0/6 | -0.26% |
| root_beam4_oracle_eval | root_heuristic_top1 | CNOT | 4/1/5 | -0.17% |
| root_oracle12 | root_beam4_oracle_eval | score | 3/0/7 | -0.18% |
| root_oracle12 | root_beam4_oracle_eval | T | 3/0/7 | -0.19% |
| root_oracle12 | root_beam4_oracle_eval | CNOT | 2/1/7 | -0.04% |
| root_oracle24 | root_beam4_oracle_eval | score | 3/0/7 | -0.18% |
| root_oracle24 | root_beam4_oracle_eval | T | 3/0/7 | -0.19% |
| root_oracle24 | root_beam4_oracle_eval | CNOT | 2/1/7 | -0.04% |
| root_oracle24 | root_heuristic_top1 | score | 7/0/3 | -0.43% |
| root_oracle24 | root_heuristic_top1 | T | 6/0/4 | -0.45% |
| root_oracle24 | root_heuristic_top1 | CNOT | 6/1/3 | -0.21% |
| root_neural_top4 | root_beam4_oracle_eval | score | 1/1/8 | +0.06% |
| root_neural_top4 | root_beam4_oracle_eval | T | 1/1/8 | +0.06% |
| root_neural_top4 | root_beam4_oracle_eval | CNOT | 1/1/8 | +0.06% |
| root_oracle24 | root_neural_top4 | score | 4/0/6 | -0.24% |
| root_oracle24 | root_neural_top4 | T | 4/0/6 | -0.25% |
| root_oracle24 | root_neural_top4 | CNOT | 3/1/6 | -0.10% |

## Interpretation

- `root_beam4_oracle_eval` measures the best action available inside the current heuristic top-4 window after true child evaluation.
- `root_oracle12` and `root_oracle24` measure how much extra quality is available if a wider root-action set can be ranked correctly.
- Positive headroom here is a supervised target for a stronger high-dimensional learned root-action ranker; it should not be presented as a final synthesis optimum.
