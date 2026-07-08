# Method Workflow Table

This table summarizes the end-to-end Resource-NMCTS synthesis workflow and the verification invariant attached to each stage.

| stage | mechanism | invariant | artifact |
|---|---|---|---|
| Input normalization | Convert a truth table, exported benchmark, or supplied term set into a square-free ANF monomial mask set M. | The term set must evaluate to the target Boolean function before any search step is trusted. | ANF terms, preset name, and source manifest. |
| Candidate generation | Generate direct ANF, FPRM polarity, common-factor, Boolean-ring linear-factor, affine, and depth-frontier candidates. | Every action must have an explicit GF(2) expansion back to the original variables. | Candidate logical plans with resource estimates. |
| Search control | Use neural action priors, MCTS/beam expansion, staged frontiers, and sparse learned gates to allocate the search budget. | Learned decisions rank or skip evaluations; they do not define semantic correctness. | Scored candidate pool and search-time diagnostics. |
| Guarded selection | Compare learned and expensive candidates with deterministic baselines, then apply Pareto filtering before active-score selection. | A selected plan must be a valid generated candidate and remains bounded by the stated guard and score model. | Selected logical plan and non-dominated archive entry. |
| Circuit emission | Expand the selected plan into X/CNOT/MCT compute-action-uncompute operations and compute logical resource counts. | The reported score is a ranking objective; T, CNOT, depth, gates, and ancilla are retained separately. | Logical circuit proxy and resource row. |
| Verification and reporting | Check the plan algebraically, check emitted-circuit ANF semantics, add full truth-table or phase checks where feasible, and write raw CSV plus manifest rows. | Paper comparisons use matched rows that pass the relevant semantic checks and exclude errors, skips, and timeouts. | raw_*.csv, summary_*.csv, manifest_*.json, and paper tables. |
