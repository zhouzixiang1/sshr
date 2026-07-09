# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 218.4 KiB | `621b64386b965104` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 175 | 0 | 182.6 KiB | `b5b0e1de2ef16660` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `fbad406ea6ba537b` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 149 | 0 | 93.8 MiB | `30d67e8ff400d4d5` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 388 | 0 | 4.4 MiB | `1e49dcfb2b918c64` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 105 | 0 | 179.7 KiB | `88da023b5a1a2170` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 135 | 0 | 2.4 MiB | `0021ca31bb82028c` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 85.5 KiB | `c33ac38169472054` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
