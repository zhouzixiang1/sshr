# Large_Resource_Core Analysis

Rows: 1980; usable: 1975; errors: 5; skipped: 0.

## Timeout / error rows

| function | n | method | error |
|---|---:|---|---|
| anf_n12_30 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
| anf_n12_31 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
| anf_n12_40 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
| anf_n12_42 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
| anf_n12_46 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_affine_nmcts | 330 | -60.31% | -88.57% | +0.00% |
| and_direct_anf | 330 | -39.78% | -50.00% | +0.00% |
| and_mcts_factor | 325 | -55.16% | -74.11% | +0.00% |
| and_profile_resource_nmcts | 330 | -59.92% | -88.57% | +0.00% |
| and_resource_nmcts | 330 | -60.37% | -88.57% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_affine_nmcts | direct_anf | T | 291 | 0 | 39 | -60.31% |
| and_affine_nmcts | direct_anf | CNOT | 173 | 147 | 10 | -6.97% |
| and_affine_nmcts | direct_anf | depth | 171 | 149 | 10 | -5.31% |
| and_affine_nmcts | direct_anf | peak_ancilla | 0 | 189 | 141 | +47.53% |
| and_affine_nmcts | direct_anf | score | 291 | 30 | 9 | -56.77% |
| and_affine_nmcts | and_direct_anf | T | 286 | 0 | 44 | -37.13% |
| and_affine_nmcts | and_direct_anf | CNOT | 286 | 0 | 44 | -27.28% |
| and_affine_nmcts | and_direct_anf | depth | 286 | 0 | 44 | -25.81% |
| and_affine_nmcts | and_direct_anf | peak_ancilla | 62 | 0 | 268 | -5.52% |
| and_affine_nmcts | and_direct_anf | score | 286 | 0 | 44 | -35.09% |
| and_affine_nmcts | and_mcts_factor | T | 130 | 0 | 195 | -12.33% |
| and_affine_nmcts | and_mcts_factor | CNOT | 134 | 0 | 191 | -11.37% |
| and_affine_nmcts | and_mcts_factor | depth | 131 | 2 | 192 | -9.58% |
| and_affine_nmcts | and_mcts_factor | peak_ancilla | 1 | 14 | 310 | +1.81% |
| and_affine_nmcts | and_mcts_factor | score | 134 | 0 | 191 | -11.31% |
| and_resource_nmcts | direct_anf | T | 291 | 0 | 39 | -60.37% |
| and_resource_nmcts | direct_anf | CNOT | 173 | 147 | 10 | -7.30% |
| and_resource_nmcts | direct_anf | depth | 171 | 149 | 10 | -5.47% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 190 | 140 | +47.68% |
| and_resource_nmcts | direct_anf | score | 291 | 30 | 9 | -56.84% |
| and_resource_nmcts | and_direct_anf | T | 286 | 0 | 44 | -37.25% |
| and_resource_nmcts | and_direct_anf | CNOT | 286 | 0 | 44 | -27.53% |
| and_resource_nmcts | and_direct_anf | depth | 286 | 0 | 44 | -25.94% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 61 | 0 | 269 | -5.41% |
| and_resource_nmcts | and_direct_anf | score | 286 | 0 | 44 | -35.21% |
| and_resource_nmcts | and_affine_nmcts | T | 19 | 15 | 296 | -0.20% |
| and_resource_nmcts | and_affine_nmcts | CNOT | 32 | 13 | 285 | -0.39% |
| and_resource_nmcts | and_affine_nmcts | depth | 28 | 15 | 287 | -0.19% |
| and_resource_nmcts | and_affine_nmcts | peak_ancilla | 1 | 2 | 327 | +0.18% |
| and_resource_nmcts | and_affine_nmcts | score | 29 | 16 | 285 | -0.20% |
| and_resource_nmcts | and_mcts_factor | T | 139 | 15 | 171 | -12.43% |
| and_resource_nmcts | and_mcts_factor | CNOT | 149 | 13 | 163 | -11.69% |
| and_resource_nmcts | and_mcts_factor | depth | 146 | 15 | 164 | -9.72% |
| and_resource_nmcts | and_mcts_factor | peak_ancilla | 1 | 15 | 309 | +1.96% |
| and_resource_nmcts | and_mcts_factor | score | 146 | 16 | 163 | -11.41% |
| and_profile_resource_nmcts | direct_anf | T | 291 | 0 | 39 | -59.92% |
| and_profile_resource_nmcts | direct_anf | CNOT | 174 | 146 | 10 | -6.48% |
| and_profile_resource_nmcts | direct_anf | depth | 173 | 147 | 10 | -4.72% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 188 | 142 | +47.98% |
| and_profile_resource_nmcts | direct_anf | score | 291 | 30 | 9 | -56.39% |
| and_profile_resource_nmcts | and_direct_anf | T | 286 | 0 | 44 | -36.35% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 286 | 0 | 44 | -27.05% |
| and_profile_resource_nmcts | and_direct_anf | depth | 286 | 0 | 44 | -25.49% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 59 | 0 | 271 | -5.31% |
| and_profile_resource_nmcts | and_direct_anf | score | 286 | 0 | 44 | -34.36% |
| and_profile_resource_nmcts | and_resource_nmcts | T | 21 | 75 | 234 | +1.40% |
| and_profile_resource_nmcts | and_resource_nmcts | CNOT | 27 | 76 | 227 | +0.71% |
| and_profile_resource_nmcts | and_resource_nmcts | depth | 28 | 77 | 225 | +0.63% |
| and_profile_resource_nmcts | and_resource_nmcts | peak_ancilla | 5 | 7 | 318 | +0.28% |
| and_profile_resource_nmcts | and_resource_nmcts | score | 30 | 75 | 225 | +1.31% |
| and_profile_resource_nmcts | and_affine_nmcts | T | 25 | 71 | 234 | +1.20% |
| and_profile_resource_nmcts | and_affine_nmcts | CNOT | 33 | 71 | 226 | +0.31% |
| and_profile_resource_nmcts | and_affine_nmcts | depth | 32 | 73 | 225 | +0.45% |
| and_profile_resource_nmcts | and_affine_nmcts | peak_ancilla | 5 | 8 | 317 | +0.43% |
| and_profile_resource_nmcts | and_affine_nmcts | score | 35 | 71 | 224 | +1.11% |
| and_profile_resource_nmcts | and_mcts_factor | T | 134 | 71 | 120 | -11.06% |
| and_profile_resource_nmcts | and_mcts_factor | CNOT | 143 | 66 | 116 | -11.01% |
| and_profile_resource_nmcts | and_mcts_factor | depth | 141 | 67 | 117 | -9.10% |
| and_profile_resource_nmcts | and_mcts_factor | peak_ancilla | 1 | 17 | 307 | +2.06% |
| and_profile_resource_nmcts | and_mcts_factor | score | 138 | 71 | 116 | -10.13% |

## Largest and-affine-nmcts gains vs direct ANF

| function | n | direct T | and_affine_nmcts T | relative |
|---|---:|---:|---:|---:|
| majority_n5 | 5 | 280 | 32 | -88.57% |
| truth_n5_12 | 5 | 208 | 24 | -88.46% |
| truth_n5_46 | 5 | 220 | 32 | -85.45% |
| truth_n5_2 | 5 | 256 | 40 | -84.38% |
| majority_n7 | 7 | 840 | 132 | -84.29% |
| truth_n4_44 | 4 | 76 | 12 | -84.21% |
| truth_n4_24 | 4 | 100 | 16 | -84.00% |
| truth_n4_37 | 4 | 100 | 16 | -84.00% |
| truth_n5_29 | 5 | 192 | 32 | -83.33% |
| truth_n4_15 | 4 | 68 | 12 | -82.35% |
| truth_n5_24 | 5 | 244 | 44 | -81.97% |
| majority_n8 | 8 | 3352 | 612 | -81.74% |

## Largest and-resource-nmcts gains vs direct ANF

| function | n | direct T | and_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| majority_n5 | 5 | 280 | 32 | -88.57% |
| truth_n5_12 | 5 | 208 | 24 | -88.46% |
| truth_n5_46 | 5 | 220 | 32 | -85.45% |
| truth_n5_2 | 5 | 256 | 40 | -84.38% |
| majority_n7 | 7 | 840 | 132 | -84.29% |
| truth_n4_44 | 4 | 76 | 12 | -84.21% |
| truth_n4_24 | 4 | 100 | 16 | -84.00% |
| truth_n4_37 | 4 | 100 | 16 | -84.00% |
| truth_n5_29 | 5 | 192 | 32 | -83.33% |
| truth_n4_15 | 4 | 68 | 12 | -82.35% |
| truth_n5_24 | 5 | 244 | 44 | -81.97% |
| truth_n6_6 | 6 | 620 | 112 | -81.94% |

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| majority_n5 | 5 | 280 | 32 | -88.57% |
| truth_n5_12 | 5 | 208 | 24 | -88.46% |
| truth_n5_46 | 5 | 220 | 32 | -85.45% |
| truth_n5_2 | 5 | 256 | 40 | -84.38% |
| majority_n7 | 7 | 840 | 132 | -84.29% |
| truth_n4_44 | 4 | 76 | 12 | -84.21% |
| truth_n4_24 | 4 | 100 | 16 | -84.00% |
| truth_n4_37 | 4 | 100 | 16 | -84.00% |
| truth_n5_29 | 5 | 192 | 32 | -83.33% |
| truth_n4_15 | 4 | 68 | 12 | -82.35% |
| truth_n5_24 | 5 | 244 | 44 | -81.97% |
| truth_n6_6 | 6 | 620 | 112 | -81.94% |
