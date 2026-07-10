# Exact XAG Multiplicative-Complexity Analysis

This analysis computes the exact minimum number of AND nodes in an
XAG/AND-XOR network for n<=4 target Boolean functions.  The value
`4 * AND` is a global lower bound on logical-AND T-count, not a full
CNOT/depth optimum.

Rows: 72; solved: 72; errors/unknown: 0.

## Exact lower-bound summary

| n | functions | mean AND | mean T lower bound | max visited states |
|---:|---:|---:|---:|---:|
| 3 | 3 | 0.67 | 2.67 | 8 |
| 4 | 69 | 2.43 | 9.74 | 66541 |

## Paired comparison to the lower bound

| target method | metric | pairs | below lower | above lower | on lower | mean relative to lower |
|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | T | 72 | 0 | 60 | 12 | +53.01% |
| and_resource_nmcts | score | 72 | 0 | 72 | 0 | +101.42% |
| and_pareto_resource_nmcts | T | 72 | 0 | 60 | 12 | +53.01% |
| and_pareto_resource_nmcts | score | 72 | 0 | 72 | 0 | +101.38% |
| and_esop_milp | T | 72 | 0 | 69 | 3 | +120.14% |
| and_esop_milp | score | 72 | 0 | 72 | 0 | +172.37% |
| external_sshr_i_t | T | 72 | 0 | 67 | 5 | +143.06% |
| external_sshr_i_t | score | 72 | 0 | 72 | 0 | +179.21% |

## Interpretation

- `below lower` should be zero for T-count; otherwise the accounting models are inconsistent.
- Equality means the method reaches the global multiplicative-complexity T lower bound for that function.
- A positive relative gap is expected because the bound ignores CNOT, depth, uncomputation structure, and ancilla profile.
