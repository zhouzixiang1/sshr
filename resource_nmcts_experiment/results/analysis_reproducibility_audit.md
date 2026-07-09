# Reproducibility and Compute Audit

This audit records the local compute envelope, manifest-level parallelism, artifact counts, and external-tool provenance.

| aspect | evidence | boundary |
|---|---|---|
| Host compute envelope | Apple M4 Pro; 14 physical/14 logical CPU cores; 24.0 GiB RAM; Apple M4 Pro, 20 GPU cores, Metal 4; Python 3.11.15 | Workstation context for reproducibility; not a hardware-mapping result. |
| Learning accelerator | PyTorch 2.12.0; MPS=True; CUDA=False | GPU/MPS is available for neural training; synthesis resources remain logical-layer estimates. |
| Parallel-run provenance | 54 manifests record worker counts; max workers=10; traditional resource 10 workers/1770 rows; RevKit CLI 8 workers/708 rows; ROS-style LUT 8 workers/927 rows; CirKit 8 workers/177 rows; mockturtle 4 workers/177 rows | Wall times are machine-dependent and are not claimed as portable speedups. |
| Artifact coverage | 77 top-level run/train/analyze scripts; 144 raw CSVs; 189 summaries; 88 manifests; 154 paper tables; 7 figure panels (21 PDF/PNG/SVG assets) | Counts describe the current artifact package, not independent datasets. |
| External-tool provenance | mockturtle 25beb0e; CirKit 4531533; RevKit CLI 104eb35 | Toolchain rows are logic-level probes or exact-oracle reversible probes, not full hardware flows. |
