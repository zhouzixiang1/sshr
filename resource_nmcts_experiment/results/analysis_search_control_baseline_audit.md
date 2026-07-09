# Search-Control Baseline Audit

This audit answers the reviewer-facing question: which search/control baselines are compared, and what does each comparison mean?

## Status counts

- pass: 9

| layer | comparison | scope | score W/L/T | mean score change | supported conclusion | boundary | status |
|---|---|---|---:|---:|---|---|---|
| search-space baseline | Affine greedy vs fixed-coordinate MCTS | 321 matched affine pairs | 165/88/68 | -12.12% | Changing the algebraic action space is a major source of score improvement. | This is not a neural-only effect. | pass |
| deterministic search controls | No-MCTS portfolio over heuristic-only | 177 n<=6 functions | 54/0/123 | -2.51% | A deterministic portfolio improves over a single heuristic baseline. | This row does not isolate MCTS. | pass |
| deterministic search controls | No-MCTS portfolio over beam-only | 177 n<=6 functions | 106/1/70 | -8.36% | The no-MCTS portfolio is stronger than the beam-only child in the same slice. | Beam is a child/search baseline, not the full method. | pass |
| MCTS over deterministic portfolio | Resource-NMCTS over no-MCTS portfolio | 177 n<=6 functions | 54/0/123 | -1.44% | MCTS adds a small but non-degrading score gain over the strengthened no-MCTS portfolio. | The magnitude is incremental, not the whole resource drop. | pass |
| Pareto search control | Pareto Resource-NMCTS over no-MCTS portfolio | 177 n<=6 functions | 106/0/71 | -4.69% | The Pareto archive makes the search-control gain clearer than base Resource-NMCTS alone. | Ancilla tradeoffs still need separate reporting. | pass |
| learned prior | Learned prior for Resource-NMCTS | 177 n<=6 functions | 39/0/138 | -1.10% | The learned scorer is a quality signal under the same functions and methods. | It is not a runtime claim and should not be promoted as the main source of improvement. | pass |
| bit-flip random control | Learned bit-flip prior vs same-budget random-prior mean | 177 n<=6 functions; eight random-prior repeats | 17/8/152 | -0.15% | The learned scorer beats deterministic random action priors as a bounded quality signal. | The margin is small and runtime-negative; this is not a claim that neural ranking explains the full gain. | pass |
| high-dimensional deterministic control | Highdim no-MCTS portfolio over root beam | 16 n=14 ANF instances | 14/0/2 | -6.25% | High-dimensional gains also need strong deterministic guards, not only MCTS. | This is symbolic/high-dimensional evidence, not exhaustive truth-table optimality. | pass |
| phase random control | Diverse phase shortlist top-512 vs same-budget random mean | 38 held-out n=6 phase functions; eight random repeats | 17/0/21 | -0.012% | The phase shortlist is better than same-budget random controls on this proxy. | This is a phase/Rz proxy control, not a bit-flip random baseline or rotation synthesis. | pass |

## Interpretation

- The bit-flip branch compares against heuristic-only, beam-only, no-MCTS, MCTS, Pareto, learned-prior/no-prior, and same-budget random-prior controls.
- Random controls now cover both the bit-flip action-prior scorer and the phase/Rz shortlist branch; they support bounded ranking/pruning claims, not runtime or full-causality claims.
- The evidence supports resource-aware search control, not a claim that reinforcement learning alone causes the full improvement.
