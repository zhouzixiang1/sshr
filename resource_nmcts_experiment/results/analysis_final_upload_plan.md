# Final Upload Plan

This public audit records whether a private route-specific upload plan can be generated from filled author/venue metadata.

Tracked outputs intentionally contain only route labels, counts, and field names; the generated upload plan itself is ignored by Git.

## Status counts

- needs author input: 1

| item | status | route | private output | evidence | next action |
|---|---|---|---|---|---|
| Final upload plan | needs author input | `missing_metadata` | `submission_package/generated_upload_plan.md` | metadata_missing=True; removed_stale_private_output=0; output_ignored=True. | Fill ignored submission_metadata.json, then rerun make_final_upload_plan.py. |
