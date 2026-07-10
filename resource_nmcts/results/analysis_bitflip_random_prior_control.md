# Bit-Flip Random-Prior Control

This audit compares the learned bit-flip prior with same-budget deterministic random priors.
The random-prior scorer has the same `score_many()` interface as the neural scorer and changes only action-prior ranking; all semantic checks and candidate legality remain unchanged.

## Status counts

- pass: 18

## Score headline

| method | pairs | random repeats | W/L/T vs random mean | mean learned | mean random | mean relative | seed means beaten | learned <= best random | W/L/T vs no prior |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Affine-Resource-NMCTS | 177 | 8 | 20/12/145 | 55.36983051 | 55.43321328 | -0.12% | 8/8 | 165/177 | 42/0/135 |
| Resource-NMCTS | 177 | 8 | 17/8/152 | 53.21581921 | 53.28714689 | -0.15% | 8/8 | 169/177 | 39/0/138 |
| Pareto-Resource-NMCTS | 177 | 8 | 5/5/167 | 49.55649718 | 49.57258121 | -0.03% | 6/8 | 172/177 | 29/0/148 |

## Metric details

| method | metric | W/L/T vs random mean | mean relative | W/L/T vs no prior |
|---|---|---:|---:|---:|
| Affine-Resource-NMCTS | score | 20/12/145 | -0.12% | 42/0/135 |
| Affine-Resource-NMCTS | T | 13/6/158 | -0.11% | 22/0/155 |
| Affine-Resource-NMCTS | CNOT | 16/11/150 | -0.15% | 33/2/142 |
| Affine-Resource-NMCTS | depth | 19/12/146 | -0.18% | 33/5/139 |
| Affine-Resource-NMCTS | peak_ancilla | 1/0/176 | -0.11% | 1/0/176 |
| Affine-Resource-NMCTS | time_s | 24/153/0 | +29.02% | 3/174/0 |
| Resource-NMCTS | score | 17/8/152 | -0.15% | 39/0/138 |
| Resource-NMCTS | T | 9/3/165 | -0.17% | 17/0/160 |
| Resource-NMCTS | CNOT | 10/11/156 | -0.08% | 27/5/145 |
| Resource-NMCTS | depth | 15/9/153 | -0.12% | 31/4/142 |
| Resource-NMCTS | peak_ancilla | 2/0/175 | -0.07% | 3/0/174 |
| Resource-NMCTS | time_s | 72/105/0 | +48.05% | 54/123/0 |
| Pareto-Resource-NMCTS | score | 5/5/167 | -0.03% | 29/0/148 |
| Pareto-Resource-NMCTS | T | 2/2/173 | -0.04% | 9/0/168 |
| Pareto-Resource-NMCTS | CNOT | 3/5/169 | -0.00% | 19/3/155 |
| Pareto-Resource-NMCTS | depth | 5/5/167 | -0.03% | 21/5/151 |
| Pareto-Resource-NMCTS | peak_ancilla | 1/0/176 | -0.03% | 5/0/172 |
| Pareto-Resource-NMCTS | time_s | 21/156/0 | +38.18% | 37/140/0 |
