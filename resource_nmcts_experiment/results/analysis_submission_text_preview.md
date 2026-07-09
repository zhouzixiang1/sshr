# Submission Text Preview

This audit records whether private author/venue metadata was sufficient to generate ignored Markdown previews for the submission system.

Tracked outputs intentionally do not include author names, emails, funding details, or venue-private text.

## Status counts

- needs author input: 1

| item | status | source | private outputs | evidence | next action |
|---|---|---|---|---|---|
| Private submission text preview | needs author input | `submission_package/submission_metadata_template.json` | submission_package/generated_author_declarations.md; submission_package/generated_availability_statements.md; submission_package/generated_cover_letter.md; submission_package/generated_submission_text.md | submission_package/submission_metadata.json is missing; removed stale private output files=0. | Run /opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_starter.py --write-private, or copy submission_metadata_template.json manually, fill every AUTHOR INPUT REQUIRED value, then rerun the rebuild script. |
