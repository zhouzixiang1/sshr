# XA-202609 术语账本

状态：`locked-v1`（2026-07-22）。本账本是竞赛 PDF、图题、实验表、数据库导出和答辩材料的统一命名依据。除非方法、实验协议或证据边界发生实质变化，不在不同章节中为同一对象改名。

## 方法与模块

| 规范术语 | 首次出现时的定义 | 禁止或需限定的变体 | 使用规则 |
|---|---|---|---|
| **Resource-NMCTS** | 资源感知组合综合器（Resource-NMCTS） | “神经 MCTS 本方法”“纯 AI 综合器” | 指请求方法 `resource_nmcts` 的完整候选组合系统。它可选择 Direct-ANF、FPRM、affine、cube、MCTS 或学习辅助候选；任何资源收益都必须同时报告 `selected_method`，不得自动归因于 learned prior。 |
| **learned prior** | 监督训练动作评分器（learned prior） | “强化学习策略”“神经网络优化器” | 指 `action_scorer_competition.pt` 对候选动作的排序分数。主模型为 `24→96→96→96→1` MLP，训练目标为 immediate-label regression；它只影响搜索顺序，不决定语义正确性。当前代码路径在 `n≥6` 时跳过神经评分，相应结果不得作 AI 归因。 |
| **heuristic prior** | 确定性资源启发式先验 | “无先验”“uniform” | `heuristic_only` 保留启发式分数，不等于 uniform。 |
| **uniform prior** | 对保留动作使用相同 PUCT prior 的替换控制 | “无模型”“heuristic-only” | 用于 AI 因果消融；必须与 heuristic prior 分开报告。 |
| **random prior** | 同预算、由固定 seed 决定的哈希随机动作评分控制 | “随机 MCTS” | 写明 `random-prior:<seed>`，并与 learned prior 使用相同候选宽度和 simulation budget。 |
| **Direct-ANF** | 直接代数范式综合（`direct_anf`） | “Direct”“ANF baseline” | 首次定义后可写 Direct-ANF；它是不做因子复用的透明基线。 |
| **Greedy-Factor** | 确定性因子贪心（`greedy_factor`） | “Greedy” | 图表空间不足时可写 Greedy，但图注或表注必须给出完整名称。 |
| **MCTS-Factor** | 启发式先验 MCTS（`mcts_factor`） | “MCTS”“Neural MCTS” | 该基线不加载 learned prior；不得称为 neural。 |
| **SSHR-H** | 项目内复现的 SSHR 启发式基线（`sshr_h`） | “SSHR” | 与 SSHR-Beam 同时出现时必须写全名。 |
| **SSHR-Beam** | 项目内复现的 SSHR beam-search 基线（`sshr_beam`） | “SSHR” | 超时属于实验结果，不能从 coverage 分母删除。 |
| **selected method** | Resource-NMCTS 最终选中候选的实际方法（数据库/JSONL 字段 `selected_method`） | “子方法”“获胜模型” | 所有单实例线路图和组合系统归因必须报告该字段。 |

## 任务、线路与验证

| 规范术语 | 定义 | 使用边界 |
|---|---|---|
| **bit-flip Boolean Oracle** | 实现 $|x\rangle|y\rangle\mapsto|x\rangle|y\oplus f(x)\rangle$ 的可逆线路 | 核心引擎的当前任务。不得泛化为任意 unitary、连续参数线路或独立 Rz/相位 Oracle 综合。 |
| **逻辑线路** | 引擎输出的 X/CNOT/MCT 抽象门序列 | 尚未包含特定设备门基、布局、路由、时长或噪声。 |
| **逻辑 T（logic T）** | 由冻结 MCT/相对相位成本表估计的 T-count | 是容错代理指标，不是真实设备 T 门执行数或 QEC 总开销。数据库字段为 `t_count`。 |
| **逻辑 CNOT（logic CNOT）** | 由同一逻辑成本模型估计的 CNOT-count | 不等于映射后的原生二比特门数。数据库字段为 `cnot_count`。 |
| **逻辑深度代理** | 逻辑 MCT 成本模型中的顺序/阶段代理 | 不称为真实硬件运行时间。 |
| **plan ANF 检查** | 将 factor plan 展开回 GF(2) 单项式集合的符号检查 | 当前主要用于回归测试和实例审计；若未接入某正式 runner，不得写成该批次强制门槛。 |
| **逻辑穷举验证** | `verify_oracle()` 对全部 $2^n$ 个输入的位并行精确验证 | 检查输出真值表、输入保持和辅助位归零；与 mapped Aer 验证分开。 |
| **映射后精确验证** | 按 initial/final layout 对全部 $(x,y)$ 基态检查输出、数据保持、辅助位、泄漏和输入相关相位 | `n\leq8` 时覆盖 $2^{n+1}$ 个输入态。不得简称为“真机验证”。 |

## 硬件映射与指标

| 规范术语 | 定义 | 禁止表述 |
|---|---|---|
| **synthetic Target** | 无校准的 Qiskit `Target`，含显式原生门集、耦合边和方向 | 不称“真实芯片”“某厂商真机后端”“真实保真度模型”。 |
| **硬件映射** | 从逻辑线路到指定 synthetic Target 的门分解、初始布局、SABRE 路由和原生门检查 | 单纯 basis decomposition 不得称硬件映射。 |
| **native-2Q** | 映射线路中的原生二比特门数量（`native_twoq_count`；数据库字段 `native_entangling_count`） | 不与逻辑 CNOT 混用；CZ/ECR Target 下不得统一写成 CX 数。 |
| **mapped depth** | Qiskit 映射后线路总深度 | 仅在 target、Qiskit 版本、optimization level、layout/routing、HLS 和 transpiler seed 全部一致时比较。 |
| **native-2Q depth** | 映射线路的原生二比特门深度 | 与 mapped depth 分开报告。 |
| **routing delta** | 相对同门集 basis-only 参考的有符号 gate/depth/native-2Q 差值 | 不称为 SWAP 数；负值可以出现。 |
| **`cx_full_12`** | 资源安全主分析使用的 12 比特全连接 CX synthetic Target | 当前 PDF 主统计的唯一冻结 target。 |
| **line pilot** | `cx_line_*_bidir` 上的稀疏路由实例或先导实验 | 不与 `cx_full_12` 主分析合并。 |
| **grid/heavy-hex 支持** | 代码能够构造并编译 CZ grid 与 ECR heavy-hex synthetic Target | 未进入冻结数据库分析前，只能称“实现支持”。 |

## 实验与统计

| 规范术语 | 定义 | 使用规则 |
|---|---|---|
| **primary20** | 预先冻结的 20 个独立 Boolean functions：8 structured、6 random-truth、4 random-ANF、2 AES | 不把同一函数的 CSV/JSONL 副本当作独立样本。 |
| **semantic cell** | experiment × suite × function × method × synthesis seed × 精确 target/transpile 配置定义的唯一实验单元 | 恢复运行按该键去重；不能从多次成功中挑最优。 |
| **资源安全主分析** | primary20 × 6 methods × seeds `{7,17,29}` × `cx_full_12` × transpiler seed 3 | 计划逻辑单元数为 360；只有同一函数三个 seed 全部成功并验证，才进入正式配对统计。 |
| **clean experiment** | 在稳定方法身份和统一冻结配置下，将去重后的成功事实汇入同一 experiment slug 的分析对象 | 不跨 experiment 在统计层盲拼。 |
| **coverage** | 计划单元、成功、验证失败、超时、中断及缺失的完整分母记录 | 质量统计只使用共同成功集合，但 coverage 必须保留所有失败。 |
| **pilot** | 用于验证实现、估时或探索趋势的先导结果 | 不作为正式显著性结论。 |
| **available-seed sensitivity** | 使用现有共同 seed 的敏感性分析 | 不得冒充 `{7,17,29}` 完整种子主分析。 |
| **显著优于** | 匹配实验、全部正确性门槛、完整种子、函数级推断、Holm-adjusted $p<0.05$、95% CI 不跨 0 且方向一致 | 不满足任一条件时，使用“降低”“趋势”“单实例改善”或“未观察到稳定增益”等限定表述。 |
| **resource score** | 冻结权重下的候选排序标量 | 次要指标。正文必须同时报告组成指标，且说明训练标签权重与正式评估权重是否不同。 |

## 计算设备与可复现性

| 规范术语 | 定义 | 使用规则 |
|---|---|---|
| **training device** | 模型训练实际使用的设备；当前主 checkpoint 为 RTX 5090 Laptop GPU | 与 inference/simulator device 分列。 |
| **inference device** | learned prior 推理实际使用的设备；小批搜索默认 CPU | 不因机器存在 GPU 就写成 GPU 推理。 |
| **simulator device** | Qiskit Aer 实际设备；当前环境只提供 CPU | 禁止写“RTX 5090 加速了 Aer 仿真”。 |
| **JSONL v3** | append-only 原始运行记录，含阶段耗时、worker 树 RSS 与系统内存峰值 | 原始失败与中断证据不能只靠 DuckDB 成功视图反推。 |
| **DuckDB 实验库** | 保存实验、方法、target、attempt、mapping、verification 与 artifact provenance 的结构化数据库 | 正文不再笼统写“CSV 汇总”。 |
| **analysis ID** | 一次冻结统计导出的内容寻址标识 | 最终 PDF 中总体统计数字和统计图必须关联 analysis ID。 |

## 固定措辞模板

- 允许：**“Resource-NMCTS 在程序生成的 `maj3` 单实例中选择 `affine_greedy`，因此该实例改善不能归因于 learned prior。”**
- 允许：**“在 `cx_line_4_bidir` synthetic Target 上完成原生门、耦合边、布局和映射后精确验证。”**
- 允许：**“当前消融未观察到 learned prior 的稳定独立收益。”**
- 禁止：**“神经 MCTS 显著优于所有现有研究。”**
- 禁止：**“已在 RTX 5090 上完成量子 GPU 仿真。”**
- 禁止：**“已在天衍或其他真实量子芯片上验证。”**
