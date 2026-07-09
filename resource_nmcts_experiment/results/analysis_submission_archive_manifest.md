# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 256.2 KiB | `3fc16036354eeec1` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 191 | 0 | 207.3 KiB | `c3f4c97ca3c1116c` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `57c8751f06116db0` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 160 | 0 | 98.1 MiB | `8e59cceb9d586536` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 422 | 0 | 4.6 MiB | `b5d5b0fde65c9f7d` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 118 | 0 | 219.3 KiB | `6894c4928cf90eb2` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 148 | 0 | 2.7 MiB | `18180255e8231259` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 13 | 0 | 103.1 KiB | `395c556f5c266054` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
