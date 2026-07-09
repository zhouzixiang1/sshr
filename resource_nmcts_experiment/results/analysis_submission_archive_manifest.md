# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 200.0 KiB | `9d931e4cbae17df1` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 168 | 0 | 168.3 KiB | `212b04b0784b597b` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `7e792ff61993e4e8` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 146 | 0 | 93.1 MiB | `b487b54b2f39140b` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 373 | 0 | 4.4 MiB | `c753bb8febea7440` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 96 | 0 | 165.8 KiB | `0f84ab5f2756b6b0` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 127 | 0 | 2.2 MiB | `e1580053921e1dc2` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 83.3 KiB | `c25573f3ccfc2593` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
