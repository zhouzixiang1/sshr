# Author Declarations Template

This file collects author-specific statements that cannot be inferred from the code or experiment artifacts.  Complete these fields before journal upload.

For the structured intake path, run
`make_submission_metadata_from_answers.py --init-private-answers`, fill the
ignored `submission_metadata_answers.json`, then run
`make_submission_metadata_from_answers.py --write-private`.  The filled private
answer and metadata files are ignored by Git so private author metadata is not
committed accidentally.

When the JSON file is complete, the rebuild writes ignored private previews:
`generated_author_declarations.md`, `generated_availability_statements.md`,
`generated_cover_letter.md`, and `generated_submission_text.md`.  Review these
against the target venue submission system before upload.
The rebuild also runs `validate_submission_metadata.py` to check common format
and consistency issues without exposing private values in tracked files.
`analyze_anonymous_review_readiness.py` separately flags whether the selected
venue requires an anonymous manuscript copy or anonymous artifact links.
Set `target_venue.anonymous_review_required` before upload.  The current main
manuscript remains author-labeled; if the selected venue requires double-blind
review, use the generated anonymous draft and replace repository-relative
availability links with anonymous review links.

Use `AUTHOR_INPUT_REQUIRED.md` as the final author-side checklist before
upload.

Use `target_venue_brief.md` to pick the venue-specific declaration style before
filling author contributions, AI assistance, and policy fields.

## Manuscript

- Title: Resource-Constrained Neural Monte Carlo Tree Search for Quantum Boolean Oracle Synthesis
- Current manuscript source: `paper_latex/resource_nmcts_submission_v1.tex`
- Current manuscript PDF: `paper_latex/resource_nmcts_submission_v1.pdf`
- Scope boundary: logical-layer quantum Boolean oracle synthesis only; no hardware mapping, routing, native-gate scheduling, noise model, or magic-state-factory resource estimate.

## Authors and Affiliations

AUTHOR INPUT REQUIRED:
- Author list in journal order:
- ORCID IDs:
- Affiliations:
- Corresponding author:
- Author email addresses:

## Author Contributions

AUTHOR INPUT REQUIRED.  A possible CRediT-style structure is:

- Conceptualization:
- Methodology:
- Software:
- Validation:
- Formal analysis:
- Investigation:
- Data curation:
- Writing - original draft:
- Writing - review and editing:
- Visualization:
- Supervision:
- Funding acquisition:

## Funding

AUTHOR INPUT REQUIRED:

State all funding sources, grant numbers, and institutional support.  If there was no external funding, write the exact no-funding statement required by the target venue.

## Acknowledgements

AUTHOR INPUT REQUIRED:

State any technical assistance, institutional support, computing support, or individuals who should be acknowledged.  If there are no acknowledgements, use the exact no-acknowledgement wording required by the target venue.

## Competing Interests

AUTHOR INPUT REQUIRED:

State whether any author has financial or non-financial competing interests.  If none exist, use the exact no-competing-interest wording required by the target venue.

## Ethics Approval

Not applicable unless the target venue requires a formal statement.  The current work uses synthetic/generated Boolean functions, logic-synthesis toolchains, and local computational experiments; it does not involve human participants, animal subjects, clinical data, or private personal data.

## Data Availability

AUTHOR INPUT REQUIRED:

Replace repository-relative paths with a permanent archive link or anonymous review link before submission if required.  The manuscript currently points to `resource_nmcts_experiment/`, including raw CSV files, summary CSV files, manifest JSON files, generated LaTeX tables, generated figures, source data, and the compiled PDF.

## Code Availability

AUTHOR INPUT REQUIRED:

Provide the final repository URL, commit hash, license, environment notes, and any anonymous review link required by the venue.  The current local rebuild command is:

```bash
./rebuild_submission_package.sh
```

The current generated upload payload is:

```text
submission_package/dist/resource_nmcts_submission_payload.tar.gz
submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256
```

## AI-Assisted Writing or Coding Statement

AUTHOR INPUT REQUIRED:

Use the target venue's required wording.  If disclosure is required, state which parts used AI assistance and confirm that the authors verified all scientific content, citations, code, and outputs.

## Preprint and Prior Submission

AUTHOR INPUT REQUIRED:

- Preprint server and DOI/URL, if any:
- Prior submission history, if any:
- Related manuscripts under review, if any:

## Permissions

The current figures and tables are generated from local scripts and experiment artifacts.  Confirm before submission that no third-party figure, table, or long copyrighted excerpt has been included without permission.
