# Structure Gate Training

The gate predicts whether the adaptive Boolean-ring screen is sufficient,
or whether the expensive Resource-NMCTS tail should still run.

## Learned gate

- model: `decision_stump`
- feature: `n`
- threshold: `20`
- skip if >= threshold: `True`
- training examples: 18
- training errors: 1
- training false skips: 0
- apparent saved time: 338.589 s

## Confusion Matrix

| truth / prediction | skip resource | run resource |
|---|---:|---:|
| skip resource | 6 | 1 |
| run resource | 0 | 11 |

## Training Rows

| name | n | anf terms | resource gain vs screen | predicted skip | true skip | screen time | resource time |
|---|---:|---:|---:|---:|---:|---:|---:|
| anf_n18_0 | 18 | 21 | +0.00% | False | True | 0.860 | 65.535 |
| anf_n18_1 | 18 | 1130 | -31.22% | False | False | 6.753 | 300.008 |
| anf_n18_10 | 18 | 558 | -25.96% | False | False | 3.012 | 300.011 |
| anf_n18_11 | 18 | 208 | -25.38% | False | False | 1.499 | 211.603 |
| anf_n18_2 | 18 | 1218 | -31.25% | False | False | 6.915 | 300.018 |
| anf_n18_3 | 18 | 2276 | -32.80% | False | False | 14.179 | 300.035 |
| anf_n18_4 | 18 | 417 | -26.33% | False | False | 2.301 | 276.813 |
| anf_n18_5 | 18 | 755 | -30.88% | False | False | 4.421 | 299.984 |
| anf_n18_6 | 18 | 45 | -12.09% | False | False | 0.771 | 80.991 |
| anf_n18_7 | 18 | 1612 | -33.17% | False | False | 9.647 | 300.008 |
| anf_n18_8 | 18 | 227 | -25.35% | False | False | 1.597 | 214.396 |
| anf_n18_9 | 18 | 12 | -11.72% | False | False | 0.723 | 64.740 |
| anf_n20_0 | 20 | 30 | +0.00% | True | True | 10.510 | 62.460 |
| anf_n20_1 | 20 | 4265 | +0.00% | True | True | 47.356 | 115.754 |
| anf_n20_2 | 20 | 682 | +0.00% | True | True | 14.045 | 67.589 |
| anf_n20_3 | 20 | 216 | +0.00% | True | True | 11.233 | 64.013 |
| anf_n20_4 | 20 | 2952 | +0.00% | True | True | 30.486 | 91.195 |
| anf_n20_5 | 20 | 19 | +0.00% | True | True | 10.378 | 61.586 |
