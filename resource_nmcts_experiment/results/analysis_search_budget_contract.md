# Search Budget Contract

This audit records the explicit search budgets and scalability guards used by Resource-NMCTS.
It is a method contract rather than a performance result.

## Status counts

- pass: 8

| budget family | budget or cap | source anchors | scalability role | boundary | status |
|---|---|---|---|---|---|
| Action fan-out | candidate_top_k=24; max_factor_size=5; min_factor_count=2 | `factor_plan.py: SearchConfig, candidate_actions, actions[: config.candidate_top_k]` | Bounds the number of algebraic actions expanded at each ANF state. | The cap controls search cost; it is not a proof that the globally best factor action is always included. | pass |
| Ancilla and recursion | max_factor_ancilla=4; depth guard=64 in MCTS recursion | `factor_plan.py: live_factor_ancilla guard; nmcts_solver.py: depth > 64 fallback` | Prevents recursive factoring from allocating unbounded temporary factor lines. | This is a resource guard, not an ancilla-optimality theorem. | pass |
| PUCT/MCTS simulations | mcts_simulations=96; neural_mcts_simulations=128; c_puct=1.35 | `nmcts_solver.py: NeuralMCTSSolver, c_puct, _simulate; synthesizers.py: mcts_factor, neural_mcts` | Makes tree-search compute an explicit, rerunnable budget rather than an open-ended optimizer. | The MCTS budget supports a bounded search-control claim, not exact optimal synthesis. | pass |
| Polarity and affine search | max_polarities=384; high-dimensional direct screening narrows expensive planning trials | `synthesizers.py: _ranked_polarities, _direct_screened_polarities, screen_budget, screen_top_k` | Keeps fixed-polarity and affine preconditioning searches tractable on larger sparse term sets. | Screening is a controlled heuristic; missed polarities remain part of the search-boundary limitation. | pass |
| Resource portfolio | fast_config caps candidate_top_k<=18, MCTS<=32/40, max_polarities<=16/24 before portfolio selection | `synthesizers.py: resource_heuristic/resource_no_mcts/resource_nmcts fast_config, _run_child_portfolio` | Separates cheap deterministic candidates from more expensive MCTS or affine branches. | Portfolio selection gives a best verified candidate among attempted children, not a certificate over all possible children. | pass |
| Pareto archive | Deduplicate by (T,CNOT,depth,gates,peak ancilla), remove dominated candidates, then rank the non-dominated front by active score | `synthesizers.py: _resource_dims, _dominates, _pareto_front, _resource_selection_key` | Keeps multi-objective diversity without carrying every generated candidate into the final comparison. | The archive is Pareto over generated candidates only; it is not a global Pareto frontier. | pass |
| High-dimensional frontier controllers | Staged, sparse, and learned gates decide whether depth-3/depth-4 Boolean-ring screens are evaluated | `train_sparse_depth4_gate.py: threshold; run_truth_bridge_terms.py: load_depth2_guard, depth_frontier_policy, screen_depth4` | Moves large-term-set runs from all-frontier evaluation toward validated budget control. | The controller is empirical on the audited slices and is not a proof that depth-4 can always be skipped. | pass |
| Verification route | Symbolic ANF/circuit checks for large rows; complete truth-table bridge slices where enumeration is feasible | `factor_plan.py: verify_plan_anf, verify_circuit_anf, verify_oracle; run_truth_bridge_terms.py: truth bridge rows` | Allows high-dimensional evidence without pretending that every large instance was exhaustively enumerated. | Symbolic verification is exact for emitted GF(2) semantics but does not replace hardware mapping or exhaustive enumeration for all n. | pass |
