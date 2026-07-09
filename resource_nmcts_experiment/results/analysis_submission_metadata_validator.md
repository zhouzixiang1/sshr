# Submission Metadata Validator

This audit validates private `submission_metadata.json` without exposing private values in tracked outputs.

## Status counts

- needs author input: 1

| item | status | field names | evidence | next action |
|---|---|---|---|---|
| Metadata file presence | needs author input | submission_metadata.json | submission_package/submission_metadata.json is missing. | Copy submission_metadata_template.json to submission_metadata.json, fill it, and rerun the rebuild. |
