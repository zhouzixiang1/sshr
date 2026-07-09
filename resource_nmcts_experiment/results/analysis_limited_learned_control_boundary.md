# Limited Learned-Control Boundary Audit

This audit checks that runtime-negative or weak learned-control diagnostics are retained as claim-boundary evidence rather than promoted as headline AI improvements.

## Status counts

- pass: 6

| check | evidence | boundary | status |
|---|---|---|---|
| Limited component inventory | limited components are Bit-flip learned prior, Boolean neural guard; class counts bounded=6, limited=2, promoted=4. | Only the generic bit-flip learned prior and Boolean neural guard are classified as limited. | pass |
| Limited rows retain negative cost context | Bit-flip learned prior: -0.15% quality; Boolean neural guard: -0.12% quality; Bit-flip learned prior: +48.05% runtime; Boolean neural guard: +94.49% runtime. | Small quality deltas with positive runtime overhead cannot be cited as runtime or headline wins. | pass |
| Limited rows are not promoted by class or role | promotions=none; roles: limited quality signal, not runtime claim; limited quality guard, not runtime claim. | The learned-control audit must keep these components out of promoted or bounded headline evidence. | pass |
| Manuscript exposes the limited boundary | missing_tokens=none. | The paper-facing text must say why limited diagnostics are not promoted. | pass |
| Support packet answers AI-overclaim risk | missing_tokens=none. | Reviewer-facing support must route AI/MCTS attribution questions to bounded-control evidence. | pass |
| Neural/MCTS title remains calibrated | neural_mcts_table_anchor_present=True. | The title can use neural MCTS only as a bounded ranking, gating, and budget-allocation framework. | pass |
