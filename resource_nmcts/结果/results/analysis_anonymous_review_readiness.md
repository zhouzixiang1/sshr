# Anonymous Review Readiness Audit

This audit separates the current author-labeled manuscript from the extra actions required by a double-blind venue.

## Status counts

- needs author input: 3
- pass: 3

| item | status | evidence | next action |
|---|---|---|---|
| Target anonymous-review decision | needs author input | target_venue.anonymous_review_required is not finalized. | Set target_venue.anonymous_review_required after choosing the venue, then rerun the rebuild. |
| Current manuscript author field | needs author input | author_field=present; double_blind_ready=False. | For double-blind review, create a venue-specific anonymous copy with an anonymized author field; keep this author-labeled source for non-anonymous venues. |
| Anonymous artifact-link boundary | needs author input | data_code_section_present=True; repo_relative_link=True; anonymous_wording=False. | If double-blind review is required, replace repository-relative availability wording with an anonymous review archive/link before upload. |
| Generated anonymous source draft | pass | source_exists=True; author_anonymized=True; author_name_present=False; availability_repo_relative=False; anonymous_wording=True. | Run make_anonymous_review_draft.py and inspect the generated source before double-blind upload. |
| Private file boundary for anonymous review | pass | extracted_payload=False; present_private_files=['submission_package/submission_metadata_answers.json']; tracked_private_files=none; gitignore_covers_private_paths=True; missing_gitignore_entries=none. | Keep private metadata ignored and untracked in the worktree, and absent from extracted public payloads. |
| Anonymous-review metadata fields | pass | missing_template_paths=none; support_docs_mention_anonymous_review=True. | Keep anonymous-review metadata fields and support-document instructions in sync. |
