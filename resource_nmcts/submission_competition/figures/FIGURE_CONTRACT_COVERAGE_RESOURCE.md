# 覆盖、正确性与资源安全图契约

- **核心结论**：冻结的 primary20 core3 计划包含 `20 个函数 × 6 种方法 × 3 个种子 = 360`
  个单元，其中 354 个完成逻辑与映射后精确验证；唯一的 6 个缺口严格局限于
  `AES S-box b0/b7 × SSHR-Beam × seed 7/17/29` 的 300 s 综合超时，未出现错误结果、
  非法耦合或内存保护触发。
- **图形类型**：asymmetric mixed-modality figure；覆盖矩阵是主证据，完整性审计和资源遥测是
  两组支持证据。
- **目标输出**：中文竞赛 PDF 双栏图；Python/matplotlib 独占绘制；SVG/PDF 与 600 dpi PNG。
- **最终尺寸**：183 mm × 110 mm，白底，正文、刻度和图例在最终尺寸不低于 6 pt。
- **面板映射**：
  - **a**：primary20 的 20 个函数 × 6 种方法覆盖矩阵；每格汇总 3 个综合种子，绿色 `3/3`
    表示三种子均精确验证，橙色 `0/3` 表示三种子均在综合阶段超时。
  - **b**：冻结审计链 `360 planned → 354 verified + 6 timeout`；并列报告 354/354 逻辑正确、
    354/354 映射后精确验证、0 truth-table mismatch、0 coupling violation 与 0 unsupported
    instruction。
  - **c**：仅对具有资源遥测的 v3 recovery 记录（n=100；94 verified、6 timeout）绘制总系统
    内存峰值分布，标注中位数、95th percentile、最大值和 70% 内存软阈值；注明 Qiskit Aer
    可用设备为 CPU，RTX 5090 不被表述为 Aer 仿真设备。
- **证据层级**：冻结清单和 formal coverage audit 是覆盖/正确性的主证据；v3 原始 JSONL 是超时和
  资源安全的主证据；旧版 recovered JSONL 只参与来源追溯与哈希核验。
- **统计要求**：本图是确定性审计，不进行显著性检验；报告精确计数、比例和资源分布的经验分位数，
  明确遥测样本定义。
- **源数据**：formal coverage audit、primary20 final manifest 及其声明的原始 JSONL、
  `results/recovered/*.jsonl`、`results/recovery*_v3.jsonl` 和 primary20 执行环境快照；
  脚本导出图专用 CSV/JSON 并记录输入哈希。
- **完整性**：全矢量，SVG 保留 `<text>` 节点；覆盖状态同时以颜色、格内数字和超时标记编码，
  不依赖红绿颜色单独传意。
- **审稿风险**：不得把 6 个超时写成错误结果；不得把 100 条 v3 遥测外推为全部 354 个验证单元；
  不得声称 GPU Aer；70% 是软件软阈值而非硬件物理上限。
- **图注最小信息**：primary20 样本定义、三种子集合 `{7,17,29}`、精确验证定义、300 s 超时、
  v3 遥测 n=100、分位数定义、CPU Aer 与 Source Data 文件名。
