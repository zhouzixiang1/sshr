# Bit-Flip Learned-Prior Difficulty Slices

This derived audit localizes the low-budget bit-flip learned-prior effect by no-prior score terciles.
Within each budget and method, functions are sorted by the matched no-prior score and split into easy, middle, and hard thirds.

## Status counts

- pass: 36

## Aggregate slices

| budget | difficulty slice | pairs | score W/L/T | mean score change | T W/L/T | mean T change | runtime change |
|---|---|---:|---:|---:|---:|---:|---:|
| top-8, 8/12 sim. | easy tercile | 177 | 33/0/144 | -0.41% | 3/0/174 | -0.42% | +25.38% |
| top-8, 8/12 sim. | middle tercile | 177 | 53/0/124 | -1.87% | 26/0/151 | -2.04% | +24.53% |
| top-8, 8/12 sim. | hard tercile | 177 | 23/0/154 | -0.84% | 14/0/163 | -0.78% | +17.05% |
| top-12, 12/16 sim. | easy tercile | 177 | 33/0/144 | -0.41% | 3/0/174 | -0.42% | +29.17% |
| top-12, 12/16 sim. | middle tercile | 177 | 53/0/124 | -1.87% | 26/0/151 | -2.04% | +29.68% |
| top-12, 12/16 sim. | hard tercile | 177 | 23/0/154 | -0.84% | 14/0/163 | -0.78% | +19.50% |
| top-24, 24/32 sim. | easy tercile | 177 | 31/0/146 | -0.42% | 3/0/174 | -0.42% | +73.71% |
| top-24, 24/32 sim. | middle tercile | 177 | 53/0/124 | -1.95% | 27/0/150 | -2.17% | +55.16% |
| top-24, 24/32 sim. | hard tercile | 177 | 26/0/151 | -0.97% | 18/0/159 | -0.95% | +36.23% |

## Interpretation

- Every aggregate slice has zero score losses, so the learned prior is non-degrading under these paired budgets.
- The largest mean score and T-count reductions occur in the middle no-prior-score tercile, where candidate ordering has room to improve but the functions are not already saturated by very hard tradeoffs.
- Runtime remains higher because Python model evaluation is included; the result is a search-quality localization, not a speedup claim.

## Method-slice rows

| budget | method | difficulty slice | pairs | score W/L/T | mean score change | runtime change |
|---|---|---|---:|---:|---:|---:|
| top-8, 8/12 sim. | and_affine_nmcts | easy tercile | 59 | 12/0/47 | -0.41% | +46.63% |
| top-8, 8/12 sim. | and_affine_nmcts | middle tercile | 59 | 22/0/37 | -2.57% | +34.02% |
| top-8, 8/12 sim. | and_affine_nmcts | hard tercile | 59 | 8/0/51 | -0.87% | +29.15% |
| top-8, 8/12 sim. | and_resource_nmcts | easy tercile | 59 | 11/0/48 | -0.41% | +21.72% |
| top-8, 8/12 sim. | and_resource_nmcts | middle tercile | 59 | 18/0/41 | -1.79% | +26.03% |
| top-8, 8/12 sim. | and_resource_nmcts | hard tercile | 59 | 9/0/50 | -1.00% | +14.49% |
| top-8, 8/12 sim. | and_pareto_resource_nmcts | easy tercile | 59 | 10/0/49 | -0.41% | +7.79% |
| top-8, 8/12 sim. | and_pareto_resource_nmcts | middle tercile | 59 | 13/0/46 | -1.25% | +13.54% |
| top-8, 8/12 sim. | and_pareto_resource_nmcts | hard tercile | 59 | 6/0/53 | -0.66% | +7.50% |
| top-12, 12/16 sim. | and_affine_nmcts | easy tercile | 59 | 12/0/47 | -0.41% | +36.91% |
| top-12, 12/16 sim. | and_affine_nmcts | middle tercile | 59 | 22/0/37 | -2.57% | +38.89% |
| top-12, 12/16 sim. | and_affine_nmcts | hard tercile | 59 | 8/0/51 | -0.87% | +26.83% |
| top-12, 12/16 sim. | and_resource_nmcts | easy tercile | 59 | 11/0/48 | -0.41% | +35.11% |
| top-12, 12/16 sim. | and_resource_nmcts | middle tercile | 59 | 18/0/41 | -1.79% | +29.38% |
| top-12, 12/16 sim. | and_resource_nmcts | hard tercile | 59 | 9/0/50 | -1.00% | +21.38% |
| top-12, 12/16 sim. | and_pareto_resource_nmcts | easy tercile | 59 | 10/0/49 | -0.41% | +15.48% |
| top-12, 12/16 sim. | and_pareto_resource_nmcts | middle tercile | 59 | 13/0/46 | -1.25% | +20.77% |
| top-12, 12/16 sim. | and_pareto_resource_nmcts | hard tercile | 59 | 6/0/53 | -0.66% | +10.28% |
| top-24, 24/32 sim. | and_affine_nmcts | easy tercile | 59 | 10/0/49 | -0.42% | +96.79% |
| top-24, 24/32 sim. | and_affine_nmcts | middle tercile | 59 | 22/0/37 | -2.78% | +103.05% |
| top-24, 24/32 sim. | and_affine_nmcts | hard tercile | 59 | 10/0/49 | -1.20% | +73.80% |
| top-24, 24/32 sim. | and_resource_nmcts | easy tercile | 59 | 11/0/48 | -0.44% | +101.52% |
| top-24, 24/32 sim. | and_resource_nmcts | middle tercile | 59 | 18/0/41 | -1.82% | +39.55% |
| top-24, 24/32 sim. | and_resource_nmcts | hard tercile | 59 | 10/0/49 | -1.03% | +24.27% |
| top-24, 24/32 sim. | and_pareto_resource_nmcts | easy tercile | 59 | 10/0/49 | -0.41% | +22.82% |
| top-24, 24/32 sim. | and_pareto_resource_nmcts | middle tercile | 59 | 13/0/46 | -1.25% | +22.86% |
| top-24, 24/32 sim. | and_pareto_resource_nmcts | hard tercile | 59 | 6/0/53 | -0.66% | +10.63% |
