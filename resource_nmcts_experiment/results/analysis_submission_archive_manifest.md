# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 305.0 KiB | `b7317b5dc3f5c8d4` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 206 | 0 | 233.8 KiB | `9e08bc7b3f2f4b7a` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.3 MiB | `30253d5b93681ed7` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 464 | 0 | 4.7 MiB | `f73bbc6123408083` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 139 | 0 | 267.6 KiB | `723d2ef918e13662` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 173 | 0 | 3.2 MiB | `b517c23f8f1ebd5d` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 18 | 0 | 139.4 KiB | `e27edf607112eaaa` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
