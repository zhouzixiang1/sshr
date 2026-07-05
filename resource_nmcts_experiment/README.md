# Resource-Constrained Neural MCTS Oracle Synthesis

This directory implements a new logic-level line of work for:

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

The method does not use SSHR parallelotope candidates.  It treats Boolean
oracle synthesis as a symbolic factorization search over ANF/XAG-style
compute/uncompute plans, then verifies the generated oracle circuits by
classical simulation.

Core commands:

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python tests_smoke.py
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset rollout --gate-mode logical_and --label-mode rollout --max-depth 3 --child-branch 2 --out models/action_scorer_rollout_logical_and.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset smoke
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset evidence_affine --model models/action_scorer_rollout_logical_and.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset evidence_affine
```

Current presets:

- `smoke`: fast correctness/regression run.
- `pilot`: medium structured-oracle run with ANF, factor-MCTS, FPRM-MCTS,
  neural-MCTS, and SSHR-H references.
- `evidence_affine`: current paper-facing run.  It compares direct ANF,
  logical-AND direct ANF, fixed-coordinate logical-AND MCTS, affine-preconditioned
  neural MCTS, and SSHR-H on 322 Boolean functions.
- `main`: large-scale placeholder for broader sweeps.

Outputs are written to `results/`.  The neural prior is saved at
`models/action_scorer_rollout_logical_and.pt`.

Current evidence from `results/analysis_evidence_affine.md`:

- 322 functions, 5 methods, 1610 result rows.
- `and_affine_nmcts` is correct on all 322 functions.
- Mean T-count reduction versus direct ANF: 61.83%.
- Mean T-count reduction versus logical-AND direct ANF: 40.12%.
- Versus fixed-coordinate logical-AND MCTS, `and_affine_nmcts` has 161 T-count
  wins, 160 ties, and 0 losses over the 321 completed baseline pairs; mean
  T-count reduction is 16.18%.
- Versus SSHR-H on supported functions, `and_affine_nmcts` has 171 wins, 5
  ties, and 1 loss in T-count; mean T-count reduction is 43.89%.
- One fixed-coordinate MCTS baseline row (`anf_n12_10`) timed out at 600 s.
  The affine method completed that same function within the experiment budget.

Scope boundary: all costs are logical-level resource estimates.  The verifier
circuit is deterministic and classically checked, while the logical-AND cost
model accounts for low-T compute and Clifford/measurement-based uncompute.
No hardware mapping or connectivity constraints are included.
