# RevKit CLI Reversible Baseline

Scope: each Boolean function is embedded as the exact reversible oracle permutation `(x,y)->(x,y xor f(x))`; legacy RevKit CLI reads that SPEC permutation and runs the configured reversible synthesis flow.  The default run uses `tbs`.

This is a legacy RevKit/CirKit command-line reversible-synthesis probe.  It is logic-layer only and does not include hardware mapping.

- RevKit binary: `/Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit_legacy/build/programs/revkit`
- RevKit root: `/Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit_legacy`
- RevKit commit: `104eb35f1933b080aa228ad419756f04682d4a2e`
- CLI flow rows attempted: 531
- usable CLI flow rows: 531
- synthetic best-score portfolio rows: 177
- error CLI flow rows: 0
- timeout CLI flow rows: 0
- median time: 0.0619 s
- max time: 0.1062 s

## Comparisons

| Target | Baseline | Metric | Items | W/L/T | Mean relative | Median relative |
|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_revkit_cli_best_score | score | 177 | 173/0/4 | -66.32% | -68.76% |
| and_resource_nmcts | external_revkit_cli_best_score | T | 177 | 173/0/4 | -71.64% | -73.91% |
| and_resource_nmcts | external_revkit_cli_best_score | CNOT | 177 | 102/70/5 | -4.75% | -7.76% |
| and_resource_nmcts | external_revkit_cli_best_score | depth | 177 | 88/82/7 | +1.43% | +0.00% |
| and_resource_nmcts | external_revkit_cli_best_score | peak_ancilla | 177 | 0/169/8 | +142.37% | +100.00% |
| and_pareto_resource_nmcts | external_revkit_cli_best_score | score | 177 | 173/0/4 | -67.28% | -70.18% |
| and_pareto_resource_nmcts | external_revkit_cli_best_score | T | 177 | 173/0/4 | -72.59% | -74.60% |
| and_pareto_resource_nmcts | external_revkit_cli_best_score | CNOT | 177 | 107/63/7 | -9.32% | -9.30% |
| and_pareto_resource_nmcts | external_revkit_cli_best_score | depth | 177 | 90/79/8 | -2.87% | -2.22% |
| and_pareto_resource_nmcts | external_revkit_cli_best_score | peak_ancilla | 177 | 0/169/8 | +153.11% | +100.00% |
| and_fprm_polarity_archive | external_revkit_cli_best_score | score | 177 | 173/0/4 | -64.24% | -67.36% |
| and_fprm_polarity_archive | external_revkit_cli_best_score | T | 177 | 173/0/4 | -69.97% | -73.13% |
| and_fprm_polarity_archive | external_revkit_cli_best_score | CNOT | 177 | 91/78/8 | -3.53% | -1.39% |
| and_fprm_polarity_archive | external_revkit_cli_best_score | depth | 177 | 76/94/7 | +2.60% | +3.47% |
| and_fprm_polarity_archive | external_revkit_cli_best_score | peak_ancilla | 177 | 0/171/6 | +161.02% | +100.00% |
| and_direct_anf | external_revkit_cli_best_score | score | 177 | 167/6/4 | -32.79% | -37.90% |
| and_direct_anf | external_revkit_cli_best_score | T | 177 | 169/3/5 | -39.23% | -44.35% |
| and_direct_anf | external_revkit_cli_best_score | CNOT | 177 | 5/164/8 | +71.98% | +47.30% |
| and_direct_anf | external_revkit_cli_best_score | depth | 177 | 5/164/8 | +72.33% | +47.83% |
| and_direct_anf | external_revkit_cli_best_score | peak_ancilla | 177 | 0/169/8 | +167.80% | +200.00% |
| direct_anf | external_revkit_cli_best_score | score | 177 | 87/86/4 | +5.78% | +0.00% |
| direct_anf | external_revkit_cli_best_score | T | 177 | 92/78/7 | +3.30% | -2.12% |
| direct_anf | external_revkit_cli_best_score | CNOT | 177 | 0/116/61 | +43.81% | +33.33% |
| direct_anf | external_revkit_cli_best_score | depth | 177 | 0/116/61 | +44.21% | +34.21% |
| direct_anf | external_revkit_cli_best_score | peak_ancilla | 177 | 0/135/42 | +83.05% | +100.00% |
| and_esop_milp | external_revkit_cli_best_score | score | 177 | 172/1/4 | -51.50% | -53.67% |
| and_esop_milp | external_revkit_cli_best_score | T | 177 | 173/0/4 | -57.39% | -60.66% |
| and_esop_milp | external_revkit_cli_best_score | CNOT | 177 | 93/75/9 | +21.18% | -3.41% |
| and_esop_milp | external_revkit_cli_best_score | depth | 177 | 55/115/7 | +43.82% | +14.58% |
| and_esop_milp | external_revkit_cli_best_score | peak_ancilla | 177 | 0/170/7 | +182.49% | +200.00% |
| sshr_h | external_revkit_cli_best_score | score | 177 | 170/7/0 | +83.84% | -48.55% |
| sshr_h | external_revkit_cli_best_score | T | 177 | 170/7/0 | +69.71% | -51.52% |
| sshr_h | external_revkit_cli_best_score | CNOT | 177 | 154/19/4 | +5.15% | -24.73% |
| sshr_h | external_revkit_cli_best_score | depth | 177 | 88/84/5 | +34.11% | +0.00% |
| sshr_h | external_revkit_cli_best_score | peak_ancilla | 177 | 0/138/39 | +85.88% | +100.00% |
| and_resource_nmcts | external_revkit_cli_dbs | score | 177 | 173/0/4 | -68.30% | -70.94% |
| and_resource_nmcts | external_revkit_cli_dbs | T | 177 | 173/0/4 | -73.30% | -75.35% |
| and_resource_nmcts | external_revkit_cli_dbs | CNOT | 177 | 92/78/7 | -2.69% | -2.78% |
| and_resource_nmcts | external_revkit_cli_dbs | depth | 177 | 78/93/6 | +3.74% | +2.94% |
| and_resource_nmcts | external_revkit_cli_dbs | peak_ancilla | 177 | 2/160/15 | +126.55% | +100.00% |
| and_pareto_resource_nmcts | external_revkit_cli_dbs | score | 177 | 173/0/4 | -69.22% | -71.92% |
| and_pareto_resource_nmcts | external_revkit_cli_dbs | T | 177 | 173/0/4 | -74.20% | -76.96% |
| and_pareto_resource_nmcts | external_revkit_cli_dbs | CNOT | 177 | 100/68/9 | -7.49% | -5.56% |
| and_pareto_resource_nmcts | external_revkit_cli_dbs | depth | 177 | 83/87/7 | -0.78% | +0.00% |
| and_pareto_resource_nmcts | external_revkit_cli_dbs | peak_ancilla | 177 | 2/160/15 | +137.29% | +100.00% |
| and_fprm_polarity_archive | external_revkit_cli_dbs | score | 177 | 173/0/4 | -66.49% | -69.15% |
| and_fprm_polarity_archive | external_revkit_cli_dbs | T | 177 | 173/0/4 | -71.80% | -74.60% |
| and_fprm_polarity_archive | external_revkit_cli_dbs | CNOT | 177 | 83/85/9 | -1.72% | +0.00% |
| and_fprm_polarity_archive | external_revkit_cli_dbs | depth | 177 | 66/103/8 | +4.59% | +6.12% |
| and_fprm_polarity_archive | external_revkit_cli_dbs | peak_ancilla | 177 | 0/164/13 | +145.20% | +100.00% |
| and_direct_anf | external_revkit_cli_dbs | score | 177 | 167/6/4 | -36.49% | -38.98% |
| and_direct_anf | external_revkit_cli_dbs | T | 177 | 169/3/5 | -42.59% | -44.62% |
| and_direct_anf | external_revkit_cli_dbs | CNOT | 177 | 14/158/5 | +76.04% | +63.73% |
| and_direct_anf | external_revkit_cli_dbs | depth | 177 | 14/159/4 | +76.61% | +64.71% |
| and_direct_anf | external_revkit_cli_dbs | peak_ancilla | 177 | 2/160/15 | +151.98% | +100.00% |
| direct_anf | external_revkit_cli_dbs | score | 177 | 89/84/4 | +0.10% | -0.07% |
| direct_anf | external_revkit_cli_dbs | T | 177 | 94/78/5 | -2.31% | -3.70% |
| direct_anf | external_revkit_cli_dbs | CNOT | 177 | 24/144/9 | +47.33% | +43.55% |
| direct_anf | external_revkit_cli_dbs | depth | 177 | 22/145/10 | +47.93% | +44.64% |
| direct_anf | external_revkit_cli_dbs | peak_ancilla | 177 | 2/112/63 | +67.23% | +100.00% |
| and_esop_milp | external_revkit_cli_dbs | score | 177 | 172/1/4 | -54.47% | -59.02% |
| and_esop_milp | external_revkit_cli_dbs | T | 177 | 173/0/4 | -60.02% | -64.29% |
| and_esop_milp | external_revkit_cli_dbs | CNOT | 177 | 91/76/10 | +24.39% | -2.59% |
| and_esop_milp | external_revkit_cli_dbs | depth | 177 | 48/123/6 | +48.00% | +14.63% |
| and_esop_milp | external_revkit_cli_dbs | peak_ancilla | 177 | 2/163/12 | +166.67% | +200.00% |
| sshr_h | external_revkit_cli_dbs | score | 177 | 171/6/0 | +80.65% | -51.04% |
| sshr_h | external_revkit_cli_dbs | T | 177 | 171/6/0 | +66.67% | -53.03% |
| sshr_h | external_revkit_cli_dbs | CNOT | 177 | 153/20/4 | +6.31% | -22.92% |
| sshr_h | external_revkit_cli_dbs | depth | 177 | 82/90/5 | +35.88% | +2.17% |
| sshr_h | external_revkit_cli_dbs | peak_ancilla | 177 | 2/117/58 | +70.06% | +100.00% |
| and_resource_nmcts | external_revkit_cli_rms | score | 177 | 173/0/4 | -71.49% | -74.78% |
| and_resource_nmcts | external_revkit_cli_rms | T | 177 | 173/0/4 | -75.90% | -78.95% |
| and_resource_nmcts | external_revkit_cli_rms | CNOT | 177 | 164/9/4 | -31.46% | -34.06% |
| and_resource_nmcts | external_revkit_cli_rms | depth | 177 | 162/10/5 | -27.21% | -29.58% |
| and_resource_nmcts | external_revkit_cli_rms | peak_ancilla | 177 | 0/170/7 | +145.20% | +100.00% |
| and_pareto_resource_nmcts | external_revkit_cli_rms | score | 177 | 173/0/4 | -72.24% | -75.34% |
| and_pareto_resource_nmcts | external_revkit_cli_rms | T | 177 | 173/0/4 | -76.66% | -79.59% |
| and_pareto_resource_nmcts | external_revkit_cli_rms | CNOT | 177 | 164/9/4 | -34.20% | -37.50% |
| and_pareto_resource_nmcts | external_revkit_cli_rms | depth | 177 | 163/9/5 | -29.74% | -33.51% |
| and_pareto_resource_nmcts | external_revkit_cli_rms | peak_ancilla | 177 | 0/170/7 | +155.93% | +100.00% |
| and_fprm_polarity_archive | external_revkit_cli_rms | score | 177 | 173/0/4 | -69.65% | -71.69% |
| and_fprm_polarity_archive | external_revkit_cli_rms | T | 177 | 173/0/4 | -74.44% | -76.61% |
| and_fprm_polarity_archive | external_revkit_cli_rms | CNOT | 177 | 162/11/4 | -29.73% | -32.81% |
| and_fprm_polarity_archive | external_revkit_cli_rms | depth | 177 | 160/13/4 | -25.57% | -28.57% |
| and_fprm_polarity_archive | external_revkit_cli_rms | peak_ancilla | 177 | 0/172/5 | +163.84% | +100.00% |
| and_direct_anf | external_revkit_cli_rms | score | 177 | 173/0/4 | -44.83% | -43.51% |
| and_direct_anf | external_revkit_cli_rms | T | 177 | 173/0/4 | -50.05% | -48.72% |
| and_direct_anf | external_revkit_cli_rms | CNOT | 177 | 6/156/15 | +18.66% | +17.65% |
| and_direct_anf | external_revkit_cli_rms | depth | 177 | 6/156/15 | +18.58% | +17.39% |
| and_direct_anf | external_revkit_cli_rms | peak_ancilla | 177 | 0/170/7 | +170.62% | +200.00% |
| direct_anf | external_revkit_cli_rms | score | 177 | 169/3/5 | -13.90% | -14.44% |
| direct_anf | external_revkit_cli_rms | T | 177 | 169/0/8 | -15.82% | -16.34% |
| direct_anf | external_revkit_cli_rms | CNOT | 177 | 0/0/177 | +0.00% | +0.00% |
| direct_anf | external_revkit_cli_rms | depth | 177 | 0/0/177 | +0.00% | +0.00% |
| direct_anf | external_revkit_cli_rms | peak_ancilla | 177 | 0/138/39 | +85.88% | +100.00% |
| and_esop_milp | external_revkit_cli_rms | score | 177 | 173/0/4 | -59.20% | -61.50% |
| and_esop_milp | external_revkit_cli_rms | T | 177 | 173/0/4 | -64.04% | -66.67% |
| and_esop_milp | external_revkit_cli_rms | CNOT | 177 | 130/43/4 | -15.14% | -29.31% |
| and_esop_milp | external_revkit_cli_rms | depth | 177 | 118/52/7 | -0.14% | -17.14% |
| and_esop_milp | external_revkit_cli_rms | peak_ancilla | 177 | 0/170/7 | +185.31% | +200.00% |
| sshr_h | external_revkit_cli_rms | score | 177 | 171/6/0 | +75.23% | -57.84% |
| sshr_h | external_revkit_cli_rms | T | 177 | 171/6/0 | +61.64% | -61.06% |
| sshr_h | external_revkit_cli_rms | CNOT | 177 | 169/7/1 | -14.64% | -47.55% |
| sshr_h | external_revkit_cli_rms | depth | 177 | 153/22/2 | +7.54% | -32.28% |
| sshr_h | external_revkit_cli_rms | peak_ancilla | 177 | 0/141/36 | +88.70% | +100.00% |
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
