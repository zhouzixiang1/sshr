# Sparse Depth Frontier Audit

The sparse frontier evaluates only `screen_depth2` and `screen_depth4`,
then selects the lower-score plan.  It is compared against the full
`screen_depth2/3/4` frontier measured in the same raw files.

| source | n scope | pairs | score W/L/T vs full | mean score change | mean time change | depth4 vs depth3 W/L/T | full depth3 selections | verified rows |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| scale-frontier | 20,28,40 | 72 | 0/0/72 | +0.00% | -27.57% | 44/0/28 | 6 | 216/216 |
| scale-generalization | 24,28,32,40 | 96 | 0/0/96 | +0.00% | -28.17% | 52/0/44 | 18 | 288/288 |
| truth-bridge-n23 | 23 | 6 | 0/0/6 | +0.00% | -24.94% | 5/0/1 | 1 | 18/18 |
| truth-bridge-n24 | 24 | 6 | 0/0/6 | +0.00% | -28.88% | 3/0/3 | 1 | 18/18 |
| truth-bridge-n25 | 25 | 6 | 0/0/6 | +0.00% | -27.06% | 4/0/2 | 0 | 18/18 |
| truth-bridge-n26 | 26 | 6 | 0/0/6 | +0.00% | -27.21% | 3/0/3 | 2 | 18/18 |

Interpretation:

- The sparse depth-2/4 frontier exactly matches the full depth-2/3/4 frontier on every listed slice.
- The improvement is a planning-cost reduction, not a new hardware-mapping claim.
- Depth 3 is retained as an audited candidate in the raw data, but it is not selected once depth 4 is available in these slices.
