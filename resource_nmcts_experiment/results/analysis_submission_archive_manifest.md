# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 241.4 KiB | `7eb6d7ebc7eec6dc` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 182 | 0 | 193.1 KiB | `49e93602472d3cdb` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `8384a386e5af073c` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 153 | 0 | 97.6 MiB | `6c69de7ea3ce5a2d` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 402 | 0 | 4.5 MiB | `8cf66dfd87e5c6ab` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 113 | 0 | 201.0 KiB | `66764bf19ed31387` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 143 | 0 | 2.6 MiB | `fa0967d8fee9c836` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 12 | 0 | 92.8 KiB | `cf0b4204cfba30fc` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
