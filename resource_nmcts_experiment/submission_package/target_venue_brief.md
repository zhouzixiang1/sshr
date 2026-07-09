# Target Venue Brief

Snapshot date: 2026-07-09

This brief narrows the venue choice for the current manuscript:
Resource-Constrained Neural Monte Carlo Tree Search for Quantum Boolean Oracle
Synthesis. It is a planning aid only. The final target venue, manuscript type,
anonymous-review status, APC constraints, and required policy checks must still
be copied into `submission_metadata.json` before upload.

Machine-checkable support files:

- Target venue decision audit: `results/analysis_target_venue_decision_audit.md`
- Summary CSV: `results/summary_target_venue_decision_audit.csv`
- Manifest: `results/manifest_target_venue_decision_audit.json`
- ACM/TQC format smoke audit: `results/analysis_target_venue_format_smoke.md`
- ACM/TQC review draft: `paper_latex/resource_nmcts_submission_acm_tqc.tex`
- recommended_first_choice: ACM Transactions on Quantum Computing

## Current Manuscript Fit

The manuscript is strongest when framed as:

- logical-layer quantum Boolean oracle synthesis;
- resource-constrained search over ANF/FPRM term sets;
- neural/MCTS/search-control assistance with explicit guards;
- broad comparison against ESOP, SSHR, ABC/BDD, ROS-style LUT, mockturtle,
  CirKit, RevKit CLI, and phase/Rz probes;
- T-count and weighted-score improvements with CNOT, depth, and ancilla
  trade-offs reported separately.

The manuscript should not be sent to a venue expecting hardware mapping,
native-gate scheduling, physical noise models, or experimental quantum-device
execution unless those sections are added later.

## Shortlist

| order | venue | short name | fit | fit_score | why it fits | main risk | pre-upload action | source_url |
|---:|---|---|---|---:|---|---|---|---|
| 1 | ACM Transactions on Quantum Computing | ACM TQC | strong | 5 | TQC covers quantum computing theory/practice, including design automation, compilers, programming systems, and AI applications. | Requires ACM-style submission preparation and likely a sharper computer-science/compilation framing. | Convert the manuscript to the ACM article template, add ACM-style metadata/keywords if required, and keep artifact links ready. | https://acm-stoc.org/stoc2020/acm-journals/tqc-new-announcement-06-2020.pdf |
| 2 | Quantum | Quantum | strong | 5 | Quantum accepts quantum-science manuscripts through an arXiv preprint, asks that main results and assumptions be clear in the first pages, and requires author contribution plus AI-use disclosure. | Editors may expect broad quantum-science significance, not only an engineering comparison table. | Post or cross-list the preprint to `quant-ph`, add a concise first-pages contribution statement, and fill author-contribution/AI-disclosure text. | https://quantum-journal.org/instructions/authors/ |
| 3 | IEEE Transactions on Quantum Engineering | IEEE TQE | moderate-to-strong | 4 | TQE covers engineering applications of quantum phenomena, including quantum computation, information, software, and hardware. | It is open access with APC; the manuscript should emphasize quantum-software engineering value and reproducibility. | Convert to IEEE style, confirm APC/funding policy, and keep logical-layer scope explicit. | https://tqe.ieee.org/ |
| 4 | IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems | IEEE TCAD | moderate | 3 | TCAD covers CAD algorithms, methods, tools, and logical design/synthesis. The paper's logic-synthesis and toolchain-comparison angle is relevant. | Quantum-specific contribution may be seen as outside the main IC/system-design audience unless framed as EDA for quantum computing. | Emphasize design automation, synthesis algorithms, verification, and tool-flow reproducibility; de-emphasize broad quantum-algorithm claims. | https://ieee-ceda.org/publications/tcad/tcad-paper-submissions |
| 5 | Quantum Science and Technology | QST | selective/high-risk | 2 | QST seeks important results across quantum science and technology and values rigorous, well-motivated original science. | QST warns that incremental steps are usually insufficient; a logical-layer synthesis paper must show broader lasting impact. | Use only if the cover framing argues why oracle synthesis materially affects quantum algorithms/compilation beyond this benchmark suite. | https://publishingsupport.iopscience.iop.org/journals/quantum-science-technology/ |

## Recommended Order

1. ACM TQC if the priority is a computer-science/quantum-compilation journal
   and a template conversion is acceptable.  A generated anonymous ACM/TQC
   review-format smoke draft is available, but final ACM metadata and archive
   links still require author input.
2. Quantum if an arXiv-first workflow is acceptable and the manuscript can be
   tightened around broadly understandable quantum-oracle contributions.
3. IEEE TQE if open access and quantum-engineering framing are acceptable.
4. TCAD if the paper is reframed as a CAD/logical-synthesis contribution.
5. QST only after strengthening the broad-impact motivation.

## Venue-Specific Metadata Still Needed

Fill these fields in `submission_metadata.json` after the venue is chosen:

- `target_venue.name`
- `target_venue.manuscript_type`
- `target_venue.formatting_policy_checked`
- `target_venue.reference_style_checked`
- `target_venue.word_limit_checked`
- `target_venue.supplementary_material_policy_checked`
- `target_venue.ai_disclosure_policy_checked`
- `target_venue.anonymous_review_required`
- author contribution and AI-assistance wording required by the selected venue
- final archive DOI, repository URL, commit hash, and license wording

## Policy Gate Checklist

Before upload, record the venue decision in the private
`submission_metadata.json` file and check:

- `target_venue.name`
- `target_venue.manuscript_type`
- `target_venue.formatting_policy_checked`
- `target_venue.reference_style_checked`
- `target_venue.word_limit_checked`
- `target_venue.supplementary_material_policy_checked`
- `target_venue.ai_disclosure_policy_checked`
- `target_venue.anonymous_review_required`

## Source Pointers

- Quantum author guidelines: https://quantum-journal.org/instructions/authors/
- ACM TQC scope announcement: https://acm-stoc.org/stoc2020/acm-journals/tqc-new-announcement-06-2020.pdf
- IEEE TQE journal information: https://tqe.ieee.org/
- IEEE TCAD submission instructions: https://ieee-ceda.org/publications/tcad/tcad-paper-submissions
- QST author guidelines: https://publishingsupport.iopscience.iop.org/journals/quantum-science-technology/
