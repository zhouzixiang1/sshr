# Public Handoff Freshness Audit

This terminal audit checks that the public handoff documents expose the current machine-generated package snapshot.

## Status counts

- pass: 4

## Current snapshot tokens

- `PDF pages=47/47`
- `readiness=72 pass + 1 needs author input`
- `payload_files=1110`
- `artifact_registry=27 families / 158 raw CSV / 78365 raw rows`
- `source_privacy=0 strict leaks / 57 provenance files / 1067 payload text files`
- `comparison_validity=8/8 pass`
- `novelty_scorecard=6/6 pass`
- `goal_gate=author/venue metadata remains open`

| item | status | evidence | next action |
|---|---|---|---|
| Current audit outputs are readable | pass | missing_files=none; snapshot={'author_pages': 47, 'anonymous_pages': 47, 'readiness_pass': 72, 'readiness_author_input': 1, 'payload_files': 1110, 'registry_families': 27, 'raw_files': 158, 'raw_rows': 78365, 'strict_local_path_leaks': 0, 'payload_text_files': 1067, 'provenance_local_path_files': 57, 'comparison_pass': 8, 'comparison_rows': 8, 'comparison_needs_revision': 0, 'novelty_pass': 6, 'novelty_rows': 6, 'novelty_needs_revision': 0}. | Regenerate the terminal audits before refreshing public handoff docs. |
| Deliverable current snapshot | pass | file=DELIVERABLE_zh.md; missing_tokens=none. | Refresh the public current-snapshot block from generated audit outputs. |
| Final handoff current snapshot | pass | file=submission_package/FINAL_SUBMISSION_HANDOFF_zh.md; missing_tokens=none. | Refresh the public current-snapshot block from generated audit outputs. |
| Submission checklist current snapshot | pass | file=submission_package/submission_checklist.md; missing_tokens=none. | Refresh the public current-snapshot block from generated audit outputs. |
