# Resource-Constrained Neural MCTS for Quantum Boolean Oracle Synthesis

Working title:

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

## Scope

This experiment stays at the logical oracle-synthesis layer.  It does not map
the resulting circuit to a physical coupling graph.  The method may compare
against SSHR, but it does not use SSHR parallelotopes or SSHR's candidate space.

## Literature Position

Recent AI-based synthesis work shows that learning-guided search is a credible
synthesis method, but the existing work sits next to this problem rather than
on top of it.

- ShortCircuit uses AlphaZero-style policy/value search for classical AIG
  generation from truth tables; it covers the generic "AI for Boolean circuit
  generation" claim, so this project must be positioned around quantum oracle
  resources rather than only around RL+MCTS.
- Rietsch et al. use Gumbel AlphaZero for Clifford+T unitary synthesis.
- Kremer et al. use RL for Clifford+T / Clifford+CS non-Clifford-count
  optimization.
- MonteQ uses MCTS for Hamiltonian-simulation Pauli ordering and supports
  logical and hardware-aware synthesis.
- RL-ZX uses PPO and graph neural networks for ZX-calculus circuit rewriting.

Traditional Boolean oracle synthesis instead optimizes symbolic resources:
XAG/multiplicative-complexity methods target T-count and ancilla, LUT/ROS
methods target resource-constrained oracle construction, BDD synthesis provides
a scalable reversible-logic baseline, and SSHR is a strong CNOT-oriented
small-function baseline built from parallelotope structure.

This project targets the open space between them: AI-guided search over
symbolic Boolean oracle construction plans, with explicit T/CNOT/depth/gate/
ancilla objectives and without using SSHR candidates internally.

## Current Contribution

The current strongest small-function resource method is
`and_pareto_resource_nmcts`, a non-dominated archive built on top of the
resource-adaptive `and_resource_nmcts` portfolio and the
`and_profile_resource_nmcts` profile variant.  The high-dimensional stress
experiments still use the bounded Resource/Profile guards.  Together these
methods add six ingredients to fixed-coordinate ANF factoring:

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
   screen plus a bounded root-child beam baseline and a one-extra-layer
   recursive CNOT-only pairwise XOR-factor candidate over both quotient and
   rest branches when the subproblem has at most 900 terms.  The `n=15` preset
   also reports a standalone width-three linear-parity ablation, but the
   portfolio does not use it because the recursive pair candidate dominates it
   under the default weighted objective.
6. **Pareto archive selection.** The Pareto variant evaluates child searches
   under active, T-sparse, CNOT/depth-heavy, ancilla-tight, and gate-count-aware
   internal scoring weights, removes candidates dominated in T-count, CNOT
   count, depth, gate count, and peak ancilla, then selects the surviving
   candidate with the active profile score.  On `n <= 6` it also adds a ranked
   polarity archive that exhaustively screens all FPRM polarities under greedy,
   root-child-beam, and CNOT-only linear-pair factorizations before contributing
   the best scored candidate to the Pareto pool.  This turns the small-function
   profile layer from a budget-only portfolio into an explicit local Pareto
   frontier approximation.

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

The learned scorer is used as an additive action-prior term rather than as a
standalone decision oracle.  A no-prior rerun on the `traditional_resource`
slice keeps the same heuristic PUCT/action prior and removes only the learned
scorer; this isolates the neural contribution without changing the symbolic
candidate generator.

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
fed to external AIG/XAG/LUT/ROS or mockturtle-style flows.  External tool
results are now partially covered by `run_external_baselines.py`: the first
exact pilot consumes the exported `traditional_resource` manifest and runs
SSHR-H, CNOT-optimized SSHR-I, and T-optimized SSHR-I from the separate
`src/sshr` implementation on the `n <= 4` subset.  A time-limited extension
covers the full `n <= 6` traditional slice with an 8 s Gurobi budget per
SSHR-I call, a Berkeley ABC AIG backend optimizes the same exported BLIF files
before bit-parallel full truth-table verification and Bennett-style resource
estimation, a Berkeley ABC XAG/GIA backend uses `&get; &st -m -L 1` plus
`&ps -m -x` before verified BLIF scoring with a logical XAG cost model, an ABC
LUT backend maps with `strash; if -K 4` before verified mapped-BLIF scoring, and
an ABC ESOP backend runs `&exorcism -q`, verifies the emitted ESOP-PLA, and
scores the resulting XOR-of-cubes oracle with the logical-AND cube model.  A
reduced ordered BDD baseline tries several deterministic variable orders,
verifies the decision diagram, and scores a Shannon-network compute/uncompute
estimate.  The ABC-AIG, ABC-XAG, ABC-LUT, and BDD paths now also cover the
isolated `n=14`, `n=15`, and `n=16` high-dimensional random-ANF presets;
ABC-ESOP remains a small-function external baseline because complex
high-dimensional ESOP minimization times out.  ROS/mockturtle adapters are
still future work, but the benchmark exchange format and SSHR/ABC/LUT/BDD
comparison paths are now reproducible and independent of the synthesis harness.

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
  benchmark, with isolated `n=14` stress, `n=15` scaling, `n=16`
  ultra-scale, and `n=18` mega-scale presets kept as runtime-boundary targets;
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
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset traditional_resource --only-methods and_affine_nmcts,and_resource_nmcts,and_pareto_resource_nmcts --model /tmp/nonexistent_model.pt --out-dir /tmp/resource_nmcts_traditional_no_model --workers 10 --checkpoint-every 50
cp /tmp/resource_nmcts_traditional_no_model/raw_traditional_resource.csv results/raw_traditional_resource_no_prior.csv
cp /tmp/resource_nmcts_traditional_no_model/summary_traditional_resource.csv results/summary_traditional_resource_no_prior.csv
cp /tmp/resource_nmcts_traditional_no_model/manifest_traditional_resource.json results/manifest_traditional_resource_no_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_neural_prior_ablation.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_resource_sweep.py --model models/action_scorer_rollout_logical_and.pt --workers 10
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_resource_sweep.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset large_resource_core --model models/action_scorer_rollout_logical_and.pt --resume --workers 6 --checkpoint-every 1 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset large_resource_core
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset large_resource_core
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_scale_resource --model models/action_scorer_rollout_logical_and.pt --workers 6 --checkpoint-every 8 --resume --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset highdim_scale_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset highdim_scale_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset ultra_highdim_resource --model models/action_scorer_rollout_logical_and.pt --workers 1 --checkpoint-every 8 --resume
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset ultra_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset ultra_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset mega_highdim_resource --model models/action_scorer_rollout_logical_and.pt --workers 4 --checkpoint-every 5
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset mega_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset mega_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset ultra_highdim_resource --formats blif,truth --out-dir benchmark_exports/ultra_highdim_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/ultra_highdim_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag,external_abc_lut,external_bdd --min-n 16 --max-n 16 --max-abc-n 16 --max-xag-n 16 --max-lut-n 16 --max-bdd-n 16 --bdd-orders 8 --timeout 45 --workers 8 --out results/raw_external_ultra_highdim_resource.csv --summary results/summary_external_ultra_highdim_resource.csv --run-manifest results/manifest_external_ultra_highdim_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_ultra_highdim_resource.csv --internal-csv results/raw_ultra_highdim_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_linear_pair,and_fprm_root_beam,direct_anf,and_direct_anf --out results/analysis_external_ultra_highdim_resource.md
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset mega_highdim_resource --formats blif,truth --out-dir benchmark_exports/mega_highdim_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/mega_highdim_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag,external_abc_lut,external_bdd --min-n 18 --max-n 18 --max-abc-n 18 --max-xag-n 18 --max-lut-n 18 --max-bdd-n 18 --bdd-orders 8 --timeout 90 --workers 8 --out results/raw_external_mega_highdim_resource.csv --summary results/summary_external_mega_highdim_resource.csv --run-manifest results/manifest_external_mega_highdim_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_mega_highdim_resource.csv --internal-csv results/raw_mega_highdim_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_root_beam,direct_anf,and_direct_anf --out results/analysis_external_mega_highdim_resource.md
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

The learned-prior ablation in `results/analysis_neural_prior_ablation.md`
compares the model-backed run with a no-prior rerun on all 177
`traditional_resource` functions for `and_affine_nmcts`, `and_resource_nmcts`,
and `and_pareto_resource_nmcts`.  It has 1062 usable rows, 0 errors, and 0
skips.  Learned-prior score wins/losses/ties are 42/0/135, 41/0/136, and
29/0/148, with mean score reductions of 1.47%, 1.34%, and 0.78%.  Runtime is
higher for the learned-prior rows on this small-function slice, so the current
claim is a quality improvement at nonzero inference cost.

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
against traditional Boolean/ESOP baselines and the Resource/Pareto-NMCTS
guards.  It covers 177 functions with `n <= 6`, 10 methods, 1770 method/function
rows, 0 errors, and 0 skips.  The added baselines are an ESOP cube-beam search
and a time-limited weighted ESOP MILP over candidate cubes, both evaluated under
the same logical-AND resource accounting where applicable.

Main `traditional_resource` evidence:

- Mean T-count / composite score: `and_pareto_resource_nmcts` 40.77 / 49.83,
  `and_fprm_polarity_archive` 43.01 / 52.50,
  `and_resource_nmcts` 45.74 / 55.21,
  `and_affine_nmcts` 45.88 / 55.37, fixed MCTS 62.06 / 73.09, ESOP cube beam
  71.32 / 83.82, ESOP MILP 83.59 / 96.73, and SSHR-H 81.04 / 88.19.
- `and_pareto_resource_nmcts` beats `and_resource_nmcts` in score on 74
  functions, loses on 0, and ties on 103, reducing mean score by 4.59%.
- `and_pareto_resource_nmcts` beats ESOP cube beam in score on 174 functions,
  loses on 0, ties on 3, and reduces mean score by 35.86%.
- `and_pareto_resource_nmcts` beats ESOP MILP in score on 167 functions, loses
  on 3, ties on 7, and reduces mean score by 29.61%.
- Against SSHR-H, `and_pareto_resource_nmcts` has 173 T-count wins, no losses,
  4 ties, and 173/4/0 score wins/losses/ties.
- SSHR-H remains better in mean CNOT count and often depth on the small
  supported subset.  This is a useful limitation, not a contradiction of the
  low-T/resource-score claim.

The exported exact SSHR-I pilot uses the same `traditional_resource` functions
but goes through `export_benchmarks.py` and a separate baseline runner.  It
covers all 72 functions with `n <= 4`, three external methods, and 216 external
rows with 0 errors/skips:

- Against CNOT-optimized SSHR-I, `and_resource_nmcts` has 65 T-count wins, 0
  losses, and 7 ties; by weighted score it has 69 wins, 3 losses, and 0 ties,
  with a 26.45% mean score reduction.
- Against T-optimized SSHR-I, `and_resource_nmcts` again has 65/0/7 T-count
  wins/losses/ties and a 26.21% mean score reduction.
- In both exact comparisons, `and_resource_nmcts` usually spends more CNOTs
  (65/72 worse against CNOT-opt SSHR-I and 62/72 worse against T-opt SSHR-I).
  This validates the low-T/resource-score framing and rules out a CNOT-only
  claim.

The time-limited exported SSHR-I plus ABC/LUT/BDD extension covers all 177
functions with `n <= 6`, eight external methods, and 1416 external rows with 0
errors/skips.  The SSHR-I rows use an 8 s per-call Gurobi budget, the
ABC-AIG rows use Berkeley ABC 1.01 built from
`bcfdf592289a408cd67ec19260f8a60a37b085b6` with BLIF truth-table
verification, the ABC-XAG rows use verified ABC GIA/XOR-aware BLIF, the ABC-LUT
rows use verified mapped BLIF after `if -K 4`, the BDD rows use verified ROBDDs,
and the ABC-ESOP rows use verified `&exorcism -q` ESOP-PLA:

- Against ABC-AIG, `and_resource_nmcts` has 170/2/5 T-count wins/losses/ties,
  wins all 177 CNOT, peak-ancilla, and weighted-score comparisons, and reduces
  mean weighted score by 54.52%.  ABC-AIG has a lower depth estimate on
  126/177 functions, so it remains a useful depth-oriented foil.
- Against ABC-XAG, `and_resource_nmcts` has 176/0/1 T-count wins/losses/ties,
  wins all 177 peak-ancilla and weighted-score comparisons, reduces mean
  weighted score by 63.23%, and reduces mean CNOT by 35.53%.  ABC-XAG has a
  lower depth estimate on 144/177 functions.
- Against ABC-LUT, `and_resource_nmcts` has 175/0/2 T-count wins/losses/ties,
  wins all 177 CNOT, depth, peak-ancilla, and weighted-score comparisons, and
  reduces mean weighted score by 76.41%.  This is a verified mapped-LUT network
  baseline rather than a complete reversible LUT-mapping toolchain.
- Against BDD, `and_resource_nmcts` wins all 177 T-count, CNOT, depth,
  peak-ancilla, and weighted-score comparisons, reducing mean weighted score
  by 67.15%.
- Against ABC-ESOP, `and_resource_nmcts` has 144/19/14 T-count
  wins/losses/ties and 147/24/6 weighted-score wins/losses/ties, reducing mean
  weighted score by 19.88%.  This adds a standard external XOR-of-products
  optimizer to the comparison boundary.
- Against CNOT-optimized SSHR-I, `and_resource_nmcts` has 164 T-count wins, 3
  losses, and 10 ties; by weighted score it has 168 wins, 9 losses, and 0 ties,
  with a 27.92% mean score reduction.
- Against T-optimized SSHR-I, it has 166/1/10 T-count wins/losses/ties, with a
  26.25% mean score reduction.
- The CNOT disadvantage is stronger on the full slice: `and_resource_nmcts` is
  worse on 168/177 CNOT comparisons against CNOT-opt SSHR-I and on 163/177
  against T-opt SSHR-I.

The high-dimensional exported ABC AIG/XAG/LUT plus BDD extension covers the
isolated `n=14`, `n=15`, `n=16`, and `n=18` random-ANF stress presets:

- `results/analysis_external_highdim_resource.md`: 64 exported `n=14`
  functions, 256/256 correct ABC-AIG/ABC-XAG/ABC-LUT/BDD rows, 0 errors/skips.
  `and_resource_nmcts` and `and_profile_resource_nmcts` beat all four
  baselines on all T-count, CNOT, peak-ancilla, and weighted-score
  comparisons, with mean score reductions of 94.13% against AIG and 95.48%
  against XAG, 97.44% against LUT, and 93.24% against BDD.  ABC-AIG and ABC-XAG
  each have a lower estimated depth on 50/64 functions; ABC-LUT and BDD do not
  under the sequential local-LUT/Shannon-network estimates.
- `results/analysis_external_highdim_scale_resource.md`: 32 exported `n=15`
  functions, 128/128 correct ABC-AIG/ABC-XAG/ABC-LUT/BDD rows, 0 errors/skips.
  The guarded methods again win all T-count, CNOT, peak-ancilla, and weighted-score
  comparisons, with mean score reductions of 94.59% against AIG, 96.33%
  against XAG, 97.76% against LUT, and 94.75% against BDD.  ABC-AIG has a lower
  estimated depth on 25/32 functions and ABC-XAG on 26/32 functions; ABC-LUT and
  BDD are deeper under the current sequential estimates.
- `results/analysis_external_ultra_highdim_resource.md`: 24 exported `n=16`
  functions, 96/96 correct ABC-AIG/ABC-XAG/ABC-LUT/BDD rows, 0 errors/skips.
  The guarded methods again win all T-count, CNOT, peak-ancilla, and
  weighted-score comparisons, with mean score reductions of 97.29% against
  AIG, 97.88% against XAG, 99.00% against LUT, and 96.81% against BDD.
  ABC-AIG and ABC-XAG each have a lower estimated depth on 22/24 functions;
  ABC-LUT and BDD are deeper under the current sequential estimates.
- `results/analysis_external_mega_highdim_resource.md`: 12 exported `n=18`
  functions, 48/48 correct ABC-AIG/ABC-XAG/ABC-LUT/BDD rows, 0 errors/skips.
  The guarded methods again win all T-count, CNOT, peak-ancilla, and
  weighted-score comparisons, with mean score reductions of 98.76% against
  AIG, 98.98% against XAG, 99.66% against LUT, and 98.19% against BDD.
  ABC-AIG has a lower estimated depth on 10/12 functions and ABC-XAG on 11/12
  functions; ABC-LUT and BDD are deeper under the current sequential estimates.

The `resource_sweep` stress test checks whether the method remains competitive
under different resource objectives.  It uses 47 functions with `n <= 6`, four
profiles (T-heavy, balanced, CNOT-depth-heavy, and ancilla-tight), nine
methods including Polarity archive, Profile-Resource-NMCTS, and
Pareto-Resource-NMCTS, and 1692 method/profile/function rows.  There are
0 errors and 0 skips.

Main `resource_sweep` evidence:

- `and_pareto_resource_nmcts` is best-or-tied on 44/47 functions under T-heavy
  weights, 44/47 under balanced weights, 42/47 under CNOT-depth-heavy weights,
  and 43/47 under ancilla-tight weights.
- Compared with `and_profile_resource_nmcts`, it has score wins/losses/ties of
  19/0/28, 19/0/28, 21/0/26, and 15/0/32 across the four profiles.
- Mean score reductions versus Profile-Resource-NMCTS are 5.56%, 4.93%,
  4.85%, and 2.51%.  Versus Resource-NMCTS they are 6.23%, 5.60%, 5.63%, and
  3.02%.
- The mean Pareto-Resource-NMCTS vector changes with the active profile: mean T
  is 35.91 under T-heavy/balanced/CNOT-depth and 39.74 under ancilla-tight,
  while mean peak ancilla drops from 1.87--1.94 to 1.62 under ancilla-tight.
  This is direct evidence for profile-sensitive Pareto-style candidate
  generation on the small-function slice.

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
tails and to add a bounded recursive FPRM linear-pair candidate.

Main `highdim_resource` evidence:

- `and_resource_nmcts` and `and_profile_resource_nmcts` complete all 64
  functions under the high-dimensional bounded guard.
- Compared with direct ANF, both guarded methods have 61 T-count wins, 0
  losses, and 3 ties, with a 57.42% mean T-count reduction and a 54.03% mean
  composite-score reduction.
- Compared with logical-AND direct ANF, both have 61 T-count wins, 0 losses,
  and 3 ties, with a 32.74% mean T-count reduction and a 30.86% mean score
  reduction.
- Compared with FPRM-greedy, both guarded methods have 60 T-count wins, 0
  losses, and 4 ties; by weighted score they also have 60 wins, 0 losses, and
  4 ties, with a 6.25% mean score reduction.  Against the one-layer linear-pair
  candidate, the recursive guard has 53 T-count wins, 0 losses, and 11 ties.
  The bounded recursive linear-pair candidate factors repeated pairs
  `x_i m xor x_j m` as `(x_i xor x_j) m`, using only CNOTs to compute and
  uncompute the temporary linear control.
- Runtime remains bounded but nontrivial: `and_resource_nmcts` has median
  runtime 8.375 s, p95 76.838 s, and max 113.164 s; the profile variant
  delegates to the same high-dimensional guard.  The standalone one-layer FPRM
  linear-pair candidate has median 2.574 s, p95 30.760 s, and max 41.593 s.
  The gain uses more workspace: mean peak ancilla rises from 2.03 to 3.05.

The `highdim_scale_resource` run extends the same high-dimensional guard to
32 random ANF functions at `n=15`.  It contains 288 method/function rows across
nine methods, with 0 errors and 0 skips.  The guarded variants select the
bounded recursive linear-pair candidate.  Compared with FPRM-greedy, they have
30 T-count wins, 0 losses, and 2 ties; by weighted score they also have 30
wins, 0 losses, and 2 ties, with a 5.73% mean score reduction.
Compared with FPRM root beam, they have 30 score wins, 0 losses, and 2 ties,
with a 5.28% mean score reduction.  The recursive linear-pair refinement
improves the one-layer linear-pair candidate in 29 score cases, ties in 3, and
has 0 score losses, while mean peak ancilla rises from 2.84 to 3.06.  The
standalone width-three linear-parity ablation is dominated by the recursive
pair method under the default objective.  The scale check is slower but finite:
`and_resource_nmcts` has median runtime 16.514 s and p95 135.536 s, while
`and_profile_resource_nmcts` has median runtime 14.684 s and p95 122.842 s.

The `ultra_highdim_resource` run is an additional scale check at `n=16`.  It
contains 24 random ANF functions, six methods, and 144 method/function rows
with 0 errors/skips.  The ultra-scale guard switches Resource/Profile to the
one-layer FPRM linear-pair candidate rather than the recursive `n=15` branch,
so both guarded variants match `and_fprm_linear_pair` on all 24 functions.
Compared with direct ANF, they have 23 T-count wins, 0 losses, and 1 tie, with
a 62.08% mean T-count reduction and a 59.52% mean score reduction.  Compared
with logical-AND direct ANF, they have 23 weighted-score wins, 0 losses, and
1 tie, with a 31.68% mean score reduction.  Compared with FPRM root beam, they
have 22 weighted-score wins, 0 losses, and 2 ties, with a 1.88% mean score
reduction.  Runtime remains finite: `and_resource_nmcts` has median runtime
17.537 s and p95 59.132 s, while `and_profile_resource_nmcts` has median
runtime 17.566 s and p95 58.479 s.  The associated Möbius/zeta-transform
implementation in `anf_utils.py` removes the avoidable per-assignment monomial
scan and makes larger ANF-derived truth tables practical to generate.

The `mega_highdim_resource` run is the current runtime-boundary check at
`n=18`.  It contains 12 random ANF functions, five methods, and 60
method/function rows with 0 errors/skips.  At this scale the high-dimensional
guard switches Resource/Profile to bounded FPRM root-beam rather than
linear-pair screening, because the pairwise-linear screen develops a
multi-minute long tail without improving the sampled costs.  The guarded
variants match `and_fprm_root_beam` on all 12 functions.  Compared with direct
ANF, they have 10 T-count wins, 0 losses, and 2 ties, with a 55.40% mean
T-count reduction and a 53.08% mean score reduction.  Compared with
logical-AND direct ANF, they have 10 score wins, 0 losses, and 2 ties, with a
27.43% mean score reduction.  Runtime is finite but much slower than direct
construction: `and_resource_nmcts` has median runtime 65.995 s and p95
143.671 s, while `and_profile_resource_nmcts` has median runtime 66.841 s and
p95 149.190 s.  This result should be framed as scale and verification evidence,
not as a new neural-portfolio separation.
