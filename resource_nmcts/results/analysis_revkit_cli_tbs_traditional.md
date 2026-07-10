# RevKit CLI Reversible Baseline

Scope: each Boolean function is embedded as the exact reversible oracle permutation `(x,y)->(x,y xor f(x))`; legacy RevKit CLI reads that SPEC permutation and runs the configured reversible synthesis flow.  The default run uses `tbs`.

This is a legacy RevKit/CirKit command-line reversible-synthesis probe.  It is logic-layer only and does not include hardware mapping.

- RevKit binary: `/Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit_legacy/build/programs/revkit`
- RevKit root: `/Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit_legacy`
- RevKit commit: `104eb35f1933b080aa228ad419756f04682d4a2e`
- CLI flow rows attempted: 177
- usable CLI flow rows: 177
- synthetic best-score portfolio rows: 0
- error CLI flow rows: 0
- timeout CLI flow rows: 0
- median time: 0.0917 s
- max time: 0.1062 s

## Comparisons

| Target | Baseline | Metric | Items | W/L/T | Mean relative | Median relative |
|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_revkit_cli_tbs | score | 177 | 173/0/4 | -71.49% | -74.78% |
| and_resource_nmcts | external_revkit_cli_tbs | T | 177 | 173/0/4 | -75.90% | -78.95% |
| and_resource_nmcts | external_revkit_cli_tbs | CNOT | 177 | 164/9/4 | -31.46% | -34.06% |
| and_resource_nmcts | external_revkit_cli_tbs | depth | 177 | 162/10/5 | -27.21% | -29.58% |
| and_resource_nmcts | external_revkit_cli_tbs | peak_ancilla | 177 | 0/170/7 | +145.20% | +100.00% |
| and_pareto_resource_nmcts | external_revkit_cli_tbs | score | 177 | 173/0/4 | -72.24% | -75.34% |
| and_pareto_resource_nmcts | external_revkit_cli_tbs | T | 177 | 173/0/4 | -76.66% | -79.59% |
| and_pareto_resource_nmcts | external_revkit_cli_tbs | CNOT | 177 | 164/9/4 | -34.20% | -37.50% |
| and_pareto_resource_nmcts | external_revkit_cli_tbs | depth | 177 | 163/9/5 | -29.74% | -33.51% |
| and_pareto_resource_nmcts | external_revkit_cli_tbs | peak_ancilla | 177 | 0/170/7 | +155.93% | +100.00% |
| and_fprm_polarity_archive | external_revkit_cli_tbs | score | 177 | 173/0/4 | -69.65% | -71.69% |
| and_fprm_polarity_archive | external_revkit_cli_tbs | T | 177 | 173/0/4 | -74.44% | -76.61% |
| and_fprm_polarity_archive | external_revkit_cli_tbs | CNOT | 177 | 162/11/4 | -29.73% | -32.81% |
| and_fprm_polarity_archive | external_revkit_cli_tbs | depth | 177 | 160/13/4 | -25.57% | -28.57% |
| and_fprm_polarity_archive | external_revkit_cli_tbs | peak_ancilla | 177 | 0/172/5 | +163.84% | +100.00% |
| and_direct_anf | external_revkit_cli_tbs | score | 177 | 173/0/4 | -44.83% | -43.51% |
| and_direct_anf | external_revkit_cli_tbs | T | 177 | 173/0/4 | -50.05% | -48.72% |
| and_direct_anf | external_revkit_cli_tbs | CNOT | 177 | 6/156/15 | +18.66% | +17.65% |
| and_direct_anf | external_revkit_cli_tbs | depth | 177 | 6/156/15 | +18.58% | +17.39% |
| and_direct_anf | external_revkit_cli_tbs | peak_ancilla | 177 | 0/170/7 | +170.62% | +200.00% |
| direct_anf | external_revkit_cli_tbs | score | 177 | 169/3/5 | -13.90% | -14.44% |
| direct_anf | external_revkit_cli_tbs | T | 177 | 169/0/8 | -15.82% | -16.34% |
| direct_anf | external_revkit_cli_tbs | CNOT | 177 | 0/0/177 | +0.00% | +0.00% |
| direct_anf | external_revkit_cli_tbs | depth | 177 | 0/0/177 | +0.00% | +0.00% |
| direct_anf | external_revkit_cli_tbs | peak_ancilla | 177 | 0/138/39 | +85.88% | +100.00% |
| and_esop_milp | external_revkit_cli_tbs | score | 177 | 173/0/4 | -59.20% | -61.50% |
| and_esop_milp | external_revkit_cli_tbs | T | 177 | 173/0/4 | -64.04% | -66.67% |
| and_esop_milp | external_revkit_cli_tbs | CNOT | 177 | 130/43/4 | -15.14% | -29.31% |
| and_esop_milp | external_revkit_cli_tbs | depth | 177 | 118/52/7 | -0.14% | -17.14% |
| and_esop_milp | external_revkit_cli_tbs | peak_ancilla | 177 | 0/170/7 | +185.31% | +200.00% |
| sshr_h | external_revkit_cli_tbs | score | 177 | 171/6/0 | +75.23% | -57.84% |
| sshr_h | external_revkit_cli_tbs | T | 177 | 171/6/0 | +61.64% | -61.06% |
| sshr_h | external_revkit_cli_tbs | CNOT | 177 | 169/7/1 | -14.64% | -47.55% |
| sshr_h | external_revkit_cli_tbs | depth | 177 | 153/22/2 | +7.54% | -32.28% |
| sshr_h | external_revkit_cli_tbs | peak_ancilla | 177 | 0/141/36 | +88.70% | +100.00% |

## Interpretation

- This probe removes the previous boundary that legacy RevKit CLI was unavailable locally: the CLI was built from the legacy `develop` branch and exercised on exact reversible oracle specifications.
- `T` is RevKit's own Maslov-style T-count from `ps -c`; CNOT and depth are derived from the Toffoli control distribution using the project's MCT cost table.
- `peak_ancilla` is derived from RevKit logic qubits relative to the `n+1` oracle lines, so this comparison focuses on logical line usage rather than hardware routing or magic-state factories.
- Successful rows are checked for oracle-permutation bijectivity before invoking RevKit.  RevKit synthesis correctness is delegated to `read_spec` plus the deterministic synthesis command accepting the exact permutation.
