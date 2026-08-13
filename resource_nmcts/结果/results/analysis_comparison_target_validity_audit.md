# Comparison Target Validity Audit

This audit answers whether each comparison target is meaningful for the manuscript's bounded logical-layer claim.

It labels each target family as a primary benchmark, external probe, exact reversible counterpoint, phase proxy, causal control, scalability check, or trade-off boundary.

## Status counts

- pass: 8

| family | role | status | meaning test | supported statement | invalid statement |
|---|---|---|---|---|---|
| Same-task Boolean-oracle baselines | primary benchmark | pass | These baselines solve the same bit-flip Boolean-oracle task or the closest small-function CNOT-oriented variant under the logical resource model. | Primary evidence for lower T-count and weighted score on matched small functions. | Not evidence of universal CNOT, depth, ancilla, line-count, or hardware-mapped optimality. |
| External logic-network probes | external stress test | pass | These probes test whether mature Boolean-network and LUT/XAG/AIG optimization already removes the apparent advantage. | Secondary evidence that the score/T-count advantage survives external logical toolchain probes. | Not a full ROS SAT garbage-management optimizer, reversible-emission, routing, or hardware-mapped comparison. |
| Published STG optimum-library counterpoint | small-function optimum counterpoint | pass | This target asks whether the generic logical search beats a precomputed tiny-function optimum library; the expected use is a boundary, not a headline win. | Evidence that public STG optima remain stronger on tiny precomputed representatives while the method still improves local direct baselines on the same slice. | Not evidence of beating published STG T-count, T-depth, or qubit optima. |
| Exact reversible-synthesis probe | exact reversible counterpoint | pass | The baseline embeds each function as the exact reversible permutation and checks a genuine reversible-synthesis toolchain. | Evidence that a real reversible-synthesis portfolio does not erase the T/score advantage. | Not evidence of lower auxiliary-line count, routed depth, or final mapped Clifford+T dominance. |
| Phase/Rz branch | phase proxy | pass | This branch tests whether the search framing transfers to verified logical phase/Rz proxy objectives. | Evidence for a related logical phase/Rz proxy and learned shortlist, not the main bit-flip claim. | Not a final approximate-rotation synthesis or full Clifford+T sequence. |
| AI/search-control ablations | causal control | pass | These controls separate representation/search-space effects from MCTS, neural ranking, guards, and reinforcement-learned Pareto budget allocation. | Evidence that learned/search controls add bounded quality or planning gains and that fitted-Q control can reduce optional Pareto effort. | Not evidence that deep reinforcement learning alone causes the full resource reduction or dominates always-on Pareto score. |
| Scaling and correctness bridges | scalability verification | pass | These rows test whether emitted logical oracles remain verifiable beyond the small truth-table benchmark slice. | Evidence for logical-layer scaling and semantic verification within the symbolic/bridge envelope. | Not exhaustive high-dimensional truth-table benchmarking or optimality evidence. |
| Trade-off counterpoints | non-dominance boundary | pass | These counterpoints keep the comparison meaningful by exposing metrics where other methods remain strong. | Evidence that the method occupies a strong T/score point with explicit resource tradeoffs. | Not a single universal leaderboard or complete Pareto dominance claim. |
