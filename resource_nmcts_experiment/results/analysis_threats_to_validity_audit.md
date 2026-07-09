# Threats-to-Validity Audit

This audit checks that the manuscript names the main validity threats, ties them to generated evidence, and preserves the residual boundaries.

## Status counts

- pass: 7

| threat | status | risk | mitigation | residual boundary |
|---|---|---|---|---|
| Logical-layer abstraction | pass | Readers may infer hardware routing, native-gate, noise, or magic-state-factory resource claims. | The abstract, discussion, claim-scope lint, and payload README state that the paper reports logical-layer resources only. | No placement, routing, native-gate scheduling, noise, or factory-level accounting is evaluated. |
| Weighted-score aggregation | pass | A single score could hide unfavorable CNOT, depth, ancilla, or lifetime behavior. | Raw dominance, schedule-proxy, weight-robustness, resource-weight sensitivity, and counterpoint audits expose resource dimensions separately from the weighted score. | The method is presented as a strong T-count and weighted-score point, not complete raw-resource dominance. |
| Baseline comparability | pass | External logic-network, reversible, phase, and ROS-style rows could be mistaken for one fully uniform compiler benchmark. | The comparison matrices assign each baseline family a role, verified evidence, usable claim, and excluded claim. | ROS-style and logic-network probes remain logical proxies; RevKit rows are exact-oracle or phase proxies, not mapped circuits. |
| AI/MCTS attribution | pass | The manuscript could overstate deep learning or MCTS as the sole reason for the gains. | Search-control, random-prior, random-depth, and learned-control audits separate algebraic search space, MCTS, Pareto archives, and learned ranking. | Learned controls are bounded and sometimes runtime-negative; they are not promoted as the whole resource-reduction mechanism. |
| High-dimensional verification envelope | pass | Large-n symbolic rows may be read as exhaustive truth-table benchmarking or optimality evidence. | Scaling, ultra-scale, resource-profile, and truth-bridge audits separate symbolic verification from complete truth-table checks. | Complete truth-table verification is limited to generated n=21--30 bridge slices; n=31--64 rows are not exhaustive truth-table enumerations. |
| Statistical and benchmark representativeness | pass | Mean improvements could be driven by outliers or by an unrepresentative benchmark subset. | Paired statistics, bootstrap intervals, and headline consistency checks recompute matched comparisons from CSV evidence. | The evidence covers the generated and benchmarked slices in the artifact package, not all Boolean functions. |
| Reproducibility and package drift | pass | A complete-looking manuscript could drift from the scripts, raw rows, tables, and archive manifest. | Reproducibility, artifact-registry, and archive-manifest audits connect scripts, raw rows, summaries, tables, and manuscript payload groups. | The lightweight rebuild regenerates paper-facing artifacts but does not rerun heavy raw sweeps or neural training jobs. |
