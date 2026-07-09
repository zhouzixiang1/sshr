# Submission Metadata Validator

This audit validates private `submission_metadata.json` without exposing private values in tracked outputs.

## Status counts

- needs author input: 1

| item | status | field names | evidence | next action |
|---|---|---|---|---|
| Metadata file presence | needs author input | submission_metadata.json | submission_package/submission_metadata.json is missing. | Run /opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_from_answers.py --init-private-answers, fill submission_metadata_answers.json, then run make_submission_metadata_from_answers.py --write-private and rerun the rebuild. |
