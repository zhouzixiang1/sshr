# Resource-NMCTS Worked Example

## Boolean function

- n: 5
- ANF: `x0*x1*x2 xor x0*x1*x3 xor x1*x2*x3 xor x0*x1*x4 xor x2*x3*x4`
- factored form: `x0*x1*(x2 xor x3 xor x4) xor x2*x3*(x1 xor x4)`
- truth-table hex: `0xB008C880`
- on-set assignments: {7, 11, 14, 15, 19, 28, 29, 31}; all other assignments evaluate to 0

## Root search trace

The combined prior is h + 2.5*s_NN, where h is the deterministic heuristic and s_NN is the trained neural score. Lower estimated score is better.

| rank | factor | grouped terms | heuristic | neural | combined | visits | estimated score | selected first |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `x0*x1` | 3 | 0.381 | 0.927 | 2.700 | 96 | 33.255 | True |
| 2 | `x1*x2` | 2 | 0.238 | 0.274 | 0.923 | 0 | 37.605 | False |
| 3 | `x1*x3` | 2 | 0.238 | 0.274 | 0.923 | 0 | 37.605 | False |
| 4 | `x2*x3` | 2 | 0.238 | 0.274 | 0.923 | 32 | 33.255 | False |

The search selects x0*x1 first, then factors x2*x3 in the rest subproblem. The reverse root order reaches the same final score; deterministic ordering fixes the emitted sequence.

## Resource change

| method | T | CNOT | depth | gates | explicit factor ancilla | peak ancilla | score |
|---|---:|---:|---:|---:|---:|---:|---:|
| AND-direct ANF | 40 | 65 | 65 | 25 | 0 | 1 | 45.825 |
| Resource-NMCTS | 28 | 55 | 55 | 23 | 1 | 1 | 33.255 |

Relative score change: -27.43%.

## Verification

- plan expansion: pass; nodes=5; mismatches=0
- emitted-circuit ANF simulation: pass; gates=9; input/output/ancilla mismatches=0/0/0
- complete truth table: 32/32 assignments pass
- full Resource-NMCTS portfolio and neural-MCTS branch emit the same plan: True

## Claim boundary

This example explains the core ANF factor-search and emitted circuit. It is not evidence that the neural prior is necessary on this easy instance, and it does not exercise the affine, phase/Rz, Pareto-budget, or high-dimensional frontier branches.
