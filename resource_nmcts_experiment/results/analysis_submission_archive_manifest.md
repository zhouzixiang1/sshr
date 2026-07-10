# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 328.8 KiB | `c035a1170aa3b0c7` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 211 | 0 | 248.5 KiB | `6fc53684d2936ea7` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `63937fb65f1e6e4a` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 166 | 0 | 98.4 MiB | `168b6e797fdd9f9a` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 477 | 0 | 4.8 MiB | `f3556750e2a521ef` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 148 | 0 | 289.6 KiB | `7e24db1c7f989afb` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 178 | 0 | 3.3 MiB | `1f0efb4c61b064ca` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 21 | 0 | 1.1 MiB | `1b2a25f8280fac80` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 18 | 0 | 141.8 KiB | `89975da3fdb65876` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
