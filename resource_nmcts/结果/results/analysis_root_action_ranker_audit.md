# Root-Action Neural Ranker Audit

This audit consolidates the high-dimensional root-action diagnostics used
to decide whether the learned root-action scorer can be described as a
bounded candidate-extension signal.  It compares a conservative union
policy that keeps the deterministic heuristic top-4 actions and adds
neural top-12 actions against the existing heuristic top-4 root window.

## Status counts

- pass: 5

| component | scope | target | baseline | pairs | score W/L/T | mean score change | oracle headroom | role | status |
|---|---|---|---|---:|---:|---:|---:|---|---|
| n=14 heuristic top-4 plus neural top-12 extension | n=14 root-action slice | root_union_h4_n12 | root_beam4_oracle_eval | 10 | 2/0/8 | -0.14% | -0.04% | bounded candidate extension | pass |
| n=16 heuristic top-4 plus neural top-12 extension | n=16 root-action slice | root_union_h4_n12 | root_beam4_oracle_eval | 23 | 6/0/17 | -0.06% | -0.12% | bounded candidate extension | pass |
| Combined heuristic top-4 plus neural top-12 extension | n=14 and n=16 root-action slices | root_union_h4_n12 | root_beam4_oracle_eval | 33 | 8/0/25 | -0.08% | -0.10% | bounded candidate extension | pass |
| Combined neural top-12 replacement | n=14 and n=16 root-action slices | root_neural_top12 | root_beam4_oracle_eval | 33 | 8/2/23 | -0.06% | -0.12% | supporting replacement diagnostic | pass |
| Combined oracle top-24 headroom | n=14 and n=16 root-action slices | root_oracle24 | root_beam4_oracle_eval | 33 | 10/0/23 | -0.18% | +0.00% | one-step teacher boundary | pass |

## Interpretation

- The union policy is the only root-action row promoted into the learned-control audit, because it preserves the deterministic heuristic window and adds learned candidates.
- The combined union row has zero score losses against heuristic top-4, but the mean gain is small; it supports bounded candidate extension, not a headline resource claim.
- The oracle-headroom row records that a wider one-step teacher still has residual room, so the learned root-action scorer remains a bounded search-control component.
