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
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_scale_resource --model models/action_scorer_rollout_logical_and.pt --workers 6 --checkpoint-every 8 --resume --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset highdim_scale_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset highdim_scale_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset large_resource_core --formats pla,blif,truth
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset traditional_resource --formats pla,blif,truth --out-dir benchmark_exports/traditional_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --max-n 4 --max-ilp-n 4 --timeout 10 --workers 4 --out results/raw_external_traditional_resource_n4.csv --summary results/summary_external_traditional_resource_n4.csv --run-manifest results/manifest_external_traditional_resource_n4.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_traditional_resource_n4.csv --internal-csv results/raw_traditional_resource.csv --out results/analysis_external_traditional_resource_n4.md
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_sshr_h,external_sshr_i_cnot,external_sshr_i_t --max-n 6 --max-ilp-n 6 --timeout 8 --workers 4 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_aig --max-n 6 --max-abc-n 6 --timeout 8 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_esop --max-n 6 --max-esop-n 6 --timeout 8 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_xag --max-n 6 --max-xag-n 6 --timeout 10 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_traditional_resource_n6.csv --internal-csv results/raw_traditional_resource.csv --out results/analysis_external_traditional_resource_n6.md
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset highdim_resource --formats blif,truth --out-dir benchmark_exports/highdim_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/highdim_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag --min-n 14 --max-n 14 --max-abc-n 14 --max-xag-n 14 --timeout 20 --workers 8 --out results/raw_external_highdim_resource.csv --summary results/summary_external_highdim_resource.csv --run-manifest results/manifest_external_highdim_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_highdim_resource.csv --internal-csv results/raw_highdim_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_linear_pair,and_fprm_root_beam,and_fprm_greedy,direct_anf,and_direct_anf --out results/analysis_external_highdim_resource.md
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset highdim_scale_resource --formats blif,truth --out-dir benchmark_exports/highdim_scale_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/highdim_scale_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag --min-n 15 --max-n 15 --max-abc-n 15 --max-xag-n 15 --timeout 30 --workers 8 --out results/raw_external_highdim_scale_resource.csv --summary results/summary_external_highdim_scale_resource.csv --run-manifest results/manifest_external_highdim_scale_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_highdim_scale_resource.csv --internal-csv results/raw_highdim_scale_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_linear_pair_deep,and_fprm_linear_pair,and_fprm_linear_parity,and_fprm_greedy,direct_anf,and_direct_anf --out results/analysis_external_highdim_scale_resource.md
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
  bounded FPRM linear-pair factoring, bounded affine-greedy, Resource-NMCTS,
  and Profile-Resource-NMCTS.  The guarded variants keep the root-child beam
  baseline and use a one-extra-layer CNOT-only pairwise XOR factor candidate.
- `highdim_scale_resource`: isolated `n=15` random-ANF scale check with direct
  ANF, logical-AND direct ANF, FPRM-greedy, bounded FPRM root-beam, FPRM
  linear-pair factoring, a one-extra-layer bounded linear-pair refinement,
  a standalone width-three linear-parity ablation, Resource-NMCTS, and
  Profile-Resource-NMCTS.
- `large_resource`: experimental `n=14` stress extension.  This preset exposed
  the mixed-suite runtime tail and is kept for broader engineering sweeps.
- `main`: large-scale placeholder for broader sweeps.

Outputs are written to `results/`.  The neural prior is saved at
`models/action_scorer_rollout_logical_and.pt`.

External-tool benchmark exchange:

- `export_benchmarks.py` writes deterministic PLA, BLIF `.names`, and JSON
  truth-table files for any experiment preset, plus `manifest.csv` and
  `manifest.json`.
- The default output directory is `benchmark_exports/<preset>_seed<seed>/` and
  is intentionally git-ignored because the files are regenerable and can be
  large for `n=12` and `n=14` suites.
- This is the bridge for reproducing the same Boolean functions in external
  AIG/XAG/ROS/LUT or mockturtle-style synthesis flows without depending on the
  Python experiment harness.
- `run_external_baselines.py` consumes the exported `manifest.csv`/JSON and
  runs cross-directory baseline backends.  The implemented external backends
  are SSHR-H/SSHR-I from `src/sshr` and a Berkeley ABC AIG path that optimizes
  exported BLIF with `strash; balance; rewrite; refactor; rewrite -z; balance`,
  verifies the optimized BLIF truth table with a bit-parallel full truth-table
  checker, and maps AIG AND/level statistics to a logic-level Bennett
  compute/uncompute resource estimate.  It also includes an ABC XAG/GIA path
  using `&get; &st -m -L 1` plus `&ps -m -x`, verified BLIF output, and a
  logical XAG cost model.  It also includes
  an ABC ESOP path using `&exorcism -q`, verified ESOP-PLA output, and the same
  logical-AND cube cost model as the internal ESOP baselines.  ROS and
  mockturtle adapters are still future work.

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

Exported exact SSHR-I pilot evidence from
`results/analysis_external_traditional_resource_n4.md`:

- Exported the `traditional_resource` suite to PLA, BLIF, and truth-table JSON,
  then ran external SSHR-H, CNOT-optimized SSHR-I, and T-optimized SSHR-I on all
  72 functions with `n <= 4`.
- The pilot produced 216 external method/function rows, 216 usable rows, and 0
  errors/skips.
- Against CNOT-optimized SSHR-I, `and_resource_nmcts` has 65 T-count wins, 0
  losses, and 7 ties; score wins/losses/ties are 69/3/0 with a 26.45% mean
  score reduction.  CNOT count is worse on 65/72 functions.
- Against T-optimized SSHR-I, `and_resource_nmcts` has the same 65/0/7 T-count
  win pattern and a 26.21% mean score reduction.  CNOT count is worse on 62/72
  functions.

Time-limited exported SSHR-I, ABC-AIG, ABC-XAG, and ABC-ESOP extension evidence from
`results/analysis_external_traditional_resource_n6.md`:

- Extends the same exported manifest to all 177 functions with `n <= 6`.
- Produces 1062 external rows across SSHR-H, CNOT-optimized SSHR-I,
  T-optimized SSHR-I, ABC-AIG, ABC-XAG, and ABC-ESOP, with 0 errors/skips.
- The SSHR-I rows use an 8 s per-call Gurobi budget, so this is a
  time-limited extension rather than an exact certificate.
- The ABC-AIG rows use Berkeley ABC 1.01 built from
  `bcfdf592289a408cd67ec19260f8a60a37b085b6`; all 177 optimized BLIF outputs
  pass truth-table verification before resource scoring.
- Against ABC-AIG, `and_resource_nmcts` has 170 T-count wins, 2 losses, and 5
  ties; it wins all 177 CNOT, peak-ancilla, and weighted-score comparisons,
  with mean reductions of 50.60%, 86.29%, and 54.52%, respectively.  ABC-AIG
  has a lower depth estimate on 126/177 functions, which is the main ABC-side
  advantage under this Bennett-style resource model.
- Against ABC-XAG, `and_resource_nmcts` has 176 T-count wins, 0 losses, and 1
  tie; it wins all 177 peak-ancilla and weighted-score comparisons, with mean
  reductions of 89.85% and 63.23%, respectively.  It reduces mean CNOT by
  35.53%, while ABC-XAG has a lower depth estimate on 144/177 functions.
- Against ABC-ESOP, `and_resource_nmcts` has 144 T-count wins, 19 losses, and
  14 ties; score wins/losses/ties are 147/24/6 with a 19.88% mean score
  reduction.  This baseline uses ABC `&exorcism -q` and verified ESOP-PLA
  output, making it a stronger external XOR-of-products comparison than the
  AIG-only path.
- Against CNOT-optimized SSHR-I, `and_resource_nmcts` has 164 T-count wins, 3
  losses, and 10 ties; score wins/losses/ties are 168/9/0 with a 27.92% mean
  score reduction.  CNOT count is worse on 168/177 functions.
- Against T-optimized SSHR-I, `and_resource_nmcts` has 166 T-count wins, 1
  loss, and 10 ties, with a 26.25% mean score reduction.

Exported high-dimensional ABC-AIG/ABC-XAG evidence from
`results/analysis_external_highdim_resource.md` and
`results/analysis_external_highdim_scale_resource.md`:

- The ABC external paths now cover 64 exported `n=14` random-ANF functions and
  32 exported `n=15` random-ANF functions for each of ABC-AIG and ABC-XAG, with
  192/192 correct rows and 0 errors/skips.
- At `n=14`, `and_resource_nmcts` and `and_profile_resource_nmcts` beat
  ABC-AIG and ABC-XAG on all 128 T-count, CNOT, peak-ancilla, and
  weighted-score comparisons.  Mean score reductions are 94.13% against AIG
  and 95.48% against XAG.
- At `n=15`, the same guarded methods beat ABC-AIG and ABC-XAG on all 64
  T-count, CNOT, peak-ancilla, and weighted-score comparisons.  Mean score
  reductions are 94.59% against AIG and 96.33% against XAG.
- ABC remains shallower under the current level-based estimate on most high
  dimensional functions, so the claim remains weighted-resource and
  low-ancilla dominance rather than depth-only dominance.

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

- 64 random ANF functions at `n=14`, 8 methods, 512 result rows, 0 errors, and
  0 skips.
- `and_resource_nmcts` and `and_profile_resource_nmcts` complete all 64
  functions under the high-dimensional bounded guard.
- Compared with direct ANF, both Resource-NMCTS variants have 61 T-count wins,
  0 losses, and 3 ties, with a 57.42% mean T-count reduction and a 54.03%
  mean score reduction.
- Compared with logical-AND direct ANF, they have 61 T-count wins, 0 losses,
  and 3 ties, with a 32.74% mean T-count reduction and a 30.86% mean score
  reduction.
- Compared with FPRM-greedy, the high-dimensional guarded variants have
  60 T-count wins, 0 losses, and 4 ties; by weighted score they also have
  60 wins, 0 losses, and 4 ties, with a 6.25% mean score reduction.  Against
  the one-layer FPRM linear-pair candidate, they have 53 T-count wins, 0
  losses, and 11 ties, with a 2.87% mean score reduction.  The improvement
  comes from a bounded recursive FPRM linear-pair candidate that factors
  repeated term pairs as `(x_i xor x_j) * g` using CNOT-only linear compute and
  uncompute around the factored subplan.
- Compared with the standalone FPRM root-beam candidate, the guarded variants
  now have 60 T-count wins, 0 losses, and 4 ties; by weighted score they have
  60 wins, 0 losses, and 4 ties, with a 5.73% mean score reduction.
- Runtime tails remain visible but bounded: `and_resource_nmcts` completes
  64/64 with median 8.375 s and p95 76.838 s; `and_profile_resource_nmcts`
  delegates to the same high-dimensional guard.  The standalone one-layer FPRM
  linear-pair candidate has median 2.574 s and p95 30.760 s.  The tradeoff is
  higher mean peak ancilla: 3.05 versus 2.03 for FPRM-greedy and root-beam.

Additional scale check from `results/analysis_highdim_scale_resource.md` and
`results/runtime_highdim_scale_resource.md`:

- 32 random ANF functions at `n=15`, 9 methods, 288 result rows, 0 errors, and
  0 skips.
- Compared with FPRM-greedy, the guarded variants have 30 T-count wins, 0
  losses, and 2 ties; by weighted score they also have 30 wins, 0 losses, and
  2 ties, with a 5.73% mean score reduction.
- Compared with the standalone FPRM root-beam candidate, they have 29 T-count
  wins, 0 losses, and 3 ties; by weighted score they have 30 wins, 0 losses,
  and 2 ties, with a 5.28% mean score reduction.
- The one-extra-layer linear-pair refinement recursively searches both the
  quotient and rest branches when the subproblem has at most 900 terms.  Versus
  the one-layer linear-pair candidate, it has 29 weighted-score wins, 0 losses,
  and 3 ties, at mean peak ancilla 3.06 instead of 2.84.
- The width-three linear-parity ablation is dominated by the recursive pair
  candidate under the default weighted score: 0 wins, 29 losses, and 3 ties
  against the recursive pair method.
- Runtime remains finite at `n=15`: `and_resource_nmcts` completes 32/32 with
  median 16.514 s and p95 135.536 s; `and_profile_resource_nmcts` completes
  32/32 with median 14.684 s and p95 122.842 s.

Scope boundary: all costs are logical-level resource estimates.  The verifier
circuit is deterministic and classically checked, while the logical-AND cost
model accounts for low-T compute and Clifford/measurement-based uncompute.
No hardware mapping or connectivity constraints are included.
