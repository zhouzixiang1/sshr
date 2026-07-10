# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 309.3 KiB | `5aa4b36d32d2e16f` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 208 | 0 | 237.2 KiB | `bc0196546eccc58c` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.3 MiB | `30253d5b93681ed7` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 162 | 0 | 98.2 MiB | `440bd6af52b01926` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 468 | 0 | 4.8 MiB | `a710f165da3cfc44` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 141 | 0 | 271.2 KiB | `38dc2c9610406294` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 175 | 0 | 3.2 MiB | `4831c88224849486` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 18 | 0 | 139.4 KiB | `49e295c9723ed794` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
