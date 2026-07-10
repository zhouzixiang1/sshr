# Editor Screening Brief

This one-page brief is intended to help an editor or associate editor decide
whether the manuscript's comparison scope and claim boundary are appropriate
for external review.

## Manuscript Positioning

Title: "Resource-Constrained Neural Monte Carlo Tree Search with
Reinforcement-Learned Budget Control for Quantum Boolean Oracle Synthesis"

The manuscript studies logical-layer synthesis of quantum Boolean bit-flip
oracles.  It does not propose a hardware-mapped quantum compiler.  The method
formulates synthesis as a resource-constrained search over ANF/FPRM term sets
and uses neural action priors, Monte Carlo tree search, Boolean-ring actions,
Pareto archives, frontier controllers, and baseline-preserving guards to choose
verified logical oracle circuits.  A contextual-bandit fitted-Q controller then
chooses whether the quality gain justifies invoking additional Pareto search.

## Why the Comparison Is Meaningful

The comparison is deliberately layered rather than presented as a universal
leaderboard.

1. Primary same-task baselines: direct ANF, AND-direct ANF, ESOP beam/MILP,
   BDD/ABC, and SSHR-H/SSHR-I are evaluated on matched small Boolean functions
   under the same logical resource model.  This layer supports the main claim:
   the method improves T-count and weighted logical resource score for the
   target oracle-synthesis problem.
2. External toolchain probes: ROS-style LUT, mockturtle KLUT-to-XAG,
   Caterpillar API, CirKit AIG/MC, RevKit CLI exact-oracle, and RevKit phase/Rz
   probes test whether the advantage persists beyond self-written baselines.
   These comparisons support robustness of the logical-layer result, not
   hardware-mapped optimality.
3. Internal search ablations: no-MCTS, learned-prior-off, guard-off,
   Pareto-archive-off, depth-frontier, sparse-frontier, and rank-diverse
   pruning runs separate the contribution of the search controller from the
   algebraic candidate space and the resource score.  A disjoint
   train/validation/test budget-policy experiment separately evaluates the
   reinforcement-learned Pareto-invocation decision.

The manuscript then reports a separate counterpoint and claim-boundary audit:
SSHR is treated as the CNOT counterpoint, Caterpillar API as an
implementation-family CNOT-pressure counterpoint, CirKit as the depth
counterpoint, RevKit CLI as the auxiliary-line counterpoint, and the
learned-prior rows as bounded evidence for search control rather than for a
deep-learning-only explanation.

## Main Evidence to Check

- Baseline claim matrix: maps each comparison family to the claim it can and
  cannot support.
- Comparison evidence matrix: consolidates verified row counts and paired score
  outcomes across internal baselines, external probes, RevKit, phase/Rz, and
  high-dimensional bridge checks.
- Baseline comparability audit: records task alignment, fairness controls,
  residual risks, and usable claims for every baseline family.
- Novelty/comparison scorecard: answers the compact reviewer questions
  "what is this compared with, why is that meaningful, and what claim remains
  outside the evidence?"
- Comparison protocol audit: cross-checks that every comparison layer has a
  role, evidence, comparability boundary, counterpoint coverage where relevant,
  and manuscript anchors.
- Counterpoint and claim-boundary audit: lists the strongest unfavorable metric
  evidence for SSHR, Caterpillar API, CirKit, RevKit CLI, learned priors, and
  large-scale verification, next to the favorable evidence that keeps each comparison
  meaningful.
- Paired statistical evidence: reports paired wins/losses/ties, mean and median
  relative score changes, and exact sign-test evidence.
- Multi-resource tradeoff audit: reports raw T/CNOT/depth/ancilla Pareto
  dominance separately from the weighted score.
- MCTS budget-policy test: reports the fitted-Q controller's disjoint split,
  per-function decisions, paired bootstrap intervals, quality retention,
  Pareto-call reduction, and all six logical resource metrics.
- Ultra-scale resource-profile audit: separates the $n=48,56,64$ stress slice
  into score, T-count, CNOT count, depth, ancilla, T-depth proxy, auxiliary
  lifetime, and planning-time means.
- Claim-scope lint: automatically checks that hardware-mapping, universal
  dominance, and external-tool-reproduction language is locally guarded by the
  stated logical-layer scope.
- Reproducibility, traceability, archive, and payload manifests: connect
  manuscript claims to scripts, CSV files, tables, figures, manifests, trained
  local policy artifacts, and the uploadable payload archive.

## Claims That Are Supported

- A logical-layer Resource-NMCTS workflow for Boolean oracle synthesis.
- Strong T-count and weighted-score improvements on matched small functions
  against algebraic, ESOP, SSHR, ABC/BDD, and external probe baselines.
- Evidence that the advantage is not limited to a single self-written baseline.
- Explicit counterpoint evidence showing where SSHR, Caterpillar API, CirKit,
  and RevKit remain strong under individual resource metrics.
- High-dimensional symbolic verification through the $n=48,56,64$ stress
  slice, with a separate resource profile, plus bridge-truth-table verification
  of emitted logical circuits within the stated scope.
- Bounded learned-control benefits and planning-time savings from frontier and
  guard policies.
- A reinforcement-learned quality-effort controller that, on 160 independent
  test functions, improves mean score by 3.48% over base Resource-NMCTS while
  reducing conservative measured search time by 13.13% relative to always-on
  Pareto and retaining 94.90% of its score gain.

## Claims That Are Not Made

- No claim of hardware mapping, routing, native-gate scheduling, noise-aware
  compilation, or magic-state-factory accounting.
- No claim of universal CNOT, depth, ancilla, or line-count dominance.
- No claim that SSHR is obsolete; it remains a strong CNOT-oriented small-scale
  counterpoint.
- No claim that RevKit `oracle_synth` is a finished Clifford+T comparison; it
  is treated as a phase/Rz lower-bound and sensitivity probe.
- No claim that high-dimensional exhaustive truth-table benchmarking is
  feasible beyond the bridge slices reported in the manuscript; the
  $n=48,56,64$ rows are symbolic stress evidence.
- No claim that the fitted-Q controller is end-to-end deep RL or that it
  dominates always-on Pareto search in score; its measured role is optional
  search-budget allocation.

## Recommended Editorial Reading Path

1. Read the abstract, contribution-to-evidence map, and first-pages scope
   paragraph to confirm the logical-layer boundary.
2. Inspect the baseline claim matrix and baseline comparability audit before
   judging whether the comparisons are fair, then read the counterpoint and
   claim-boundary audit to see which resource metrics remain unfavorable.
3. Use the paired statistical and multi-resource tradeoff tables together:
   the manuscript claims strong T-count and weighted-score gains, while
   reporting CNOT/depth/ancilla tradeoffs instead of hiding them.
4. Check the Data and Code Availability, traceability audit, and payload
   manifest to confirm that the paper-facing results are reproducible from the
   submitted artifacts.
