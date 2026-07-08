# Submission Checklist

Use this checklist immediately before uploading the manuscript.

## Required Author Input

- AUTHOR INPUT REQUIRED: Work through `submission_package/AUTHOR_INPUT_REQUIRED.md` before uploading.
- AUTHOR INPUT REQUIRED: Choose the target venue using `submission_package/target_venue_brief.md` as a planning aid, then copy the final choice into `submission_package/submission_metadata.json`.
- AUTHOR INPUT REQUIRED: Copy `submission_package/submission_metadata_template.json` to `submission_package/submission_metadata.json` and fill every `AUTHOR INPUT REQUIRED` value.
- AUTHOR INPUT REQUIRED: Confirm author order, affiliations, ORCID IDs, and corresponding author details.
- AUTHOR INPUT REQUIRED: Complete funding, acknowledgements, author contributions, and competing-interest statements.
- AUTHOR INPUT REQUIRED: Replace repository-relative availability wording with the target venue's required archive DOI, repository URL, or anonymous review link.
- AUTHOR INPUT REQUIRED: Confirm whether the venue requires an AI-assistance disclosure.
- AUTHOR INPUT REQUIRED: Confirm target journal formatting, reference style, manuscript type, word limit, and supplementary-material policy.

## Manuscript Files

- Submission package guide: `submission_package/README.md`
- Main source: `paper_latex/resource_nmcts_submission_v1.tex`
- Main PDF: `paper_latex/resource_nmcts_submission_v1.pdf`
- Bibliography: `paper_latex/references.bib`
- Generated tables: `paper_latex/tables/*.tex`
- Generated figures: `paper_latex/figures/submission_v36/`
- Figure source data: `paper_latex/figures/submission_v36/source_data/*.csv`
- Uploadable payload archive: `submission_package/dist/resource_nmcts_submission_payload.tar.gz`
- Payload archive checksum: `submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256`

## Reproducibility Files

- Rebuild script: `rebuild_submission_package.sh`
- Fast verifier script: `verify_submission_package.sh`
- Readiness audit: `results/analysis_submission_readiness_audit.md`
- Author input packet: `submission_package/AUTHOR_INPUT_REQUIRED.md`
- Terminal package verifier: `results/analysis_submission_package_verifier.md`
- Claim-scope lint: `results/analysis_claim_scope_lint.md`
- Metadata audit: `results/analysis_submission_metadata_audit.md`
- Private submission text preview audit: `results/analysis_submission_text_preview.md`
- Goal-completion audit: `results/analysis_goal_completion_audit.md`
- Raw rerun registry: `results/analysis_artifact_rerun_registry.md`
- Artifact reproduction guide: `submission_package/artifact_reproduction_guide.md`
- Editor screening brief: `submission_package/editor_screening_brief.md`
- Target venue brief: `submission_package/target_venue_brief.md`
- Structured metadata template: `submission_package/submission_metadata_template.json`
- Traceability audit: `results/analysis_submission_traceability_audit.md`
- Archive manifest: `results/analysis_submission_archive_manifest.md`
- Payload archive manifest: `results/analysis_submission_payload_archive.md`
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
  analyze_goal_completion_audit.py \
  analyze_submission_archive_manifest.py \
  analyze_claim_scope_lint.py \
  analyze_submission_metadata_audit.py \
  analyze_submission_readiness_audit.py \
  analyze_submission_traceability_audit.py \
  make_submission_text_preview.py
./rebuild_submission_package.sh
./verify_submission_package.sh
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_submission_package_verifier.py
rg -n "Overfull|Underfull|undefined|Undefined|Warning|Error|LaTeX Warning|Rerun" \
  paper_latex/resource_nmcts_submission_v1.log
```

Expected current state:

- Archive manifest: all payload groups complete.
- Payload archive: tarball, SHA256 sidecar, CSV, Markdown, and JSON manifest are present.
- Claim-scope lint: all required boundaries pass and no unguarded overclaim remains.
- Metadata audit: all author- and venue-specific fields are enumerated before upload, and any filled `submission_metadata.json` is checked.
- Private submission text preview: public audit exists; generated private Markdown previews remain ignored by Git and excluded from the payload archive.
- Goal-completion audit: all research/package requirements pass and only author/venue gates remain open.
- Traceability audit: all claim families complete.
- Readiness audit: all paper/package checks pass except author-specific declarations.
- Terminal package verifier: all read-only package invariants pass.
- LaTeX warning status: only the existing `\showhyphens` package warning should remain.

## Claim Boundary Check

- Do not claim hardware mapping, routing, native-gate scheduling, or noise-aware compilation.
- Do not claim universal dominance over SSHR, CirKit, RevKit, or all CNOT/depth/ancilla metrics.
- Keep RevKit `oracle_synth` framed as a phase/Rz lower-bound or sensitivity probe, not a final Clifford+T comparison.
- Keep learned-control claims bounded: neural controls contribute measurable guarded or pruning gains, but the largest gains come from the algebraic action space and guarded portfolio search.

## Upload Order

1. Upload the main PDF and source archive required by the venue.
2. Upload `submission_package/dist/resource_nmcts_submission_payload.tar.gz` or a venue-specific source archive assembled from it.
3. Upload generated figure files and source data separately if the venue requires them outside the payload archive.
4. Paste author declarations into the submission system.
5. Paste generated private preview text from `submission_package/generated_*.md` after reviewing venue wording, or paste the manually edited declarations if the venue requires a different format.
6. Paste the cover letter and reviewer suggestions if requested.
7. Review the generated proof for table placement and figure readability before final approval.
