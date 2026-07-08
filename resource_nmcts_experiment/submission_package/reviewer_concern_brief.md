# Reviewer Concern Brief

This brief summarizes the main reviewer-facing risks and where the current manuscript addresses them.

## Is this only an SSHR variant?

No.  The method does not use SSHR parallelotope candidates.  It formulates logical-layer Boolean oracle synthesis as an ANF/FPRM resource search with neural/MCTS and guarded portfolio controls.  SSHR-H and SSHR-I are used as CNOT-oriented small-function baselines.

Manuscript anchors:
- Abstract
- Introduction contribution map
- Related-work positioning matrix
- Baseline claim matrix
- Baseline comparability audit

## Are the baselines fair?

The manuscript uses layered comparisons rather than a single universal leaderboard.  Direct ANF, ESOP, BDD/ABC, SSHR, ROS-style LUT, mockturtle, CirKit, RevKit CLI, and phase/Rz probes are assigned different claim roles.  Each row is bounded by task alignment, fairness controls, and residual abstraction risk.

Manuscript anchors:
- Experimental Design
- Baseline claim matrix
- Comparison evidence matrix
- Baseline comparability audit
- Raw multi-resource dominance table

## Does the method dominate every resource?

No.  The paper claims strong T-count and weighted-score advantages, not universal dominance.  It explicitly reports tradeoffs: SSHR remains a strong CNOT counterpoint, CirKit is often shallower, and RevKit CLI often uses fewer auxiliary lines.

Manuscript anchors:
- Abstract
- Traditional functions result
- External toolchain result
- Multi-resource tradeoff result
- Discussion

## Is the AI contribution overstated?

The manuscript separates the algebraic search-space contribution from learned-control effects.  Neural priors and learned gates are treated as bounded controls.  Limited diagnostics that do not improve quality or runtime are kept as limitations rather than headline claims.

Manuscript anchors:
- Search contribution decomposition
- Learned-control audit
- Sparse depth-frontier analysis
- Discussion

## Does the large-scale result rely only on symbolic checks?

Large rows use symbolic term-set and emitted-circuit verification.  Complete truth-table checks are used only for bridge slices because exhaustive truth tables scale exponentially.  The paper states this boundary explicitly.

Manuscript anchors:
- High-dimensional verification result
- Validation table
- Scaling resource audit
- Discussion

## Is the package reproducible?

The paper-facing package includes raw CSV files, summaries, manifests, generated LaTeX tables, generated figures, source data, local trained policy artifacts, tool adapters, and a rebuild script.  The archive manifest hashes stable payload groups and the readiness audit checks the compiled PDF separately.

Manuscript anchors:
- Compute and reproducibility audit
- Submission traceability audit
- Submission archive manifest
- Data and Code Availability

Remaining author-side item:
- Funding, acknowledgements, competing interests, author metadata, and final archive DOI or anonymous link must still be completed by the author before upload.
