# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 4 | 0 | 138.4 KiB | `6d021006231f9e9f` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 165 | 0 | 163.5 KiB | `d167d84a145417d0` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `a9bdb91e8e0345ac` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 145 | 0 | 93.1 MiB | `a868b9542153ff9b` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 364 | 0 | 4.4 MiB | `78987f172bc935f3` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 93 | 0 | 160.4 KiB | `fcacb868cd92958e` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 122 | 0 | 2.1 MiB | `fdc16ccc9e3e8b95` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 80.6 KiB | `eca8b688ba7dd27f` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
