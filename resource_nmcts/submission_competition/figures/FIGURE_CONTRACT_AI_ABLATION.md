# AI 消融图契约

- **核心结论**：在当前匹配 pilot 中，learned prior 未显示稳定、独立的线路资源收益；
  它与 heuristic/uniform 大量打平，只相对 random control 出现少量改善，并增加运行时间。
- **图形类型**：quantitative grid，负结果为主，不把训练损失当作下游性能。
- **目标输出**：中文竞赛 PDF 双栏图；Python/matplotlib 独占绘制；SVG/PDF 与 600 dpi PNG。
- **最终尺寸**：183 mm × 100--115 mm，白底，最终字号不低于 6 pt。
- **面板映射**：
  - **a**：正式 immediate-label 动作评分器的训练事实（数据规模、函数级划分、
    `24→96→96→96→1` 架构、检查点哈希与 RTX 5090 训练设备）；明确 MSE 不是线路收益。
  - **b**：干净 pilot 的 8 个函数×seed 配对单元；learned 对 heuristic、uniform、
    rollout、random 的逻辑 T/CNOT 联合支配 win/tie/loss，并报告 T/CNOT 双侧 Wilcoxon。
  - **c**：`maj7`、`randtt6_s139`、`aes_sbox_b0` hard3 中 immediate/rollout
    相对 heuristic 的逐指标 win/tie/loss，以及中位综合耗时倍率。
  - **d**：冻结的全部 60 个 primary20 Resource-NMCTS 已验证单元的 `selected_method`
    归因审计：54 个明确确定性分支，6 个 `affine_nmcts` 仅标为“可能受 AI 影响”。
- **证据层级**：匹配下游资源是主证据；训练/测试 MSE 只作模型训练质量注释；
  hard cases 是稳健性/反例。
- **统计要求**：明确 pilot 样本数、配对定义、Holm 结论；当前不得标注显著提升。
- **源数据**：五组 clean-pilot JSONL、三组 AI hard-case JSONL、正式训练 manifest、
  冻结的 primary20 Resource-NMCTS JSONL 快照；脚本导出图专用 CSV/JSON 并记录输入哈希。
- **完整性**：全矢量且 SVG 文本可编辑；颜色外再用分组/纹理区分胜平负。
- **审稿风险**：不得把 Resource-NMCTS portfolio 的整体收益归因于 learned prior；
  不得用回归测试损失替代下游线路资源；必须保留退化和运行时间代价。
- **排除项**：160 函数 fitted-Q 离线结果尚未接入当前主综合闭环，只能作为候选下一步，
  不进入本图正式性能证据。
