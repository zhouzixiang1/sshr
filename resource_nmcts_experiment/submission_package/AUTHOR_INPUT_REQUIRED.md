# Author Input Required

This packet lists the remaining author- and venue-specific fields that cannot be inferred from code, experiments, or generated artifacts.

Do not fill private author metadata into tracked files unless the target venue requires it.  The preferred private intake path is:

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_starter.py --write-private
$EDITOR submission_package/submission_metadata.json
./rebuild_submission_package.sh
./verify_submission_package.sh
```

Use `cp submission_package/submission_metadata_template.json submission_package/submission_metadata.json`
instead if you prefer a completely blank template.  `submission_metadata.json`
is ignored by Git so private author metadata is not committed accidentally.
When the metadata file is complete, the rebuild also creates ignored private previews:
`generated_author_declarations.md`, `generated_availability_statements.md`,
`generated_cover_letter.md`, and `generated_submission_text.md`.
Before generating final upload text, `validate_submission_metadata.py` checks common
format issues without writing private values to tracked files.

Before editing venue-specific claims, cover-letter language, or reviewer replies, read
`submission_package/COMPARISON_HANDOFF_zh.md`.  It gives the Chinese author-facing
answer to what the method is compared against, why the comparison set is meaningful,
and which stronger claims must not be made.
For a compact matrix of baseline roles, supported claims, excluded claims, and
evidence entry points, use `submission_package/COMPARISON_SIGNIFICANCE_MATRIX_zh.md`.

If you want a Chinese field-by-field intake checklist, use
`submission_package/AUTHOR_METADATA_QUESTIONNAIRE_zh.md` before filling
`submission_package/submission_metadata.json`.  The questionnaire maps each
human answer to the corresponding JSON path and does not contain private values.
For the shortest possible reply format, use
`submission_package/AUTHOR_MINIMAL_RESPONSE_FORM_zh.md`; it compresses the same
remaining author/venue gate into ten answer groups.

## Current Gate

- metadata rows needing author input: 12
- metadata validator rows needing author input: 1
- metadata validator rows needing revision: 0
- anonymous-review rows needing author input: 3
- anonymous-review rows needing revision: 0
- research, experiment, manuscript, archive, payload, and verifier checks are handled by the generated audits.
- final goal closure should not be marked complete until these fields are filled and the rebuild/verifier pass again.

## Required Actions

1. **Structured metadata intake file**
   - source: `submission_package/submission_metadata_template.json`
   - required fields: target_venue.name; target_venue.manuscript_type; target_venue.formatting_policy_checked; target_venue.reference_style_checked; target_venue.word_limit_checked; target_venue.supplementary_material_policy_checked; target_venue.ai_disclosure_policy_checked; target_venue.anonymous_review_required; authors; corresponding_author.name; corresponding_author.email; corresponding_author.affiliation; corresponding_author.postal_address; author_contributions.conceptualization; author_contributions.methodology; author_contributions.software; author_contributions.validation; author_contributions.formal_analysis; author_contributions.investigation; author_contributions.data_curation; author_contributions.writing_original_draft; author_contributions.writing_review_editing; author_contributions.visualization; author_contributions.supervision; author_contributions.funding_acquisition; funding.statement; funding.grant_numbers; acknowledgements.statement; competing_interests.statement; data_availability.archive_link_or_doi; data_availability.anonymous_review_link; data_availability.access_restrictions; data_availability.statement; code_availability.repository_url; code_availability.commit_hash; code_availability.license; code_availability.environment_notes; code_availability.anonymous_review_link; code_availability.statement; ai_assistance.statement; preprint_and_prior_submission.preprint_url_or_doi; preprint_and_prior_submission.prior_submission_history; preprint_and_prior_submission.related_manuscripts; preprint_and_prior_submission.statement; cover_letter.target_editor; cover_letter.suggested_reviewers; cover_letter.excluded_reviewers; cover_letter.editorial_routing_statement; permissions.third_party_material_confirmed; permissions.statement
   - evidence: Template exists; copy it to submission_package/submission_metadata.json and fill every AUTHOR INPUT REQUIRED value.
   - next action: Create `submission_package/submission_metadata.json` from the template, fill it, then rerun the rebuild script.

2. **Author identity and affiliations**
   - source: `submission_package/author_declarations_template.md`
   - required fields: author order; ORCID IDs; affiliations; corresponding author; emails
   - evidence: 1 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/author_declarations_template.md.
   - next action: Fill the author list, affiliations, ORCIDs, corresponding author, and email addresses.

3. **CRediT author contributions**
   - source: `submission_package/author_declarations_template.md`
   - required fields: conceptualization; methodology; software; validation; writing; supervision
   - evidence: 1 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/author_declarations_template.md.
   - next action: Assign CRediT-style roles for every author before upload.

4. **Funding statement**
   - source: `submission_package/author_declarations_template.md`
   - required fields: funding sources; grant numbers; no-funding statement if applicable
   - evidence: 1 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/author_declarations_template.md.
   - next action: Insert the exact target-venue funding or no-funding wording.

5. **Acknowledgements**
   - source: `submission_package/author_declarations_template.md`
   - required fields: technical help; institutional support; people to acknowledge; no-acknowledgement statement if applicable
   - evidence: 1 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/author_declarations_template.md.
   - next action: Add acknowledgements or the venue-required no-acknowledgement statement.

6. **Competing interests**
   - source: `submission_package/author_declarations_template.md`
   - required fields: financial interests; non-financial interests; none-declared wording if applicable
   - evidence: 1 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/author_declarations_template.md.
   - next action: Insert the exact competing-interest statement required by the target venue.

7. **Data availability archive link**
   - source: `submission_package/author_declarations_template.md`
   - required fields: repository DOI or URL; anonymous review link if needed; access restrictions if any
   - evidence: 1 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/author_declarations_template.md.
   - next action: Create or select the final archive/repository link and paste it into the statement.

8. **Code availability and license**
   - source: `submission_package/author_declarations_template.md`
   - required fields: repository URL; commit hash; license; environment notes; anonymous review link if needed
   - evidence: 1 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/author_declarations_template.md.
   - next action: Add the final repository URL, commit hash, license, and any anonymous review link.

9. **AI assistance disclosure**
   - source: `submission_package/author_declarations_template.md`
   - required fields: venue wording; scope of assistance; author verification statement
   - evidence: 1 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/author_declarations_template.md.
   - next action: Use the venue-required disclosure wording or confirm that no disclosure is required.

10. **Preprint and prior submission history**
   - source: `submission_package/author_declarations_template.md`
   - required fields: preprint DOI/URL; prior submission history; related manuscripts
   - evidence: 1 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/author_declarations_template.md.
   - next action: Record any preprint, previous submission, or related manuscript under review.

11. **Cover-letter routing metadata**
   - source: `submission_package/cover_letter_template.md`
   - required fields: corresponding author; target venue; manuscript type; reviewer suggestions; excluded reviewers
   - evidence: 2 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/cover_letter_template.md.
   - next action: Fill the cover-letter required fields after selecting the target venue.

12. **Target-venue policy check**
   - source: `submission_package/submission_checklist.md`
   - required fields: formatting policy; reference style; word limit; supplement policy; AI disclosure policy
   - evidence: 10 AUTHOR INPUT REQUIRED marker(s) remain in submission_package/submission_checklist.md.
   - next action: Check the target venue guide and update manuscript or support files accordingly.

## Files To Update After Author Decisions

- `submission_package/AUTHOR_METADATA_QUESTIONNAIRE_zh.md` as the Chinese field-by-field intake guide.
- `submission_package/COMPARISON_SIGNIFICANCE_MATRIX_zh.md` as the Chinese comparison-role matrix before editing cover-letter, response, or venue-system claim text.
- `submission_package/submission_metadata.json` for the private structured intake.
- `submission_package/generated_*.md` private previews, generated automatically from the structured intake and intentionally ignored by Git.
- `submission_package/author_declarations_template.md` if the venue wants declarations in prose form.
- `submission_package/cover_letter_template.md` after the target venue and routing details are known.
- `submission_package/submission_checklist.md` after venue formatting, reference style, word limit, supplementary-material policy, and AI-disclosure policy are confirmed.
- `paper_latex/resource_nmcts_submission_v1.tex` only if the selected venue requires author names, declarations, formatting conversion, or final availability links inside the manuscript source.
- A venue-specific anonymous manuscript copy and anonymous artifact links if `target_venue.anonymous_review_required` is yes.

## Final Checks After Filling Metadata

```bash
./rebuild_submission_package.sh
./verify_submission_package.sh
rg -n "needs author input|needs revision" results/analysis_submission_readiness_audit.md results/analysis_submission_metadata_audit.md
```

Expected terminal state after real author metadata is supplied: no `needs revision` rows, no unresolved author-input rows in the final upload copy, and a passing terminal package verifier.
