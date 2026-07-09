# Learned-Control Effect Uncertainty

This audit adds deterministic paired bootstrap intervals to learned-control components with instance-level paired evidence.
Intervals use 3000 percentile bootstrap resamples per row.
Negative score changes favor the learned or gated target.  Effort columns are planning time, runtime, exact evaluations, or blank when runtime is not claimed.

## Status counts

- pass: 8

| component | class | pairs | score mean [95% CI] | effort mean [95% CI] | interpretation | status |
|---|---|---:|---:|---:|---|---|
| Depth-frontier policy | promoted | 48 | +0.04% [+0.00, +0.09] | planning time: -51.30% [-56.82, -45.67] | Preserves oracle-frontier score within a narrow interval while reducing all-depth evaluation effort. | pass |
| Stage-gated frontier | promoted | 96 | +0.04% [+0.00, +0.09] | planning time: -25.43% [-30.80, -20.15] | Validation-calibrated gate keeps score near the all-depth frontier while reducing planning time. | pass |
| Sparse depth-4 gate | promoted | 144 | +0.00% [+0.00, +0.00] | evaluation time: -13.43% [-17.20, -9.86] | Seed-stable skip gate preserves sparse-frontier score and reduces sparse-frontier evaluation time. | pass |
| Rank-diverse phase shortlist | promoted | 38 | -2.48% [-5.21, -0.26] | exact forms: -93.75% [-93.75, -93.75] | Policy shortlist improves the small-budget score while using far fewer exact evaluations than wide128. | pass |
| Bit-flip learned prior | limited | 177 | -0.15% [-0.30, -0.03] | runtime: +48.05% [+30.91, +68.18] | Score effect is small and runtime-positive, so this remains a limited quality signal, not a speed claim. | pass |
| Bit-flip low-budget prior | bounded | 1062 | -1.04% [-1.25, -0.84] | runtime: +24.22% [+21.90, +26.72] | Low-budget learned prior has a bounded quality effect with visible runtime cost. | pass |
| Boolean neural guard | limited | 24 | -0.12% [-0.27, -0.00] | runtime: +94.49% [+81.75, +106.10] | Quality effect is small and runtime-positive, so this remains a limited guard diagnostic. | pass |
| Root-action neural candidate extension | bounded | 33 | -0.08% [-0.16, -0.02] |  | Root-only candidate extension is bounded score evidence; runtime is not claimed. | pass |
