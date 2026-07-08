# Resource-NMCTS 中文交付文档

更新时间：2026-07-08
当前代码版本：以 `origin/main` 最新提交为准
代码位置：`/Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment`

## 1. 项目定位

本项目面向量子布尔函数 oracle 综合，目标是在逻辑层降低 T-count、CNOT、深度和辅助比特等资源。当前方法不依赖 SSHR 的 parallelotope 结构，而是把布尔 oracle 综合建模为 ANF/FPRM 项集合上的搜索问题：

- 用资源加权目标函数评价候选线路：
  `score = T + 0.04*CNOT + 0.015*depth + 0.01*gates + 2*ancilla`。
- 用神经先验、MCTS、FPRM 极性搜索、线性因子分解和 Pareto archive 生成候选。
- 用 direct ANF、AND-direct ANF、ESOP、ABC、BDD、SSHR-H/SSHR-I 等作为外部或内部 baseline。
- 所有结果均是逻辑层资源估计，不包含硬件映射和连通性约束。

论文主张应限定为：资源约束、低 T-count、低加权 score 的量子布尔函数 oracle 综合方法。不能写成 CNOT-only 最优，也不能写成硬件映射优势。

## 2. 当前已完成内容

### 2.0 RevKit API baseline 与工具链边界

本轮已把外部工具链审计从“是否存在命令”升级为“能否真实运行一个可复现 baseline”。当前 `mcts-qoracle` 环境中已安装 `cmake`、`pybind11` 和 RevKit Python API，并新增 `run_revkit_baseline.py` 调用 RevKit 的 `oracle_synth` 对完整 truth-table 函数合成。

主要产物：

- `analyze_toolchain_readiness.py`
- `run_revkit_baseline.py`
- `results/analysis_toolchain_readiness.md`
- `results/toolchain_readiness.json`
- `results/raw_revkit_oracle_synth_traditional.csv`
- `results/summary_revkit_oracle_synth_traditional.csv`
- `results/analysis_revkit_oracle_synth_traditional.md`
- `results/manifest_revkit_oracle_synth_traditional.json`
- `paper_latex/tables/revkit_oracle_synth_traditional.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v21.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v21.pdf`

核心结果：

| 对比 | 指标 | 函数数 | 胜/负/平 | 平均变化 |
|---|---|---:|---:|---:|
| Resource-NMCTS vs RevKit `oracle_synth` | score | 177 | 6/171/0 | +751.69% |
| Pareto-Resource-NMCTS vs RevKit `oracle_synth` | score | 177 | 6/171/0 | +711.60% |
| FPRM polarity archive vs RevKit `oracle_synth` | score | 177 | 4/173/0 | +774.83% |
| SSHR-H vs RevKit `oracle_synth` | CNOT | 177 | 34/141/2 | +34.23% |
| Resource-NMCTS vs RevKit `oracle_synth` | T-count | 177 | 2/171/4 | +4060.08% |

解释边界：

- 这是一个真实 RevKit Python API baseline，不是 ABC-only 的 ROS-style LUT proxy。
- RevKit 返回的是 Clifford+T netlist；当前 Resource-NMCTS emitter 是 X/CNOT/MCT bit-flip compute/action/uncompute 路线，两者资源口径不同。
- 该结果不是坏消息，而是新的强基线：投稿前要么新增 phase-oracle / Clifford+T-aware emitter，要么把论文主张严格限定为 bit-flip oracle 的逻辑层资源综合。
- 当前仍未打通官方 ROS、mockturtle 和 legacy RevKit/CirKit CLI 流程。

### 2.1 ESOP baseline 对比

新增 `analyze_esop_baseline.py`，专门从同一 benchmark 的内部 ESOP-MILP 和外部 ABC-ESOP 结果中生成 ESOP 视角分析。

主要产物：

- `results/analysis_esop_baseline.md`
- `results/summary_esop_baseline.csv`
- `paper_latex/tables/esop_baseline_by_n.tex`

核心结果：

| Baseline | 函数数 | T-count 变化 | CNOT 变化 | ancilla 变化 | score 变化 | score 胜/负/平 |
|---|---:|---:|---:|---:|---:|---:|
| Internal ESOP-MILP | 177 | -51.64% | -37.80% | -12.65% | -48.77% | 167/3/7 |
| ABC-ESOP export | 177 | -25.80% | -5.40% | -11.58% | -23.42% | 170/1/6 |

按变量数分组：

- 对 internal ESOP-MILP：`n=3..6` 每组 T-count 和 CNOT 总量都更低；ancilla 在 `n=3` 持平，在 `n=4..6` 更低。
- 对 ABC-ESOP：`n=3..6` 每组 T-count、CNOT 和 ancilla 总量都更低。

因此，论文中应写成“相同 benchmark 下显著优于 ESOP 的低 T / 加权资源结果”，而不是写成“所有 CNOT 指标都优于 ESOP”。

### 2.2 n=18 mega stress 收束

当前 `mega_highdim_resource` 已完成 12 个随机 `n=18` ANF 函数、7 个方法、84 行结果：

- `direct_anf`
- `and_direct_anf`
- `and_fprm_root_beam`
- `and_fprm_linear_pair_fast`
- `and_resource_nmcts`
- `and_profile_resource_nmcts`
- `and_pareto_resource_nmcts`

数据审计结果：

- 总行数：84
- error：0
- skipped：0
- incorrect：0
- 每个方法 12 行

核心结果：

| 对比 | T-count 胜/负/平 | score 胜/负/平 | 平均 T-count 变化 | 平均 score 变化 |
|---|---:|---:|---:|---:|
| fast linear-pair vs root-beam | 6/0/6 | 6/0/6 | -2.72% | -1.91% |
| Resource/Profile/Pareto vs fast linear-pair | 12/0/0 | 12/0/0 | -3.75% | -3.55% |
| Resource/Profile/Pareto vs root-beam | 12/0/0 | 12/0/0 | -6.19% | -5.29% |
| Resource/Profile/Pareto vs direct ANF | 12/0/0 | 12/0/0 | -60.05% | -56.99% |
| Resource/Profile/Pareto vs AND-direct ANF | 12/0/0 | 12/0/0 | -33.39% | -32.01% |

代价：

- 相对 direct ANF，CNOT、depth 和 peak ancilla 增加。
- 相对 AND-direct ANF，T、CNOT、depth 和 score 都改善，但 peak ancilla 增加。
- n=18 的 Pareto-Resource-NMCTS 当前故意收窄到与 Resource/Profile 相同的稳定高维 guard，因此它不是新的 Pareto 分离证据，而是规模和验证边界证据。

### 2.2.1 n=20 giga stress 边界测试

本轮新增 `giga_highdim_resource` 压力边界切片，覆盖 6 个随机 `n=20` ANF 函数、8 个方法、48 行结果；随后又补了 recursive Boolean-ring screen 的 targeted rerun，并继续把递归深度从 1 扩到 2：

- `direct_anf`
- `and_direct_anf`
- `and_boolean_linear_pair_screen`
- `and_boolean_linear_pair_screen_deep`（targeted rerun）
- `and_boolean_linear_pair_screen_deeper`（targeted rerun，recursive depth=2）
- `and_fprm_root_beam`
- `and_fprm_linear_pair_fast`
- `and_resource_nmcts`
- `and_profile_resource_nmcts`
- `and_pareto_resource_nmcts`

主要产物：

- `results/raw_giga_highdim_resource.csv`
- `results/summary_giga_highdim_resource.csv`
- `results/manifest_giga_highdim_resource.json`
- `results/analysis_giga_highdim_resource.md`
- `results/runtime_giga_highdim_resource.md`
- `paper_latex/tables/resource_giga_highdim_resource.tex`
- `paper_latex/tables/runtime_giga_highdim_resource.tex`
- `results/raw_giga_boolean_screen_deep.csv`
- `results/analysis_giga_screen_deep_vs_screen.md`
- `results/analysis_giga_resource_recursive_screen_vs_old.md`
- `results/raw_giga_boolean_screen_deeper.csv`
- `results/analysis_giga_screen_deeper_vs_deep.md`
- `results/analysis_giga_resource_deeper_vs_depth1_resource.md`
- `results/analysis_giga_resource_deeper_vs_old_resource.md`
- `paper_latex/tables/giga_screen_deep_vs_screen.tex`
- `paper_latex/tables/giga_resource_recursive_screen_vs_old.tex`
- `paper_latex/tables/giga_screen_deeper_vs_deep.tex`
- `paper_latex/tables/giga_resource_deeper_vs_old_resource.tex`

核心结果：

| 对比 | T-count 胜/负/平 | score 胜/负/平 | 平均 T-count 变化 | 平均 score 变化 |
|---|---:|---:|---:|---:|
| Resource/Profile/Pareto vs direct ANF | 5/0/1 | 5/1/0 | -36.80% | -34.00% |
| Resource/Profile/Pareto vs AND-direct ANF | 5/0/1 | 5/0/1 | -5.24% | -4.89% |
| ANF Boolean linear screen vs AND-direct ANF | 5/0/1 | 5/0/1 | -5.24% | -4.89% |
| Recursive Boolean screen vs single Boolean screen | 5/0/1 | 5/0/1 | -4.62% | -4.52% |
| Recursive-screen Resource-NMCTS vs old Resource-NMCTS | 5/0/1 | 5/0/1 | -4.62% | -4.52% |
| Deeper recursive Boolean screen vs depth-1 screen | 5/0/1 | 5/0/1 | -3.22% | -3.13% |
| Deeper-screen Resource-NMCTS vs old Resource-NMCTS | 5/0/1 | 5/0/1 | -7.64% | -7.47% |
| Deeper-screen Resource-NMCTS vs AND-direct ANF | 5/0/1 | 5/0/1 | -12.24% | -11.80% |

运行边界：

- `and_fprm_root_beam` 和 `and_fprm_linear_pair_fast` 在 6 个函数上全部触发 300 s task timeout。
- `and_boolean_linear_pair_screen` 是新增的可扩展修复分支：它不做 FPRM 极性筛选，只在原始 ANF 上用 Boolean-ring 规则筛选单层 linear factor，因此 6/6 完成，median runtime 为 10.659 s。
- `and_boolean_linear_pair_screen_deep` 在单层 screen 的 quotient/rest 子问题上再做一层同类 Boolean-ring screen，仍不做 FPRM 极性筛选。它 6/6 完成，相对单层 screen 为 5/0/1、平均 score -4.52%，standalone mean runtime 12.73 s，仅比单层 screen 慢约 16.92%。
- `and_boolean_linear_pair_screen_deeper` 把同类 screen 深度扩到 2，仍不做 FPRM 极性筛选。它 6/6 完成，相对 depth-1 screen 为 5/0/1、平均 score -3.13%，standalone mean runtime 20.15 s；代价是 peak ancilla 平均从 2.833 增至 3.000。
- 集成后的 `and_resource_nmcts` 也完成 6/6，相对上一版 depth-1 Resource 为 5/0/1、平均 score -3.13%；相对旧 Resource-NMCTS 为 5/0/1、平均 score -7.47%；相对 AND-direct ANF 为 5/0/1、平均 score -11.80%；相对 direct ANF 为 5/1/0、平均 score -38.86%。
- 因此，n=20 可以写成“边界改善进一步扩大”：当前实现仍无法让 FPRM root-beam/fast linear-pair 在 300 s 内完成，但 ANF-only depth-2 recursive Boolean-ring screen 能在超高维上提供可验证的 baseline-preserving 增益。不能把它写成深层神经/FPRM 搜索已经解决 n=20；也要注明运行时间和辅助比特有上升。

### 2.3 外部 ABC/BDD 高维对比

当前高维外部 baseline 覆盖：

- 64 个 `n=14` 函数
- 32 个 `n=15` 函数
- 24 个 `n=16` 函数
- 12 个 `n=18` 函数

每个函数都有 ABC-AIG、ABC-XAG、ABC-LUT、BDD 行，总计 528 个外部比较行，均通过 truth-table 验证。

`n=18` 上 Resource/Profile/Pareto 的平均 score 降幅：

- ABC-AIG：-98.85%
- ABC-XAG：-99.05%
- ABC-LUT：-99.69%
- BDD：-98.30%

边界条件：

- ABC-AIG 和 ABC-XAG 在多数高维函数上保持更低的 level/depth 估计。
- 因此，高维外部结果支持“低 ancilla / 低加权资源 / 低 T-count”，但不支持“depth-only 支配”。

### 2.4 搜索贡献分解

新增 `analyze_search_contribution.py`，把分散在多个实验文件中的消融结果统一成一张 contribution decomposition 表，避免论文只给出“大结果”而无法回答“提升到底来自哪里”。

主要产物：

- `results/analysis_search_contribution.md`
- `results/summary_search_contribution.csv`
- `results/analysis_weight_robustness.md`
- `results/summary_weight_robustness.csv`
- `results/raw_search_ablation_traditional.csv`
- `results/analysis_search_ablation_traditional.md`
- `results/raw_search_ablation_highdim.csv`
- `results/analysis_search_ablation_highdim.md`
- `results/raw_neural_prior_ablation.csv`
- `results/analysis_neural_prior_ablation.md`
- `paper_latex/tables/search_contribution_decomposition.tex`

关键结论：

| 贡献环节 | 函数集 | score 胜/负/平 | 平均 score 变化 | 解释 |
|---|---|---:|---:|---|
| affine greedy vs fixed-coordinate MCTS | `ablation_affine` | 165/88/68 | -12.12% | 仿射坐标搜索是最大前置收益，但不是单调 guard |
| neural refine over affine greedy | `ablation_affine` | 65/0/257 | -1.08% | 神经 refine 有小幅、无 score loss 的增益 |
| guarded Affine-NMCTS over no-guard | `ablation_affine` | 88/0/234 | -1.74% | final guard 有无损增益 |
| learned prior for Resource-NMCTS | `traditional_resource` | 39/0/138 | -1.10% | 学习先验是质量信号，但不是最快模式 |
| Pareto archive over Resource-NMCTS | `traditional_resource` | 68/0/109 | -3.26% | 小规模 profile/Pareto archive 贡献明确 |
| Resource-NMCTS over no-MCTS portfolio | `search_ablation_traditional` | 54/0/123 | -1.44% | dedicated rerun 证明 MCTS/神经候选在强化 no-MCTS baseline 后仍有增益 |
| Pareto Resource-NMCTS over no-MCTS portfolio | `search_ablation_traditional` | 106/0/71 | -4.69% | Pareto archive 对 no-MCTS portfolio 的增益更明确 |
| highdim no-MCTS portfolio over root beam | `search_ablation_highdim` | 14/0/2 | -6.25% | n=14 同 preset 高维 guard/no-MCTS 机制证据 |
| highdim no-MCTS portfolio over linear-pair | `search_ablation_highdim` | 14/0/2 | -3.08% | 说明 no-MCTS portfolio 在高维下仍能改善单一 linear-pair child |
| linear-pair guard vs root beam, n=14 | `highdim_resource` | 60/0/4 | -3.00% | 高维主要增益来自 bounded linear-pair guard |
| recursive linear-pair guard vs root beam, n=15 | `highdim_scale_resource` | 30/0/2 | -5.28% | 递归 pair guard 是 n=15 的主要规模贡献 |
| shallow linear-pair guard vs root beam, n=16 | `ultra_highdim_resource` | 22/0/2 | -1.88% | 旧浅层 guard 仍有可测增益 |
| recursive linear-pair guard vs shallow linear-pair, n=16 | `ultra_highdim_resource` | 23/0/1 | -2.54% | 新增递归 guard 明确优于浅层 guard |
| recursive linear-pair guard vs root beam, n=16 | `ultra_highdim_resource` | 23/0/1 | -4.31% | n=16 的主要规模贡献已更新为 recursive linear-pair guard |
| root-neural recursive guard vs deterministic recursive guard, n=16 | `ultra_highdim_resource` | 6/7/11 | +0.08% | 单独神经排序不稳定，不能作为正向主张 |
| baseline-preserving AI guard vs deterministic recursive guard, n=16 | `ultra_highdim_resource` | 6/0/18 | -0.05% | 用 deterministic guard 兜底后获得无 score-loss 小增益 |
| pairwise-wide Resource-NMCTS vs deterministic recursive guard, n=16 | `ultra_pairwise_wide_vs_recursive` | 10/0/14 | -0.18% | root-action pairwise ranker + heuristic/neural union 把高维 AI 增益放大到 full synthesis 层面 |
| pairwise-wide Resource-NMCTS vs old Resource-NMCTS, n=16 | `ultra_pairwise_wide_vs_old_resource` | 10/0/14 | -0.12% | 新 pairwise-wide 分支优于旧 root-teacher Resource 结果 |
| Boolean-ring linear-deep vs deterministic recursive guard, n=16 | `ultra_boolean_linear_vs_deep` | 17/3/4 | -0.39% | 允许 quotient 与 linear factor 共享变量后，结构性收益强于 pairwise-wide neural guard |
| Boolean-guard Resource-NMCTS vs pairwise-wide Resource-NMCTS, n=16 | `ultra_boolean_guard_vs_pairwise_wide` | 14/0/10 | -0.34% | full synthesis 主方法获得无 score-loss 的新高维改进 |
| fast linear-pair guard vs root beam, n=18 | `mega_highdim_resource` | 6/0/6 | -1.91% | n=18 是可验证的压力边界证据 |
| Resource-NMCTS vs fast linear-pair, n=18 | `mega_highdim_resource` | 12/0/0 | -3.55% | n=18 Resource guard 对 fast child 仍有进一步选择收益 |

这个结果把论文主张进一步收窄为：仿射坐标搜索、神经 refine、guard/Pareto archive、高维 linear-pair guard 和 Boolean-ring linear factor 共同构成方法贡献；其中高维大规模证据不能夸大为完整 Pareto archive 的强独立优势，因为部分高维设置中 Resource/Profile/Pareto 会退化或收窄到稳定 guard。最新 `n=16` Boolean-ring rerun 后，`Resource-NMCTS` 在 full synthesis 层面相对上一轮 pairwise-wide Resource 获得 14/0/10、平均 score 降低 0.34%；相对 deterministic recursive guard 获得 18/0/6、平均 score 降低 0.52%。因此该切片现在应写成“recursive guard + Boolean-ring linear factor + baseline-preserving portfolio”的结构性正向证据；pairwise-wide neural guard 仍是 AI 模块的小幅正向消融，但不再是高维主质量增益的唯一来源。

### 2.5 高维 learned-prior 诊断

本轮补了 `highdim_neural_prior` 小切片，目标是回答“学习先验在高维 Resource-NMCTS 中是否仍有贡献”。直接使用全递归 neural linear-pair child 会在 n=14 上产生明显长尾，因此代码改成了 root-only neural screening：神经模型只影响高维 linear-pair 的根层候选排序，后续子问题仍使用确定性 greedy/beam。

新增训练产物：

- `models/linear_action_scorer_highdim.pt`

新增结果产物：

- `results/raw_highdim_neural_prior_learned_prior.csv`
- `results/raw_highdim_neural_prior_no_prior.csv`
- `results/raw_neural_prior_highdim_ablation.csv`
- `results/analysis_neural_prior_highdim_ablation.md`
- `paper_latex/tables/neural_prior_highdim_ablation.tex`

核心结果：

| 对比 | 函数集 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---|---:|---:|---:|
| learned Resource-NMCTS vs no-prior Resource-NMCTS | 12 个 n=14 random ANF | 1/0/11 | -0.01% | +104.07% |

结论：高维 learned-prior 小切片已经完成，但它不是强正向证据。专用 linear-action 模型只带来 1 个轻微 score 胜例，且运行时间约翻倍。因此论文主贡献仍应放在 n<=6 learned-prior 正向证据、低维 neural refine、MCTS/Pareto archive、以及高维 bounded linear-pair guard；高维 neural guidance 目前只能写成边界诊断或 future work。

### 2.5.1 结构级 Boolean screen depth policy

本轮新增 `train_screen_depth_policy.py`，把 AI 从 root action 排序推进到结构级选择：给定高维 ANF 项集合的统计特征，预测应该使用 single、depth-1 还是 depth-2 Boolean-ring screen。标签不是人工规则，而是实际运行三种 screen 后按统一资源 score 选择 oracle depth。

主要产物：

- `train_screen_depth_policy.py`
- `models/boolean_screen_depth_policy.pt`
- `results/raw_boolean_screen_depth_policy.csv`
- `results/summary_boolean_screen_depth_policy.csv`
- `results/analysis_boolean_screen_depth_policy.md`
- `paper_latex/tables/boolean_screen_depth_policy.tex`

实验设置：

- 训练集：240 个生成式高维 ANF 项集合，变量数 `n=14,16,18`。
- 验证集：72 个同分布项集合。
- 测试集：48 个 held-out `n=20` 项集合。
- 特征：项数、次数分布、变量/二元共现密度、root Boolean-ring action 数量与 top action 覆盖率/收益等结构统计。

核心结果：

| 对比 | 函数数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---:|---:|---:|---:|
| policy vs single screen | 48 | 42/0/6 | -6.57% | +2224.00% |
| policy vs depth-1 screen | 48 | 34/0/14 | -2.57% | +257.27% |
| policy vs depth-2 screen | 48 | 0/5/43 | +0.28% | -10.85% |
| policy vs all-depth adaptive | 48 | 0/5/43 | +0.28% | -34.71% |

结论：这是比 action-level prior 更明确的结构级 AI 证据，说明模型可以学习何时需要更深 Boolean-ring screen；但它仍不能写成最终质量突破，因为固定 depth-2 screen 在 score 上略优。论文里应表述为“结构级 AI 已经能减少全 depth adaptive 评估开销，并优于浅层固定策略；下一步需要加 baseline-preserving guard，让 policy 在不劣于 depth-2 的前提下降低运行时间或选择更强分支”。

### 2.5.2 保守 depth-2 skip guard

本轮新增并更新 `train_screen_depth_guard.py`，专门修补上一节的质量缺口。它不再直接预测 single/depth-1/depth-2 三分类，而是学习一个更保守的问题：何时可以跳过 depth-2，使 depth-1 screen 与固定 depth-2 screen 的 score 持平。当前实现区分两种执行模式：`static-direct` 只用静态 ANF/action 特征，在综合前直接派发到 depth-1 或 depth-2；`shallow-staged` 先运行 single/depth-1 screen，再用浅层观测特征决定是否跳过 depth-2。阈值在 train+validation 上按 zero-false-skip 约束选择；shallow-staged 额外使用 0.95 高置信阈值下限。

主要产物：

- `train_screen_depth_guard.py`
- `models/boolean_screen_depth_guard.pt`
- `models/boolean_screen_depth_guard.json`
- `models/boolean_screen_depth_guard_shallow_staged.pt`
- `models/boolean_screen_depth_guard_shallow_staged.json`
- `results/raw_boolean_screen_depth_guard.csv`
- `results/summary_boolean_screen_depth_guard.csv`
- `results/analysis_boolean_screen_depth_guard.md`
- `results/boolean_screen_depth_guard_shallow_staged/`
- `results/analysis_boolean_screen_depth_guard_modes.md`
- `results/summary_boolean_screen_depth_guard_modes.csv`
- `paper_latex/tables/boolean_screen_depth_guard.tex`
- `paper_latex/tables/boolean_screen_depth_guard_modes.tex`

核心结果：

| split | 函数数 | skip depth-2 | false skip | vs fixed depth-2 score | vs fixed depth-2 time | vs all-depth time |
|---|---:|---:|---:|---:|---:|---:|
| static-direct train | 480 | 12 | 0 | 0/0/480 持平 | -0.16% | -23.62% |
| static-direct valid | 144 | 3 | 0 | 0/0/144 持平 | -0.28% | -23.45% |
| static-direct test, n=20 | 96 | 4 | 0 | 0/0/96 持平 | -0.54% | -24.74% |
| shallow-staged test, n=20 | 48 | 8 | 0 | 0/0/48 持平 | +29.10% | -7.81% |

解释：这个 guard 第一次把结构级策略的 score 缺口降为 0，并把运行时证据拆成两条清晰路线。`static-direct` 是可部署默认模式：不先跑 shallow screen，在 96 个 held-out `n=20` 样本上相对固定 depth-2 小幅节省 0.54%，相对 all-depth adaptive 节省 24.74%。`shallow-staged` 用浅层观测把安全跳过覆盖提高到 8/48，仍保持 0 false skip 和 0 score loss，但因为先运行 single/depth-1 screen，相对固定 depth-2 screen 仍慢 29.10%。这已经比上一版“3/48 skip、-2.87% all-depth time”的证据更清楚，但仍不能写成最终高维质量突破。下一步应把 shallow 观测蒸馏回 direct guard，或让 guard 同时选择 Resource tail / FPRM / screen 分支。

### 2.5.3 Resource screen-gate 运行时门控

本轮还出现了一个工程性改进：`train_structure_gate.py` 用 adaptive Boolean-ring screen 与完整 Resource-NMCTS 的配对结果训练一个可解释 decision stump，判断何时可以跳过昂贵的 Resource-NMCTS tail。当前模型很小，经过 safety-first 阈值选择后学到的规则是 `n >= 20` 时优先跳过 Resource tail；`synthesizers.py` 也同步改为 direct branch gate：当模型只依赖 `n` 且判定不跳过时，直接运行 Resource-NMCTS，不再预先支付 screen 开销；当判定跳过时，只运行 adaptive screen 作为输出候选。它应被视为运行时门控证据，而不是新的资源质量模型。

主要产物：

- `train_structure_gate.py`
- `models/resource_structure_gate.json`
- `results/analysis_structure_gate.md`
- `results/raw_giga_screen_gate_resource.csv`
- `results/summary_giga_screen_gate_resource.csv`
- `results/analysis_giga_screen_gate_vs_resource.md`
- `results/analysis_giga_screen_gate_vs_adaptive_screen.md`
- `results/raw_gate_holdout_resource.csv`
- `results/analysis_gate_holdout_by_n.md`
- `results/analysis_gate_holdout_screen_gate_vs_resource.md`
- `results/analysis_gate_holdout_adaptive_vs_resource.md`
- `paper_latex/tables/giga_screen_gate_vs_resource.tex`
- `paper_latex/tables/giga_screen_gate_vs_adaptive_screen.tex`
- `paper_latex/tables/gate_holdout_by_n.tex`

核心结果：

| 对比 | 函数数 | T/CNOT/depth/score | 平均运行时间变化 |
|---|---:|---:|---:|
| screen-gated Resource vs full Resource, n=20 | 6 | 全部 0/0/6 持平 | -75.58% |
| screen-gated Resource vs adaptive screen, n=20 | 6 | 全部 0/0/6 持平 | -0.04% |
| held-out gate vs full Resource, n=19+20 | 16 | score 全部 0/0/16 持平 | -36.83% |
| held-out adaptive screen vs full Resource, n=19 | 8 | score 0/4/4，平均 +14.14% | -94.42% |
| held-out gate vs full Resource, n=20 | 8 | score 全部 0/0/8 持平 | -73.66% |

结论：screen-gate 说明当前 n=20 上完整 Resource tail 没有带来额外资源收益，可以被结构门控跳过以减少运行时间；新增 held-out n=19/20 切片更关键：n=19 上 adaptive screen 仍会输给 full Resource，因此 gate 不跳过且通过 direct branch 避免额外 screen 开销；n=20 上 adaptive screen 与 full Resource 全部持平，因此 gate 跳过并节省时间。这使门控证据比单一 n=20 切片更可信，但因为训练样本仍只有 18 个，论文中仍只能写成“高维运行时尾部控制”，不能写成普适替代 Resource-NMCTS。

### 2.5.4 n=20--28 项集级大规模 screen-scale

完整 truth table 在 n>20 后构造和验证成本迅速上升，因此本轮继续升级 `run_screen_scale_terms.py`：它直接在 ANF 项集合这一搜索状态上评估 direct logical-AND、single/depth-1/depth-2 Boolean-ring screen、all-depth adaptive、已训练 depth policy 和保守 depth-2 guard。同时，脚本先对每个返回的 factor plan 做 ANF 符号展开验证：direct 节点返回自身项集，普通 factor 将 quotient 项乘回 monomial factor，Boolean-ring linear factor 在 GF(2) 上展开线性因子，再与 rest 项集合异或合并；随后把 `emit_plan_to_circuit` 产生的 X/CNOT/MCT oracle 线路也作为 GF(2) 多项式系统符号模拟，检查输入线恢复、输出项集合等价和辅助线清零。该实验不替代完整 truth-table simulation，但已经从“只看资源估计”提升到“项集级资源评估 + plan 级符号等价验证 + emitted-circuit 级符号验证”。

主要产物：

- `run_screen_scale_terms.py`
- `results/raw_screen_scale_terms.csv`
- `results/summary_screen_scale_terms.csv`
- `results/analysis_screen_scale_terms.md`
- `paper_latex/tables/screen_scale_terms.tex`

核心结果：

| 对比 | 项集数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---:|---:|---:|---:|
| adaptive all-depth vs single screen, n=20/22/24/28 | 192 | 169/0/23 | -6.63% | +3077.71% |
| adaptive all-depth vs fixed depth-2, n=20/22/24/28 | 192 | 0/0/192 | +0.00% | +47.92% |
| depth policy vs single screen, n=20/22/24/28 | 192 | 169/0/23 | -6.56% | +2328.66% |
| depth policy vs all-depth adaptive, n=20/22/24/28 | 192 | 0/6/186 | +0.08% | -31.01% |
| depth policy vs all-depth adaptive, n=28 | 48 | 0/0/48 | +0.00% | -32.15% |
| direct depth-2 guard vs fixed depth-2, n=20/22/24/28 | 192 | 0/0/192 | +0.00% | -0.14% |
| ANF plan 符号验证 | 1344 方法行 | 1344/0 通过/失败 | 0 mismatch | - |
| emitted-circuit ANF 符号验证 | 1344 方法行 | 1344/0 通过/失败 | 0 mismatch | max wire terms 272 |

结论：这是目前最清楚的大规模结构级 AI 证据。All-depth adaptive 说明 depth-2 screen 是强质量基线；depth policy 在 n=20--28 上几乎复制 all-depth 的质量收益，并节省约三成 all-depth 评估时间，尤其 n=28 上全部持平。新增 emitted-circuit ANF 符号验证后，n>20 结果不再只是资源估算表，也不只停留在 plan 级等价；每个候选分解生成的 X/CNOT/MCT 线路都能在符号多项式层面验证输出等价和辅助线复原。它仍不是完整 truth-table simulation，也不能替代 n<=20 的 truth-table correctness 结果，但可以更有力地支撑“结构级策略可扩展到更高维项集合”的论文主张。

### 2.5.5 n=32--40 项集级 extended scale

为进一步回应“大规模是否只是 n=20--28 的偶然切片”这一风险，本轮把同一项集级 screen-scale 协议扩展到 `n=32,36,40`，每个维度 48 个生成式高维 ANF 项集，共 144 个样本。该实验使用 `run_screen_scale_terms.py --tag extended` 写入独立结果文件，不覆盖 2.5.4 的主表。验证协议与 n=20--28 完全一致：每个 factor plan 先做 ANF 符号展开验证，再把生成的 X/CNOT/MCT oracle 线路作为 GF(2) 多项式系统符号模拟，检查输入线恢复、输出项集合等价和辅助线清零。

主要产物：

- `results/raw_screen_scale_extended_terms.csv`
- `results/summary_screen_scale_extended_terms.csv`
- `results/analysis_screen_scale_extended_terms.md`
- `paper_latex/tables/screen_scale_extended_terms.tex`

核心结果：

| 对比 | 项集数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---:|---:|---:|---:|
| adaptive all-depth vs single screen, n=32/36/40 | 144 | 110/0/34 | -5.55% | +2680.60% |
| adaptive all-depth vs fixed depth-2, n=32/36/40 | 144 | 0/0/144 | +0.00% | +64.37% |
| depth policy vs single screen, n=32/36/40 | 144 | 110/0/34 | -5.55% | +2061.11% |
| depth policy vs all-depth adaptive, n=32/36/40 | 144 | 0/0/144 | +0.00% | -33.14% |
| depth2 guard vs fixed depth-2, n=32/36/40 | 144 | 0/0/144 | +0.00% | -0.00% |
| ANF plan 符号验证 | 1008 方法行 | 1008/0 通过/失败 | 0 mismatch | - |
| emitted-circuit ANF 符号验证 | 1008 方法行 | 1008/0 通过/失败 | 0 mismatch | max wire terms 288 |

结论：extended scale 的价值在于验证结构策略的高维泛化边界。Depth policy 的训练维度仍是 n=14/16/18，但在 n=32/36/40 上与 all-depth adaptive 全部 score 持平，并节省约三分之一 all-depth 评估时间；相对 single screen 仍保持 110/0/34、平均 score -5.55% 的质量优势。这比 n=20--28 结果更能支撑“大规模项集合上结构级策略可扩展”的主张。边界也必须保留：该实验仍是项集级 symbolic verification，不是完整 truth-table simulation，也没有证明 policy 超过 fixed depth-2 质量基线。

### 2.5.6 depth-3/4 Boolean-ring screen 质量-时间前沿

前两组 scale 结果说明 fixed depth-2 是很强的默认质量基线，但这也带来一个审稿风险：结构级 AI 只是学习何时复制 depth-2，并没有继续提升质量。本轮新增 `--max-screen-depth` 参数，把同一项集级协议扩展到 depth-3 和 depth-4 Boolean-ring screen。该实验定位为高预算质量前沿，不替代默认快速策略。

主要产物：

- `results/raw_screen_scale_depth_frontier_terms.csv`
- `results/summary_screen_scale_depth_frontier_terms.csv`
- `results/analysis_screen_scale_depth_frontier_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_terms.tex`

核心结果：

| 对比 | 项集数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---:|---:|---:|---:|
| screen depth-3 vs fixed depth-2, n=20/28/40 | 72 | 49/0/23 | -1.93% | +193.71% |
| screen depth-4 vs fixed depth-2, n=20/28/40 | 72 | 49/0/23 | -3.10% | +682.97% |
| screen depth-4 vs depth-3, n=20/28/40 | 72 | 44/0/28 | -1.21% | +127.55% |
| all-depth adaptive depth<=4 vs fixed depth-2 | 72 | 49/0/23 | -3.10% | +1129.85% |
| ANF plan 符号验证 | 648 方法行 | 648/0 通过/失败 | 0 mismatch | - |
| emitted-circuit ANF 符号验证 | 648 方法行 | 648/0 通过/失败 | 0 mismatch | max wire terms 244 |

结论：这是本轮最重要的质量增益证据。Depth-3/4 不再只是省时门控，而是稳定打破 fixed depth-2 的 score 上限：在 n=20/28/40 上均无 score loss，depth-4 平均 score 进一步降低 3.10%。代价也很明确，depth-4 平均运行时间比 depth-2 增加约 6.8 倍，all-depth<=4 因需要同时跑多种深度，时间开销更高。因此论文中应把它写成“可调预算的质量-时间前沿”：快速默认模式仍是 depth policy/guard，投稿级质量模式可以加入 depth-3/4 作为高预算候选。

### 2.5.7 depth-frontier policy：把高预算质量前沿学习化

v12 中把 depth-frontier 写成下一步缺口：需要训练一个策略，在 depth-2/3/4 之间选择，使其接近 depth-4 的质量但低于 all-depth<=4 的运行成本。本轮新增 `train_screen_depth_frontier_policy.py`，训练结构级 depth-frontier policy，并把该策略接入 `run_screen_scale_terms.py`。

主要产物：

- `train_screen_depth_frontier_policy.py`
- `models/boolean_screen_depth_frontier_policy.pt`
- `results/raw_boolean_screen_depth_frontier_policy.csv`
- `results/summary_boolean_screen_depth_frontier_policy.csv`
- `results/analysis_boolean_screen_depth_frontier_policy.md`
- `paper_latex/tables/boolean_screen_depth_frontier_policy.tex`
- `results/raw_screen_scale_depth_frontier_policy_terms.csv`
- `results/summary_screen_scale_depth_frontier_policy_terms.csv`
- `results/analysis_screen_scale_depth_frontier_policy_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_policy_terms.tex`
- `results/raw_screen_scale_depth_frontier_policy_generalization_terms.csv`
- `results/summary_screen_scale_depth_frontier_policy_generalization_terms.csv`
- `results/analysis_screen_scale_depth_frontier_policy_generalization_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_policy_generalization_terms.tex`

核心结果：

| 设置 | 对比 | 项集数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---|---:|---:|---:|---:|
| held-out n=28/40 | frontier policy vs depth-2 | 32 | 13/0/19 | -1.95% | +455.93% |
| held-out n=28/40 | frontier policy vs depth-4 | 32 | 0/9/23 | +0.80% | -25.99% |
| held-out n=28/40 | frontier policy vs oracle depth-2/3/4 frontier | 32 | 0/9/23 | +0.80% | -58.76% |
| scale n=20/28/40 | depth_frontier_policy vs depth-2 | 72 | 35/0/37 | -2.19% | +503.20% |
| scale n=20/28/40 | depth_frontier_policy vs depth-4 | 72 | 0/16/56 | +0.97% | -22.17% |
| scale n=20/28/40 | depth_frontier_policy vs all-depth depth<=4 | 72 | 0/16/56 | +0.97% | -58.69% |
| independent seed n=24/28/32/40 | depth_frontier_policy vs depth-2 | 96 | 40/0/56 | -1.85% | +456.43% |
| independent seed n=24/28/32/40 | depth_frontier_policy vs depth-4 | 96 | 0/19/77 | +0.61% | -23.40% |
| independent seed n=24/28/32/40 | depth_frontier_policy vs all-depth depth<=4 | 96 | 0/19/77 | +0.61% | -61.25% |
| ANF plan 符号验证 | 720 方法行 | 720/0 通过/失败 | 0 mismatch | - |
| emitted-circuit ANF 符号验证 | 720 方法行 | 720/0 通过/失败 | 0 mismatch | max wire terms 244 |
| independent seed ANF plan 符号验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | - |
| independent seed emitted-circuit ANF 符号验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | max wire terms 270 |

结论：这是本轮相对 v12 的主要 AI 进展。Depth-frontier policy 不能完全达到 depth-4/oracle frontier，但已经把 depth-4 的质量收益学习化为可选择策略：正式 scale 中相对 fixed depth-2 平均 score 降低 2.19%，独立 seed 泛化集中仍降低 1.85%，两组均无 score loss；同时相对完整 all-depth<=4 评估节省 58.69%--61.25% 时间。论文中应写成“结构级 AI 的质量-时间折中证据”，而不是写成全局最优策略。

### 2.5.7.1 large frontier policy：压缩质量 gap 的增强版

为回应“frontier policy 相对 all-depth 仍有约 0.61%--0.80% score gap”的问题，本轮把 teacher 数据和模型容量继续放大：训练样本从 96 增至 192，验证样本从 36 增至 72，held-out 测试样本从 32 增至 48，隐藏层宽度从 96 增至 160，并保留 depth-2/3/4 frontier 作为监督目标。

主要产物：

- `models/boolean_screen_depth_frontier_policy_large.pt`
- `results/raw_boolean_screen_depth_frontier_policy_large.csv`
- `results/summary_boolean_screen_depth_frontier_policy_large.csv`
- `results/analysis_boolean_screen_depth_frontier_policy_large.md`
- `paper_latex/tables/boolean_screen_depth_frontier_policy_large.tex`
- `results/raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv`
- `results/summary_screen_scale_depth_frontier_policy_large_generalization_terms.csv`
- `results/analysis_screen_scale_depth_frontier_policy_large_generalization_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_policy_large_generalization_terms.tex`
- `results/raw_truth_bridge_n23_large_frontier_terms.csv`
- `results/summary_truth_bridge_n23_large_frontier_terms.csv`
- `results/analysis_truth_bridge_n23_large_frontier_terms.md`
- `paper_latex/tables/truth_bridge_n23_large_frontier_terms.tex`
- `results/analysis_frontier_policy_upgrade.md`
- `paper_latex/tables/frontier_policy_upgrade.tex`

核心结果：

| 设置 | 对比 | 项集/函数数 | score 胜/负/平 | 平均 score 变化 | 平均时间变化 |
|---|---|---:|---:|---:|---:|
| held-out n=28/40 | large frontier vs oracle depth-2/3/4 frontier | 48 | 0/3/45 | +0.04% | -51.30% |
| independent seed n=24/28/32/40 | large frontier vs fixed depth-2 | 96 | 56/0/40 | -2.34% | +563.80% |
| independent seed n=24/28/32/40 | large frontier vs old frontier | 96 | 17/0/79 | -0.49% | +119.26% |
| independent seed n=24/28/32/40 | large frontier vs all-depth depth<=4 | 96 | 0/6/90 | +0.10% | -53.50% |
| n=23 bridge | large frontier vs fixed depth-2 | 6 | 5/0/1 | -2.36% | +790.62% |
| n=23 bridge | large frontier vs old frontier | 6 | 1/0/5 | -0.48% | +46.16% |
| n=23 bridge | large frontier vs all-depth | 6 | 0/1/5 | +0.12% | -45.99% |
| large scale ANF plan 验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | - |
| large scale emitted-circuit ANF 验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | - |
| large n=23 完整 truth-table / plan / emitted-circuit 验证 | 60 方法行 | 60/0 通过/失败 | 0 mismatch | - |

结论：large frontier policy 是本轮更明确的“明显提升”证据。它把 held-out 相对 oracle frontier 的 score gap 从旧模型的 +0.80% 压到 +0.04%，把独立泛化集相对 all-depth 的 gap 从 +0.61% 压到 +0.10%，并在同一泛化集上相对旧 policy 取得 17/0/79、平均 score -0.49%。但它更频繁选择 depth-3/4，因而比旧 policy 慢、辅助线 lifetime area 也可能增加。论文中应写成“质量增强型结构策略”，不能写成“同时更快更优”的策略。

### 2.5.7.2 cost-aware frontier policy：质量-时间-辅助线折中版

large frontier policy 解决了质量 gap，但时间和辅助线生命周期代价偏高。为把策略从单一质量目标推进到质量-时间-辅助线折中，本轮扩展 `train_screen_depth_frontier_policy.py`，新增 `--label-time-weight` 和 `--label-ancilla-weight`。当前 cost-aware 版本使用标签目标 `score_delta + 0.003*time_delta`（相对 fixed depth-2），保持同样的 192/72/48 train/validation/test 规模和 hidden=160。

主要产物：

- `models/boolean_screen_depth_frontier_policy_cost_time003.pt`
- `results/raw_boolean_screen_depth_frontier_policy_cost_time003.csv`
- `results/summary_boolean_screen_depth_frontier_policy_cost_time003.csv`
- `results/analysis_boolean_screen_depth_frontier_policy_cost_time003.md`
- `paper_latex/tables/boolean_screen_depth_frontier_policy_cost_time003.tex`
- `results/raw_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv`
- `results/summary_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv`
- `results/analysis_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_policy_cost_time003_generalization_terms.tex`
- `results/raw_truth_bridge_n23_cost_time003_frontier_terms.csv`
- `results/summary_truth_bridge_n23_cost_time003_frontier_terms.csv`
- `results/analysis_truth_bridge_n23_cost_time003_frontier_terms.md`
- `paper_latex/tables/truth_bridge_n23_cost_time003_frontier_terms.tex`

核心结果：

| 设置 | 对比 | 项集/函数数 | score 胜/负/平 | 平均 score 变化 | 平均时间变化 | T-depth / lifetime area |
|---|---|---:|---:|---:|---:|---:|
| held-out n=28/40 | cost policy vs cost-aware frontier | 48 | 0/6/40 | +0.38% | -71.54% | - |
| independent seed n=24/28/32/40 | cost policy vs fixed depth-2 | 96 | 56/0/40 | -1.39% | +170.03% | T-depth -1.36%，lifetime +14.63% |
| independent seed n=24/28/32/40 | cost policy vs all-depth | 96 | 0/53/43 | +1.10% | -76.54% | T-depth +1.06%，lifetime -8.86% |
| independent seed n=24/28/32/40 | cost policy vs large policy | 96 | 1/48/47 | +0.99% | -33.02% | T-depth +0.97%，lifetime -7.61% |
| n=23 bridge | cost policy vs fixed depth-2 | 6 | 4/0/2 | -1.46% | +196.09% | T-depth -1.43%，lifetime +15.95% |
| n=23 bridge | cost policy vs large policy | 6 | 0/5/1 | +0.92% | -56.29% | T-depth +0.73%，lifetime -12.62% |
| cost scale ANF plan / emitted-circuit 验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | - | - |
| cost n=23 完整 truth-table / plan / emitted-circuit 验证 | 60 方法行 | 60/0 通过/失败 | 0 mismatch | - | - |

结论：cost-aware frontier policy 不是新的最高质量策略，而是一个可写进论文的“运行模式”贡献：large policy 是质量模式，cost-aware policy 是快速质量折中模式。它在独立泛化集上保持与 large policy 相同的 56/0/40 胜/负/平结构，但把相对 depth-2 的平均 plan time 增幅从 +563.80% 压到 +170.03%，把 lifetime area 增幅从 +26.13% 压到 +14.63%。在 n=23 完整 bridge 上，相对 large policy 节省 56.29% plan time 和 12.62% lifetime area，代价是 score 高 0.92%。这比单纯继续追求最低 score 更接近“资源约束综合”的论文主题。

### 2.5.8 n=21/22 完整 truth-table bridge

为回应“n>20 只有项集级符号验证”的审稿风险，本轮新增 `run_truth_bridge_terms.py`，在 n=21/22 上构造完整 truth table，并对 emitted X/CNOT/MCT oracle circuit 做 bit-parallel truth-table verification。该实验规模故意小于 n=20--40 scale，因为 truth-table 构造是主成本，但它把完整验证边界向 n>20 后移。

主要产物：

- `run_truth_bridge_terms.py`
- `results/raw_truth_bridge_terms.csv`
- `results/summary_truth_bridge_terms.csv`
- `results/analysis_truth_bridge_terms.md`
- `paper_latex/tables/truth_bridge_terms.tex`

核心结果：

| 验证项或比较 | 结果 | 说明 |
|---|---:|---|
| 完整 truth-table oracle 验证 | 120/120 | 所有 emitted circuit 逐点验证通过 |
| ANF plan 符号验证 | 120/120 | 0 plan mismatch |
| emitted-circuit ANF 符号验证 | 120/120 | 0 circuit mismatch，max wire terms 215 |
| 平均 truth-table 构造时间 | 30.34 s/function | n=21/22 合计 12 个函数 |
| screen depth-4 vs fixed depth-2 | 10/0/2 | 平均 score -3.81%，plan time +734.91% |
| depth-frontier policy vs fixed depth-2 | 8/0/4 | 平均 score -3.50%，plan time +634.71% |
| depth-frontier policy vs depth-4 | 0/2/10 | 平均 score +0.32%，plan time -15.54% |
| depth-frontier policy vs all-depth | 0/2/10 | 平均 score +0.32%，plan time -50.87% |
| adaptive all-depth vs single screen | 11/0/1 | 平均 score -10.19% |

结论：这是验证边界上的实质推进。n=21/22 bridge 不能替代 n=24--40 的完整 truth-table simulation，但它证明本项目的 emitted-circuit 生成与符号验证不是孤立的资源估算；同一类方法在 n>20 的完整枚举切片上也通过了逐点 oracle 验证。

### 2.5.9 逻辑层 schedule proxy：补充 T-depth 与辅助线生命周期证据

为回应“只报告 T-count/CNOT/peak ancilla 仍偏逻辑资源静态统计”的审稿风险，本轮新增 emitted-circuit schedule proxy。它不做硬件 mapping，不引入连通性、routing 或噪声模型；只在生成的 X/CNOT/MCT oracle circuit 上计算并行逻辑深度、CNOT-depth proxy、T-depth proxy、显式辅助线 live peak 和显式辅助线 lifetime area。这使论文能讨论后端相关的逻辑层时序/生命周期 trade-off，而不越界声称真实设备优势。

主要产物：

- `analyze_schedule_metrics.py`
- `results/raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv`
- `results/summary_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv`
- `results/analysis_screen_scale_schedule_depth_frontier_policy_generalization_terms.md`
- `results/raw_schedule_truth_bridge_terms.csv`
- `results/summary_schedule_truth_bridge_terms.csv`
- `results/analysis_schedule_truth_bridge_terms.md`
- `results/raw_schedule_truth_bridge_n23_terms.csv`
- `results/summary_schedule_truth_bridge_n23_terms.csv`
- `results/analysis_schedule_truth_bridge_n23_terms.md`
- `results/summary_schedule_metrics.csv`
- `results/analysis_schedule_metrics.md`
- `paper_latex/tables/schedule_truth_bridge_n23_terms.tex`
- `paper_latex/tables/schedule_metrics.tex`

核心结果：

| 设置 | 对比 | 项数/方法行 | score 胜/负/平 | T-depth proxy 胜/负/平 | lifetime area 变化 |
|---|---|---:|---:|---:|---:|
| schedule generalization n=24/28/32/40 | frontier policy vs fixed depth-2 | 96 | 40/0/56，-1.85% | 40/0/56，-1.85% | +20.09% |
| schedule generalization n=24/28/32/40 | frontier policy vs depth-4 | 96 | 0/19/77，+0.61% | 0/19/77，+0.55% | -5.42% |
| schedule generalization n=24/28/32/40 | frontier policy vs all-depth | 96 | 0/19/77，+0.61% | 0/19/77，+0.55% | -5.42% |
| schedule truth bridge n=21/22 | frontier policy vs fixed depth-2 | 12 函数/120 方法行 | 8/0/4，-3.50% | 8/0/4，-3.32% | +32.93% |
| schedule truth bridge n=21/22 | frontier policy vs depth-4 | 12 函数/120 方法行 | 0/2/10，+0.32% | 0/2/10，+0.32% | -4.01% |
| schedule truth bridge n=21/22 | 完整 truth-table 验证 | 120 方法行 | 120/120 通过 | 120/120 plan/circuit 验证通过 | 0 mismatch |
| schedule truth bridge n=23 | frontier policy vs fixed depth-2 | 6 函数/60 方法行 | 4/0/2，-1.88% | 4/0/2，-1.69% | +29.49% |
| schedule truth bridge n=23 | frontier policy vs depth-4 | 6 函数/60 方法行 | 0/1/5，+0.61% | 0/1/5，+0.52% | -5.09% |
| schedule truth bridge n=23 | 完整 truth-table 验证 | 60 方法行 | 60/60 通过 | 60/60 plan/circuit 验证通过 | 0 mismatch |

解释：这个结果让 frontier policy 的定位更清楚。相对 fixed depth-2，它不仅降低 score，也同步降低 T-depth proxy；代价是显式辅助线生命周期面积增加，说明更深结构会延长部分辅助线占用。相对 depth-4/all-depth，它牺牲约 0.32%--0.55% 的 T-depth proxy，在 n=23 上牺牲 0.52%，却减少约 4%--5% 的显式辅助线 lifetime area，并显著节省搜索时间。论文中应把它写成“逻辑层后端相关 proxy 下的质量-生命周期 trade-off”，而不是写成硬件后端映射结论。

### 2.5.10 n=23 完整 truth-table bridge

本轮把完整 truth-table bridge 从 n=21/22 继续推进到 n=23。该实验仍只覆盖小样本，因为完整 truth-table 构造是主成本；但它把“项集级符号验证是否可信”的验证边界向更高维推进了一步。

运行命令：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_truth_bridge_terms.py --seed 20260713 --ns 23 --per-n 6 --workers 2 --max-screen-depth 4 --tag schedule_truth_bridge_n23
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_schedule_metrics.py --input schedule_generalization=results/raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv --input schedule_truth_bridge=results/raw_schedule_truth_bridge_terms.csv --input schedule_truth_bridge_n23=results/raw_schedule_truth_bridge_n23_terms.csv --summary results/summary_schedule_metrics.csv --out results/analysis_schedule_metrics.md --latex-out paper_latex/tables/schedule_metrics.tex
```

主要产物：

- `results/raw_schedule_truth_bridge_n23_terms.csv`
- `results/summary_schedule_truth_bridge_n23_terms.csv`
- `results/analysis_schedule_truth_bridge_n23_terms.md`
- `paper_latex/tables/schedule_truth_bridge_n23_terms.tex`

核心审计：

| 验证项或比较 | 结果 | 说明 |
|---|---:|---|
| n=23 完整 truth-table oracle 验证 | 60/60 | 6 个函数、10 个方法，所有 emitted circuit 逐点验证通过 |
| n=23 ANF plan 符号验证 | 60/60 | 0 plan mismatch |
| n=23 emitted-circuit ANF 符号验证 | 60/60 | 0 circuit mismatch |
| 平均 truth-table 构造时间 | 209.54 s/function | 总运行时间 665.54 s，2 workers |
| depth-frontier policy vs fixed depth-2 | 4/0/2 | score -1.88%，T-depth proxy -1.69%，lifetime area +29.49% |
| depth-frontier policy vs depth-4 | 0/1/5 | score +0.61%，T-depth proxy +0.52%，lifetime area -5.09% |
| depth-frontier policy vs all-depth | 0/1/5 | score +0.61%，plan time -48.77% |

结论：n=21/22/23 bridge 合计达到 18 个函数、180 个方法行的完整 truth-table oracle 验证、plan 验证和 emitted-circuit 符号验证。它仍不能替代 n=24--40 的完整枚举，但比 v16 更有力地证明了项集级符号验证与最终 oracle circuit 逐点语义之间的一致性。

### 2.6 高维 root-action teacher 诊断

新增 `analyze_highdim_root_action_oracle.py`，用于回答一个更具体的问题：高维 CNOT-only linear-pair 根层动作排序是否还有可学习空间。该脚本不追求全局最优，而是在 `highdim_neural_prior` 的 12 个 `n=14` random ANF 函数上，用真实 greedy child plan 对更宽的 root-action 集合做 one-step teacher 评分。

主要产物：

- `results/raw_highdim_root_action_oracle.csv`
- `results/summary_highdim_root_action_oracle.csv`
- `results/analysis_highdim_root_action_oracle.md`
- `paper_latex/tables/highdim_root_action_oracle.tex`

核心结果：

| 对比 | score 胜/负/平 | 平均 score 变化 | 解释 |
|---|---:|---:|---|
| oracle top-12 vs heuristic top-4 | 3/0/7 | -0.18% | 更宽动作集合有小幅 headroom |
| oracle top-24 vs heuristic top-4 | 3/0/7 | -0.18% | top-12 已覆盖该切片的额外收益 |
| oracle top-24 vs heuristic top-1 | 7/0/3 | -0.43% | 单一启发式 top-1 会丢失多个更好 root action |
| neural top-4 vs heuristic top-4 | 1/1/8 | +0.06% | 现有 immediate-label 高维模型没有利用 teacher signal |

解释：

- 这个结果不是新的最终综合最优结果，而是给高维 neural guidance 提供监督目标。
- 它说明高维 root-action 排序有真实但幅度较小的可学习空间；当前 immediate-gain 训练的 `linear_action_scorer_highdim.pt` 还没有学到这个 one-step teacher。
- 后续如果继续补强 AI 贡献，应优先训练 root-action ranker 去逼近 oracle top-12/top-24，而不是继续简单叠加现有 neural prior。

### 2.6.1 Pairwise-wide root-action ranker 与 n=16 full synthesis

本轮在 pairwise root-action ranker 基础上继续补了一层保守候选扩展：不再让神经排序替换启发式 top-4，而是保留 heuristic top-4，并额外加入 neural top-8 的 root action。这个策略对应代码中的 `fprm_linear_pair_deep_root_neural_wide` 和 `fprm_linear_pair_deep_ai_guard_wide`。它的意义是把神经模型写成“候选扩展器”，而不是高维递归搜索的单点决策器。

新增/更新产物：

- `analyze_paired_method_comparison.py`
- `results/raw_highdim_root_action_pairwise_widths.csv`
- `results/analysis_highdim_root_action_pairwise_widths.md`
- `results/raw_ultra_root_action_pairwise_widths.csv`
- `results/analysis_ultra_root_action_pairwise_widths.md`
- `results/raw_highdim_neural_prior_pairwise_wide.csv`
- `results/analysis_neural_prior_highdim_pairwise_wide_ablation.md`
- `results/raw_ultra_highdim_resource_pairwise_wide_resource.csv`
- `results/analysis_ultra_pairwise_wide_vs_recursive.md`
- `results/analysis_ultra_pairwise_wide_vs_old_resource.md`

关键结果：

| 对比 | 函数集 | score 胜/负/平 | 平均 score 变化 | 解释 |
|---|---|---:|---:|---|
| heuristic top-4 + neural top-8 vs heuristic top-4 | 10 个有 linear action 的 n=14 random ANF | 2/0/8 | -0.14% | 接近 oracle top-24 的 3/0/7、-0.18% headroom |
| highdim pairwise-wide learned prior vs no-prior | 12 个 n=14 random ANF | 2/0/10 | -0.05% | 比原 pairwise top-4 的 -0.04% 略好，但运行时间 +179.59% |
| heuristic top-4 + neural top-8 vs heuristic top-4 | 23 个有 linear action 的 n=16 random ANF | 5/0/18 | -0.06% | 修复旧 neural top-4 的负迁移；旧 neural top-4 为 4/2/17、+0.05% |
| pairwise-wide Resource-NMCTS vs deterministic recursive guard | 24 个 n=16 random ANF | 10/0/14 | -0.18% | full synthesis 层面的无 score-loss AI 增益 |
| pairwise-wide Resource-NMCTS vs old Resource-NMCTS root-teacher | 24 个 n=16 random ANF | 10/0/14 | -0.12% | 新 ranker 与 wide union 明确优于旧 root-teacher 结果 |

解释：这是当前高维 AI 贡献中最可信的一组正向证据。它仍不是“大幅提升”：n=16 平均 score 降幅为 0.18%，且运行时间相对 deterministic recursive guard 增加约 274.75%。但它已经把之前“高维 neural top-4 会负迁移”的问题改成了 full synthesis 层面的无 score-loss 正向结果，适合作为下一版论文中 AI 模块的核心消融之一。

### 2.6.2 Boolean-ring linear factor 与 n=16 结构性提升

pairwise-wide 主要改善“根动作排序”，但 headroom 只有 0.1%--0.2%。本轮把高维结构分支从普通 square-free ANF 乘法推广到 Boolean 环规则：允许 quotient monomial 与 linear factor 共享变量，并在展开时使用 `x_i^2=x_i` 和 GF(2) 偶数项消去。这样可以捕获形如 `(x_i xor x_j) * x_i m = x_i m xor x_i x_j m` 的重叠变量因子；旧 `linear_pair` 要求 quotient 与 factor 变量不相交，会漏掉这类结构。

新增/更新产物：

- `results/raw_highdim_neural_prior_boolean_guard.csv`
- `results/analysis_highdim_boolean_guard_vs_pairwise_wide.md`
- `results/analysis_highdim_boolean_guard_vs_no_prior.md`
- `results/raw_ultra_boolean_linear_pair_deep.csv`
- `results/analysis_ultra_boolean_linear_vs_deep.md`
- `results/analysis_ultra_boolean_linear_vs_pairwise_resource.md`
- `results/raw_ultra_highdim_resource_boolean_guard.csv`
- `results/analysis_ultra_boolean_guard_vs_pairwise_wide.md`
- `results/analysis_ultra_boolean_guard_vs_old_deep.md`
- `results/raw_mega_boolean_linear_screen.csv`
- `results/analysis_mega_boolean_screen_vs_resource.md`
- `models/boolean_linear_action_scorer_root_teacher.pt`
- `results/raw_boolean_neural_highdim.csv`
- `results/analysis_boolean_neural_guard_vs_deterministic.md`
- `results/raw_giga_boolean_neural_resource.csv`
- `results/analysis_giga_resource_vs_boolean_screen.md`
- `results/analysis_giga_resource_vs_and_direct.md`
- `results/raw_mega_boolean_screen_deep.csv`
- `results/analysis_mega_screen_deep_vs_screen.md`
- `results/raw_giga_boolean_screen_deep.csv`
- `results/analysis_giga_screen_deep_vs_screen.md`
- `results/raw_giga_recursive_screen_resource.csv`
- `results/analysis_giga_resource_recursive_screen_vs_old.md`
- `results/raw_giga_boolean_screen_deeper.csv`
- `results/analysis_giga_screen_deeper_vs_deep.md`
- `results/raw_giga_deeper_screen_resource.csv`
- `results/analysis_giga_resource_deeper_vs_old_resource.md`

关键结果：

| 对比 | 函数集 | score 胜/负/平 | 平均 score 变化 | 解释 |
|---|---|---:|---:|---|
| Boolean-guard Resource-NMCTS vs pairwise-wide Resource-NMCTS | 12 个 n=14 random ANF | 9/0/3 | -0.82% | 高维 learned-prior 切片从 0.05% 量级提升到接近 1% |
| Boolean-guard Resource-NMCTS vs no-prior Resource-NMCTS | 12 个 n=14 random ANF | 9/0/3 | -0.86% | 同时降低 T、CNOT 和 depth；时间代价约 +247.75% |
| Boolean-linear-deep vs deterministic recursive guard | 24 个 n=16 random ANF | 17/3/4 | -0.39% | 单独结构分支已经优于旧 recursive linear-pair guard |
| Boolean-linear-deep vs pairwise-wide Resource-NMCTS | 24 个 n=16 random ANF | 14/6/4 | -0.22% | 单分支质量优于上一轮完整 Resource，且平均时间低 72.31% |
| Boolean-guard Resource-NMCTS vs pairwise-wide Resource-NMCTS | 24 个 n=16 random ANF | 14/0/10 | -0.34% | 组合主方法无 score-loss 改善，T/CNOT/depth 同时下降 |
| Boolean-guard Resource-NMCTS vs deterministic recursive guard | 24 个 n=16 random ANF | 18/0/6 | -0.52% | 当前最强 n=16 full synthesis 证据 |
| Boolean-linear neural guard vs deterministic Boolean-linear | 24 个 n=16 random ANF | 4/0/20 | -0.12% | 新 boolean-linear root-teacher 模型只有小幅无 loss 收益，平均时间 +94.49%，仍不是主提升来源 |
| Boolean-linear screen vs old Resource-NMCTS | 12 个 n=18 random ANF | 0/12/0 | +42.45% | ANF-only screen 很快但质量差，只能作为 n=18/n=20 边界诊断 |
| Adaptive depth-2 Boolean screen vs single Boolean screen | 12 个 n=18 random ANF | 11/0/1 | -6.47% | adaptive screen 改善单层 screen，但完整 Resource 仍进一步降低 23.85% |
| Recursive-screen Resource-NMCTS vs old Resource-NMCTS | 6 个 n=20 random ANF | 5/0/1 | -4.52% | root-beam/fast pair timeout 时的超高维有效修复 |
| Deeper-screen Resource-NMCTS vs old Resource-NMCTS | 6 个 n=20 random ANF | 5/0/1 | -7.47% | depth-2 screen 在同一 timeout 边界上进一步降低 T/CNOT/depth/score |

解释：Boolean-ring linear-deep 是 n=16 上最重要的实际提升。它不是单纯扩大 beam 或神经 top-k，而是扩大了可表示的代数因子类型；因此相对 pairwise-wide neural guard 更像“方法创新”。本轮新训练的 Boolean-linear action scorer 能在 guard 下避免 score loss，但 4/0/20、-0.12% 的幅度仍不足以作为显著 AI 贡献。必须区分 deep 版本和 screen 版本：deep 版本在 n=14/n=16 有稳定质量收益；recursive screen 在 n=20 这种 FPRM 分支全部 timeout 的边界上有效，depth-2 screen 还能把旧 Resource 的 score 降幅扩大到 -7.47%，但在 n=18 仍远差于旧 Resource，不应泛化为中高维主质量方法。

### 2.7 小规模 exact FPRM-DP 精确切片

本轮新增 `analyze_exact_fprm_dp.py`，用于补上一个小规模、同模型内部精确证据链。它对 bounded fixed-polarity FPRM factor model 做动态规划，枚举所有单项式 factor action 和 CNOT-only linear-pair factor action，并对所有 FPRM polarity 求最优。这个 exact 只限定在该受限 FPRM 因子模型内，不是全局 reversible circuit optimum。

主要产物：

- `results/raw_exact_fprm_dp.csv`
- `results/summary_exact_fprm_dp.csv`
- `results/analysis_exact_fprm_dp.md`
- `paper_latex/tables/exact_fprm_dp.tex`

数据范围与审计：

- 覆盖 `traditional_resource` 中全部 `n<=4` 的 72 个函数。
- error：0
- skipped：0
- incorrect：0
- 每条 exact DP 线路均通过 oracle truth-table 验证。

核心结果：

| 对比 | 配对数 | score 胜/负/平 | 平均 score 变化 |
|---|---:|---:|---:|
| Resource-NMCTS vs Exact FPRM-DP | 72 | 51/3/18 | -12.18% |
| Pareto-Resource-NMCTS vs Exact FPRM-DP | 72 | 51/0/21 | -12.20% |
| Exact FPRM-DP vs ESOP-MILP | 72 | 57/12/3 | -13.30% |
| Exact FPRM-DP vs SSHR-I CNOT | 72 | 60/12/0 | -13.73% |
| Exact FPRM-DP vs SSHR-I T | 72 | 59/12/1 | -13.38% |

解释：

- 如果 Resource/Pareto 能击败 Exact FPRM-DP，说明 portfolio 找到了这个受限 FPRM-DP 模型之外的候选线路，而不是 exact solver 失败。
- Exact FPRM-DP 自身比 ESOP-MILP 和 exact SSHR-I 的加权 score 更好，但相对 SSHR-I 的 CNOT 通常更高；因此它进一步支持低 T / 低加权资源主张，不支持 CNOT-only 最优主张。
- 这一切片把“公平性”从 time-limited external baseline 往前推进了一步：至少在 `n<=4` 的 bounded FPRM factor family 内，可以给出 exact optimum 参照。

### 2.8 小规模 exact XAG 乘法复杂度下界

本轮新增 `analyze_exact_xag_mc.py`，用于补上比 bounded FPRM-DP 更硬的 T-count 参照。该脚本在 XOR-AND graph 模型中对 `n<=4` 的目标布尔函数做 exact breadth-first search，求最少 AND 节点数。由于 logical-AND 资源模型中每个 AND 至少需要 4 个 T gate，因此 `4 * min AND` 是全局逻辑层 T-count 下界。它不是 CNOT、depth 或完整可逆线路最优。

主要产物：

- `results/raw_exact_xag_mc.csv`
- `results/summary_exact_xag_mc.csv`
- `results/analysis_exact_xag_mc.md`
- `paper_latex/tables/exact_xag_mc.tex`

数据范围与审计：

- 覆盖 `traditional_resource` 中全部 `n<=4` 的 72 个函数。
- solved：72/72
- unknown/error：0
- 最重函数访问 66541 个 exact BFS 状态，说明该切片当前是可复现的全局小规模下界，而不是采样估计。

核心结果：

| 方法 | 配对数 | 达到 T 下界 | 高于下界 | 平均 T gap |
|---|---:|---:|---:|---:|
| Resource-NMCTS | 72 | 12 | 60 | +53.01% |
| Pareto-Resource-NMCTS | 72 | 12 | 60 | +53.01% |
| ESOP-MILP | 72 | 3 | 69 | +120.14% |
| SSHR-I-T | 72 | 5 | 67 | +143.06% |

解释：

- 没有任何方法低于 exact XAG T 下界，说明当前 T-count 口径与下界一致。
- Resource/Pareto 在 12/72 个函数上达到全局 XAG 乘法复杂度 T 下界，且平均 T gap 明显低于 ESOP-MILP 和 T-optimized SSHR-I。
- 这个证据只能支撑低 T-count 接近全局乘法复杂度下界，不能支撑 CNOT/depth 全局最优。

### 2.9 高维 root teacher 与 wide guard 负向诊断

本轮进一步把 2.6 的 teacher signal 实际用于训练 `models/linear_action_scorer_root_teacher.pt`，并新增 `highdim_guard_upgrade` preset 测试宽根层 deterministic guard。

主要产物：

- `models/linear_action_scorer_root_teacher.pt`
- `results/raw_highdim_root_action_teacher.csv`
- `results/summary_highdim_root_action_teacher.csv`
- `results/analysis_highdim_root_action_teacher.md`
- `results/raw_highdim_guard_upgrade.csv`
- `results/summary_highdim_guard_upgrade.csv`
- `results/analysis_highdim_guard_upgrade.md`

核心结论：

- root-teacher 模型训练 2287 个样本，valid loss 为 0.2778；但在同一 root-action 诊断上，`root_neural_top4` 相对 heuristic top-4 为 2/3/5，平均 score 变化 +0.16%，没有形成可用提升。
- `and_resource_nmcts_wide` 在 12 个 `n=14` random ANF 函数上相对 `and_resource_nmcts` 为 0/0/12，资源完全持平，但平均运行时间增加 59.80%。
- 因此，本轮不能把高维 root-teacher 或 wide-fast 写成主贡献；它们应作为负向诊断，说明当前高维 AI 排序仍未突破，后续需要更强的策略梯度、pairwise ranking 或更丰富特征。

### 2.10 多资源权重鲁棒性与中文 PDF 交付

本轮新增 `analyze_weight_robustness.py`，用于回答一个直接的审稿风险：当前 score 结论是否只是某一组权重系数制造出来的。该脚本不重新综合线路，而是对已经通过验证的 raw CSV 行做 post-hoc rescoring，比较 Paper score、T-only、T-heavy、CNOT-depth 和 Ancilla-tight 五种逻辑资源权重。

主要产物：

- `results/summary_weight_robustness.csv`
- `results/analysis_weight_robustness.md`
- `paper_latex/tables/weight_robustness_compact.tex`
- `paper_latex_zh/resource_nmcts_zh_robustness.tex`
- `paper_latex_zh/resource_nmcts_zh_robustness.pdf`
- `paper_latex_zh/resource_nmcts_zh_stage_delivery.tex`
- `paper_latex_zh/resource_nmcts_zh_stage_delivery.pdf`

核心结果：

| 对比 | Paper score | T-only | CNOT-depth | Ancilla-tight |
|---|---:|---:|---:|---:|
| Pareto vs ESOP cube beam, n<=6 | 174/0/3，-36.09% | 174/0/3，-38.95% | 174/0/3，-32.08% | 174/0/3，-32.75% |
| Pareto vs ESOP-MILP, n<=6 | 167/3/7，-29.84% | 166/0/11，-32.77% | 165/4/8，-25.44% | 167/3/7，-26.68% |
| Pareto vs SSHR-H, n<=6 | 173/4/0，-41.06% | 173/0/4，-47.93% | 168/9/0，-27.87% | 172/5/0，-31.95% |
| Resource vs root beam, n=16 | 23/0/1，-4.36% | 23/0/1，-4.70% | 23/0/1，-4.28% | 23/0/1，-3.43% |
| Resource vs root beam, n=18 | 12/0/0，-5.29% | 12/0/0，-6.19% | 12/0/0，-4.54% | 11/1/0，-3.33% |
| Resource vs fast linear-pair, n=18 | 12/0/0，-3.55% | 12/0/0，-3.75% | 12/0/0，-3.23% | 12/0/0，-3.33% |

解释：

- 主要结论在 T-only、CNOT-depth 和 Ancilla-tight 等替代权重下仍成立，说明当前结果不是单一 score 权重偶然造成的。
- CNOT-depth profile 下相对 SSHR-H 的优势收窄到 -27.87%，这反而强化了论文边界：SSHR 的 CNOT-oriented 优势必须如实承认，本文只主张低 T 和低加权资源。
- 新中文 PDF `resource_nmcts_zh_robustness.pdf` 是独立投稿论证稿，重点写清楚“方法不依赖 SSHR、AI/MCTS 贡献如何被消融支持、权重鲁棒性如何降低审稿风险”。

### 2.11 外部工具链 readiness 与文献边界审计

本轮新增 `analyze_toolchain_readiness.py`，把“还缺 ROS/mockturtle/RevKit 复现实验”从文字判断变成可复现环境审计。

主要产物：

- `results/analysis_toolchain_readiness.md`
- `results/raw_screen_scale_extended_terms.csv`
- `results/summary_screen_scale_extended_terms.csv`
- `results/analysis_screen_scale_extended_terms.md`
- `results/raw_screen_scale_depth_frontier_terms.csv`
- `results/summary_screen_scale_depth_frontier_terms.csv`
- `results/analysis_screen_scale_depth_frontier_terms.md`
- `literature_notes.md` 中新增 back-end-aware oracle synthesis、mockturtle、RevKit 定位说明。

当前环境审计结果：

| 工具 | 当前状态 | 作用 |
|---|---|---|
| ABC | 可用，位于 `tmp/abc/abc` | 已支撑 AIG/XAG/LUT/ESOP 外部估算 baseline |
| mockturtle | 未在 PATH 或 Python 环境中发现 | 后续 logic-network / reversible-toolchain baseline 候选 |
| RevKit | 未在 PATH 或 Python 环境中发现 | 后续 reversible-synthesis baseline 候选 |

解释：

- 这不是新的资源提升结果，但它降低了投稿准备中的不确定性：当前能诚实声称的是 ABC/BDD/ESOP/SSHR 复现路径，不能声称已经完成 mockturtle/RevKit/ROS 复现。
- 文献上，back-end-aware fault-tolerant oracle synthesis 已经把 XAG oracle synthesis 扩展到后端感知指标；本文目前只做逻辑层，因此不能借用其 mapping/back-end 结论。
- 本轮还临时探测了两个潜在算法升级方向：高维 affine-linear factor 和局部 polarity 下降。前者在前几个 `n=14` 函数上更慢且 score 更差，后者在高项数函数上选回 polarity 0 且 fast linear-pair 结果更差；因此暂不纳入方法贡献。

### 2.12 ROS-style LUT proxy：资源约束 LUT 路线压力测试

本轮新增 `run_ros_lut_proxy.py`，用于弥补“只有固定 K=4 ABC-LUT baseline，不足以代表 LUT 路线”的缺口。它不是官方 ROS、RevKit 或 mockturtle 复现，而是一个明确标注的外部 proxy：从同一导出 BLIF benchmark 出发，调用 ABC `if -K` 对 `K=3,4,5` 做 sweep；每个映射后 BLIF 都经过 truth-table 检查，再把 LUT 网络估算成 local-ANF compute/action/uncompute 资源，并按当前 score 选择 best-K。

主要产物：

- `run_ros_lut_proxy.py`
- `results/raw_ros_lut_proxy_sweep.csv`
- `results/raw_ros_lut_proxy_best.csv`
- `results/summary_ros_lut_proxy.csv`
- `results/analysis_ros_lut_proxy.md`
- `results/manifest_ros_lut_proxy.json`
- `paper_latex/tables/ros_lut_proxy.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v18.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v18.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v19.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v19.pdf`

覆盖范围与正确性：

- 函数集：`n=3..6` 传统函数 177 个，加上 `n=14,15,16,18` 高维导出函数 132 个，共 309 个函数。
- K-sweep 行：927 行。
- Best-K 行：309 行。
- truth-table 检查：927/927 通过；无 timeout、error、skipped 或 incorrect 行。

关键结果：

| 对比 | 指标 | 函数数 | 胜/负/平 | 平均相对变化 |
|---|---|---:|---:|---:|
| Resource-NMCTS vs ROS-style LUT proxy | score | 309 | 309/0/0 | -83.77% |
| Profile-Resource-NMCTS vs ROS-style LUT proxy | score | 132 | 132/0/0 | -97.38% |
| Pareto-Resource-NMCTS vs ROS-style LUT proxy | score | 309 | 309/0/0 | -84.27% |
| AND-direct ANF vs ROS-style LUT proxy | score | 309 | 307/2/0 | -67.45% |
| ROS-style LUT proxy vs fixed K=4 LUT | score | 309 | 219/0/90 | -18.12% |

解释：

- Best-K proxy 相比固定 K=4 ABC-LUT 自身有明显提升，因此它是更强的 LUT 压力测试，而不是重复已有 fixed-K 结果。
- Resource/Pareto/Profile 仍然全胜该 proxy，说明当前低加权资源优势不只依赖于一个较弱的固定 LUT 参数。
- 这仍不能写成“已复现 ROS”。官方 ROS 的 LUT decomposition、垃圾管理和 reversible-toolchain 细节没有被实现；本文只能把它写成“ROS-style LUT proxy 外部对比”。

## 3. 当前文件交付清单

### 3.1 核心代码

- `factor_plan.py`：FPRM/线性因子/beam/greedy 计划生成。
- `synthesizers.py`：方法组合、Resource/Profile/Pareto 候选选择。
- `run_experiments.py`：实验运行、隔离超时、resume/replace 逻辑。
- `train_neural_policy.py`：普通 factor-action 与高维 linear-action 神经先验训练。
- `analyze_results.py`：内部实验分析。
- `analyze_runtime.py`：运行时间和资源表生成。
- `analyze_external_baselines.py`：外部 baseline 对比分析。
- `analyze_esop_baseline.py`：新增 ESOP 专项分析。
- `analyze_search_contribution.py`：新增搜索贡献分解分析。
- `analyze_weight_robustness.py`：新增多资源 score 权重鲁棒性分析。
- `analyze_exact_fprm_dp.py`：新增小规模 bounded FPRM-DP 精确切片。
- `analyze_exact_xag_mc.py`：新增小规模 exact XAG 乘法复杂度 T 下界。
- `analyze_highdim_root_action_oracle.py`：新增高维 root-action teacher 诊断。
- `analyze_toolchain_readiness.py`：新增外部工具链 readiness 审计。
- `run_ros_lut_proxy.py`：新增 ROS-style LUT proxy 外部基线。

### 3.2 结果文件

- `results/raw_traditional_resource.csv`
- `results/raw_external_traditional_resource_n6.csv`
- `results/analysis_esop_baseline.md`
- `results/summary_esop_baseline.csv`
- `results/raw_mega_highdim_resource.csv`
- `results/analysis_mega_highdim_resource.md`
- `results/runtime_mega_highdim_resource.md`
- `results/raw_giga_highdim_resource.csv`
- `results/summary_giga_highdim_resource.csv`
- `results/analysis_giga_highdim_resource.md`
- `results/runtime_giga_highdim_resource.md`
- `results/analysis_external_mega_highdim_resource.md`
- `results/analysis_search_contribution.md`
- `results/summary_search_contribution.csv`
- `results/analysis_neural_prior_highdim_ablation.md`
- `results/raw_neural_prior_highdim_ablation.csv`
- `results/raw_exact_fprm_dp.csv`
- `results/summary_exact_fprm_dp.csv`
- `results/analysis_exact_fprm_dp.md`
- `results/raw_exact_xag_mc.csv`
- `results/summary_exact_xag_mc.csv`
- `results/analysis_exact_xag_mc.md`
- `results/raw_highdim_root_action_oracle.csv`
- `results/summary_highdim_root_action_oracle.csv`
- `results/analysis_highdim_root_action_oracle.md`
- `results/analysis_highdim_root_action_teacher.md`
- `results/analysis_highdim_guard_upgrade.md`
- `results/analysis_toolchain_readiness.md`
- `results/raw_ros_lut_proxy_sweep.csv`
- `results/raw_ros_lut_proxy_best.csv`
- `results/summary_ros_lut_proxy.csv`
- `results/analysis_ros_lut_proxy.md`
- `results/manifest_ros_lut_proxy.json`

### 3.3 论文文件

- `paper_latex/main.tex`
- `paper_latex/main.pdf`
- `paper_latex/tables/esop_baseline_by_n.tex`
- `paper_latex/tables/neural_prior_ablation.tex`
- `paper_latex/tables/search_contribution_decomposition.tex`
- `paper_latex/tables/weight_robustness_compact.tex`
- `paper_latex/tables/neural_prior_highdim_ablation.tex`
- `paper_latex/tables/exact_fprm_dp.tex`
- `paper_latex/tables/exact_xag_mc.tex`
- `paper_latex/tables/highdim_root_action_oracle.tex`
- `paper_latex/tables/resource_search_ablation_highdim.tex`
- `paper_latex/tables/runtime_search_ablation_highdim.tex`
- `paper_latex/tables/external_traditional_resource_n6.tex`
- `paper_latex/tables/resource_mega_highdim_resource.tex`
- `paper_latex/tables/runtime_mega_highdim_resource.tex`
- `paper_latex/tables/resource_giga_highdim_resource.tex`
- `paper_latex/tables/runtime_giga_highdim_resource.tex`
- `paper_latex/tables/ros_lut_proxy.tex`
- `paper_latex_zh/resource_nmcts_zh_report.tex`
- `paper_latex_zh/resource_nmcts_zh_report.pdf`
- `paper_latex_zh/resource_nmcts_zh_robustness.tex`
- `paper_latex_zh/resource_nmcts_zh_robustness.pdf`
- `paper_latex_zh/resource_nmcts_zh_boolean_ring_v3.tex`
- `paper_latex_zh/resource_nmcts_zh_boolean_ring_v3.pdf`
- `paper_latex_zh/resource_nmcts_zh_stage_delivery.tex`
- `paper_latex_zh/resource_nmcts_zh_stage_delivery.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v18.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v18.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v19.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v19.pdf`

## 4. 复现命令

环境使用：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python <script>.py
```

基础验证：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python tests_smoke.py
```

重新生成 ESOP 分析：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src
/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/analyze_esop_baseline.py
```

重新生成 exact FPRM-DP 精确切片：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_exact_fprm_dp.py --max-n 4
```

重新生成 exact XAG 乘法复杂度下界：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_exact_xag_mc.py --max-n 4
```

重新生成多资源权重鲁棒性分析和中文 PDF：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_weight_robustness.py
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment/paper_latex_zh
latexmk -xelatex -g resource_nmcts_zh_robustness.tex
```

重新生成外部工具链 readiness 审计：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_toolchain_readiness.py
```

重新生成 ROS-style LUT proxy：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_ros_lut_proxy.py --manifest traditional=benchmark_exports/traditional_resource_external_seed42/manifest.json --manifest n14=benchmark_exports/highdim_resource_external_seed42/manifest.json --manifest n15=benchmark_exports/highdim_scale_resource_external_seed42/manifest.json --manifest n16=benchmark_exports/ultra_highdim_resource_external_seed42/manifest.json --manifest n18=benchmark_exports/mega_highdim_resource_external_seed42/manifest.json --internal traditional=results/raw_traditional_resource.csv --internal n14=results/raw_highdim_resource.csv --internal n15=results/raw_highdim_scale_resource.csv --internal n16=results/raw_ultra_highdim_resource.csv --internal n18=results/raw_mega_highdim_resource.csv --ks 3,4,5 --workers 8 --timeout 45 --raw-out results/raw_ros_lut_proxy_sweep.csv --best-out results/raw_ros_lut_proxy_best.csv --summary results/summary_ros_lut_proxy.csv --analysis results/analysis_ros_lut_proxy.md --latex-out paper_latex/tables/ros_lut_proxy.tex --run-manifest results/manifest_ros_lut_proxy.json
```

重新生成搜索贡献分解：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset search_ablation_traditional --model models/action_scorer_rollout_logical_and.pt --workers 10 --checkpoint-every 100 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset search_ablation_traditional
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset search_ablation_highdim --model models/action_scorer_rollout_logical_and.pt --workers 6 --checkpoint-every 16 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset search_ablation_highdim
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_search_contribution.py
```

重新生成 n=32/36/40 extended screen-scale：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --ns 32,36,40 --per-n 48 --workers 6 --tag extended
```

重新生成 depth-3/4 quality-frontier screen-scale：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --ns 20,28,40 --per-n 24 --workers 6 --max-screen-depth 4 --tag depth_frontier
```

重新生成高维 learned-prior 诊断：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset linear_highdim --gate-mode logical_and --label-mode immediate --action-family linear --max-depth 1 --child-branch 1 --out models/linear_action_scorer_highdim.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_neural_prior --model models/linear_action_scorer_highdim.pt --out-dir /tmp/resource_nmcts_highdim_learned_prior --workers 6 --checkpoint-every 6 --isolate-timeouts
cp /tmp/resource_nmcts_highdim_learned_prior/raw_highdim_neural_prior.csv results/raw_highdim_neural_prior_learned_prior.csv
cp /tmp/resource_nmcts_highdim_learned_prior/summary_highdim_neural_prior.csv results/summary_highdim_neural_prior_learned_prior.csv
cp /tmp/resource_nmcts_highdim_learned_prior/manifest_highdim_neural_prior.json results/manifest_highdim_neural_prior_learned_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_neural_prior --model /tmp/nonexistent_model.pt --out-dir /tmp/resource_nmcts_highdim_no_prior --workers 6 --checkpoint-every 6 --isolate-timeouts
cp /tmp/resource_nmcts_highdim_no_prior/raw_highdim_neural_prior.csv results/raw_highdim_neural_prior_no_prior.csv
cp /tmp/resource_nmcts_highdim_no_prior/summary_highdim_neural_prior.csv results/summary_highdim_neural_prior_no_prior.csv
cp /tmp/resource_nmcts_highdim_no_prior/manifest_highdim_neural_prior.json results/manifest_highdim_neural_prior_no_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_neural_prior_ablation.py --learned-csv results/raw_highdim_neural_prior_learned_prior.csv --no-prior-csv results/raw_highdim_neural_prior_no_prior.csv --methods and_resource_nmcts --out-raw results/raw_neural_prior_highdim_ablation.csv --summary results/summary_neural_prior_highdim_ablation.csv --out results/analysis_neural_prior_highdim_ablation.md --latex-out paper_latex/tables/neural_prior_highdim_ablation.tex --dataset-label highdim_neural_prior --model-label models/linear_action_scorer_highdim.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_highdim_root_action_oracle.py
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset linear_root_teacher --seed 31415 --gate-mode logical_and --label-mode root_teacher --action-family linear --max-depth 0 --child-branch 1 --root-teacher-width 24 --rest-direct-limit 450 --hidden 128 --out models/linear_action_scorer_root_teacher.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_highdim_root_action_oracle.py --model models/linear_action_scorer_root_teacher.pt --raw results/raw_highdim_root_action_teacher.csv --summary results/summary_highdim_root_action_teacher.csv --analysis results/analysis_highdim_root_action_teacher.md --latex-out paper_latex/tables/highdim_root_action_teacher.tex
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_guard_upgrade --model /tmp/nonexistent_model.pt --workers 6 --checkpoint-every 6 --isolate-timeouts
```

重新生成 n=18 内部分析：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset mega_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset mega_highdim_resource
```

重新生成 n=18 外部分析：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py \
  --external-csv results/raw_external_mega_highdim_resource.csv \
  --internal-csv results/raw_mega_highdim_resource.csv \
  --targets and_resource_nmcts,and_profile_resource_nmcts,and_pareto_resource_nmcts,and_fprm_linear_pair_fast,and_fprm_root_beam,direct_anf,and_direct_anf \
  --out results/analysis_external_mega_highdim_resource.md
```

编译论文：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment/paper_latex
latexmk -pdf -g main.tex
```

## 5. 当前验证状态

已完成验证：

- `latexmk -pdf -g main.tex` 通过。
- `latexmk -xelatex -g resource_nmcts_zh_manuscript_v19.tex` 通过；生成 13 页中文 PDF。
- `tests_smoke.py` 通过，输出 `smoke ok`。
- `py_compile` 通过。
- `git diff --check` 通过。
- `raw_mega_highdim_resource.csv` 审计：84 行、0 error、0 skipped、0 incorrect。
- `raw_giga_highdim_resource.csv` 审计：48 行、36 usable、12 timeout error、0 skipped；timeout 均来自 `and_fprm_root_beam` 和 `and_fprm_linear_pair_fast`。
- `analysis_search_contribution.md` 审计：无 NaN/空配对。
- `raw_search_ablation_highdim.csv` 审计：128 行、0 error、0 skipped、0 incorrect。
- `raw_neural_prior_highdim_ablation.csv` 审计：24 行、0 error、0 skipped、0 incorrect。
- `raw_exact_fprm_dp.csv` 审计：72 行、0 error、0 skipped、0 incorrect。
- `raw_exact_xag_mc.csv` 审计：72 行、72 solved、0 unknown/error。
- `raw_highdim_root_action_oracle.csv` 审计：62 行、0 error、0 incorrect。
- `raw_highdim_root_action_teacher.csv` 审计：62 行、0 error、0 incorrect。
- `raw_highdim_guard_upgrade.csv` 审计：24 行、0 error、0 skipped、0 incorrect。
- `analysis_toolchain_readiness.md` 审计：ABC 可用；mockturtle 和 RevKit 在当前环境缺失。
- `raw_screen_scale_extended_terms.csv` 审计：1008 行、1008/1008 plan 符号验证通过、1008/1008 emitted-circuit 符号验证通过、0 mismatch。
- `raw_screen_scale_depth_frontier_terms.csv` 审计：648 行、648/648 plan 符号验证通过、648/648 emitted-circuit 符号验证通过、0 mismatch。
- `raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv` 审计：960 行、960/960 plan 符号验证通过、960/960 emitted-circuit 符号验证通过、0 mismatch。
- `raw_truth_bridge_n23_large_frontier_terms.csv` 审计：60 行、60/60 完整 truth-table oracle 验证通过、60/60 plan 符号验证通过、60/60 emitted-circuit 符号验证通过、0 mismatch。
- `raw_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv` 审计：960 行、960/960 plan 符号验证通过、960/960 emitted-circuit 符号验证通过、0 mismatch。
- `raw_truth_bridge_n23_cost_time003_frontier_terms.csv` 审计：60 行、60/60 完整 truth-table oracle 验证通过、60/60 plan 符号验证通过、60/60 emitted-circuit 符号验证通过、0 mismatch。

Git 状态：

- 最新提交：以本轮最终回复中的 Git commit 为准。
- 远端：`origin/main` 已同步。
- 注意：仓库根目录外层曾出现未跟踪压缩包 `resource_nmcts_experiment.zip`，不属于本次代码交付。

## 6. 论文当前可写主张

推荐主张：

1. 本文提出一种面向资源约束的量子布尔函数 oracle 综合方法，将问题表示为 ANF/FPRM 项集合上的搜索。
2. 方法不依赖 SSHR 的 parallelotope 结构，可以把 SSHR 作为外部 baseline。
3. 在 `n<=6` 传统 baseline 切片上，Pareto-Resource-NMCTS 对 ESOP cube beam、ESOP-MILP 和 ABC-ESOP 均有明显 score 优势。
4. 在 `n=18` 高维随机 ANF stress test 上，fast linear-pair guard 与 Resource/Profile/Pareto 可稳定改善 root-beam，说明高维 guard 不再只是保底策略。
5. 外部 ABC/BDD 结果支持低加权资源和低 ancilla 优势，但 depth 仍是 ABC-AIG/ABC-XAG 的优势指标。
6. 贡献分解显示：仿射坐标搜索是最大前置收益，神经 refine 和 final guard 提供无 score loss 的小幅增益，Pareto archive 在小规模传统切片上贡献明确，高维主要由 bounded linear-pair guard 支撑。
7. `n<=4` exact FPRM-DP 精确切片显示：Resource/Pareto portfolio 可以在受限 FPRM exact 模型之外继续降低 score；Exact FPRM-DP 本身也优于 ESOP-MILP 和 exact SSHR-I 的加权 score。
8. `n<=4` exact XAG 乘法复杂度切片显示：Resource/Pareto 在 12/72 个函数上达到全局 T 下界，平均 T gap 为 +53.01%，明显低于 ESOP-MILP 的 +120.14% 和 SSHR-I-T 的 +143.06%。
9. 高维 root-action teacher 诊断显示：oracle top-24 相对启发式 top-4 有 3/0/7、-0.18% 的小幅 headroom；pairwise-wide root-action ranker 进一步在 n=16 full synthesis 中相对 deterministic recursive guard 获得 10/0/14、-0.18%，因此高维 AI 贡献已从负向诊断推进到小幅正向证据。
10. Boolean-ring linear factor 将 quotient 与 linear factor 的变量不相交限制放宽到 Boolean 环 `x_i^2=x_i` 展开；在 n=16 上，Boolean-guard Resource-NMCTS 相对 pairwise-wide Resource-NMCTS 获得 14/0/10、平均 score 降低 0.34%，相对 deterministic recursive guard 获得 18/0/6、平均 score 降低 0.52%。这是当前高维结构搜索中比 pairwise-wide 更明显的正向提升。
11. 外部工具链 readiness 审计显示：ABC 已可用并支撑当前 AIG/XAG/LUT/ESOP baseline；mockturtle/RevKit 当前缺失，因此不能声称已完成这类 reversible-toolchain 复现。
12. ROS-style LUT proxy 显示：在 309 个 `n=3..6,14,15,16,18` 函数上，ABC `K=3,4,5` LUT sweep 的 927/927 行均通过 truth-table 检查；best-K proxy 相对固定 K=4 为 219/0/90、平均 score -18.12%，而 Resource-NMCTS 相对该更强 proxy 仍为 309/0/0、平均 score -83.77%。
13. `n=20` giga stress 已从纯边界失败推进为边界改善：root-beam 与 fast linear-pair 仍全部 timeout，但 depth-2 recursive Boolean screen 让 Resource-NMCTS 相对旧 Resource-NMCTS 获得 5/0/1、平均 score -7.47%；相对 AND-direct ANF 获得 5/0/1、平均 score -11.80%；相对 direct ANF 获得 5/1/0、平均 score -38.86%。
14. `n=32,36,40` extended screen-scale 显示：depth policy 相对 single screen 获得 110/0/34、平均 score -5.55%；相对 all-depth adaptive 在 144 个项集上全部 score 持平，并节省 33.14% 平均运行时间；1008/1008 个方法行通过 plan 和 emitted-circuit 两层 ANF 符号验证。
15. `n=20,28,40` depth-frontier 显示：depth-3 Boolean-ring screen 相对 fixed depth-2 为 49/0/23、平均 score -1.93%；depth-4 相对 fixed depth-2 为 49/0/23、平均 score -3.10%；648/648 个方法行通过 plan 和 emitted-circuit 两层 ANF 符号验证。这是新的高预算质量前沿证据，但运行时间显著增加。
16. Depth-frontier policy 已把高预算质量前沿学习化：在 `n=20,28,40` scale harness 中，相对 fixed depth-2 获得 35/0/37、平均 score -2.19%；相对 all-depth depth<=4 平均 score +0.97%，但节省 58.69% 时间；720/720 个方法行通过 plan 和 emitted-circuit 两层 ANF 符号验证。
17. Large frontier policy 进一步压缩质量 gap：held-out 相对 oracle frontier 从旧模型 +0.80% 降到 +0.04%；独立 seed `n=24,28,32,40` 相对旧 policy 为 17/0/79、平均 score -0.49%，相对 all-depth 仅 +0.10% 且节省 53.50% 时间；代价是比旧 policy 更慢。
18. Cost-aware frontier policy 给出更符合“资源约束”的快速质量模式：独立 seed `n=24,28,32,40` 相对 fixed depth-2 仍为 56/0/40、平均 score -1.39%，但相对 depth-2 的 plan time 增幅为 +170.03%，显著低于 large policy 的 +563.80%；在 n=23 bridge 上相对 large policy 节省 56.29% plan time 和 12.62% lifetime area，代价是 score +0.92%。
19. `n=21,22,23` 完整 truth-table bridge 加 large-policy 与 cost-aware `n=23` rerun 显示：300/300 个方法行同时通过完整 truth-table oracle 验证、ANF plan 符号验证和 emitted-circuit ANF 符号验证；该结果把完整验证边界从 n<=20 主实验推进到 n>20 的桥接切片。

不应写的主张：

1. 不应写“CNOT 全面优于 SSHR/ESOP/ABC”。
2. 不应写“硬件映射后仍然更优”，因为当前没有 mapping。
3. 不应写“Pareto 在 n=18 有额外独立收益”，因为 n=18 的 Pareto 当前故意收窄为稳定 guard。
4. 不应直接拿 SSHR 论文表格里的 ESOP 总量横比，除非函数集和成本模型一致。
5. 不应把 Exact FPRM-DP 写成全局可逆线路最优；它只是在 bounded fixed-polarity FPRM factor model 内 exact。
6. 不应把 Exact XAG 乘法复杂度写成 CNOT/depth/ancilla 最优；它只给出 logical-AND T-count 的全局下界。
7. 不应把 n=20 giga stress 写成深层神经/FPRM 搜索的新突破；当前正向增益来自 ANF-only recursive Boolean-ring screen，root-beam/fast linear-pair 仍在 300 s 预算下失效。
8. 不应把 Boolean-linear screen 泛化成所有高维上的高质量方法；recursive screen 在 n=20 是有效的可扩展修复，在 n=18 也优于单层 screen，但 n=18 结果仍显示 deep Resource 分支明显更强，因此 screen 应写成超高维边界候选。

## 7. 下一步建议

当前已经完成第一版“搜索贡献分解”，并新增了 `search_ablation_traditional`、`search_ablation_highdim`、`highdim_neural_prior`、`highdim_root_action_oracle`、`exact_fprm_dp`、`exact_xag_mc`、`highdim_root_action_teacher` 和 `highdim_guard_upgrade` 等 dedicated ablation/diagnostic。投稿前仍建议继续补强：

1. 高维 neural guidance 仍需继续改进；当前 pairwise-wide 版本已经把 n=16 full synthesis 推进到 10/0/14、-0.18%，但真正更明显的新收益来自 Boolean-ring linear factor。下一步应把 neural ranker 从“排序旧 pair action”升级为“选择 Boolean-ring factor / recursive depth / polarity 的策略网络”，否则 AI 贡献仍弱于手工结构扩展。
2. 小规模 exact/exhaustive oracle slice 已完成 bounded FPRM-DP 和 exact XAG 乘法复杂度版本；如果继续加强，可以再补一个更接近全局 reversible circuit 的 exact/SMT/SAT 小规模证书。
3. 继续补官方 ROS/mockturtle/RevKit 或其他外部 reversible-toolchain 对比，减少“proxy 式 ABC/BDD/LUT baseline”的审稿风险；当前已有 ROS-style LUT proxy，但 readiness 审计显示 mockturtle/RevKit 尚未安装。

已完成/待补强状态：

| 设置 | 函数集 | 当前证据 | 状态 |
|---|---|---|---|
| no neural prior | n<=6 traditional | Resource-NMCTS score 39/0/138，-1.10% | 已有 |
| affine/neural/guard 分解 | 322-function ablation | neural refine 65/0/257，guard 88/0/234 | 已有 |
| heuristic-only / no-MCTS | n<=6 traditional | Resource vs no-MCTS 54/0/123，-1.44%；Pareto vs no-MCTS 106/0/71，-4.69% | 已有 |
| highdim no-MCTS guard | n=14 random ANF | no-MCTS vs root-beam 14/0/2，-6.25%；no-MCTS vs linear-pair 14/0/2，-3.08% | 已有 |
| Pareto archive | n<=6 traditional | Pareto vs Resource 68/0/109，-3.26% | 已有 |
| highdim guard | n=14/15/16/18 | linear-pair guard 相对 root-beam 均无 score loss | 已有 |
| highdim no-neural-prior | 12 个 n=14 random ANF | pairwise-wide learned prior 2/0/10，-0.05%，运行时间 +179.59% | 已有但仍弱 |
| highdim root-action teacher | n=14/n=16 random ANF | n=14 heuristic top-4 + neural top-8 为 2/0/8，-0.14%；n=16 为 5/0/18，-0.06% | 已有小幅正向诊断 |
| n=16 pairwise-wide full synthesis | 24 个 n=16 random ANF | vs deterministic recursive guard 为 10/0/14，-0.18%；vs old Resource 为 10/0/14，-0.12% | 新增正向 AI 证据，但运行时间更高 |
| n=16 Boolean-ring full synthesis | 24 个 n=16 random ANF | Boolean-guard vs pairwise-wide Resource 为 14/0/10，-0.34%；vs deterministic recursive guard 为 18/0/6，-0.52% | 当前最强高维结构改进 |
| n=18 Boolean-linear screen | 12 个 n=18 random ANF | vs old Resource 为 0/12/0，+42.45%，但运行时间 -98.48% | 负向质量诊断，只能说明快速边界可跑 |
| n=18 adaptive depth-2 Boolean screen | 12 个 n=18 random ANF | vs single screen 为 11/0/1，-6.47%；Resource vs adaptive screen 为 11/0/1，-23.85% | 改善 screen 但不能替代深搜索 |
| n=20 depth-2 recursive Boolean screen | 6 个 n=20 random ANF | Resource vs old Resource 为 5/0/1，-7.47%；vs AND-direct 为 5/0/1，-11.80%；vs depth-1 Resource 为 5/0/1，-3.13% | 当前最明确的超高维边界改善 |
| n=32/36/40 extended screen-scale | 144 个高维 ANF 项集 | depth policy vs single 为 110/0/34，-5.55%；vs all-depth adaptive 为 0/0/144，省时 -33.14%；1008/1008 emitted-circuit 符号验证通过 | 新增大规模泛化证据 |
| n=20/28/40 depth-frontier | 72 个高维 ANF 项集 | depth-3 vs depth-2 为 49/0/23，-1.93%；depth-4 vs depth-2 为 49/0/23，-3.10%；648/648 emitted-circuit 符号验证通过 | 新增高预算质量前沿 |
| depth-frontier policy | 32 个 held-out + 72 个 scale 项集 | held-out vs oracle frontier 为 +0.80% score、-58.76% time；scale vs depth-2 为 35/0/37、-2.19%；720/720 emitted-circuit 符号验证通过 | 新增结构级 AI 质量-时间折中 |
| large frontier policy | 48 个 held-out + 96 个独立泛化项集 + 6 个 n=23 bridge 函数 | held-out vs oracle frontier 为 +0.04% score、-51.30% time；独立泛化 vs 旧 policy 为 17/0/79、-0.49%；n=23 bridge vs 旧 policy 为 1/0/5、-0.48% score、-0.45% T-depth proxy | 新增质量增强型结构 AI 证据 |
| cost-aware frontier policy | 48 个 held-out + 96 个独立泛化项集 + 6 个 n=23 bridge 函数 | scale vs depth-2 为 56/0/40、score -1.39%、time +170.03%；n=23 vs large 为 score +0.92%、time -56.29%、lifetime -12.62% | 新增快速质量折中模式 |
| n=21/22/23 truth-table bridge | 18 个生成式 ANF 函数 + 12 个 n=23 rerun 函数 | 300/300 完整 truth-table oracle 验证通过，300/300 plan 与 emitted-circuit 符号验证通过，0 mismatch；large/cost 两种 n=23 rerun 均完整验证 | 新增 n>20 完整验证桥接 |
| schedule proxy | 96 个 n=24/28/32/40 项集 + 30 个 n=21/22/23 bridge/rerun 函数 | frontier policy vs depth-2：项集 T-depth proxy 40/0/56、-1.85%，large n=23 vs old policy 为 1/0/5、-0.45% T-depth proxy；cost n=23 vs large 为 time -56.29%、lifetime -12.62% | 新增逻辑层后端相关指标，非硬件 mapping |
| ROS-style LUT proxy | 309 个 n=3..6/14/15/16/18 函数 | 927/927 K-sweep truth-table 检查通过；best-K vs fixed K=4 为 219/0/90、-18.12%；Resource vs proxy 为 309/0/0、-83.77% | 新增更强 LUT proxy，但不是官方 ROS 复现 |
| highdim wide-fast guard | 12 个 n=14 random ANF | wide vs Resource 为 0/0/12，运行时间 +59.80% | 已有但属负向诊断 |
| exact FPRM-DP | n<=4 traditional | Resource vs exact FPRM-DP 51/3/18，-12.18%；Pareto vs exact FPRM-DP 51/0/21，-12.20% | 已有但模型受限 |
| exact XAG MC | n<=4 traditional | Resource/Pareto 达到 T 下界 12/72，平均 T gap +53.01%；ESOP 为 +120.14%，SSHR-I-T 为 +143.06% | 已有全局 T 下界 |
| toolchain readiness | 当前工作站 | ABC 可用；mockturtle/RevKit 缺失 | 已有环境审计，仍需安装后复现 |

## 8. 当前结论

当前版本已经具备一条比 SSHR 路线更适合投稿的主线：

“基于资源感知搜索、神经先验和 MCTS/Pareto 候选选择的量子布尔函数 oracle 综合方法，在同 benchmark 的 ESOP、ABC、BDD 和 direct ANF baseline 上展示显著低 T-count 与低加权资源优势。”

但是投稿前还需要继续补强“AI 搜索本身带来的贡献”这一点。否则文章容易被评价为一组 FPRM/ESOP 工程启发的组合，而不是强化学习与 MCTS 方法论文。

本轮新增贡献分解、`search_ablation_traditional`、`search_ablation_highdim`、`highdim_neural_prior`、`highdim_root_action_oracle`、`exact_fprm_dp`、`exact_xag_mc`、pairwise-wide n=16 full synthesis、Boolean-ring linear factor、schedule proxy、n=23 完整 truth-table bridge、ROS-style LUT proxy、large frontier policy 和 cost-aware frontier policy 后，这个风险已经下降：现在能证明 neural refine、learned prior、final guard、no-MCTS portfolio、Resource-NMCTS、Pareto archive、高维 guard/no-MCTS 组合、小规模 exact bounded FPRM 对照、全局 XAG T 下界对照、高维 pairwise-wide root-action ranker、Boolean-ring factor 扩展、emitted-circuit 层 T-depth/辅助生命周期 trade-off、n=21/22/23 加 large/cost n=23 rerun 共 300/300 方法行的完整 oracle 验证、large frontier policy 相对旧 policy 的质量提升、cost-aware frontier policy 的快速质量折中，以及相对更强 LUT proxy 的 309/0/0 score 优势。不过官方 ROS/RevKit/mockturtle 复现和真实后端 mapping 仍然缺失，所以目标还不能判定完成。
