# 比较对象与投稿口径交接单

本文档面向作者本人使用，用来回答投稿前最容易被追问的两个问题：
“本文到底和什么比？”以及“这些比较是否有意义？”。它不引入新的实验结果，
而是把论文和审计文件中已经验证的比较边界整理成中文口径。

## 一句话定位

本文不是 SSHR 的变体，也不是硬件映射编译器。本文研究的是逻辑层 quantum
Boolean oracle synthesis：把 Boolean function 的 bit-flip oracle 综合写成
ANF/FPRM 和 Boolean-ring action 上的资源约束搜索问题，并用 MCTS、Pareto
archive、神经 action prior、frontier controller 和 baseline-preserving guard
控制搜索。

可以安全使用的核心表述是：

> 本文在逻辑层 Boolean oracle synthesis 任务上，与 Direct ANF、ESOP、
> SSHR、ABC/BDD、ROS-style LUT、mockturtle、Caterpillar API、CirKit、RevKit 等分层基线比较；
> 主张 T-count 和 weighted logical-resource score 的系统性改进，同时明确保留
> CNOT、depth、ancilla、line count 和 hardware mapping 的边界。

## 主比较对象

第一层是同任务、同资源模型的主比较对象：

- Direct ANF 和 AND-direct ANF：检验本文是否只是在替代最直接的代数实现。
- ESOP beam/MILP：检验本文是否优于经典 two-level ESOP/Toffoli 路线。
- BDD/ABC：检验本文是否只赢了自写的弱 baseline。
- SSHR-H/SSHR-I：检验本文是否能对抗 CNOT-oriented small-function synthesis。

这一层最适合支撑主 claim：本文在 matched Boolean functions 上降低 T-count 和
weighted score。不要把这一层写成硬件级全局最优，也不要写成所有单项资源全胜。

## 二级外部探针

第二层是外部工具链或工具链近似探针：

- ROS-style LUT proxy：检验 LUT/resource-constrained oracle synthesis 路线下的
  资源对比，但不是完整官方 ROS SAT garbage-management 复现。
- mockturtle KLUT-to-XAG、Caterpillar API 和 CirKit AIG/MC：检验 XAG/AIG/multiplicative-complexity
  逻辑网络路线是否仍然构成强对照。
- RevKit CLI exact-oracle：检验精确 reversible-oracle synthesis 下的资源差异。
- RevKit phase/Rz branch：用于 phase/Rz lower-bound 或 sensitivity probe，不是最终
  Clifford+T T-count 比较。

这一层的意义是防止论文被看成“只和自己写的 baseline 比”。但是这些结果只能支持
logical-layer robustness，不能支持 full ROS reproduction、hardware mapping 或 routed
depth claim。

## 反例边界

投稿时必须主动承认以下反例边界，因为它们让比较更可信：

- SSHR 仍然是 CNOT-oriented strong counterpoint。本文可以说 score 和 T-count 更好，
  但不能说 CNOT 全面优于 SSHR。
- CirKit AIG/MC 仍然是 depth-oriented strong counterpoint。本文不能 claim depth
  dominance。
- RevKit CLI 经常使用更少 auxiliary lines。本文不能 claim line-count 或 peak-ancilla
  dominance。
- STG published optimum library 是小规模 T-count 最优表的强反例。本文可以说明 direct
  ANF slice 改善，但不能 claim 超过 published optimum。
- Learned prior 的提升是 incremental search-control evidence。本文不能说 deep learning
  alone explains the full improvement。

## AI/MCTS 口径

标题中使用 neural MCTS 是可以的，但必须按论文中的校准口径写：

- MCTS 和 Pareto archive 是 measured search-control increments。
- 神经组件负责 ranking、pruning、budget allocation 或 sparse gating。
- 正确性来自 GF(2)、ANF、emitted-circuit、truth-table 和 phase verifier，不来自神经网络。
- 最大资源提升来自可搜索代数动作空间、guarded selection 和 Pareto selection 的组合，
  不应归因于深度学习单独完成。

## 审稿问答口径

如果审稿人问“只和 SSHR 比有意义吗？”，回答：

> 不是。SSHR 只是 CNOT-oriented small-function counterpoint。主比较层还包括
> Direct ANF、AND-direct ANF、ESOP beam/MILP、BDD/ABC；外部探针还包括 ROS-style
> LUT、mockturtle、Caterpillar API、CirKit 和 RevKit。论文把每类比较绑定到可支持的 claim，并用
> counterpoint audit 明确哪些资源指标没有全胜。

如果审稿人问“为什么不和硬件编译器比？”，回答：

> 本文目标是逻辑层 Boolean oracle synthesis，不做 physical mapping、routing、
> native-gate scheduling、noise model 或 magic-state-factory accounting。因此硬件级
> 编译器不是主 claim 的直接对照；论文只在 logical resource model 下比较 T-count、
> CNOT、depth proxy、ancilla 和 weighted score。

如果审稿人问“ROS 没有完整复现怎么办？”，回答：

> 论文没有 claim full ROS reproduction。ROS-style LUT proxy 用来检验 LUT/resource-aware
> 方向的逻辑层压力，另有 line-aware 和 garbage-pressure proxy 审计；完整 SAT garbage
> management 和官方 ROS flow 明确写在 excluded claim 中。

如果审稿人问“AI 创新是否太弱？”，回答：

> 论文没有 claim deep RL alone。AI 的贡献是 bounded search control：learned prior、
> sparse gate、frontier policy、random-prior/random-depth control 和 phase shortlist
> 分别支撑 ranking、pruning 或 budget-allocation 口径。主贡献是 resource-constrained
> algebraic search workflow。

## 投稿前检查

投稿前按以下文件检查口径是否一致：

- `results/analysis_comparison_answer_scorecard.md`
- `results/analysis_comparison_target_validity_audit.md`
- `results/analysis_comparison_route_decision_audit.md`
- `results/analysis_baseline_claim_matrix.md`
- `results/analysis_comparison_evidence_matrix.md`
- `results/analysis_baseline_comparability_audit.md`
- `results/analysis_counterpoint_claim_boundary.md`
- `results/analysis_neural_mcts_claim_calibration.md`
- `results/analysis_claim_scope_lint.md`
- `submission_package/editor_screening_brief.md`
- `submission_package/reviewer_concern_brief.md`

最终原则：能说“本文在逻辑层、matched Boolean-oracle resource model 下取得强
T-count/weighted-score 改进”；不能说“全面优于所有 oracle synthesis 或 quantum
compiler 方法”。
