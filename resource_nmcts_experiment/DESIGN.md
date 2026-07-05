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

The current strongest method is `and_affine_nmcts`, a guarded affine-preconditioned
neural MCTS solver.  It adds three ingredients to fixed-coordinate ANF factoring:

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
- SSHR-H as a CNOT-oriented reference for small `n`.

Later baselines should add XAG/ROS/LUT tooling if external binaries become
available.

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
- random sparse/dense ANF functions for `n=6..12`;
- structured oracles such as parity, majority, threshold, mux, adders, and
  multipliers.

## Current Evidence

The current paper-facing run is:

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset evidence_affine --model models/action_scorer_rollout_logical_and.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset evidence_affine
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

The main weakness is CNOT/depth relative to SSHR-H: the affine method wins
T-count strongly but often spends more CNOTs and depth against SSHR's
CNOT-oriented circuits.  The paper should frame the contribution as
resource-constrained low-T logical Boolean synthesis rather than CNOT-only
optimization.
