# Boolean Screen Depth-2 Guard Modes

Two deployment modes were evaluated for held-out `n=20` depth-guard test slices.

| mode | features | execution | test pairs | skips | false skips | score W/L/T vs depth-2 | mean score vs depth-2 | mean time vs depth-2 | mean time vs all-depth |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| static-direct | static ANF/action features | dispatch directly to depth-1 or depth-2 | 96 | 4 | 0 | 0/0/96 | +0.00% | -0.54% | -24.74% |
| shallow-staged high-confidence | static + single/depth-1 screen features | run shallow screens, then skip or fall back | 48 | 8 | 0 | 0/0/48 | +0.00% | +29.10% | -7.81% |

Interpretation:

- `static-direct` is the deployable default: it does not need to run shallow screens before choosing depth-2, so it removes most all-depth adaptive overhead, preserves the fixed depth-2 score, and is now slightly faster than fixed depth-2 on the larger held-out slice.
- `shallow-staged high-confidence` reaches 8/48 safe skips on its auxiliary slice, while the larger static-direct run reaches 4/96 safe skips. The staged mode pays the cost of single and depth-1 screens before the decision, so it is useful evidence that shallow observations identify more safe skips, but it is not faster than running fixed depth-2 alone.
- Both modes keep zero false skips and zero score losses on their held-out test slices. The result is still a structure-level guard, not a final high-dimensional quality breakthrough.
