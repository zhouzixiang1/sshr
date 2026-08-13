# High-dimensional Guard Upgrade Diagnostic

This diagnostic compares the existing high-dimensional `and_resource_nmcts`
portfolio with `and_resource_nmcts_wide`, a bounded variant that adds a
wide-root linear-pair candidate (`fprm_linear_pair_wide_fast`).  The run uses
the same 12 `n=14` random ANF functions as `highdim_neural_prior` and disables
the learned model to isolate the deterministic guard change.

Rows: 24; errors: 0; skipped: 0; incorrect: 0.

## Mean resources

| method | functions | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|---:|
| and_resource_nmcts | 12 | 3326.67 | 5736.50 | 5738.33 | 3.50 | 3671.30 | 23.708 |
| and_resource_nmcts_wide | 12 | 3326.67 | 5736.50 | 5738.33 | 3.50 | 3671.30 | 32.704 |

## Paired comparison

| metric | W/L/T for wide | mean relative |
|---|---:|---:|
| T | 0/0/12 | +0.00% |
| CNOT | 0/0/12 | +0.00% |
| depth | 0/0/12 | +0.00% |
| peak ancilla | 0/0/12 | +0.00% |
| score | 0/0/12 | +0.00% |
| time | 0/12/0 | +59.80% |

## Interpretation

- The fast wide-root guard does not improve resource quality on this matched
  slice and increases runtime.
- The slower recursive wide-root variant showed only a small score gain in an
  exploratory run, so neither variant is currently strong enough to promote as
  a paper contribution.
- This supports keeping the paper's high-dimensional claim focused on the
  existing bounded linear-pair guard and treating stronger learned/wide root
  ranking as future work.
