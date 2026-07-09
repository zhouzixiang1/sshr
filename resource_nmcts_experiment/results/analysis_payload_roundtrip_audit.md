# Payload Round-Trip Audit

This terminal audit opens the reviewer/upload tarball and checks manifest agreement, per-file hashes, path hygiene, required artifacts, and deterministic tar metadata.

## Status counts

- pass: 38

| item | status | evidence | next action |
|---|---|---|---|
| Payload archive readable | pass | archive=submission_package/dist/resource_nmcts_submission_payload.tar.gz; members=1100; error=none. | Regenerate the payload archive if it cannot be opened by Python tarfile. |
| Payload manifest round-trip | pass | manifest_files=1100; archive_files=1100; missing=none; extra=none. | Regenerate make_submission_payload_archive.py outputs if manifest and archive contents diverge. |
| Payload per-file SHA256 | pass | checked=1100; mismatches=none. | Regenerate the payload archive and manifest if any archived file digest differs from the manifest. |
| Payload path hygiene | pass | unsafe_paths=none; private_hits=none. | Remove unsafe, platform-generated, or private files from the payload inputs. |
| Payload required artifacts | pass | required=15; missing=none. | Ensure the uploadable archive includes manuscript, bibliography, rebuild/verify scripts, handoff docs, and submission audits. |
| Payload reviewer entrypoints | pass | reviewer_entries=7; missing=none. | Ensure the uploadable archive includes reviewer-facing guide, editor/reviewer briefs, venue brief, registry, and reproducibility audit. |
| Payload comparison protocol evidence | pass | comparison_protocol_files=11; missing=none. | Ensure the uploadable archive includes the comparison protocol audit plus its claim, evidence, comparability, counterpoint, statistical, and tradeoff sources. |
| Payload comparison target validity evidence | pass | comparison_target_validity_files=5; missing=none. | Ensure the uploadable archive includes the comparison target validity audit script, generated evidence, and manuscript table. |
| Payload comparison answer scorecard | pass | comparison_answer_files=5; missing=none. | Ensure the uploadable archive includes the comparison answer scorecard script, generated evidence, and manuscript table. |
| Payload score-weight robustness evidence | pass | weight_robustness_files=5; missing=none. | Ensure the uploadable archive includes the score-weight robustness script, generated evidence, manifest, and manuscript table. |
| Payload resource-weight sensitivity evidence | pass | resource_weight_sensitivity_files=6; missing=none. | Ensure the uploadable archive includes the broader resource-weight sensitivity audit script, raw rows, generated evidence, manifest, and manuscript table. |
| Payload SSHR reproduction-scope evidence | pass | sshr_reproduction_scope_files=21; missing=none. | Ensure the uploadable archive includes the SSHR reproduction-scope audit script, required raw rows, generated evidence, manifest, and manuscript table. |
| Payload novelty/comparison scorecard | pass | novelty_scorecard_files=5; missing=none. | Ensure the uploadable archive includes the novelty/comparison scorecard script, generated evidence, and manuscript table. |
| Payload threats-to-validity audit | pass | threats_validity_files=5; missing=none. | Ensure the uploadable archive includes the threats-to-validity audit script, generated evidence, and manuscript table. |
| Payload ROS reproduction-boundary evidence | pass | ros_gap_files=23; missing=none. | Ensure the uploadable archive includes the ROS reproduction gap audit script, generated evidence, and support table. |
| Payload published STG counterpoint | pass | stg_benchmark_files=6; missing=none. | Ensure the uploadable archive includes the STG counterpoint script, raw rows, generated evidence, manifest, and manuscript table. |
| Payload schedule-proxy evidence | pass | schedule_proxy_files=8; missing=none. | Ensure the uploadable archive includes the schedule metrics scripts, compact audit outputs, and manuscript schedule-proxy table. |
| Payload ultra-scale n=48--64 evidence | pass | ultra_scale64_files=16; missing=none. | Ensure the uploadable archive includes the n=48--64 raw term-set stress rows, compact audit, and manuscript tables. |
| Payload search-budget contract evidence | pass | search_budget_files=5; missing=none. | Ensure the uploadable archive includes the search-budget contract script, generated evidence, and manuscript table. |
| Payload learned-control evidence | pass | learned_control_files=31; missing=none. | Ensure the uploadable archive includes the learned-control audit script, generated evidence, manifest, and manuscript table. |
| Payload neural/MCTS claim calibration | pass | neural_mcts_claim_calibration_files=5; missing=none. | Ensure the uploadable archive includes the neural/MCTS claim-calibration script, generated evidence, manifest, and manuscript table. |
| Payload bit-flip random-prior evidence | pass | bitflip_random_prior_files=9; missing=none. | Ensure the uploadable archive includes the bit-flip random-prior run script, analysis outputs, raw CSV, and manuscript table. |
| Payload bit-flip low-budget learned-prior evidence | pass | bitflip_neural_budget_files=9; missing=none. | Ensure the uploadable archive includes the low-budget learned-prior run script, raw rows, analysis outputs, and manuscript table. |
| Payload frontier random-depth evidence | pass | frontier_random_depth_files=5; missing=none. | Ensure the uploadable archive includes the frontier random-depth analysis script, generated evidence, and manuscript table. |
| Payload headline numeric evidence | pass | headline_numeric_files=4; missing=none. | Ensure the uploadable archive includes the headline numeric audit script and generated CSV/Markdown/JSON evidence. |
| Payload citation support evidence | pass | citation_support_files=4; missing=none. | Ensure the uploadable archive includes the citation support audit script and generated CSV/Markdown/JSON evidence. |
| Payload editorial screening evidence | pass | editorial_screening_files=5; missing=none. | Ensure the uploadable archive includes the editorial screening audit script, generated evidence, and support table. |
| Payload target-venue decision evidence | pass | target_venue_decision_files=5; missing=none. | Ensure the uploadable archive includes the target-venue decision audit script, generated evidence, and support table. |
| Payload target-venue ACM/TQC format evidence | pass | target_venue_format_files=7; missing=none. | Ensure the uploadable archive includes the ACM/TQC generated review source, compiled PDF, and format smoke audit. |
| Payload support packet evidence | pass | support_packet_files=7; missing=none. | Ensure the uploadable archive includes the support packet audit script, generated evidence, and support table. |
| Payload author-input closure evidence | pass | author_input_closure_files=4; missing=none. | Ensure the uploadable archive includes the author-input closure audit script and generated CSV/Markdown/JSON evidence. |
| Payload author-questionnaire coverage evidence | pass | author_questionnaire_files=5; missing=none. | Ensure the uploadable archive includes the questionnaire coverage audit, generated evidence, and Chinese intake form. |
| Payload metadata closure-path evidence | pass | metadata_closure_files=4; missing=none. | Ensure the uploadable archive includes the final metadata closure-path audit script and generated evidence. |
| Payload source/path privacy executable | pass | source_path_privacy_scripts=1; missing=none; terminal_outputs_excluded=3. | Ensure the uploadable archive includes source/path privacy audit code; generated terminal outputs are intentionally excluded and reproduced by the extracted-payload smoke test. |
| Payload Git-policy executable | pass | payload_git_policy_scripts=1; missing=none; terminal_outputs_excluded=3. | Ensure the uploadable archive includes payload Git-policy audit code; generated terminal outputs are intentionally excluded and regenerated from the source tree. |
| Payload extraction smoke executable | pass | payload_extraction_smoke_scripts=1; missing=none; terminal_outputs_excluded=3. | Ensure the uploadable archive includes the extraction smoke audit code; generated terminal outputs are intentionally excluded and regenerated from the source tree. |
| Payload verifier smoke executable | pass | payload_verifier_smoke_scripts=1; missing=none; terminal_outputs_excluded=3. | Ensure the uploadable archive includes the verifier smoke audit code; generated terminal outputs are intentionally excluded and regenerated from the source tree. |
| Payload deterministic tar metadata | pass | members_checked=1100; metadata_issues=none. | Keep tar member mtime/uid/gid/user/group/mode normalized for deterministic payloads. |
