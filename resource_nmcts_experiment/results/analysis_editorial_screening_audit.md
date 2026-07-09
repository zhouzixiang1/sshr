# Editorial Screening Audit

This audit checks that the editor and reviewer support package exposes scope, novelty, comparison, counterpoint, AI, scale, reproducibility, and author-gate boundaries.

## Status counts

- pass: 8

## Screening Matrix

| item | status | risk | evidence | supported decision | boundary |
|---|---|---|---|---|---|
| Logical-layer scope visible at first screening | pass | Editor may reject the manuscript as an overbroad hardware compiler claim. | files_missing=none; tokens=4/4; missing_tokens=none; manifest=results/manifest_claim_scope_lint.json::unresolved_count=0 | The manuscript can be sent to reviewers as a logical-layer oracle-synthesis paper. | Do not imply hardware routing, native-gate scheduling, noise modeling, or device execution. |
| Novelty and comparison route visible | pass | Editor may see the work as only an SSHR variant or as a weak-baseline comparison. | files_missing=none; tokens=4/4; missing_tokens=none; manifest=results/manifest_comparison_protocol_audit.json::needs_revision_count=0 | The screening package explains why SSHR is a baseline and why comparisons are layered. | The claim is not universal superiority over every synthesis method. |
| Counterpoint and negative-result visibility | pass | Reviewer may object that weighted-score wins hide CNOT, depth, or ancilla losses. | files_missing=none; tokens=4/4; missing_tokens=none; manifest=results/manifest_claim_scope_lint.json::unresolved_count=0 | Unfavorable metric evidence is visible before review rather than hidden in raw tables. | Weighted-score wins must stay separated from raw resource dominance. |
| AI and MCTS contribution bounded | pass | Reviewer may reject an overclaim that deep learning alone explains the gains. | files_missing=none; tokens=4/4; missing_tokens=none; manifest=results/manifest_search_control_baseline_audit.json::needs_revision_count=0 | The manuscript can claim neural/MCTS search-control support without overclaiming deep RL. | The largest gains remain tied to algebraic action space and guarded/Pareto selection. |
| Large-scale verification boundary visible | pass | Reviewer may object that n=20--40 rows are not exhaustive truth-table checks. | files_missing=none; tokens=4/4; missing_tokens=none; manifest=not_applicable | Large-scale evidence is framed as symbolic verification plus bounded truth-table bridges. | Do not claim exhaustive high-dimensional truth-table benchmarking. |
| Reproducibility path visible | pass | Editor may desk-reject if the manuscript cannot be audited from submitted artifacts. | files_missing=none; tokens=4/4; missing_tokens=none; manifest=results/manifest_citation_support_audit.json::needs_revision_count=0 | The submission package exposes a clear reviewer path from claims to files and scripts. | The lightweight rebuild verifies paper-facing outputs; raw sweeps remain heavier rerun tiers. |
| Author and venue gate explicit | pass | Submission may be blocked by missing declarations, anonymous-review policy, or archive links. | files_missing=none; tokens=4/4; missing_tokens=none; manifest=results/manifest_submission_metadata_closure_path.json::needs_revision_count=0 | The remaining nontechnical submission gate is explicit and private rather than implicit. | Author order, affiliations, funding, conflicts, venue choice, and archive links still require author input. |
| Editorial reading path present | pass | Editor may miss the comparison boundary if the package lacks a short triage route. | files_missing=none; tokens=4/4; missing_tokens=none; manifest=not_applicable | The support package gives editors a concise route to judge fit before full review. | This is a navigation aid, not an acceptance guarantee. |
