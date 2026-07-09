# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 241.9 KiB | `120183635591c833` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 183 | 0 | 195.9 KiB | `9ea1417d7d1c6b1a` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.1 MiB | `fe6acc594c095f49` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 154 | 0 | 97.6 MiB | `599f0822fe1d5a79` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 404 | 0 | 4.5 MiB | `9351c19e6cff1b52` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 113 | 0 | 203.0 KiB | `0fd65dbbcf7257cc` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 143 | 0 | 2.6 MiB | `f49caf8eb14bf417` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 13 | 0 | 100.5 KiB | `c9d087ff6b992017` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
