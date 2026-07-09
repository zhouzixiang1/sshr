# Contribution-to-Evidence Map

This map links the introduction-level contribution claims to concrete manuscript evidence.

| contribution | implementation | evidence | boundary |
|---|---|---|---|
| Resource-constrained Boolean-oracle search formulation | ANF/FPRM term-set state, Boolean-ring and affine actions, guarded candidate selection, symbolic circuit emission. | pipeline figure; related-work positioning matrix | Logical-layer oracle synthesis only; no routing, native-gate mapping, or noise model. |
| Neural/MCTS resource-search workflow | Neural action priors, MCTS/beam/portfolio search, Pareto archive, frontier policies, staged and sparse learned gates. | contribution decomposition, search-control baseline audit, learned-control audit, learned-control figure | The largest gains come from searchable algebraic actions plus guarded selection; the paper does not claim deep RL alone explains all gains. |
| Broad baseline and toolchain comparison | Direct ANF, ESOP beam/MILP, SSHR, ABC/BDD, ROS-style LUT, mockturtle, Caterpillar API, CirKit, RevKit CLI, and phase/Rz probes. | baseline claim matrix, evidence matrix, paired statistics, baseline figure | Strong T-count and weighted-score evidence, not universal CNOT/depth/ancilla dominance or full ROS reproduction. |
| High-dimensional and phase-search verification envelope | n=20,24,28,32,40 symbolic term-set checks, n=48,56,64 ultra-scale symbolic stress, n=21--30 complete truth-table bridges, Affine-FPRM phase search, learned phase shortlist. | scale audit, ultra-scale stress and resource-profile tables, validation table, phase random-control table, validation figure | Large rows are logically and symbolically verified; complete truth-table enumeration remains limited to bridge slices. |
