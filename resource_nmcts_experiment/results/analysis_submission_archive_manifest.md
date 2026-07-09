# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 268.3 KiB | `ab772755c9f1573d` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 195 | 0 | 215.7 KiB | `18b9ed83aee5f842` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `57c8751f06116db0` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 434 | 0 | 4.6 MiB | `9b4eb4ecd6d3b080` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 124 | 0 | 237.4 KiB | `0825b58b698aa713` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 155 | 0 | 2.8 MiB | `b2fe030faec37f2d` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 17 | 0 | 128.3 KiB | `5d25c5fb8a474ca4` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
