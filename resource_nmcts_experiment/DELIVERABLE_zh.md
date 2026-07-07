# Resource-NMCTS 中文交付文档

更新时间：2026-07-07
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
| fast linear-pair guard vs root beam, n=18 | `mega_highdim_resource` | 6/0/6 | -1.91% | n=18 是可验证的压力边界证据 |
| Resource-NMCTS vs fast linear-pair, n=18 | `mega_highdim_resource` | 12/0/0 | -3.55% | n=18 Resource guard 对 fast child 仍有进一步选择收益 |

这个结果把论文主张进一步收窄为：仿射坐标搜索、神经 refine、guard/Pareto archive 和高维 linear-pair guard 共同构成方法贡献；其中高维大规模证据不能夸大为完整 Pareto archive 的强独立优势，因为部分高维设置中 Resource/Profile/Pareto 会退化或收窄到稳定 guard。最新 `n=16` pairwise-wide rerun 后，`Resource-NMCTS` 在 full synthesis 层面相对 deterministic recursive guard 获得 10/0/14、平均 score 降低 0.18%；相对旧 root-teacher Resource 获得 10/0/14、平均 score 降低 0.12%。因此该切片现在应写成“recursive guard + pairwise-wide baseline-preserving AI guard 小幅正向增益”的证据，而不是独立 Pareto archive 证据。

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

### 3.2 结果文件

- `results/raw_traditional_resource.csv`
- `results/raw_external_traditional_resource_n6.csv`
- `results/analysis_esop_baseline.md`
- `results/summary_esop_baseline.csv`
- `results/raw_mega_highdim_resource.csv`
- `results/analysis_mega_highdim_resource.md`
- `results/runtime_mega_highdim_resource.md`
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
- `paper_latex_zh/resource_nmcts_zh_report.tex`
- `paper_latex_zh/resource_nmcts_zh_report.pdf`
- `paper_latex_zh/resource_nmcts_zh_robustness.tex`
- `paper_latex_zh/resource_nmcts_zh_robustness.pdf`

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

重新生成搜索贡献分解：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset search_ablation_traditional --model models/action_scorer_rollout_logical_and.pt --workers 10 --checkpoint-every 100 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset search_ablation_traditional
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset search_ablation_highdim --model models/action_scorer_rollout_logical_and.pt --workers 6 --checkpoint-every 16 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset search_ablation_highdim
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_search_contribution.py
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
- `tests_smoke.py` 通过，输出 `smoke ok`。
- `py_compile` 通过。
- `git diff --check` 通过。
- `raw_mega_highdim_resource.csv` 审计：84 行、0 error、0 skipped、0 incorrect。
- `analysis_search_contribution.md` 审计：无 NaN/空配对。
- `raw_search_ablation_highdim.csv` 审计：128 行、0 error、0 skipped、0 incorrect。
- `raw_neural_prior_highdim_ablation.csv` 审计：24 行、0 error、0 skipped、0 incorrect。
- `raw_exact_fprm_dp.csv` 审计：72 行、0 error、0 skipped、0 incorrect。
- `raw_exact_xag_mc.csv` 审计：72 行、72 solved、0 unknown/error。
- `raw_highdim_root_action_oracle.csv` 审计：62 行、0 error、0 incorrect。
- `raw_highdim_root_action_teacher.csv` 审计：62 行、0 error、0 incorrect。
- `raw_highdim_guard_upgrade.csv` 审计：24 行、0 error、0 skipped、0 incorrect。
- `analysis_toolchain_readiness.md` 审计：ABC 可用；mockturtle 和 RevKit 在当前环境缺失。

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
10. 外部工具链 readiness 审计显示：ABC 已可用并支撑当前 AIG/XAG/LUT/ESOP baseline；mockturtle/RevKit 当前缺失，因此不能声称已完成这类 reversible-toolchain 复现。

不应写的主张：

1. 不应写“CNOT 全面优于 SSHR/ESOP/ABC”。
2. 不应写“硬件映射后仍然更优”，因为当前没有 mapping。
3. 不应写“Pareto 在 n=18 有额外独立收益”，因为 n=18 的 Pareto 当前故意收窄为稳定 guard。
4. 不应直接拿 SSHR 论文表格里的 ESOP 总量横比，除非函数集和成本模型一致。
5. 不应把 Exact FPRM-DP 写成全局可逆线路最优；它只是在 bounded fixed-polarity FPRM factor model 内 exact。
6. 不应把 Exact XAG 乘法复杂度写成 CNOT/depth/ancilla 最优；它只给出 logical-AND T-count 的全局下界。

## 7. 下一步建议

当前已经完成第一版“搜索贡献分解”，并新增了 `search_ablation_traditional`、`search_ablation_highdim`、`highdim_neural_prior`、`highdim_root_action_oracle`、`exact_fprm_dp`、`exact_xag_mc`、`highdim_root_action_teacher` 和 `highdim_guard_upgrade` 等 dedicated ablation/diagnostic。投稿前仍建议继续补强：

1. 高维 neural guidance 仍需继续改进；当前 pairwise-wide 版本已经把 n=16 full synthesis 推进到 10/0/14、-0.18%，但幅度仍小，且运行时间显著增加。下一步应继续提高 learned ranker 的效果，而不是只扩大 root action 宽度。
2. 小规模 exact/exhaustive oracle slice 已完成 bounded FPRM-DP 和 exact XAG 乘法复杂度版本；如果继续加强，可以再补一个更接近全局 reversible circuit 的 exact/SMT/SAT 小规模证书。
3. 继续补 ROS/mockturtle 或其他外部 reversible-toolchain 对比，减少“估算式 ABC/BDD baseline”的审稿风险；当前 readiness 审计显示 mockturtle/RevKit 尚未安装。

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
| highdim wide-fast guard | 12 个 n=14 random ANF | wide vs Resource 为 0/0/12，运行时间 +59.80% | 已有但属负向诊断 |
| exact FPRM-DP | n<=4 traditional | Resource vs exact FPRM-DP 51/3/18，-12.18%；Pareto vs exact FPRM-DP 51/0/21，-12.20% | 已有但模型受限 |
| exact XAG MC | n<=4 traditional | Resource/Pareto 达到 T 下界 12/72，平均 T gap +53.01%；ESOP 为 +120.14%，SSHR-I-T 为 +143.06% | 已有全局 T 下界 |
| toolchain readiness | 当前工作站 | ABC 可用；mockturtle/RevKit 缺失 | 已有环境审计，仍需安装后复现 |

## 8. 当前结论

当前版本已经具备一条比 SSHR 路线更适合投稿的主线：

“基于资源感知搜索、神经先验和 MCTS/Pareto 候选选择的量子布尔函数 oracle 综合方法，在同 benchmark 的 ESOP、ABC、BDD 和 direct ANF baseline 上展示显著低 T-count 与低加权资源优势。”

但是投稿前还需要继续补强“AI 搜索本身带来的贡献”这一点。否则文章容易被评价为一组 FPRM/ESOP 工程启发的组合，而不是强化学习与 MCTS 方法论文。

本轮新增贡献分解、`search_ablation_traditional`、`search_ablation_highdim`、`highdim_neural_prior`、`highdim_root_action_oracle`、`exact_fprm_dp`、`exact_xag_mc` 和 pairwise-wide n=16 full synthesis 后，这个风险已经下降：现在能证明 neural refine、learned prior、final guard、no-MCTS portfolio、Resource-NMCTS、Pareto archive、高维 guard/no-MCTS 组合、小规模 exact bounded FPRM 对照、全局 XAG T 下界对照，以及高维 pairwise-wide root-action ranker 都有可测证据。不过高维 neural guidance 的幅度仍然偏小，更强外部 reversible-toolchain 对比也仍然缺失，所以目标还不能判定完成。
