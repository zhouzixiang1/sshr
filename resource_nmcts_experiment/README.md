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
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset ablation_affine --model models/action_scorer_rollout_logical_and.pt --resume
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset ablation_affine
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset ablation_affine
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset traditional_small --model models/action_scorer_rollout_logical_and.pt --resume
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset traditional_small
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset traditional_small
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset traditional_resource --model models/action_scorer_rollout_logical_and.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset traditional_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset traditional_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python run_resource_sweep.py --model models/action_scorer_rollout_logical_and.pt --workers 10
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_resource_sweep.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset large_resource_core --model models/action_scorer_rollout_logical_and.pt --resume --workers 6 --checkpoint-every 1 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset large_resource_core
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset large_resource_core
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_resource --model models/action_scorer_rollout_logical_and.pt --workers 2 --checkpoint-every 5 --resume --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset highdim_resource
```

Current presets:

- `smoke`: fast correctness/regression run.
- `pilot`: medium structured-oracle run with ANF, factor-MCTS, FPRM-MCTS,
  neural-MCTS, and SSHR-H references.
- `evidence_affine`: current paper-facing run.  It compares direct ANF,
  logical-AND direct ANF, fixed-coordinate logical-AND MCTS, affine-preconditioned
  neural MCTS, and SSHR-H on 322 Boolean functions.
- `ablation_affine`: same 322-function suite with affine-greedy and
  affine-no-guard variants added to isolate the neural refine and guard
  contributions.
- `traditional_small`: $n \leq 6$ comparison slice with direct ANF,
  logical-AND direct ANF, fixed-coordinate logical-AND MCTS, affine-preconditioned
  neural MCTS, ESOP cube beam, time-limited weighted ESOP MILP, and SSHR-H.
- `traditional_resource`: same $n \leq 6$ slice with the full Resource-NMCTS
  portfolio guard added.
- `large_resource_core`: 330-function large logical benchmark through `n=12`,
  now including the profile-aware Resource-NMCTS variant and process-isolated
  hard timeouts for long-tail tasks.
- `highdim_resource`: isolated `n=14` random-ANF stress benchmark with direct
  ANF, logical-AND direct ANF, FPRM-greedy, bounded FPRM root-beam,
  bounded affine-greedy, Resource-NMCTS, and Profile-Resource-NMCTS.
- `large_resource`: experimental `n=14` stress extension.  This preset exposed
  the mixed-suite runtime tail and is kept for broader engineering sweeps.
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

Ablation evidence from `results/analysis_ablation_affine.md`:

- `and_affine_greedy` alone already reduces mean T-count by 60.92% versus
  direct ANF, showing that affine coordinate search is the dominant source of
  improvement.
- `and_affine_no_guard` improves over `and_affine_greedy` in 65 score cases
  with 0 score losses, isolating the low-dimensional neural-refine benefit.
- `and_affine_nmcts` improves over `and_affine_no_guard` in 88 score cases
  with 0 score losses, isolating the fixed-coordinate MCTS guard benefit.
- `and_affine_nmcts` improves over `and_affine_greedy` in 153 score cases
  with 0 score losses.

Runtime/resource evidence from `results/runtime_ablation_affine.md`:

- affine-greedy completed all 322 functions with median runtime 0.033 s and
  max runtime 1.825 s.
- full `and_affine_nmcts` completed all 322 functions with median runtime
  0.609 s and max runtime 300.025 s.
- fixed-coordinate MCTS completed 321 functions and timed out once; its median
  runtime was 0.076 s and max completed runtime was 89.897 s.
- full `and_affine_nmcts` has the lowest all-suite mean T-count and composite
  score among the non-SSHR methods, while affine-greedy is the fastest strong
  setting.

Traditional Boolean/ESOP baseline evidence from
`results/analysis_traditional_resource.md` and
`results/runtime_traditional_resource.md`:

- 177 functions with $n \leq 6$, 8 methods, 1416 result rows, 0 errors, and 0
  skips.
- Mean T-count / composite score: `and_resource_nmcts` 45.74 / 55.21,
  `and_affine_nmcts` 45.88 / 55.37, fixed MCTS 62.06 / 73.09, ESOP cube beam
  71.32 / 83.82, ESOP MILP 83.59 / 96.73, and SSHR-H 81.04 / 88.19.
- Against Affine-NMCTS, `and_resource_nmcts` has 8 score wins, 0 score losses,
  and 169 score ties.
- Against ESOP cube beam, `and_resource_nmcts` has 172 T-count wins, 0 losses,
  and 5 ties, with a 34.72% mean T-count reduction and a 32.28% mean score
  reduction.
- Against time-limited weighted ESOP MILP, `and_resource_nmcts` has 162 T-count
  wins, 1 loss, and 14 ties, with a 29.50% mean T-count reduction and a
  26.95% mean score reduction.
- SSHR-H still has the lowest mean CNOT count on this small-function slice, so
  the claim remains low-T/resource-score synthesis rather than CNOT-only
  optimality.

Resource-profile stress-test evidence from
`results/analysis_resource_sweep.md`:

- 47 functions with $n \leq 6$, 4 resource profiles, 7 methods, 1316 result
  rows, 0 errors, and 0 skips.
- `and_profile_resource_nmcts` is best-or-tied on 42/47 functions under T-heavy
  weights, 42/47 under balanced weights, 41/47 under CNOT-depth-heavy weights,
  and 42/47 under ancilla-tight weights.
- Against Resource-NMCTS, `and_profile_resource_nmcts` has no score losses in
  any profile, with score wins/ties of 5/42, 6/41, 7/40, and 4/43.
- The mean Profile-Resource-NMCTS resource vector changes modestly across
  profiles (mean T 40.34--42.38; mean CNOT 82.43--84.79; mean depth
  86.72--88.72).  This supports objective robustness but still shows that the
  search is not yet a full profile-sensitive Pareto optimizer.

Large-scale core evidence from `results/analysis_large_resource_core.md` and
`results/runtime_large_resource_core.md`:

- 330 functions through `n=12`, 6 methods, 1980 result rows, 5 fixed-MCTS
  timeout rows, and 0 skips.  The stable run used process-isolated hard
  timeouts on an Apple M4 Pro with 14 logical CPU cores and 24 GB memory.
- `and_resource_nmcts` and `and_profile_resource_nmcts` completed all 330
  functions.  Fixed-coordinate MCTS timed out on 5 `n=12` random ANF functions.
- Compared with direct ANF, `and_resource_nmcts` has 291 T-count wins, 0
  losses, and 39 ties, with a 60.37% mean T-count reduction and a 56.84% mean
  score reduction.
- Compared with logical-AND direct ANF, it has 286 T-count wins, 0 losses, and
  44 ties, with a 37.25% mean T-count reduction and a 35.21% mean score
  reduction.
- Compared with fixed-coordinate MCTS on completed pairs, it has 139 T-count
  wins, 15 losses, and 171 ties, with an 11.41% mean score reduction.  The
  fixed-MCTS completed-row mean excludes its five timeout rows, so those means
  are censored toward easier functions.
- Compared with standalone Affine-NMCTS, it has 29 score wins, 16 score losses,
  and 285 ties, with a 0.20% mean score reduction.  This is a scalable budgeted
  portfolio result, not a dominance guarantee over the full affine search.
- Runtime for `and_resource_nmcts`: 330/330 completed, median 1.311 s, p95
  58.857 s, max 300.848 s.
- `and_profile_resource_nmcts` trades score for a shorter large-core runtime
  tail: 330/330 completed, median 2.292 s, p95 25.682 s, max 67.609 s, mean
  score 286.54 versus 273.72 for `and_resource_nmcts`.

High-dimensional stress evidence from `results/analysis_highdim_resource.md`
and `results/runtime_highdim_resource.md`:

- 64 random ANF functions at `n=14`, 7 methods, 448 result rows, 0 errors, and
  0 skips.
- `and_resource_nmcts` and `and_profile_resource_nmcts` complete all 64
  functions under the high-dimensional bounded guard.
- Compared with direct ANF, both Resource-NMCTS variants have 51 T-count wins,
  0 losses, and 13 ties, with a 52.71% mean T-count reduction and a 50.39%
  mean score reduction.
- Compared with logical-AND direct ANF, they have 51 T-count wins, 0 losses,
  and 13 ties, with a 26.88% mean T-count reduction and a 26.23% mean score
  reduction.
- Compared with FPRM-greedy, the high-dimensional guarded variants have
  40 T-count wins, 0 losses, and 24 ties; by weighted score they have
  41 wins, 0 losses, and 23 ties.  The improvement comes from the bounded
  FPRM root-beam candidate, which evaluates the full ranked first-factor list
  after cheap direct-cost polarity screening.
- Runtime tails remain visible but bounded: `and_resource_nmcts` completes
  64/64 with median 4.765 s and p95 52.113 s; `and_profile_resource_nmcts`
  completes 64/64 with median 3.734 s and p95 40.386 s.  The standalone
  FPRM root-beam candidate has median 2.834 s and p95 37.226 s.

Scope boundary: all costs are logical-level resource estimates.  The verifier
circuit is deterministic and classically checked, while the logical-AND cost
model accounts for low-T compute and Clifford/measurement-based uncompute.
No hardware mapping or connectivity constraints are included.
