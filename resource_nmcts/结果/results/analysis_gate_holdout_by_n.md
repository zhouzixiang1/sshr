# Structure Gate Holdout

Raw CSV: `results/raw_gate_holdout_resource.csv`.

The held-out set contains random ANF functions at `n=19` and `n=20`.
The gate is evaluated against full Resource-NMCTS, and adaptive screen is reported as the unsafe skip baseline.

## Gate

- feature: `n`
- threshold: `20.0`
- skip if >= threshold: `True`
- training false skips: `0`

## Dimension grouped comparison

| comparison | n | pairs | score W/L/T | mean score delta | time W/L/T | mean time delta |
|---|---:|---:|---:|---:|---:|---:|
| screen-gated Resource vs full Resource | 19 | 8 | 0/0/8 | +0.00% | 3/5/0 | +0.00% |
| screen-gated Resource vs full Resource | 20 | 8 | 0/0/8 | +0.00% | 8/0/0 | -73.66% |
| screen-gated Resource vs full Resource | all | 16 | 0/0/16 | +0.00% | 11/5/0 | -36.83% |
| adaptive screen vs full Resource | 19 | 8 | 0/4/4 | +14.14% | 8/0/0 | -94.42% |
| adaptive screen vs full Resource | 20 | 8 | 0/0/8 | +0.00% | 8/0/0 | -74.12% |
| adaptive screen vs full Resource | all | 16 | 0/4/12 | +7.07% | 16/0/0 | -84.27% |

Interpretation:

- At `n=19`, adaptive screen still loses score against full Resource-NMCTS on 4/8 held-out functions, so skipping the Resource tail would be unsafe.
- The conservative gate does not skip at `n=19`; it exactly matches full Resource-NMCTS resources and avoids the old midpoint extrapolation.
- At `n=20`, adaptive screen and full Resource-NMCTS tie on all 8 held-out functions; the gate skips the Resource tail and preserves all resource metrics while reducing mean runtime.
