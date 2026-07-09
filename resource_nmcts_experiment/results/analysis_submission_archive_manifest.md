# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 292.2 KiB | `1c28db6ee3916976` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 202 | 0 | 226.3 KiB | `4d53b2d60a3deb38` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.3 MiB | `30253d5b93681ed7` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 456 | 0 | 4.7 MiB | `f2acc9d53dacc0aa` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 135 | 0 | 263.4 KiB | `dbe16d060b8abfc7` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 169 | 0 | 3.1 MiB | `56e99fcf775d4989` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 18 | 0 | 138.8 KiB | `4980547571ce275c` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
