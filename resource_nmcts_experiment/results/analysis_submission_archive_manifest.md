# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 289.4 KiB | `f171b1af33f06876` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 201 | 0 | 225.6 KiB | `605f91f084b7929b` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `b115976593d275f4` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 454 | 0 | 4.7 MiB | `99845b7ddb3df719` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 134 | 0 | 261.9 KiB | `2a4bcdc572949280` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 168 | 0 | 3.1 MiB | `8f8eedfbe1025ea5` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 18 | 0 | 138.8 KiB | `c260c42900575e08` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
