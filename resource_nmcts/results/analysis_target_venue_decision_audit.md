# Target Venue Decision Audit

Checked date: 2026-07-09

This audit makes the venue decision support packet source-backed and machine-checkable.  It does not choose the final journal for the author and does not fill private metadata.

## Status counts

- pass: 5

## Recommended first choice

- recommended_first_choice: ACM Transactions on Quantum Computing
- rationale: Best fit when framed as quantum-computing design automation, oracle compilation, and resource-aware logical synthesis.

| order | venue | fit | fit score | pre-upload action | policy gate | source_url | status |
|---:|---|---|---:|---|---|---|---|
| 1 | ACM TQC | strong | 5 | Use ACM's current primary article template in single-column review format, add ACM journal metadata/keywords if required, and keep artifact links ready. | Confirm ACM primary-article template version, approved LaTeX packages, article type, references, artifact policy, and any author/AI disclosure requirements. | https://www.acm.org/publications/authors/submissions | pass |
| 2 | Quantum | strong | 5 | Post or cross-list the preprint to quant-ph, sharpen the first-pages contribution summary, and prepare mandatory author-contribution plus AI-use statements. | Confirm arXiv/quant-ph submission route, author contribution statement, AI-use disclosure, and optional template expectations. | https://quantum-journal.org/instructions/authors/ | pass |
| 3 | IEEE TQE | moderate-to-strong | 4 | Convert to IEEE style, confirm the open-access APC/funding path, and keep the logical-layer software-engineering boundary explicit. | Confirm IEEE template, article type, open-access/APC path, reference style, and disclosure requirements. | https://tqe.ieee.org/submission-process/ | pass |
| 4 | IEEE TCAD | moderate | 3 | Condense to TCAD page limits and emphasize synthesis algorithms, verification, tool reproducibility, and EDA relevance. | Confirm IEEE two-column format, regular-paper page limit, abstract length, index terms, keywords, and reference style. | https://ieee-ceda.org/publications/tcad/tcad-paper-submissions | pass |
| 5 | QST | selective/high-risk | 2 | Strengthen the broad-impact motivation, choose Paper versus Letter only after checking article-type expectations, and align declarations with IOP requirements. | Confirm article type, TeX/LaTeX submission route, peer-review model, author contribution/funding/conflict fields, and supplementary data policy. | https://publishingsupport.iopscience.iop.org/journals/quantum-science-technology/ | pass |

## Required target-venue metadata fields

- target_venue.name
- target_venue.manuscript_type
- target_venue.formatting_policy_checked
- target_venue.reference_style_checked
- target_venue.word_limit_checked
- target_venue.supplementary_material_policy_checked
- target_venue.ai_disclosure_policy_checked
- target_venue.anonymous_review_required

## Boundary

- This audit supports venue selection and policy checks only.
- Final venue choice, manuscript type, anonymous-review status, archive links, author declarations, APC/funding constraints, and AI-disclosure wording remain author input.
