# 图 1：端到端系统架构图契约

- **核心结论**：系统把候选综合（含可消融的神经先验）、真实线路 artifact、拓扑约束编译、精确验证与 DuckDB 证据归档串成可复现闭环；神经先验只是被独立审计的候选排序信号，不是系统收益的默认归因。
- **图形类型**：schematic-led composite（流程示意为主，验证与算力边界为辅）。
- **目标输出**：中文竞赛 PDF 双栏宽图；Python/matplotlib 独占绘制；主输出 SVG/PDF，PNG 600 dpi 预览。
- **最终尺寸**：183 mm × 105 mm；白底；正文/标签在最终尺寸不低于 6 pt。
- **面板映射**：
  - **a 主流程**：Boolean 函数与冻结 benchmark → ANF/FPRM/affine/Direct 候选 → heuristic/MCTS/learned-prior 排序 → `SynthesisArtifact` → Qiskit Target + SABRE → 原生门线路。
  - **b 验证与证据闭环**：符号真值、逻辑线路、原生门/耦合、精确 `(x,y)` 与相位/辅助位检查；通过后写入 append-only JSONL/DuckDB，失败保留在审计清单。
  - **c 算力与边界**：RTX 5090 用于模型训练/批推理；Aer 在本机 CPU 上做无噪声精确验证；当前 synthetic Target 不等于真机校准或保真度。
- **证据层级**：主证据是已实现的数据/线路/验证流；验证证据是四级门控和数据库溯源；控制是 learned/heuristic/uniform/random 消融与统一预算。
- **统计要求**：本图不展示效果量或显著性，不放未经冻结统计支持的百分比。
- **源数据**：公共 API、runner、环境 manifest、实验数据库 schema 与验证字段；不使用手绘结果或模拟统计值。
- **图像完整性**：全矢量，SVG 文本保留为 `<text>`；不嵌入位图；颜色同时辅以线型/边框语义。
- **审稿风险**：不得把 portfolio 总收益归因于神经先验；不得暗示 Aer GPU、真实硬件执行、噪声感知或量子反哺 AI 加速已经完成。
