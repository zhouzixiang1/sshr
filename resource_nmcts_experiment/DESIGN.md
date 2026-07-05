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
- greedy resource-aware ANF factoring;
- untrained/heuristic MCTS;
- neural-prior MCTS;
- greedy ESOP from the existing repository;
- SSHR-H / SSHR-Beam as CNOT-oriented references for small `n`.

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

