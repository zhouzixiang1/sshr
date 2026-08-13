# Cross-Validated Bit-Flip Learned-Prior Feature Gate

This audit tests whether the ANF-term gate can be selected without looking at held-out functions.
Functions are split into 5 deterministic folds by SHA-256(name) modulo 5.
For each fold, the gate is the training-fold learned-win ANF-term support interval expanded by 2 terms on each side.

## Status counts

- pass: 6

## Held-out fold rows

| fold | train pairs | test pairs | train win support | selected gate | enabled | score W/L/T | mean score | time | always-learned time | overhead cut |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1305 | 288 | 6--23 | 4--25 | 225 | 68/0/220 | -1.57% | +29.75% | +31.00% | +4.03% |
| 1 | 1296 | 297 | 6--23 | 4--25 | 225 | 32/0/265 | -0.79% | +31.35% | +33.40% | +6.15% |
| 2 | 1269 | 324 | 6--23 | 4--25 | 261 | 54/0/270 | -0.41% | +36.92% | +39.87% | +7.39% |
| 3 | 1314 | 279 | 6--21 | 4--23 | 225 | 38/0/241 | -0.52% | +27.16% | +28.00% | +3.01% |
| 4 | 1188 | 405 | 6--23 | 4--25 | 333 | 136/0/269 | -1.81% | +31.14% | +37.94% | +17.93% |

## Aggregate held-out result

- Held-out pairs: 1593; learned enabled: 1269; score W/L/T: 328/0/1265.
- Retained learned score wins: 328/328 (100.00%).
- Mean score change: -1.07%; time change: +31.40%; always-learned time: +34.49%; overhead cut: +8.94%.

## Interpretation

- The held-out folds keep every learned-prior score win while preserving zero score losses.
- The cross-validated rule is weaker than a final retrained deployment interval but stronger than a purely explanatory no-prior-score slice.
- The rule still uses existing benchmark rows, so it is evidence for input-feature gate stability rather than a new large-scale learned-policy theorem.
