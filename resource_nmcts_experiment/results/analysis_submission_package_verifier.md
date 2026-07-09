# Submission Package Verifier

This read-only verifier checks the terminal package invariants after the payload archive has been created.

## Status counts

- pass: 34

| item | status | evidence | next action |
|---|---|---|---|
| Compiled author PDF | pass | paper_latex/resource_nmcts_submission_v1.pdf pages=29, bytes=606524. | Rebuild the submission package and inspect latexmk output if the PDF is missing. |
| Compiled anonymous PDF | pass | paper_latex/resource_nmcts_submission_anonymous.pdf pages=29, bytes=603167. | Rebuild the submission package and inspect latexmk output if the PDF is missing. |
| Payload SHA sidecar | pass | actual=21610c882c232a60bd096c83f5711fad2aea7f9189adf0300e136c7dcdd2fdf7; sidecar=21610c882c232a60bd096c83f5711fad2aea7f9189adf0300e136c7dcdd2fdf7. | Regenerate the payload archive if the digests differ. |
| Payload manifest consistency | pass | summary=21610c882c232a60bd096c83f5711fad2aea7f9189adf0300e136c7dcdd2fdf7; manifest=21610c882c232a60bd096c83f5711fad2aea7f9189adf0300e136c7dcdd2fdf7; file_count=905. | Regenerate make_submission_payload_archive.py outputs if summary and manifest disagree. |
| Readiness audit terminal state | pass | status_counts={'pass': 45, 'needs author input': 1}; terminal_verifier_self_row_excluded=True. | Resolve any needs-revision rows; author-specific declarations remain manual. |
| Artifact rerun registry coverage | pass | families=19; registry_raw=144; actual_raw=144. | Rerun analyze_artifact_rerun_registry.py after adding raw CSVs or driver scripts. |
| Claim-scope lint | pass | unresolved_count=0; status_counts={'guarded': 60, 'pass': 5}. | Run analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims. |
| Comparison protocol audit | pass | layers=7; needs_revision_count=0; status_counts={'pass': 7}; table_exists=True. | Run analyze_comparison_protocol_audit.py and restore missing baseline-role, evidence, comparability, counterpoint, or manuscript anchors. |
| ROS reproduction gap audit | pass | rows=8; needs_revision_count=0; status_counts={'pass': 8}; coverage_counts={'covered': 4, 'not reproduced': 1, 'partial': 3}; official_ros_fully_reproduced=False; full_ros_boundary_is_explicit=True. | Run analyze_ros_lut_line_sensitivity.py and analyze_ros_reproduction_gap_audit.py and restore ROS proxy/full-reproduction boundary anchors. |
| Search-control baseline audit | pass | rows=8; needs_revision_count=0; status_counts={'pass': 8}. | Run analyze_search_control_baseline_audit.py and restore heuristic, beam, no-MCTS, MCTS, Pareto, learned-prior, and phase random-control evidence rows. |
| Editorial screening audit | pass | rows=8; needs_revision_count=0; status_counts={'pass': 8}. | Run analyze_editorial_screening_audit.py and restore scope, novelty, comparison, counterpoint, AI-boundary, scale-boundary, reproducibility, author-gate, or editor-reading anchors. |
| Submission support packet audit | pass | rows=8; needs_revision_count=0; status_counts={'pass': 8}. | Run analyze_submission_support_packet_audit.py and restore cover-letter, declaration, venue, checklist, handoff, anonymous-review, private-preview, or editor/reviewer support anchors. |
| Citation support audit | pass | rows=10; cited_keys=18; bib_keys=18; needs_revision_count=0; status_counts={'pass': 10}. | Run analyze_citation_support_audit.py and restore missing citations, BibTeX entries, or reference locators. |
| Headline numeric consistency | pass | claims=15; needs_revision_count=0; status_counts={'pass': 15}. | Run analyze_headline_numeric_consistency.py and align abstract tokens with CSV-derived evidence. |
| Figure asset audit | pass | figures=7; needs_revision_count=0; status_counts={'pass': 7}. | Run make_submission_figures.py and analyze_figure_asset_audit.py to restore referenced PDF/PNG/SVG assets and source-data CSVs. |
| LaTeX dependency audit | pass | dependencies=84; type_counts={'bibliography': 2, 'figure': 14, 'main_source': 2, 'tex_input': 66}; needs_revision_count=0; status_counts={'pass': 84}. | Run analyze_latex_dependency_audit.py after payload creation and restore missing TeX, table, figure, bibliography, or payload entries. |
| PDF visual render audit | pass | rows=2; needs_revision_count=0; status_counts={'pass': 2}. | Run analyze_pdf_visual_audit.py and inspect rendered PDF pages for blank, clipped, or overfilled output. |
| PDF text/searchability audit | pass | rows=2; required_anchors=18; needs_revision_count=0; status_counts={'pass': 2}. | Run analyze_pdf_text_audit.py and inspect pdftotext output for missing anchors, identity leaks, or placeholder remnants. |
| PDF metadata/privacy audit | pass | rows=2; needs_revision_count=0; status_counts={'pass': 2}. | Run analyze_pdf_metadata_audit.py and inspect pdfinfo metadata for privacy leaks, encryption, JavaScript, forms, or page-geometry drift. |
| Source/path privacy audit | pass | rows=6; payload_local_path_files=53; needs_revision_count=0; status_counts={'pass': 6}. | Run analyze_source_path_privacy_audit.py and move local paths out of manuscript/support sources while keeping toolchain paths only in provenance outputs. |
| Metadata starter dry-run | pass | returncode=0; missing_tokens=none; private_preexisting=False; private_created=False; private_modified=False. | Run make_submission_metadata_starter.py without --write-private and keep it read-only until author input is explicit. |
| Private metadata validator | pass | needs_revision_count=0; status_counts={'needs author input': 1}. | Run validate_submission_metadata.py and fix metadata format or consistency rows before upload. |
| Metadata pipeline self-test | pass | needs_revision_count=0; status_counts={'pass': 14}; synthetic_only=True; writes_private_metadata=False; writes_private_preview_files=False. | Run selftest_submission_metadata_pipeline.py and keep the fixture synthetic and non-private. |
| Anonymous-review readiness audit | pass | needs_revision_count=0; needs_author_input_count=3; status_counts={'needs author input': 3, 'pass': 3}. | Run analyze_anonymous_review_readiness.py and resolve needs-revision rows; double-blind conversion remains venue-dependent author input. |
| Author-input closure audit | pass | needs_revision_count=0; required_metadata_paths=50; metadata_present=False; status_counts={'pass': 7}. | Run analyze_author_input_closure_audit.py and restore author-packet coverage, private metadata protection, or support-document visibility. |
| Submission metadata closure path | pass | needs_revision_count=0; required_metadata_paths=50; metadata_present=False; closure_path_ready=True; status_counts={'pass': 8}. | Run analyze_submission_metadata_closure_path.py and keep the final author/venue metadata path explicit, ignored, and machine-checkable. |
| Private submission text preview | pass | status_counts={'needs author input': 1}; private_outputs_are_git_ignored=True. | Run make_submission_text_preview.py and keep generated private Markdown files ignored by Git. |
| Private metadata payload exclusion | pass | private_payload_hits=none; checked_basenames=['generated_author_declarations.md', 'generated_availability_statements.md', 'generated_cover_letter.md', 'generated_submission_text.md', 'submission_metadata.json']. | Regenerate the payload after removing ignored private metadata or preview files from package inputs. |
| Payload round-trip audit | pass | needs_revision_count=0; status_counts={'pass': 18}. | Run analyze_payload_roundtrip_audit.py after payload creation and fix any archive/manifest/path/hash issues. |
| Payload extraction smoke audit | pass | needs_revision_count=0; status_counts={'pass': 16}; smoke_scripts=15. | Run analyze_payload_extraction_smoke_audit.py after payload creation and fix extracted-payload script failures. |
| Payload verifier smoke audit | pass | needs_revision_count=0; verifier_returncode=0; rows=2; status_counts={'pass': 2}. | Run analyze_payload_verifier_smoke_audit.py after payload creation and fix extracted one-command verifier failures. |
| Payload LaTeX compile audit | pass | needs_revision_count=0; compiled_manuscripts=2; status_counts={'pass': 3}. | Run analyze_payload_latex_compile_audit.py and restore missing extracted-payload TeX, table, figure, or bibliography dependencies. |
| Author LaTeX log boundary | pass | Only allowed rerunfilecheck/showhyphens log lines found. | Inspect the LaTeX log and fix unexpected warnings or errors. |
| Anonymous LaTeX log boundary | pass | Only allowed rerunfilecheck/showhyphens log lines found. | Inspect the LaTeX log and fix unexpected warnings or errors. |
