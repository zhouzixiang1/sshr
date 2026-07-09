# Submission Metadata Validator

This audit validates private `submission_metadata.json` without exposing private values in tracked outputs.

## Status counts

- needs author input: 1

| item | status | field names | evidence | next action |
|---|---|---|---|---|
| Metadata file presence | needs author input | submission_metadata.json | submission_package/submission_metadata.json is missing. | Run /opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_starter.py --write-private, or copy submission_metadata_template.json manually, fill submission_metadata.json, and rerun the rebuild. |
