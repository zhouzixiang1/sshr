# CNOT Constraint Profile Audit

This audit checks the small-function sweep rerun under a pure CNOT objective. It is not a post-hoc rescore: the search was run with the CNOT-only profile in `run_resource_sweep.py`.

## Status counts

- pass: 5

## Compact results

| method | functions | mean CNOT | CNOT change vs balanced | CNOT vs SSHR-H | CNOT best/tied functions | status |
|---|---:|---:|---:|---:|---:|---|
| Pareto-Resource-NMCTS | 47 | 71.3830 | -3.025875% | 14/33/0 | 14 | pass |
| Profile-Resource-NMCTS | 47 | 76.2340 | -5.536971% | 12/35/0 | 11 | pass |
| Resource-NMCTS | 47 | 76.9787 | -5.839495% | 12/35/0 | 11 | pass |
| Polarity archive | 47 | 73.6170 | -3.233924% | 12/35/0 | 10 | pass |
| Affine-NMCTS | 47 | 84.0638 | -0.812239% | 11/36/0 | 9 | pass |
| SSHR-H | 47 | 64.5957 | 0.000000% | 0/0/47 | 33 | pass |

## Interpretation

- The CNOT-only profile is an actual rerun profile, not only a changed reporting weight.
- Pareto-Resource-NMCTS lowers its CNOT count relative to its balanced-profile run, so the search responds to the resource constraint.
- SSHR-H remains the CNOT-specialized boundary; this supports a bounded resource-constrained claim, not CNOT-only dominance.

## Gate rows

| gate | status | evidence | next action |
|---|---|---|---|
| CNOT-only rerun coverage | pass | profiles=['ancilla_tight', 'balanced', 'cnot_depth', 'cnot_only', 't_heavy']; functions_cnot_only=47; raw_rows=2115; errors=0. | Rerun run_resource_sweep.py --resume after adding or changing resource profiles. |
| Pareto CNOT response | pass | Pareto CNOT-only mean=71.3830; same-method CNOT delta vs balanced=-3.025875%. | Inspect the CNOT-only SearchConfig and child profiles if Pareto does not reduce CNOT. |
| Profile-resource CNOT response | pass | Profile-Resource mean_CNOT=76.2340; same-method CNOT delta vs balanced=-5.536971%. | Inspect profile_resource_nmcts children if the CNOT-only profile does not change the selected circuit. |
| SSHR CNOT boundary | pass | Pareto vs SSHR-H CNOT=14/33/0; Pareto mean_CNOT=71.3830; SSHR-H mean_CNOT=64.5957. | Keep SSHR-H as a CNOT-oriented boundary unless a future CNOT-specific method changes this row. |
| Manuscript table anchors | pass | table_exists=True; anchors={'author': True, 'anonymous': True, 'acm': True}. | Add Table cnot-constraint-profile to author manuscript and regenerate anonymous/ACM drafts. |
