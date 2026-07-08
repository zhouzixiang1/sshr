# Submission Checklist

Use this checklist immediately before uploading the manuscript.

## Required Author Input

- AUTHOR INPUT REQUIRED: Confirm author order, affiliations, ORCID IDs, and corresponding author details.
- AUTHOR INPUT REQUIRED: Complete funding, acknowledgements, author contributions, and competing-interest statements.
- AUTHOR INPUT REQUIRED: Replace repository-relative availability wording with the target venue's required archive DOI, repository URL, or anonymous review link.
- AUTHOR INPUT REQUIRED: Confirm whether the venue requires an AI-assistance disclosure.
- AUTHOR INPUT REQUIRED: Confirm target journal formatting, reference style, manuscript type, word limit, and supplementary-material policy.

## Manuscript Files

- Main source: `paper_latex/resource_nmcts_submission_v1.tex`
- Main PDF: `paper_latex/resource_nmcts_submission_v1.pdf`
- Bibliography: `paper_latex/references.bib`
- Generated tables: `paper_latex/tables/*.tex`
- Generated figures: `paper_latex/figures/submission_v36/`
- Figure source data: `paper_latex/figures/submission_v36/source_data/*.csv`

## Reproducibility Files

- Rebuild script: `rebuild_submission_package.sh`
- Readiness audit: `results/analysis_submission_readiness_audit.md`
- Traceability audit: `results/analysis_submission_traceability_audit.md`
- Archive manifest: `results/analysis_submission_archive_manifest.md`
- Reproducibility audit: `results/analysis_reproducibility_audit.md`
- Raw data: `results/raw_*.csv`
- Summary data: `results/summary_*.csv`
- Run manifests: `results/manifest_*.json`
- Trained local policy artifacts: `models/`
- External adapter source: `tools/`

## Verification Commands

Run these from `resource_nmcts_experiment/`:

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python -m py_compile \
  analyze_submission_archive_manifest.py \
  analyze_submission_readiness_audit.py \
  analyze_submission_traceability_audit.py
./rebuild_submission_package.sh
rg -n "Overfull|Underfull|undefined|Undefined|Warning|Error|LaTeX Warning|Rerun" \
  paper_latex/resource_nmcts_submission_v1.log
```

Expected current state:

- Archive manifest: all payload groups complete.
- Traceability audit: all claim families complete.
- Readiness audit: all paper/package checks pass except author-specific declarations.
- LaTeX warning status: only the existing `\showhyphens` package warning should remain.

## Claim Boundary Check

- Do not claim hardware mapping, routing, native-gate scheduling, or noise-aware compilation.
- Do not claim universal dominance over SSHR, CirKit, RevKit, or all CNOT/depth/ancilla metrics.
- Keep RevKit `oracle_synth` framed as a phase/Rz lower-bound or sensitivity probe, not a final Clifford+T comparison.
- Keep learned-control claims bounded: neural controls contribute measurable guarded or pruning gains, but the largest gains come from the algebraic action space and guarded portfolio search.

## Upload Order

1. Upload the main PDF and source archive required by the venue.
2. Upload generated figure files and source data if requested separately.
3. Upload or link the reproducibility archive.
4. Paste author declarations into the submission system.
5. Paste the cover letter and reviewer suggestions if requested.
6. Review the generated proof for table placement and figure readability before final approval.
