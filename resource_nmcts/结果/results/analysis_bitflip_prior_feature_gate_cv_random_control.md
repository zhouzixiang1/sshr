# Random-Interval Control for the CV ANF-Term Gate

This audit asks whether the cross-validated ANF-term gate is better than arbitrary intervals of the same fold-wise width.
It samples 200 deterministic random interval assignments over the observed ANF-term range and compares them with the training-support CV gate.

## Summary

| control | repeats | full-retained repeats | retained learned wins | score W/L/T | mean score | time | overhead cut |
|---|---:|---:|---:|---:|---:|---:|---:|
| CV learned-win support gate | 1 | 1 | 328/328 (100.00%) | 328/0/1265 | -1.07% | +31.40% | +8.94% |
| Random same-width intervals mean | 200 | 0 | 220.7/328 (67.29%) | 221/0/1372 | -0.75% | +20.88% | +39.46% |
| Random same-width intervals p95 retained | 200 | 0 | 304/328 (92.68%) | 304/0/1450 | -1.05% | +27.47% | +58.07% |
| Best random retained interval | 200 | 0 | 319/328 (97.26%) | 319/0/1274 | -1.06% | +26.19% | +24.06% |

## Interpretation

- The learned-support CV gate retains all 328 learned-prior score wins with zero score losses.
- No random same-width interval assignment retains all learned wins (0/200).
- The best random retained interval keeps 319/328 learned wins; the random mean keeps 67.29%.
- Random intervals often cut more runtime because they skip useful learned-prior rows, so overhead alone is not a sufficient quality metric.

## CV gate source

- CV gate audit: `results/analysis_bitflip_prior_feature_gate_cv.md`
