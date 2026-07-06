# Resource-Constrained Neural MCTS for Quantum Boolean Oracle Synthesis

Working title:

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

## Scope

This experiment stays at the logical oracle-synthesis layer.  It does not map
the resulting circuit to a physical coupling graph.  The method may compare
against SSHR, but it does not use SSHR parallelotopes or SSHR's candidate space.

## Literature Position

Recent AI-based quantum synthesis work shows that learning-guided search is a
credible synthesis method, but most existing systems target generic unitary
synthesis, routing, Pauli scheduling, or post-synthesis rewriting rather than
Boolean oracle construction.

- Rietsch et al. use Gumbel AlphaZero for Clifford+T unitary synthesis.
- Kremer et al. use RL for Clifford+T / Clifford+CS non-Clifford-count
  optimization.
- MonteQ uses MCTS for Hamiltonian-simulation Pauli ordering and supports
  logical and hardware-aware synthesis.
- RL-ZX uses PPO and graph neural networks for ZX-calculus circuit rewriting.

Traditional Boolean oracle synthesis instead optimizes symbolic resources:
XAG/multiplicative-complexity methods target T-count and ancilla, LUT/ROS
methods target resource-constrained oracle construction, and SSHR is a strong
CNOT-oriented small Boolean-function baseline.

This project targets the open space between them: AI-guided search over
symbolic Boolean construction plans, with explicit multi-resource objectives.

## Current Contribution

The current strongest method is `and_resource_nmcts`, a resource-adaptive
portfolio around a guarded affine-preconditioned neural MCTS solver.  The
experimental `and_profile_resource_nmcts` variant adds profile-specialized
candidate generation.  Together they add five ingredients to fixed-coordinate
ANF factoring:

1. **Logical-AND resource accounting.** Temporary conjunctions are charged as
   low-T logical ANDs, with T-free Clifford/measurement uncomputation in the
   objective.  The emitted verifier circuit remains deterministic for classical
   correctness checking; this is a logic-level cost model, not a hardware
   mapping model.
2. **Affine Boolean preconditioning.** The solver searches invertible linear
   changes of input coordinates before ANF/FPRM factoring.  This exposes
   decompositions that are invisible in the raw ANF basis.
3. **MCTS guard.** The affine plan is compared against a fixed-coordinate MCTS
   plan under the same resource score.  On completed pairs this makes the
   affine method score-nondegrading relative to the fixed-coordinate MCTS
   baseline, while retaining large wins when affine coordinates reveal stronger
   factorizations.
4. **Resource portfolio guard.** The full method compares internally generated
   direct ANF, FPRM/greedy, budgeted affine-neural, dimension-guarded
   fixed-coordinate MCTS, and small-$n$ ESOP cube-beam candidates under the
   active weighted objective.  SSHR is not part of this portfolio; it remains
   an external baseline.  The guard is intentionally budgeted for larger
   functions rather than a full dominance certificate over every internal
   solver.
5. **Profile-aware candidate generation.** The profile variant adds
   T-aggressive, CNOT/depth-oriented, and ancilla-tight candidate configurations
   on small functions.  For larger random-ANF instances it switches to a cheap
   direct/FPRM guard; for `n > 12`, that guard uses a direct-cost polarity
   screen plus a bounded root-child beam baseline and a CNOT-only pairwise
   XOR-factor candidate.

## Representation

For a Boolean function `f`, compute its algebraic normal form (ANF):

```text
f(x) = XOR_{m in M} prod_{i in m} x_i
```

The direct ANF oracle applies one MCT to the output for each monomial.  This is
correct but often resource-heavy.  The search state is a finite set of residual
monomial masks `M` under a prefix of already-computed controls.

## Action Space

An action chooses a common factor `S` that appears in at least two residual
monomials:

```text
M = {S*r_1, S*r_2, ...} XOR R
```

The synthesis plan is:

1. compute `S` into a fresh clean ancilla;
2. synthesize residual monomials `{r_1, r_2, ...}` using that ancilla as an
   additional prefix control;
3. uncompute `S`;
4. synthesize the rest `R`.

This is a logical compute/uncompute version of XAG-style factoring.  It can
reduce T-count, CNOT count, gate count, and depth at the cost of explicit
ancilla.  The action is independent of SSHR.

## Affine Preconditioning

Before the factor search, `and_affine_nmcts` considers invertible row-encoded
linear transforms `y = Bx` and synthesizes `h(y) = f(B^{-1}y)`.  The final
oracle wraps the synthesized body with CNOT networks that implement and undo
`B`.  The transform search currently uses:

- identity;
- star-like XOR transforms;
- single-CNOT transforms;
- random short CNOT sequences for larger budgets.

Candidate transforms are ranked by a fast FPRM/greedy plan.  For `n <= 6`, the
top candidates are refined by neural MCTS.  For larger instances, affine search
uses conservative budgets and term-count guards to avoid densifying sparse ANF
instances into intractable transformed forms.  This staged policy is important:
low-dimensional truth-table functions benefit from strong search, while large
random ANF functions require predictable runtime.

## Search

The main solver is a recursive PUCT/MCTS over factorization actions.  It uses:

- action candidates from frequent residual variable subsets;
- a heuristic prior based on immediate weighted resource gain;
- an optional neural action scorer trained from synthetic ANF states;
- a greedy value fallback for unexplored subproblems;
- an explicit limit on live factor ancilla.

The objective is a weighted resource score:

```text
score = wt*T + wc*CNOT + wd*depth + wg*logical_gates + wa*peak_ancilla
```

Experiments sweep resource weights and ancilla limits to produce Pareto-style
tradeoffs rather than a single CNOT-only table.

## Baselines

The first implementation compares against:

- direct ANF synthesis;
- logical-AND direct ANF synthesis;
- fixed-coordinate logical-AND MCTS factoring;
- affine-preconditioned logical-AND neural MCTS;
- ESOP cube beam search;
- time-limited weighted ESOP MILP;
- SSHR-H as a CNOT-oriented reference for small `n`.

`export_benchmarks.py` exports every preset to PLA, BLIF `.names`, and
truth-table JSON with a manifest, so the exact same Boolean functions can be
fed to external XAG/ROS/LUT or mockturtle-style flows.  External tool results
are still future work, but the benchmark exchange format is now reproducible
and independent of the Python synthesis harness.

## Evaluation

Metrics:

- T-count;
- CNOT count;
- logical gate count;
- sequential logical/decomposition depth estimate;
- explicit clean factor ancilla;
- total peak ancilla including MCT-decomposition helpers;
- runtime;
- classical simulation correctness.

Datasets:

- exhaustive small functions for `n=3`;
- random truth-table functions for `n=4..6`;
- random sparse/dense ANF functions for `n=6..12` in the paper-facing core
  benchmark, with isolated `n=14` stress and `n=15` scaling presets kept as
  runtime-boundary targets;
- structured oracles such as parity, majority, threshold, mux, adders, and
  multipliers.

## Current Evidence

The current paper-facing run is:

```bash
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
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_scale_resource --model models/action_scorer_rollout_logical_and.pt --workers 6 --checkpoint-every 8 --resume --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset highdim_scale_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset highdim_scale_resource
```

It covers 322 functions and 1610 method/function rows.  The main results are:

- `and_affine_nmcts` is correct on all 322 functions.
- Compared with direct ANF, it reduces mean T-count by 61.83% and mean
  composite score by 58.12%.
- Compared with logical-AND direct ANF, it reduces mean T-count by 40.12% and
  mean score by 37.77%.
- Compared with fixed-coordinate logical-AND MCTS, it has 161 T-count wins,
  160 ties, and 0 losses over 321 completed baseline pairs; mean T-count
  reduction is 16.18% and mean score reduction is 14.82%.
- Compared with SSHR-H on supported functions, it has 171 wins, 5 ties, and 1
  loss in T-count; mean T-count reduction is 43.89%.
- Fixed-coordinate MCTS times out on `anf_n12_10` at 600 s, while the affine
  method completes that function within the experiment budget.

The `ablation_affine` run uses the same 322-function suite and adds two method
variants:

- `and_affine_greedy`: affine transform search plus FPRM/greedy factoring, with
  no neural refinement and no fixed-coordinate MCTS guard.
- `and_affine_no_guard`: affine transform search plus neural refinement, with
  no fixed-coordinate MCTS guard.

This run isolates the mechanism:

- Affine-greedy alone reduces mean T-count by 60.92% relative to direct ANF,
  so the affine coordinate search is the dominant contributor.
- Neural refinement gives 65 score wins, 257 ties, and 0 score losses over
  affine-greedy.
- The MCTS guard gives 88 score wins, 234 ties, and 0 score losses over
  affine-no-guard.
- The full method gives 153 score wins, 169 ties, and 0 score losses over
  affine-greedy.

The runtime/resource table in `results/runtime_ablation_affine.md` adds the
cost side of the argument:

- Affine-greedy is the fast strong setting: 322/322 completed, median runtime
  0.033 s, maximum runtime 1.825 s.
- Full `and_affine_nmcts` is slower because it runs the fixed-coordinate MCTS
  guard: 322/322 completed, median runtime 0.609 s, p95 runtime 13.670 s, and
  maximum runtime 300.025 s.
- Fixed-coordinate MCTS has one timeout, while the full affine method completes
  that same function.
- Among non-SSHR methods over the all-suite completed rows, full
  `and_affine_nmcts` has the best mean T-count and composite score; SSHR-H has
  lower CNOT-oriented costs only on its supported `n <= 6` subset.

The main weakness is CNOT/depth relative to SSHR-H: the affine method wins
T-count strongly but often spends more CNOTs and depth against SSHR's
CNOT-oriented circuits.  The paper should frame the contribution as
resource-constrained low-T logical Boolean synthesis rather than CNOT-only
optimization.

The `traditional_resource` run adds a stronger small-function comparison
against traditional Boolean/ESOP baselines and the full Resource-NMCTS portfolio
guard.  It covers 177 functions with `n <= 6`, 8 methods, 1416 method/function
rows, 0 errors, and 0 skips.  The added baselines are an ESOP cube-beam search
and a time-limited weighted ESOP MILP over candidate cubes, both evaluated under
the same logical-AND resource accounting where applicable.

Main `traditional_resource` evidence:

- Mean T-count / composite score: `and_resource_nmcts` 45.74 / 55.21,
  `and_affine_nmcts` 45.88 / 55.37, fixed MCTS 62.06 / 73.09, ESOP cube beam
  71.32 / 83.82, ESOP MILP 83.59 / 96.73, and SSHR-H 81.04 / 88.19.
- `and_resource_nmcts` beats `and_affine_nmcts` in score on 8 functions, loses
  on 0, and ties on 169.
- `and_resource_nmcts` beats ESOP cube beam in T-count on 172 functions, loses
  on 0, ties on 5, and reduces mean T-count by 34.72%.
- `and_resource_nmcts` beats ESOP MILP in T-count on 162 functions, loses on 1,
  ties on 14, and reduces mean T-count by 29.50%.
- The same comparisons show mean composite-score reductions of 32.28% versus
  ESOP cube beam and 26.95% versus ESOP MILP.
- SSHR-H remains better in mean CNOT count and often depth on the small
  supported subset.  This is a useful limitation, not a contradiction of the
  low-T/resource-score claim.

The `resource_sweep` stress test checks whether the method remains competitive
under different resource objectives.  It uses 47 functions with `n <= 6`, four
profiles (T-heavy, balanced, CNOT-depth-heavy, and ancilla-tight), six methods,
plus a profile-specialized Resource-NMCTS variant, and 1316
method/profile/function rows.  There are 0 errors and 0 skips.

Main `resource_sweep` evidence:

- `and_profile_resource_nmcts` is best-or-tied on 42/47 functions under T-heavy
  weights, 42/47 under balanced weights, 41/47 under CNOT-depth-heavy weights,
  and 42/47 under ancilla-tight weights.
- Compared with `and_resource_nmcts`, it has score wins/losses/ties of 5/0/42,
  6/0/41, 7/0/40, and 4/0/43 across the four profiles.
- Compared with `and_affine_nmcts`, it has score wins/losses/ties of 5/0/42,
  6/0/41, 8/0/39, and 7/0/40 across the four profiles.
- Compared with fixed-coordinate MCTS, it has score wins/losses/ties of
  35/0/12, 35/0/12, 35/0/12, and 35/0/12.
- The mean Profile-Resource-NMCTS vector changes modestly across profiles
  (mean T 40.34--42.38, mean CNOT 82.43--84.79, mean depth 86.72--88.72).
  This is evidence of robustness and nondegrading internal portfolio selection,
  not yet evidence of strong profile-sensitive Pareto optimization.  A
  submission version should add stronger resource-profile-specific candidate
  generation if it wants to claim adaptive resource tradeoffs.

The `large_resource_core` run is the current large-scale paper-facing
benchmark.  It covers 330 functions through `n <= 12`, six methods, and 1980
method/function rows.  The stable run used process-isolated hard timeouts on an
Apple M4 Pro with 14 logical CPU cores and 24 GB memory.  There are 5 timeout
rows, all from fixed-coordinate MCTS on `n=12` random ANF functions;
`and_resource_nmcts` and `and_profile_resource_nmcts` complete all 330
functions.

Main `large_resource_core` evidence:

- Compared with direct ANF, `and_resource_nmcts` has 291 T-count wins, 0
  losses, and 39 ties, with a 60.37% mean T-count reduction and a 56.84% mean
  composite-score reduction.
- Compared with logical-AND direct ANF, it has 286 T-count wins, 0 losses, and
  44 ties, with a 37.25% mean T-count reduction and a 35.21% mean score
  reduction.
- Compared with fixed-coordinate MCTS on completed pairs, it has 139 T-count
  wins, 15 losses, and 171 ties, with an 11.41% mean score reduction.  Because
  fixed-coordinate MCTS timed out on five hard rows, its completed-row mean is
  censored and should not be interpreted as an all-suite dominance result.
- Compared with standalone `and_affine_nmcts`, the budgeted Resource-NMCTS
  portfolio has 29 score wins, 16 score losses, and 285 ties, with a 0.20% mean
  score reduction.  The large-scale claim is scalable resource-aware selection,
  not strict nondegradation against the full affine solver under tighter
  high-dimensional budgets.
- Runtime for `and_resource_nmcts` is 330/330 completed, median 1.311 s, p95
  58.857 s, and max 300.848 s.  Fixed-coordinate MCTS completes 325/330 and
  has five timeouts.
- `and_profile_resource_nmcts` completes 330/330 and reduces the large-core
  runtime tail (p95 25.682 s, max 67.609 s), but its cheap high-dimensional
  guard has a higher mean score (286.54) than `and_resource_nmcts` (273.72).
  This should be framed as a profile-aware/tail-control extension, not the
  score winner on large random ANF functions.

The `highdim_resource` stress test isolates the next scale point rather than
mixing it into the structured suite.  It covers 64 random ANF functions at
`n=14`, eight methods, and 512 method/function rows, with 0 errors and 0 skips
after the high-dimensional guard was tightened to avoid fixed-coordinate MCTS
tails and to add a bounded FPRM linear-pair candidate.

Main `highdim_resource` evidence:

- `and_resource_nmcts` and `and_profile_resource_nmcts` complete all 64
  functions under the high-dimensional bounded guard.
- Compared with direct ANF, both guarded methods have 61 T-count wins, 0
  losses, and 3 ties, with a 55.60% mean T-count reduction and a 52.27% mean
  composite-score reduction.
- Compared with logical-AND direct ANF, both have 61 T-count wins, 0 losses,
  and 3 ties, with a 30.41% mean T-count reduction and a 28.64% mean score
  reduction.
- Compared with FPRM-greedy, both guarded methods have 60 T-count wins, 0
  losses, and 4 ties; by weighted score they also have 60 wins, 0 losses, and
  4 ties.  The bounded linear-pair candidate factors repeated pairs
  `x_i m xor x_j m` as `(x_i xor x_j) m`, using only CNOTs to compute and
  uncompute the temporary linear control.
- Runtime remains bounded but nontrivial: `and_resource_nmcts` has median
  runtime 3.633 s, p95 34.982 s, and max 47.462 s; the profile variant has
  median 3.638 s, p95 35.313 s, and max 47.256 s.  The standalone FPRM
  linear-pair candidate has median 2.574 s, p95 30.760 s, and max 41.593 s.
  The gain uses more workspace: mean peak ancilla rises from 2.03 to 2.94.

The `highdim_scale_resource` run extends the same high-dimensional guard to
32 random ANF functions at `n=15`.  It contains 224 method/function rows across
seven methods, with 0 errors and 0 skips.  The guarded variants again select
the FPRM linear-pair candidate on every function.  Compared with FPRM-greedy,
they have 30 T-count wins, 0 losses, and 2 ties; by weighted score they also
have 30 wins, 0 losses, and 2 ties, with a 3.52% mean score reduction.
Compared with FPRM root beam, they have 29 score wins, 0 losses, and 3 ties,
with a 3.06% mean score reduction.  The scale check is slower but finite:
`and_resource_nmcts` has median runtime 6.938 s and p95 102.123 s, while
`and_profile_resource_nmcts` has median runtime 6.854 s and p95 97.086 s.
