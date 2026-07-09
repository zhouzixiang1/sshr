# Comparison Claim Hierarchy

This audit classifies each comparison family by how it may be used in the manuscript claim.

## Status counts

- pass: 7

| claim tier | role | comparison families | supported claim | excluded claim | status |
|---|---|---|---|---|---|
| Headline support | Primary matched logical-oracle evidence | Direct ANF, AND-direct, ESOP beam/MILP, ABC/BDD, SSHR-H/I | Lower T-count and weighted score on matched logical bit-flip Boolean-oracle benchmarks. | No universal CNOT, depth, ancilla, line-count, hardware-mapped, or global-optimality claim. | pass |
| External stress test | Independent logical-toolchain pressure | ROS-style LUT, mockturtle, Caterpillar API, CirKit, RevKit CLI, ABC AIG/XAG/LUT | The advantage is not an artifact of comparing only against local hand-written baselines. | Not a full ROS SAT garbage-management, reversible-emission, routing, or hardware-mapped comparison. | pass |
| Counterpoint boundary | Strong opposing-resource evidence | SSHR CNOT, CirKit depth, Caterpillar CNOT, RevKit line count, STG optima | Other methods keep real CNOT, depth, line-count, or tiny-optimum advantages that bound the claim. | A weighted-score win must not be reported as complete Pareto or hardware-level dominance. | pass |
| Search-control attribution | Causal and ablation evidence for AI/search components | No-MCTS, beam-only, learned/no-prior, random-prior, random-depth, sparse/guard controls | Neural/MCTS controls provide bounded quality, pruning, or budget-allocation gains over strengthened deterministic controls. | The paper does not claim that deep reinforcement learning alone causes the full resource reduction. | pass |
| Scaling verification | Logical correctness beyond small exhaustive truth-table rows | n=20--64 symbolic term-set stress and n=21--30 complete truth-table bridges | Large symbolic circuits and bridge slices preserve logical correctness inside the stated verification envelope. | Not exhaustive high-dimensional truth-table benchmarking or a proof of global optimality. | pass |
| Related phase transfer | Secondary logical phase/Rz proxy | RevKit oracle_synth, ANF/FPRM phase parity, affine phase shortlist | The search framing transfers to a verified logical phase/Rz proxy and learned shortlist setting. | Not a final approximate-rotation Clifford+T synthesis or a bit-flip headline result. | pass |
| Manuscript integration | Generated table is included in all submission TeX variants | author, anonymous, ACM TQC | The claim hierarchy is visible where comparison scope is introduced. | The hierarchy is not only a detached support-package audit. | pass |

## Missing anchors

| claim tier | missing files | missing manuscript tokens |
|---|---|---|
| Headline support | none | none |
| External stress test | none | none |
| Counterpoint boundary | none | none |
| Search-control attribution | none | none |
| Scaling verification | none | none |
| Related phase transfer | none | none |
| Manuscript integration | none | none |
