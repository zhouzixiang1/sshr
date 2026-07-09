# 比较对象与意义矩阵

本文档用于回答“本文到底和什么方法比较，以及这些比较为什么有意义”。它不引入
新的实验结果，只把论文、结果表和审计文件中已经验证的比较角色整理成投稿口径。

## 核心判断

本文的比较不是单一 leaderboard，而是分层证据链：

- 主比较层证明：在 matched logical-layer Boolean-oracle synthesis 任务上，本文在
  T-count 和 weighted logical-resource score 上有系统性优势。
- 外部工具链层证明：优势不是只来自和自写弱 baseline 比较，而是在多类逻辑综合、
  LUT/XAG/AIG 和精确 reversible-oracle probe 下仍然可见。
- 反例边界层证明：本文没有隐藏 SSHR、CirKit、RevKit、STG 等方法在 CNOT、depth、
  auxiliary lines 或小规模预计算最优表上的优势。
- AI/MCTS 消融层证明：神经组件和 MCTS 是有边界的 search-control 增益，不是把全部
  资源改进归因于 deep learning alone。

安全的一句话写法：

> 本文在逻辑层 Boolean-oracle synthesis 任务上，与同任务代数基线、SSHR、ABC/BDD、
> ROS-style LUT、mockturtle、Caterpillar、CirKit、RevKit 和搜索控制消融进行分层比较；
> 结果支持 T-count 与 weighted logical-resource score 的显著改进，同时明确排除
> hardware mapping、routing、native scheduling、universal CNOT/depth/ancilla dominance
> 和 full ROS reproduction。

## 比较矩阵

| 比较层 | 代表对象 | 为什么有意义 | 可以支撑的结论 | 不能支撑的结论 | 主要证据入口 |
|---|---|---|---|---|---|
| 同任务主基线 | Direct ANF, AND-direct ANF, ESOP beam/MILP, BDD/ABC | 解决同一个 bit-flip Boolean-oracle task，资源模型一致或可直接导出比较 | 本文不是只优化直接 ANF；在 T-count 和 weighted score 上优于常见代数/逻辑网络基线 | 不能证明硬件映射最优、所有 raw resource 全胜或全局最优 | `analysis_comparison_answer_scorecard.md`, `analysis_paired_statistical_evidence.md` |
| SSHR 小函数对照 | SSHR-H, SSHR-I | SSHR 是 CNOT-oriented small-scale Boolean synthesis 的接近相关工作，适合作为几何/并行otope路线的 counterpoint | 本文不是 SSHR 变体；在 T-count 和 weighted score 上通常更强 | 不能说 CNOT 全面优于 SSHR；SSHR 仍是 CNOT 强反例 | `analysis_sshr_reproduction_scope_audit.md`, `external_traditional_resource_n6.tex` |
| 外部逻辑工具链 | ROS-style LUT, mockturtle, Caterpillar API, CirKit, ABC/BDD | 检验成熟 LUT/XAG/AIG/MC 工具是否已经消除本文优势 | 本文优势不只存在于内部 baseline；多工具链 logical probes 下仍可见 | 不是 full ROS SAT garbage management，不是硬件 routing 或 native-gate mapping | `analysis_ros_reproduction_gap_audit.md`, `analysis_comparison_target_validity_audit.md` |
| 精确可逆综合对照 | RevKit CLI exact-oracle portfolio | 直接生成 exact reversible oracle，是比逻辑网络 proxy 更接近可逆综合的外部 probe | 本文在 T/score 上没有被 exact reversible portfolio 抹掉 | 不能 claim lower auxiliary lines、routed depth 或最终 mapped Clifford+T dominance | `analysis_comparison_answer_scorecard.md`, `revkit_oracle_synth_traditional.tex` |
| phase/Rz 扩展分支 | RevKit oracle_synth, FPRM/affine phase proxies, learned shortlist | 检验搜索框架是否可迁移到 verified logical phase/Rz proxy objective | 可以作为 phase/Rz logical proxy 和 learned pruning 的补充证据 | 不是最终 approximate-rotation sequence，也不是 full Clifford+T T-count 结论 | `analysis_phase_rotation_precision_audit.md`, `analysis_neural_mcts_claim_calibration.md` |
| 小规模最优反例 | Published STG n=4/5 representatives | 公开小函数最优库是最强边界测试，能防止论文过度宣称 | 本文在 direct baseline slice 上有改善，但承认 precomputed optimum 仍强 | 不能说超过 STG T-count/T-depth/qubit optimum | `analysis_stg_published_benchmark.md` |
| AI/MCTS 因果消融 | no-MCTS, beam, Pareto archive, learned/random prior, frontier random-depth | 分离代数动作空间、搜索策略、神经排序和预算分配各自作用 | 神经/MCTS 对 ranking、pruning、budget allocation 有 bounded 增益 | 不能说 deep RL alone 解释全部资源下降，不能说神经网络保证 correctness | `analysis_search_control_baseline_audit.md`, `analysis_learned_control_audit.md` |
| 多资源反例边界 | SSHR CNOT, CirKit depth, RevKit auxiliary lines, Caterpillar CNOT-only | 直接暴露 weighted-score 胜利之外的 raw-resource tradeoff | 本文是强 T/score 点，且 tradeoff 公开透明 | 不能写成 CNOT、depth、ancilla、line count 全面支配 | `analysis_multimetric_pareto_tradeoff.md`, `analysis_schedule_proxy_audit.md` |
| 大规模验证边界 | n=20--64 symbolic stress, n=21--30 truth-table bridge | 回应“是否只做小规模”的审稿风险，并说明高维可验证范围 | 支撑 logical-layer scaling、symbolic verification 和 bounded truth-table bridge | 不能声称所有高维函数 exhaustive truth-table benchmarking 或 global optimality | `analysis_scaling_resource_audit.md`, `analysis_screen_scale_ultra_scale64_stress.md` |

## 投稿时应采用的比较逻辑

1. 先讲主任务：本文做的是 logical-layer bit-flip Boolean oracle synthesis。
2. 再讲主基线：Direct ANF、ESOP、BDD/ABC 和 SSHR 覆盖同任务或最接近任务。
3. 再讲外部 probe：ROS-style LUT、mockturtle、Caterpillar、CirKit、RevKit 说明优势不是
   内部弱 baseline 造成的。
4. 主动讲反例：SSHR/CirKit/RevKit/STG 在部分指标上更强，这正是本文不声称 universal
   dominance 的原因。
5. 最后讲 AI：MCTS、Pareto archive、learned prior、frontier controller 是 bounded
   search-control evidence；正确性仍由 symbolic/truth-table/verifier 保证。

## 禁止扩展的说法

- 不说“全面优于 SSHR”。应说“SSHR 是 CNOT-oriented counterpoint；本文在 T/score 上更强，但不 claim CNOT dominance”。
- 不说“完整复现 ROS”。应说“ROS-style LUT proxy and garbage-pressure audits，full official ROS SAT garbage-management 不在本文 claim 内”。
- 不说“优于硬件编译器”。应说“本文不做 hardware mapping、routing、native scheduling 或 noise-aware compilation”。
- 不说“神经网络保证正确性”。应说“神经组件只负责 ranking/pruning/budget allocation；正确性由 verifier 保证”。
- 不说“所有大规模函数都穷举验证”。应说“高维采用 symbolic verification，truth-table 只用于 bridge slices”。

## 与现有文件的关系

- `COMPARISON_HANDOFF_zh.md`：给作者的比较口径交接单，适合写 cover letter 或回复审稿意见前阅读。
- 本文件：把每个比较对象压缩成“意义、能证明、不能证明、证据入口”的矩阵。
- `reviewer_concern_brief.md`：英文 reviewer-facing 风险和 manuscript anchors。
- `analysis_comparison_answer_scorecard.md`：机器生成的定量 answer scorecard，是本文件的主要证据源之一。
