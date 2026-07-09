# Submission Metadata Closure Path

This audit verifies that the final author/venue metadata step is explicit, private, and machine-checkable without exposing private values.

## Status counts

- pass: 8

## Closure Sequence

1. Use `submission_package/AUTHOR_METADATA_QUESTIONNAIRE_zh.md` to collect field-by-field author and venue answers.
2. Create ignored private short answers with `make_submission_metadata_from_answers.py --init-private-answers`.
3. Fill every `AUTHOR INPUT REQUIRED` value in `submission_package/submission_metadata_answers.json`.
4. Generate ignored private metadata with `make_submission_metadata_from_answers.py --write-private`.
5. Rerun `./rebuild_submission_package.sh` and `./verify_submission_package.sh`.
6. Review ignored `submission_package/generated_*.md` previews against the target venue.
7. Replace repository-relative availability text with final archive, repository, or anonymous-review links before upload.

| item | status | evidence | next action |
|---|---|---|---|
| Structured metadata inventory | pass | required_paths=50; template_placeholders=53; uncovered_placeholders=none. | Keep REQUIRED_METADATA_PATHS aligned with every AUTHOR INPUT REQUIRED field in submission_metadata_template.json. |
| Private metadata starter dry-run | pass | public_prefill_fields=2; unavailable=none; author_gated_examples=6. | The starter should prefill only safe public repository fields and leave author/venue declarations human-gated. |
| Private metadata Git protection | pass | private_paths=6; not_ignored=none; tracked=none; metadata_present=False. | Keep submission_metadata.json and generated private previews ignored and untracked. |
| Validator and private-preview gates | pass | validator_counts={'needs author input': 1}; preview_counts={'needs author input': 1}; needs_author_input=2; private_outputs_are_git_ignored=True. | Rerun validate_submission_metadata.py and make_submission_text_preview.py after private metadata is filled. |
| Filled-metadata rehearsal | pass | status_counts={'pass': 14}; needs_revision_count=0; synthetic_only=True; writes_private_outputs=False. | Keep the synthetic self-test aligned with validator and private-preview renderer changes. |
| Anonymous-review decision gate | pass | status_counts={'needs author input': 3, 'pass': 3}; needs_revision_count=0; needs_author_input_count=3. | After selecting the venue, set anonymous-review policy and provide anonymous links if double-blind review is required. |
| Human handoff document coverage | pass | docs=9; missing=none; token_misses=none. | Keep README, checklist, target-venue brief, target-venue policy checklist, handoff, questionnaire, minimal response form, answer template, and author packet aligned with the private metadata workflow. |
| Goal-closure gate consistency | pass | git_worktree=True; metadata_counts={'needs author input': 12}; author_input_closure_counts={'pass': 7}; goal_overall=not complete. | Do not mark the overall goal complete until author/venue metadata are filled and the readiness audit has no unresolved author-input rows. |
