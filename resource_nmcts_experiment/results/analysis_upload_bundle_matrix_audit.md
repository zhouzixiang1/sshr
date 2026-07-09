# Upload Bundle Matrix Audit

This terminal audit maps venue-facing upload bundles to checked files, evidence gates, and claim/privacy boundaries.

## Status counts

- pass: 7

| bundle | status | upload use | evidence | boundary |
|---|---|---|---|---|
| Author manuscript bundle | pass | Non-anonymous venue upload or author-labeled review copy. | missing_files=none; pdf_visual_revisions=0; pdf_text_revisions=0; pdf_metadata_revisions=0; latex_dependency_revisions=0. | Author declarations and final availability links still require private author/venue input. |
| Generic anonymous-review bundle | pass | Double-blind venue upload when a generic anonymous format is accepted. | missing_files=none; anonymous_counts={'needs author input': 3, 'pass': 3}; anonymous_revisions=0. | Anonymous artifact links remain target-venue author input if double-blind review is required. |
| ACM/TQC review-format bundle | pass | ACM Transactions on Quantum Computing review-format route. | missing_files=none; format_revisions=0; pages=50; recommended_first_choice=ACM Transactions on Quantum Computing. | Final ACM rights, named authors, ORCIDs, CCS/keywords, and publication metadata remain author/venue decisions. |
| Source/data payload bundle | pass | Reviewer/source-data archive uploaded with the manuscript or deposited externally. | missing_files=none; payload_files=1201; git_policy_revisions=0; roundtrip_revisions=0; extraction_revisions=0; verifier_revisions=0; latex_compile_revisions=0. | The payload excludes private metadata and excludes its own generated tarball from Git. |
| Support and declaration templates | pass | Human-facing upload support: README, checklist, author input, last-mile card, cover letter, declarations, and metadata templates. | missing_files=none; readme_missing_tokens=none; support_packet_revisions=0. | Templates deliberately contain author-input placeholders and should not contain real private metadata while tracked. |
| Private local-only metadata boundary | pass | Local-only author metadata and generated submission text after the author fills private JSON. | private_payload_hits=none; source_privacy_revisions=0; payload_manifest_contains_private=False; payload_path_count=1201. | These files must stay ignored, local, and outside the public upload payload unless a venue explicitly requires private upload text. |
| Venue decision and final-sequence gate | pass | Decision support before choosing author-labeled, anonymous, or ACM/TQC route. | target_decision_revisions=0; recommended_first_choice=ACM Transactions on Quantum Computing; final_upload_revisions=0; sequence_ready=True; human_gate_open=True. | The repository can prepare the route, but the author must still choose the target venue and fill author/venue metadata. |

## Bundle files

- **Author manuscript bundle**: paper_latex/resource_nmcts_submission_v1.pdf; paper_latex/resource_nmcts_submission_v1.tex; paper_latex/references.bib
- **Generic anonymous-review bundle**: paper_latex/resource_nmcts_submission_anonymous.pdf; paper_latex/resource_nmcts_submission_anonymous.tex; paper_latex/references.bib
- **ACM/TQC review-format bundle**: paper_latex/resource_nmcts_submission_acm_tqc.pdf; paper_latex/resource_nmcts_submission_acm_tqc.tex; paper_latex/references.bib
- **Source/data payload bundle**: submission_package/dist/resource_nmcts_submission_payload.tar.gz; submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256
- **Support and declaration templates**: submission_package/README.md; submission_package/submission_checklist.md; submission_package/AUTHOR_INPUT_REQUIRED.md; submission_package/LAST_MILE_ACTION_CARD_zh.md; submission_package/FINAL_SUBMISSION_HANDOFF_zh.md; submission_package/cover_letter_template.md; submission_package/author_declarations_template.md; submission_package/submission_metadata_template.json; submission_package/submission_metadata_answers_template.json
- **Private local-only metadata boundary**: submission_package/generated_author_declarations.md; submission_package/generated_availability_statements.md; submission_package/generated_cover_letter.md; submission_package/generated_submission_text.md; submission_package/generated_upload_plan.md; submission_package/submission_metadata.json; submission_package/submission_metadata_answers.json
- **Venue decision and final-sequence gate**: submission_package/FINAL_SUBMISSION_HANDOFF_zh.md; submission_package/LAST_MILE_ACTION_CARD_zh.md; submission_package/submission_checklist.md
