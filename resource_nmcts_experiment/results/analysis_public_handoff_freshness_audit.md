# Public Handoff Freshness Audit

This terminal audit checks that the public handoff documents expose the current machine-generated package snapshot.

## Status counts

- pass: 4

## Current snapshot tokens

- `PDF pages=61/60`
- `readiness=91 pass + 1 needs author input`
- `payload_files=1264`
- `artifact_registry=31 families / 166 raw CSV / 82071 raw rows`
- `source_privacy=0 strict leaks / 57 provenance files / 1220 payload text files`
- `comparison_validity=8/8 pass`
- `novelty_scorecard=6/6 pass`
- `rl_budget_policy=160 test functions / 71 Pareto calls / -3.48% score vs Resource / -13.13% time vs always-Pareto`
- `goal_gate=author/venue metadata remains open`

| item | status | evidence | next action |
|---|---|---|---|
| Current audit outputs are readable | pass | missing_files=none; snapshot={'author_pages': 61, 'anonymous_pages': 60, 'readiness_pass': 91, 'readiness_author_input': 1, 'payload_files': 1264, 'registry_families': 31, 'raw_files': 166, 'raw_rows': 82071, 'strict_local_path_leaks': 0, 'payload_text_files': 1220, 'provenance_local_path_files': 57, 'comparison_pass': 8, 'comparison_rows': 8, 'comparison_needs_revision': 0, 'novelty_pass': 6, 'novelty_rows': 6, 'novelty_needs_revision': 0, 'budget_pairs': 160, 'budget_run_pareto': 71, 'budget_score_vs_resource_pct': -3.4824715989041426, 'budget_time_vs_pareto_pct': -13.128682546406568}. | Regenerate the terminal audits before refreshing public handoff docs. |
| Deliverable current snapshot | pass | file=DELIVERABLE_zh.md; missing_tokens=none. | Refresh the public current-snapshot block from generated audit outputs. |
| Final handoff current snapshot | pass | file=submission_package/FINAL_SUBMISSION_HANDOFF_zh.md; missing_tokens=none. | Refresh the public current-snapshot block from generated audit outputs. |
| Submission checklist current snapshot | pass | file=submission_package/submission_checklist.md; missing_tokens=none. | Refresh the public current-snapshot block from generated audit outputs. |
