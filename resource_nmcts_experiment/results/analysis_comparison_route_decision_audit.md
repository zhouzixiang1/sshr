# Comparison Route Decision Audit

This audit states which comparator family should be used for each reviewer-facing claim and which stronger interpretation remains excluded.

## Status counts

- pass: 8

## Decision routes

| route | reviewer question | right comparator | evidence gate | usable claim | excluded claim | status |
|---|---|---|---|---|---|---|
| Main same-task resource claim | Are the gains only over weak algebraic baselines? | Direct ANF, ESOP beam/MILP, ABC/BDD exports, and matched SSHR rows | answer=2/2; target=2/2; suite=1/1; files=3/3 | The method improves logical bit-flip oracle resources on matched small-function tasks. | This row does not prove hardware-mapped, universal Pareto, or large-n optimality. | pass |
| CNOT-oriented geometric counterpoint | Is SSHR the whole comparison target? | SSHR-H and timed SSHR-I rows | answer=2/2; target=2/2; suite=1/1; files=3/3 | The method is competitive with a CNOT-oriented SSHR baseline while optimizing a different resource objective. | Do not state CNOT dominance over SSHR or define the contribution as an SSHR variant. | pass |
| External logical-toolchain stress test | Does the advantage survive mature logic synthesis? | ROS-style LUT, mockturtle, Caterpillar API, CirKit, and ABC-family probes | answer=2/2; target=2/2; suite=1/1; files=4/4 | The resource advantage is not an artifact of only comparing with project-internal implementations. | Do not present these probes as full ROS, routed reversible, or hardware-mapped reproductions. | pass |
| Exact reversible and phase counterpoint | What does RevKit test? | Legacy RevKit exact-oracle portfolio and RevKit/affine phase-Rz rows | answer=2/2; target=2/2; suite=1/1; files=3/3 | A real reversible-synthesis portfolio and related phase branch were checked as bounded counterpoints. | Do not claim fewer auxiliary lines, routed depth, or final approximate Clifford+T rotation synthesis. | pass |
| Tiny optimum-library boundary | Does it beat published tiny-function optima? | Published STG n=4/5 optimum-library circuits | answer=2/2; target=1/1; suite=1/1; files=3/3 | The paper reports a negative control where precomputed tiny-function optima remain stronger. | Do not claim to beat published STG optima on T-count, T-depth, or qubit count. | pass |
| AI/MCTS attribution | What part is actually AI or MCTS? | No-MCTS, beam, learned-prior, random-prior, random-depth, and stochastic controls | answer=2/2; target=2/2; suite=1/1; files=4/4 | Neural ranking, MCTS, and guards add bounded gains beyond deterministic construction. | Do not say deep reinforcement learning alone explains the full resource reduction. | pass |
| Large-scale semantic verification | Is the evidence only small-scale? | n=20--64 symbolic term-set stress and n=21--30 complete truth-table bridges | answer=2/2; target=1/1; suite=2/2; files=3/3 | The emitted logical oracle and verification harness scale beyond the n<=6 truth-table benchmark slice. | Do not claim exhaustive high-dimensional truth-table benchmarking or global optimality. | pass |
| Weighted-score and tradeoff boundary | Does weighted score hide bad tradeoffs? | Four-resource dominance, non-dominated rows, SSHR/CirKit/RevKit counterpoints, and weight profiles | answer=2/2; target=2/2; suite=2/2; files=3/3 | The method occupies a strong T/score point with visible CNOT, depth, and ancilla tradeoffs. | Do not turn weighted-score wins into a universal leaderboard or complete Pareto-dominance claim. | pass |
