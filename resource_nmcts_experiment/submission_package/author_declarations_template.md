# Author Declarations Template

This file collects author-specific statements that cannot be inferred from the code or experiment artifacts.  Complete these fields before journal upload.

For a single structured intake path, copy `submission_metadata_template.json` to
`submission_metadata.json`, fill every `AUTHOR INPUT REQUIRED` value, and rerun
`./rebuild_submission_package.sh`.  The filled JSON file is ignored by Git so
private author metadata is not committed accidentally.

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
