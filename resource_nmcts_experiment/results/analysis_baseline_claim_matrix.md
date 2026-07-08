# Baseline Claim Matrix

This table explains the role of each comparison family in the paper's argument.

| comparison role | methods | supported claim | excluded claim |
|---|---|---|---|
| Primary resource-efficiency baselines | Direct ANF, AND-direct ANF, ESOP beam/MILP, BDD/ABC-ESOP, SSHR-H/SSHR-I | Resource-NMCTS improves T-count and weighted score on matched small functions while SSHR remains a strong CNOT counterpoint. | Does not prove universal CNOT, depth, ancilla, or hardware-level optimality. |
| External logic-network probes | ABC AIG/XAG/LUT, ROS-style LUT proxy, mockturtle KLUT-to-XAG, CirKit AIG/MC | The score advantage persists against stronger exported-network and official-header tool probes. | Does not reproduce full ROS SAT garbage management or reversible/hardware mapping. |
| Exact reversible-synthesis probe | Legacy RevKit CLI TBS/DBS/RMS exact-oracle portfolio | Resource-NMCTS has lower T-count and weighted score against this portfolio but pays more auxiliary lines. | Does not imply lower line count, routed depth, or mapped Clifford+T cost. |
| Phase/Rz branch | RevKit oracle_synth, phase-parity ANF, fixed-polarity FPRM, affine FPRM, learned phase shortlist | Affine and learned candidate pruning improve verified logical phase/Rz proxy objectives. | Does not output approximate rotation sequences or a final Clifford+T decomposition. |
| Internal search ablations | No-MCTS portfolio, learned prior off, guard off, Pareto archive off, depth-frontier variants, sparse gate | AI-guided search and guards add measurable gains or time savings beyond deterministic construction. | Does not support a claim that deep reinforcement learning alone causes the whole improvement. |
| Scaling and correctness bridges | n=20-40 term-set symbolic runs; n=21-25 complete truth-table bridge rows | The emitted logical-layer circuits remain symbolically and bridge-truth-table verified at larger dimensions. | Does not make exhaustive high-dimensional truth-table benchmarking feasible or complete. |
| Trade-off audits | Raw multi-resource dominance, line-aware LUT reselection, schedule proxy, sparse-threshold sweep | The method occupies a strong T/score point with explicit depth, CNOT, ancilla, and runtime boundaries. | Does not justify reporting a single-metric victory as complete dominance. |
