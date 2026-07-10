# Runtime Envelope Audit

This audit summarizes workstation wall-clock evidence already present in raw CSV artifacts.
It supports reproducibility and feasibility checks, not portable runtime-speedup claims.

## Status counts

- pass: 5

| slice | scope | rows ok | time evidence | boundary | status |
|---|---|---:|---|---|---|
| Traditional n<=6 Resource-NMCTS | 177 matched benchmark functions | 177/177 | median=4.15s; p95=9.78s; max=15.44s | Small-function timing context only; headline claims are paired logical-resource improvements. | pass |
| External logic-tool probes | ROS-style LUT, Caterpillar, mockturtle, CirKit, RevKit | 1548/1548 | median=0.08s; p95=0.51s; max=19.06s | Tool rows are bounded logic-level probes or exact-oracle probes, not hardware-mapped baselines. | pass |
| High-dimensional symbolic frontier | n=24,28,32,40 plus n=48,56,64 | 144/144 | median=3.30s; p95=52.14s; max=117.72s | Symbolic emitted-circuit checks; no exhaustive truth tables outside bridge slices. | pass |
| Complete truth-table bridge | n=21--30 generated bridge slices | 70/70 | median=2.85s; p95=14.87s; max=17.02s; truth_verify median=0.19s | Complete checking is limited to generated bridge slices and is not global high-dimensional enumeration. | pass |
| Learned-control runtime boundary | compressed bit-flip budgets plus promoted learned controls | 708/708 | median=2.12s; p95=6.41s; max=7.72s; fitted-Q policy median=0.44s; always-Pareto median=2.77s | Learned controls are quality/budget evidence with explicit overhead or savings, not a blanket speedup claim. | pass |
