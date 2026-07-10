# Boolean-Ring Structural Evidence

This audit consolidates high-dimensional Boolean-ring and Boolean-screen comparisons.
Negative relative changes favor the first method in the comparison.

| slice | comparison | pairs | score W/L/T | mean score change | mean T change | mean CNOT change | mean depth change | mean ancilla change | mean time change | interpretation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| n=14 | Boolean guard vs pairwise-wide | 12 | 9/0/3 | -0.82% | -0.81% | -0.95% | -0.95% | +3.75% | +32.80% | quality gain; slower exhaustive guard |
| n=16 | Boolean guard vs pairwise-wide | 24 | 14/0/10 | -0.34% | -0.34% | -0.38% | -0.38% | +0.00% | +22.80% | quality gain; slower guard |
| n=16 | Boolean guard vs deterministic deep | 24 | 18/0/6 | -0.52% | -0.52% | -0.50% | -0.50% | +0.83% | +356.64% | stronger quality branch; expensive |
| n=16 | Boolean-linear deep vs pairwise-wide | 24 | 14/6/4 | -0.22% | -0.21% | -0.30% | -0.30% | +0.35% | -72.31% | fast structural variant with small quality gain |
| n=20 | Resource update vs Boolean screen | 6 | 5/0/1 | -4.52% | -4.62% | -4.11% | -4.11% | +7.50% | +453.05% | quality frontier; much slower |
| n=20 | Screen gate vs full Resource | 6 | 0/0/6 | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | -75.58% | safe skip: same resources, less planning time |
| n=20 | Recursive Boolean screen vs old Resource | 6 | 5/0/1 | -7.47% | -7.64% | -6.65% | -6.65% | +13.06% | -7.32% | large-n positive screen; ancilla tradeoff |
| n=18 | Recursive Boolean screen vs old Resource | 12 | 0/11/1 | +36.94% | +38.75% | +26.74% | +25.41% | -0.83% | -97.90% | speed-only negative control; not promoted |

Interpretation:

- Boolean-ring guards improve score on the n=14 and n=16 slices, but the more exhaustive guard is slower.
- The n=20 screen gate preserves the full Resource-NMCTS resource vector while reducing planning time.
- The n=18 recursive screen row is a useful negative control: it is much faster but worse in score, so it should not be promoted as a quality result.
