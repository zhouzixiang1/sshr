# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 212.1 KiB | `4ea6ee33baa38f1f` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 172 | 0 | 179.2 KiB | `33be30f17950a02a` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `7e792ff61993e4e8` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 147 | 0 | 93.2 MiB | `32c1a0760cec241b` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 381 | 0 | 4.4 MiB | `6860cdb6fc9e6b51` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 101 | 0 | 173.6 KiB | `00163aecfd0bdd2f` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 131 | 0 | 2.3 MiB | `6e8548648d4e2d9c` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 85.3 KiB | `b3216767063d6491` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
