# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 273.2 KiB | `9db5a05ddcef3495` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 197 | 0 | 221.2 KiB | `7d657d8b1864ea40` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `57c8751f06116db0` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 442 | 0 | 4.7 MiB | `134b371a8d43f451` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 128 | 0 | 252.0 KiB | `0c1f17e9e0fe6ed2` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 159 | 0 | 2.9 MiB | `6c51876d02952be8` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 17 | 0 | 130.8 KiB | `b217f8fe68eeb387` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
