# Neural/MCTS Claim Calibration

This audit checks whether the title-level neural MCTS framing is supported by the current evidence and bounded by explicit exclusions.

## Status counts

- pass: 7

| claim anchor | status | evidence gate | allowed claim | excluded claim |
|---|---|---|---|---|
| Neural component in the title | pass | learned-control rows=12, promoted=4, bounded=6, limited=2, not_promoted=0; limited-boundary rows=6; effect-uncertainty rows=8 | Neural policies and learned gates are bounded ranking, pruning, or budget-allocation controls with promoted and limited evidence classes. | Do not claim that deep learning alone explains the resource reduction. |
| MCTS component in the title | pass | search-control rows=12, needs_revision=0 | MCTS and Pareto search add measured, non-degrading increments over strengthened deterministic portfolios. | Do not attribute the full improvement to MCTS alone. |
| Causal search-control isolation | pass | bit-flip random rows=18, budget-sweep raw rows=2124, frontier random rows=3 | Same-budget, low-budget, and same-candidate controls support ranking and budget-allocation claims. | Do not use random-control rows as speed, hardware-scheduling, or deep-RL-only evidence. |
| Resource-constrained objective | pass | schedule-proxy rows=8, needs_revision=0 | The score and schedule-proxy evidence support resource-constrained logical-layer optimization with visible tradeoffs. | Do not turn weighted-score wins into all-resource or hardware-mapped dominance. |
| Verified workflow rather than learned correctness | pass | algorithm rows=7, budget rows=8 | Learning controls action order, pruning, or budget; correctness comes from GF(2), emitted-circuit, truth-table, and phase verifiers. | Do not imply that a neural model certifies circuit semantics. |
| Large-scale claim boundary | pass | ultra stress rows=11, profile rows=20 | Large instances are supported by symbolic term-set/emitted-circuit checks and smaller complete truth-table bridge slices. | Do not claim exhaustive truth-table benchmarking or optimality for all large n. |
| Logical-layer boundary | pass | claim-scope unresolved=0, threat rows=7 | The paper is a logical-layer synthesis study. | Do not claim routing, native-gate scheduling, noise, or magic-state-factory resources. |
