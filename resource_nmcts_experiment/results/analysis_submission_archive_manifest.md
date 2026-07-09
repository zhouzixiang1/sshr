# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 281.8 KiB | `0e3503f47524639f` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 199 | 0 | 224.1 KiB | `61eda84a5f498e62` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `57c8751f06116db0` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 450 | 0 | 4.7 MiB | `9985b4abc33e9c88` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 132 | 0 | 259.2 KiB | `00ce0d4e275dccf0` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 166 | 0 | 3.0 MiB | `9264d5dd9b19070c` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 18 | 0 | 137.0 KiB | `6b201c0c446257eb` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
