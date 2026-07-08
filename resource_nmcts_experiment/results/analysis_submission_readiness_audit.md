# Submission Readiness Audit

This audit checks paper-level readiness markers in `paper_latex/resource_nmcts_submission_v1.tex` and the compiled PDF.

## Status counts

- needs author input: 1
- pass: 8

## Checklist

| item | status | evidence | next action |
|---|---|---|---|
| Bounded abstract claim | pass | Abstract states logical-layer scope and excludes hardware-mapped/depth-only claims. | Keep hardware and mapping claims out of the abstract unless new evidence is added. |
| Contribution-to-evidence chain | pass | Introduction includes a contribution-to-evidence map. | Update the map whenever a headline contribution changes. |
| Baseline fairness and scope | pass | Experimental design includes claim, evidence, and comparability matrices. | Keep cross-toolchain claims tied to the comparability audit. |
| Reproducibility evidence | pass | Manuscript includes compute, worker, artifact, and external-tool provenance table. | Rerun analyze_reproducibility_audit.py after adding scripts, tables, or figures. |
| Limitations and failure modes | pass | Discussion names logical-layer, ROS-proxy, RevKit-derived, and high-dimensional bridge boundaries. | Add any new negative result to Discussion rather than hiding it in tables. |
| Data and code availability | pass | Manuscript has an availability section pointing to scripts, CSVs, manifests, tables, and figures. | Replace repository-relative wording with an archival DOI or anonymous link at submission time if required. |
| Clean submission source | pass | 0 TODO/TBD/placeholder markers in submission TeX. | Remove all source placeholders before journal upload. |
| Compiled PDF artifact | pass | Compiled PDF detected with 25 pages. | Run latexmk and visual spot checks after each table or figure change. |
| Author-specific declarations | needs author input | Funding, acknowledgements, competing interests, and final archival links are author-specific. | Complete declarations at the target journal's submission step. |
