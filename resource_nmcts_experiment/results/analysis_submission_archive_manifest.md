# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 251.3 KiB | `f6178f4956a8649d` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 190 | 0 | 205.0 KiB | `a352d31cd8efbdd8` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.1 MiB | `24477d2f3f8748ca` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 158 | 0 | 97.7 MiB | `a8951d057dfbac10` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 420 | 0 | 4.6 MiB | `cd42062c002fd04e` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 117 | 0 | 215.8 KiB | `b47195183521fd36` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 147 | 0 | 2.7 MiB | `d4ceb0436f9c7ea8` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 13 | 0 | 101.3 KiB | `5e553eb4958245ab` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
