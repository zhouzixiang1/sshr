# XA-202609 冻结实验协议（硬件感知综合与 AI 消融）

状态：`frozen-resource-safe-v2`（2026-07-22）。原始全量方案保留为扩展层；一次
并发验证曾使系统内存达到 89.3%，因此在查看正式显著性结果前冻结了资源安全主分析
切片、完整种子规则和内存护栏。协议变更必须生成新的 `experiment_id`，不得覆盖旧结果。

## 1. 科学问题

1. 在完全相同的 Boolean Oracle、随机种子和搜索预算下，Resource-NMCTS 是否
   降低逻辑 T/CNOT/深度及加权资源分数？
2. 逻辑层优势在全连接参考、线性、二维网格和 heavy-hex 合成拓扑上是否保持？
3. 学习先验相对启发式先验、同预算随机先验的增益是多少，时间代价是多少？
4. 方法在哪些函数族或拓扑上失败、退化或超时？失败不得从分母中删除。

## 2. 方法与公平比较

### 2.1 强基线

- `direct_anf`：未经因子复用的直接 ANF。
- `greedy_factor`：确定性因子贪心。
- `mcts_factor`：启发式先验 MCTS。
- `sshr_h`：项目内复现的 SSHR-H 逻辑综合。
- `sshr_beam`：可承受规模上执行；超时作为结果记录。
- `resource_nmcts`：完整资源感知组合方法，单独报告实际 `selected_method`。

### 2.2 AI 因果消融

同一 `neural_mcts` 代码路径、同一候选宽度、同一 simulation budget、同一 seed：

- `heuristic_only`：无模型，仅原启发式先验。
- `heuristic_plus_random`：确定性哈希随机控制，路径写作 `random-prior:<seed>`。
- `heuristic_plus_learned`：冻结模型及 SHA256。
- `uniform`：`uniform-prior` 替换控制，将保留候选的 PUCT prior 统一设为 0；不得
  将 `heuristic_only` 写成 uniform。

完整 `resource_nmcts` 另做 learned / random / no-model 三组，但只解释为组合方法中
“允许 AI 候选”产生的增量，不把整个组合方法的收益归因于神经网络。

训练函数与最终测试函数按 truth-table SHA256 分离；模型训练、验证、测试 manifest
必须保存函数哈希、生成 seed、代码哈希、模型 SHA256 和 CUDA 环境。验证集用于
选 checkpoint，测试集不得用于调参。

## 3. Benchmark

最终 `suite_id` 由函数 manifest 哈希决定，最少覆盖：

- 结构化：AND、奇偶、majority、不同阈值；`n=3..8`。
- 随机真值表：`n=4..6`，生成 seed 固定并保存完整 truth table。
- 稀疏/中密度随机 ANF：`n=6..8`，保存项集和 truth table。
- AES S-box 的多个单输出分量；不得把不同输出位当作随机 seed。
- 若引入外部 benchmark，保存原始来源、转换程序和转换后函数哈希。

报告按函数族分层；不能把同一函数在多个 CSV 中的重复副本当作独立样本。

## 4. 重复、目标与预算

- **资源安全主分析（PDF 主结论）**：`formal_coverage_audit.json` 中预先选定的 20 个
  函数（8 structured、6 random-truth、4 random-ANF、2 AES，`n=3..8`），6 个方法，
  synthesis seeds `7,17,29`，`cx_full_12`，transpiler seed `3`，optimization level 1，
  SABRE layout/routing，`hls_ancilla_budget=0`，每个 synthesis/mapping stage 300 s。
  统计只接收三个 seed 全部成功并验证的函数；不足者进入 coverage/failure 表。
- **资源执行合同**：验证 batch size 16，Aer threads 16、parallel experiments 16，
  worker 每 8 个 stage 回收，系统内存 70% 软上限。JSONL v3 保存各阶段与总峰值。
- **全量扩展方案（不冒充当前完成范围）**：synthesis seeds `7,17,29,43,71`，
  transpiler seeds `3,11,23`，并覆盖下列四类目标：
  - `cx_full_19`：全连接门集参考；
  - `cx_line_19_bidir`：稀疏路由压力测试；
  - `cz_grid_4x5`：二维 CZ 合成拓扑；
  - `ecr_heavy_hex_d3_bidir`：19 比特 ECR heavy-hex 合成拓扑。
- 所有目标均为无校准 synthetic proxy；正文不得使用具体真机名称或真实保真度措辞。
- 早期 smoke/pilot 可使用 120 s，但不得与 300 s 资源安全主分析混为同一实验。
- 同一逻辑产物只综合一次，再映射到所有 target × transpiler seed，避免重复综合造成
  不公平计时和随机差异。
- 失败后允许重试；append-only attempt/latest 视图保留全部失败，质量视图只取最早的
  验证成功 attempt，不得从多次成功中挑最优资源值。为避免成功 mapping 依附于非
  canonical synthesis attempt，正式质量实验由成功事实去重后统一 ingest；原始失败
  和超时仍由 raw JSONL/recovery manifest 给出完整分母。

## 5. 正确性门槛

任何资源数据进入主统计前必须同时满足：

1. 引擎符号/经典验证通过；
2. 逻辑 Aer 验证通过；
3. 映射线路原生指令、耦合边和方向违规数为 0；
4. `n≤8` 时对全部 `x` 和 `y∈{0,1}` 做精确状态验证；
5. 数据位保持、Oracle 输出、所有辅助位归零、泄漏和输入相关相位均通过阈值；
6. 线路、目标、配置、模型和日志 artifact SHA256 可追踪。

失败、超时和未验证样本进入 coverage/failure 表，不能静默过滤。

## 6. 指标

### 逻辑层

T、CNOT、逻辑深度、总门数、显式/峰值辅助位、冻结权重下的 resource score、
synthesis wall time。

### 映射层

原生总门、1Q/2Q 门数、2Q 深度、总深度、活跃物理比特、初末布局、各门计数、
相对同门集 basis-only 参考的 signed routing gate/depth/2Q delta、compile time。

不得使用旧 `swap_free`，也不得把“mapped/logical gate ratio”称作路由 SWAP 数。

### AI 效率

同预算质量差、learned/random/heuristic 胜负平、模型推理时间、总运行时间、
质量—时间 Pareto。RTX 5090 用于训练和足够大的批评分；小批搜索推理若 CPU 更快，
应如实记录而非强制使用 GPU。

## 7. 统计方案

- 逻辑指标严格按 experiment × suite × case × synthesis seed 配对；映射指标还必须具有
  完全相同、内容寻址的 target 和 transpile spec。后者锁定 transpiler seed、
  optimization level、layout、routing 与 HLS/辅助位配置，不允许跨配置配对。
- 对每个独立 Boolean function，先计算每个严格配对 seed 的差值，再取中位数得到
  唯一的函数级差值。Wilcoxon、rank-biserial 和 bootstrap 的推断/重抽样单位
  均为 Boolean function，seed 仅用于函数内重复性评估，不充当独立样本。
- 正式主分析预注册完整 seed 集 `required_seeds={7,17,29}`。在给定 scope 以及精确
  target/transpile 配置内，candidate 与 reference 只有在某函数的三个指定 seed
  全部存在、验证通过且指标有限时，该函数才可进入 Wilcoxon、rank-biserial 和
  bootstrap；任一 seed 缺失或无效即整函数排除，并记录所缺 seed。不得用 1–2 个
  可用 seed 冒充完整三种子结果。不指定 `--required-seeds` 的 available-seed 结果
  仅作为敏感性分析，不作为正式显著性结论。
- 每行同时报告有效 seed 数、函数级完整性、mean、median、IQR、标准差、几何均值比
  和以 Boolean function 为单位的 bootstrap 95% CI。
- 主比较使用双侧配对 Wilcoxon；同时报告配对 rank-biserial effect size。
- 预先冻结两个主假设族：`logical_primary={logic_T, logic_CNOT}` 与
  `mapping_primary={native_twoq_count, mapped_depth}`，两族分别做 Holm 校正。
  逻辑次要指标和映射次要指标各自独立 Holm；额外保留“全部输出假设”的
  global Holm 作为敏感性列，不替代预注册主族。保存原始 p、两种校正 p、
  比较族和分析合同哈希。数据库字段 `t_count/cnot_count/native_entangling_count`
  分别对应竞赛名称 `logic_T/logic_CNOT/native_twoq_count`。
- 比例在基线为 0 时不计算百分比，改报绝对差。
- 不跨 experiment 拼接样本；正式结论只能来自一个统一冻结、覆盖充足的
  experiment slug。分散恢复运行必须先去重并统一 ingest，不得在统计层盲拼。
- 主质量统计只对共同成功且共同验证的严格配对集合计算。超时、worker 异常、
  中断行和计划 coverage 必须从外部 append-only 原始/恢复 manifest 报告；对仅成功行
  ingest 的 DuckDB，分析器明确标记无法反推这些分母，不得把数据库可见键冒充 coverage。

只有同时满足以下条件才使用“显著优于”：匹配实验、全部正确性门槛、独立函数数
足够、Holm-adjusted `p<0.05`、95% CI 不跨 0、效应方向一致，并明确指标和范围。

## 8. 分级执行

1. `smoke`：2 functions × 2 methods × 2 synthesis seeds × 2 targets × 1
   transpiler seed；验证 schema、resume、去重、失败保留。
2. `pilot`：用于验证 AI 消融、拓扑能力和估算时间；不得作为正式显著性结论。
3. `resource-safe final`：冻结 primary20 后使用 3 synthesis seeds × 1 reference
   target/transpiler seed，逐块落盘并带 70% 内存护栏；这是当前 PDF 主分析。
4. `full extension`：资源允许时再扩到 5 synthesis seeds × 3 transpiler seeds × 4
   targets；不得把未完成网格写成已有结果，也不得因 pilot 结果删除不利函数族。

## 9. 输出冻结

每次分析生成 `analysis_id`，并输出：

```text
results/db_exports/<schema_version>/<analysis_id>/
  tables/*.parquet
  summaries/*.csv
  queries/*.sql
  manifest.json
```

PDF 中每个数值和图表必须引用冻结的 `analysis_id`；脚本、输入查询、CSV/Parquet、
SVG/PDF/PNG 和环境 manifest 均写 SHA256。
