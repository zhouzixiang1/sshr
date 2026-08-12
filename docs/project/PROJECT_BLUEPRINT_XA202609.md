# XA-202609 项目统一蓝图

> 状态：竞赛方向与完成定义已确认；正在迁移服务器研发快照
> 更新：2026-07-28
> 截止：2026-09-15
> 项目：密码量子 Oracle 智能综合与资源评估原型
> 赛题：中国电信集团有限公司“量子+AI 双向赋能的研究与应用探索”

本文件用于统一赛题解释、技术主线、实验范围、交付物和验收证据。若
`RESEARCH_PLAN_AI4Q_Q4AI.md`、`DELIVERABLES.md` 或
`TECHNICAL_DESIGN.md` 中的旧规划与本文件冲突，以本文件为准。

---

## 1. 一句话目标

给定密码相关布尔函数

\[
f:\{0,1\}^{n}\rightarrow\{0,1\},
\]

生成严格实现

\[
U_f|x,y\rangle=|x,y\oplus f(x)\rangle
\]

的低资源量子 Oracle；使用等变 policy/value 网络引导 MCTS，使用 QAOA
从候选动作中调度高效且多样的搜索分支，并通过原生门转换与含噪仿真把
执行层反馈送回综合目标，形成可测量、可复现、不过度宣称量子优势的闭环。

本项目不是通用量子编译器，也不是通用 QML 平台。应用边界是：

- 密码 Boolean Oracle 综合；
- Oracle 的逻辑资源、原生门资源和含噪执行风险评估；
- 为 Grover 类密码分析和密码资产风险评估提供可审计的成本依据。

---

## 2. 赛题要求的准确解释

### 2.1 必须满足

| 赛题要求 | 本项目的兑现方式 | 最终证据 |
|---|---|---|
| 不能只做孤立的量子算法或传统 AI 训练 | AI 直接控制量子 Oracle 综合；QAOA 可进一步辅助 AI 搜索 | 端到端流程图、运行日志、消融 |
| 明确 AI 与量子计算之间的赋能链路 | 主链为 AI→量子；增强链为 QAOA→AI；执行反馈形成闭环 | 三条链路各有输入、输出和指标 |
| 锚定具体应用 | 密码分析中的 Boolean Oracle 成本 | AES S-box 与代表性密码函数 |
| 兼容主流及新兴硬件技术路线 | 硬件 profile/adapter 抽象；至少完成超导可执行仿真，并展示其他路线的适配边界 | profile、原生门、拓扑和噪声报告 |
| 给出技术路线、关键参数和验证方案 | 等变网络、MCTS、QUBO/QAOA、原生门、噪声模型均有参数表 | 配置、manifest、技术报告 |
| 原型需要可复跑的运行测量与仿真实验结果 | 报告资源变化、搜索效率、QAOA 解质量、映射后开销和噪声指标 | raw/summary/CI、可复跑命令 |
| 客观说明限制，避免夸大 | 明确模拟规模、QAOA 深度、shots、模型参数、噪声假设、未用真机等 | limitations 和 claim lint |
| 提交源码、结果、报告、创新点、使用和环境说明 | 建立独立竞赛包及 verifier | 干净解包验证报告 |

### 2.2 两个关键纠偏

1. 赛题允许“量子赋能 AI”“AI 赋能量子计算”或两者闭环。因此，已经成立的
   AI→量子线路综合本身符合交叉赋能逻辑；闭环是提高主题契合度和差异化的
   强化项，不应写成“没有闭环就必然不合格”。
2. 赛题允许理论推导和仿真实验，也提供仿真资源。真实量子硬件不是明文必选项。
   原型必须有可测量结果，但不能把噪声模拟结果写成真机实测。

### 2.3 仍然必须补齐的硬边界

现有引擎只输出逻辑 X/CNOT/MCT。若没有原生门、拓扑或噪声层，就不能证明
“适配量子计算机原生门集”，也无法支撑硬件兼容性。因此硬件抽象与至少一个
可执行后端仍是本竞赛原型的必做项。

---

## 3. 统一技术主线

```text
密码 Boolean 函数 / 真值表 / ANF
              │
              ▼
      等变共享主干编码状态
       ├─ policy：动作排序
       └─ value：可达成本估计
              │
              ▼
       Neural MCTS 综合搜索
              │
       候选扩展动作集合
              │
              ▼
 QAOA 多样化 batch 调度（可切换经典求解器）
              │
              ▼
      Plan → X/CNOT/MCT 逻辑线路
              │
       GF(2) 等价性验证
              │
              ▼
  原生门分解 → 拓扑映射 → 含噪仿真
              │
              ▼
 原生门数 / 深度 / SWAP / 成功率代理
              │
              ▼
      标定综合成本并重新综合
```

整个系统只有一个中心目标：在严格保持 Oracle 语义的前提下降低目标硬件上的
可执行成本。AI、QAOA 和噪声仿真不是三个平行演示。

---

## 4. 三项核心创新

### I1. 结构等变的 policy/value Neural MCTS

把 ANF 项集表示为“单项式 × 变量”的二值关系矩阵，使用对单项式重排不变、
对变量重标号等变的共享主干，联合输出：

- policy：候选因子动作的优先级；
- value：相对 direct plan 的可达资源比。

搜索保持三个安全性质：

1. 学习模型只决定搜索控制，不决定线路语义；
2. `direct_plan` 始终是可行上界；
3. 最终线路必须经过 GF(2) 符号或完整真值表验证。

当前 v3 checkpoint 的训练域是逻辑 MCT 成本。未完成硬件条件训练前，不把它
称为“硬件感知模型”，也不允许静默用于 `logical_and` 等未标注成本域。
虽然编码器包含资源权重通道，v3 实际只在论文权重 profile 上训练，因此也
不能据此声称已经支持任意硬件权重条件化。

### I2. QAOA 多样化扩展调度

QAOA 不用于“同时执行一组因子动作”。当前 Plan 的动作语义是二叉
factor/rest 分解，每个动作应独立成为一个 MCTS 子节点。

给定 progressive widening 和过滤后冻结的候选动作
\(a_1,\ldots,a_K\)，要求 `B_requested` 为正整数并定义
\(B_{\mathrm{eff}}=\min(B_{\mathrm{requested}},K)\)，选择
\(B_{\mathrm{eff}}\) 个子节点：

\[
\max_x \quad
\sum_i u_i x_i-\lambda\sum_{i<j}s_{ij}x_ix_j,
\qquad
\sum_i x_i=B_{\mathrm{eff}}.
\]

其中：

- \(u_i\)：policy、即时收益、访问不确定性等组成的效用；
- \(s_{ij}\)：动作 group/rest 影响集合的 Jaccard 冗余，例如
  \(s_{ij}=\alpha J(group_i,group_j)+(1-\alpha)J(rest_i,rest_j)\)；
- \(\lambda\)：质量与多样性的权衡。

QUBO 形式加入基数惩罚：

\[
\min_x -\sum_i u_i x_i
+\lambda\sum_{i<j}s_{ij}x_ix_j
+\rho\left(\sum_i x_i-B_{\mathrm{eff}}\right)^2.
\]

必须同时提供 random、top-B、经典 greedy、经典 exact 和 QAOA 五条求解路径。
当 \(K=0\) 时返回空集合；当
\(0<K\le B_{\mathrm{requested}}\) 时直接扩展全部并跳过 QAOA。在线 QAOA
异常、超时或 sample 不可修复时回退 greedy；exact 只作小规模审计 oracle。
not-invoked、repair 和 fallback 必须分开记录，失败或质量较差时不能破坏
MCTS 正确性，也不能用 fallback 成绩冒充 QAOA。

完整学习反馈链为：

```text
AI 给动作赋权 → QAOA 选择扩展批次 → MCTS 得到已验证回报
→ 轨迹进入 replay buffer → expert iteration 更新 policy/value
```

如果没有最后的训练更新，只称“量子子程序辅助 AI 搜索”，不称算法级闭环。

禁止使用以下旧表述：

- “group 相交即冲突，因此求 MWIS 后同时施用”；
- “经典 MWIS 扩展必然降低树深”；
- “QAOA 加速 MCTS”。

在获得计时和质量证据前，统一称为“QAOA-assisted diversity scheduling”。

### I3. 原生门与含噪反馈闭环

定义 `HardwareProfile`，至少包含：

- 原生门集；
- 耦合图或全连接假设；
- 单/双量子位门错误；
- 读出错误；
- 退相干或等效噪声参数；
- transpile/routing seed。

最小闭环为：

1. 生成多个逻辑层可行候选；
2. 转换并映射到目标 profile；
3. 含噪仿真得到执行指标；
4. 在训练集上拟合非负或受约束的执行成本代理；
5. 用新目标重新排序或重新综合；
6. 在函数隔离的测试集上比较闭环前后结果。

含噪反馈至少报告：

- 原生单/双量子位门数；
- 映射后深度和 SWAP；
- 估计成功率、输出分布保真度或任务级正确率；
- 闭环前后配对差异。

---

## 5. 双向赋能逻辑

### 主链：AI 赋能量子

```text
等变 policy/value → Neural MCTS → 低资源、严格等价的量子 Oracle
```

这是最成熟、最直接命中赛题“AI 驱动量子线路综合”的部分。

### 增强链：量子子程序辅助 AI

```text
MCTS 候选状态 → diversity QUBO → QAOA 采样 → MCTS batch expansion
```

该链必须通过与经典 exact/greedy 的差距和成本来评价。即使没有量子优势，
仍可形成量子-经典协同原型和边界分析。

### 执行反馈链

```text
AI 综合 → 原生门/含噪执行 → 成本标定 → AI 重新综合
```

这是数据驱动的工程闭环，负责把逻辑层优化和真实执行约束连接起来。

---

## 6. 应用场景

### 6.1 核心场景

密码算法中的 Boolean Oracle 资源评估，重点使用：

- AES S-box 八个坐标函数；
- 对称、阈值、随机和结构化 ANF 函数；
- 可在截止期内完成定义与验证的轻量密码组件。

### 6.2 可用价值主张

- 给出密码 Oracle 的可审计逻辑资源和硬件 profile 成本；
- 比较不同综合策略对 Grover 子程序构造成本的影响；
- 为密码资产风险分析提供“给定假设下的资源估计”。

### 6.3 不可使用的价值主张

- 不能据此给出现有密码“还能安全多少年”的确定时间；
- 不能把单个坐标函数成本直接等同完整 AES 攻击成本；
- 不能把模拟噪声外推为天衍真机性能；
- 不能声称量子优势、全局最优或通用硬件映射优势。

---

## 7. 当前真实状态

| 能力 | 当前证据 | 状态 |
|---|---|---|
| 逻辑 Oracle 综合与验证 | `experiments/src/`、旧 smoke、论文实验 | 已有稳定底座 |
| 旧资源实验 | 177 个 n≤6 核心函数、15,774 条已审计验证证据、700/700 bridge 等 | 可复用，但不是新闭环实验 |
| AES S-box | 八个坐标函数均验证，旧逻辑 score 改善 46.36%–55.06% | 可复用应用证据 |
| 等变模型 | `src/foundation/`、v3 checkpoint、等变/value 测试 | 开发态；n=8/9 初步正结果样本仍小 |
| policy/value 公开入口 | `foundation_nmcts` 已接入；小模型单测和 v3 小样例通过 | 开发态，未冻结 |
| QAOA diversity 调度 | 只有纠偏后的设计 | 未实现 |
| QASM 交换层 | 逻辑 MCT OpenQASM 3 导出及边界测试 | QASM 专项 14 项通过；仍不等于原生门 |
| 原生门/拓扑映射 | 无 | 未实现 |
| 含噪仿真与反馈 | 无 | 未实现 |
| 竞赛专用 CLI/报告 | 无 | 未实现 |
| 竞赛报告、演示、合规包 | 无 | 未形成 |

“旧论文证据很强”和“竞赛原型已完成”是两件不同的事。旧结果只作为基线和
可信度底座；新 AI、QAOA 和硬件闭环必须拥有独立结果命名空间及 manifest。

---

## 8. 实验方案

### E0. 语义与回归门

- 旧 smoke 必须持续通过；
- 每条新逻辑线路通过符号验证；
- 小规模函数进行完整真值表验证；
- 对全部小规模 bitstring 验证 QUBO 含罚项能量恒等式，并在固定基数可行集上
  验证最小化 QUBO 与最大化直接目标的排序和最优解一致；
- 原生门转换在可模拟规模上做独立 unitary/truth-table 检查。

任何正确率低于 100% 的配置不能进入资源比较。

### E1. 置换等变 policy/value

核心测试集建议：

- \(n\in\{6,7,8,9,10\}\)；
- 每个 \(n\) 20 个与训练种子流隔离的密集函数，共 100 个；
- \(n=10,12\) 各 10 个稀疏 ANF 函数；
- majority、mux、adder、multiplier 等结构化函数至少 15 个；
- 结构化函数与 AES S-box 单列，不混入随机均值；
- 随机搜索组件至少 3 个独立 seed。

核心因果矩阵必须把 policy、value 和 progressive widening 分开：

| 编号 | Policy | Value | 动作宽度 | 作用 |
|---|---|---|---|---|
| C0 | heuristic | greedy rollout | exhaustive | 经典基线 |
| C1 | learned | greedy rollout | exhaustive | policy 单独贡献 |
| C2 | heuristic | learned | exhaustive | value 单独贡献 |
| C3 | learned | learned | exhaustive | policy+value |
| C4 | heuristic | learned | progressive | widening 单独贡献 |
| C5 | learned | learned | progressive | 最终部署配置 |
| C6 | shuffled learned | learned | progressive | AI 不可消融对照 |
| C7 | rollout oracle | learned | progressive | 排序上界，仅用于诊断 |

验证集先选择 simulation 数，再在固定 simulation 下选择 `widen_c`，不能只扫
一个因子后把条件效应误写成主效应。

P0 主矩阵为 135 个非密码测试函数 × C0–C6 × 3 个 MCTS seed，共 2,835 次
求解。C7 只在诊断子集上运行，避免把不可部署的 oracle 排序上界混进主耗时。

指标：

- score、T、CNOT、深度、辅助位；
- wall time、节点数、模型调用和 batch 大小；
- W/L/T、配对均值、中位数、95% bootstrap CI；
- policy 捕获的 oracle 排序空间；
- 分布内与分布外结果分开。

### E2. Diversity/QAOA 调度

状态样本从训练集外的 MCTS 节点提取。核心网格：

- P0 使用 48 个冻结节点，\(K\in\{8,12,16\}\) 各 16 个；
- 主设定 \(B=4\)，验证集再扫描 \(B\in\{2,4\}\)；
- 验证集扫描多个 \(\lambda\) 和 \(\alpha\)；
- QAOA \(p\in\{1,2\}\)，P1 再扩展到 \(p=3\)；
- 至少 30 个随机初始化/采样重复用于随机方法。

比较：

- random；
- top-B；
- greedy diversity；
- exact；
- ideal QAOA；
- noisy QAOA。

指标：

- objective 与 exact regret；
- utility 和 pairwise redundancy；
- \(K=0\)、\(K<B_{\mathrm{requested}}\)、
  \(K=B_{\mathrm{requested}}\)、\(K>B_{\mathrm{requested}}\) 边界覆盖；
- not-invoked、可行基数、repair 与 fallback 分离统计；
- circuit depth、两量子位门、shots、优化时间；
- 接入 MCTS 后的最终 score、time、节点覆盖和 seed 稳定性。

P0 节点级主实验为 48 节点 × 2 个 \(p\) × 3 个 QAOA 初始 seed，共 288 次
QAOA 优化。端到端再使用 \(n=8,9\) 各 10 个函数，对比单动作、random、
top-B、greedy、exact、QAOA 六种调度和 3 个 MCTS seed，共 360 次搜索。
模拟器总开销与不含量子调用的搜索开销必须分列。

### E3. 硬件与噪声

最低要求：

- 一个超导 profile：局部耦合、CX/ECR 类双量子位门、可执行噪声仿真；
- 一个离子阱风格 profile：全连接与 RXX/MS 类相互作用，至少完成资源映射；
- 光量子路线给出 adapter 能力表与不可直接映射的边界，不伪造通用门兼容。

代表性线路：

- 校准集和独立测试集各取 \(n=4,5,6\) 每尺度 10 个函数；
- 结构化函数至少 15 个；
- 密码坐标函数进入独立分层；
- 约 300 条逻辑线路完成原生门分解和理想等价检查。

两个主要 profile × 3 个 transpile seed 形成约 1,800 次映射；可执行噪声实验
使用 0.5×/1×/2× 三档噪声和独立 shot seed。

### E4. 反馈闭环

按函数划分 train/calibration/test，禁止同一函数的不同候选跨集合泄漏。

比较：

1. 固定论文权重；
2. 原生门资源 rerank；
3. 噪声标定 rerank/重新综合。

只有在独立测试集上改善，才能写成“反馈有效”。若没有改善，报告负面结果和
失效条件，不隐藏。

推荐使用非负最小二乘或正系数 ridge 拟合：

\[
-\log P_{\mathrm{success}}
\sim \beta_1N_{2Q}+\beta_2 depth+\beta_3SWAP+\beta_4 width.
\]

### E5. 密码用例

P0 目标为 25 个坐标函数：

- AES S-box：8 个；
- SM4 S-box：8 个；
- PRESENT S-box：4 个；
- ASCON S-box：5 个。

每个坐标函数至少运行 direct、Resource-NMCTS、foundation-NMCTS 和
foundation+QAOA，并进入逻辑验证、原生门和含噪评估。报告逐坐标结果及求和
结果，同时明确“坐标独立综合及资源求和”不等于已经得到共享中间项优化后的
完整 S-box 最优线路。

### E6. 统一统计口径

- 所有主比较按函数和 seed 配对；
- 报告 median relative change、几何平均 speedup、W/L/T；
- 95% CI 使用按函数聚类的 bootstrap，同一函数的所有 seed 一起重采样；
- W/L/T 使用 exact sign test，多项主比较使用 Holm 校正；
- 超时同时报告数量、cap 计时和 common-completed 子集；
- QAOA 成功率使用 Wilson CI，objective gap 按节点配对；
- 每个实验必须产出 raw CSV、summary CSV、manifest JSON 和 analysis Markdown。

---

## 9. 独立竞赛交付目录

建议新建而不是复用论文投稿包：

```text
competition/
├── README.md
├── environment.yml
├── configs/
├── examples/
├── models/
│   ├── boolean_oracle_fm_v3.pt
│   └── MODEL_CARD.md
├── src/
├── scripts/
│   ├── demo_competition.py
│   ├── run_foundation_eval.py
│   ├── run_qaoa_scheduler_eval.py
│   └── run_hardware_feedback_eval.py
├── evidence/             # 从 results/xa202609 验证后复制的小型证据
├── report/
├── demo/
├── compliance/
└── verify_competition_package.sh
```

建议端到端命令：

```bash
python scripts/demo_competition.py \
  --case aes_sbox_bit0 \
  --synthesizer foundation_nmcts \
  --scheduler qaoa_diversity \
  --hardware superconducting_noise \
  --output experiments/demo/output
```

必须输出：

- `logical_plan.json`；
- `logical.qasm`；
- `native.qasm`；
- `metrics.json`；
- `trace.jsonl`；
- 人可读的 HTML 或 PDF 结果报告。

---

## 10. 七类最终交付物与完成定义

| 交付物 | 完成定义 |
|---|---|
| 可运行原型 | 干净环境中单命令跑通“输入→AI/QAOA→验证→原生门→含噪→报告” |
| 可复现实验 | benchmark、seed、config、checkpoint SHA、commit、raw/summary/manifest 完整 |
| 完整源码与模型 | 目标模块全部纳入 Git；冻结唯一推荐模型并提供模型卡 |
| 技术报告 PDF | 专门面向 XA-202609；数据能逐项追溯；完成文字、公式和视觉 QA |
| 安装使用文档 | 不依赖本机绝对路径；按文档从零安装并运行最小及完整 demo |
| 演示材料 | PPT/PDF、演示脚本、样例输入输出和离线 fallback |
| 合规提交包 | 报名表、PDF、源码、模型、结果、文档、演示、许可/IP 说明及一键 verifier |

整体完成条件不是“七项中多数完成”，而是七项全部有可检查证据。

---

## 11. 分阶段里程碑

### M0：方向冻结（2026-07-30 前）

- 统一使用本蓝图；
- 删除或标记旧 MWIS 同时动作设计；
- 冻结核心创新、实验口径和 claim boundary；
- 确认报名、学校主体、队伍和人工提交字段。

### M1：AI 核心冻结（2026-08-05 前）

- `foundation_nmcts` 统一入口；
- 唯一 checkpoint 与模型卡；
- policy/value 四象限消融可复跑；
- 新旧回归测试通过。

### M2：量子辅助搜索（2026-08-16 前）

- diversity objective、罚项能量恒等式、可行集排序与 exact 最优解测试；
- random/top-B/greedy/exact/QAOA 五路径；
- 接入 MCTS batch expansion；
- ideal/noisy QAOA 结果。

### M3：硬件与反馈闭环（2026-08-25 前）

- 原生门分解、profile、拓扑和噪声；
- 独立等价性验证；
- 反馈标定及 held-out 对照。

### M4：应用与系统实验（2026-09-01 前）

- AES/结构化/随机实验；
- raw/summary/manifest；
- 一键 demo 和失败降级路径。

### M5：提交物冻结（2026-09-10 前）

- 报告 PDF；
- 安装文档；
- PPT/演示；
- 独立竞赛包与解包 verifier。

### 缓冲（2026-09-11 至 09-14）

- 只允许修复、复验、补人工字段和最终打包；
- 不再引入新模型、新后端或新实验主张。

---

## 12. 风险与降级规则

| 风险 | 降级规则 |
|---|---|
| QAOA 不如经典 exact/greedy | 保留量子子程序原型和负面结果；不声称加速或优势 |
| 真实平台不可用 | 使用明确参数的本地噪声仿真；报告中标注 simulator-only |
| 光量子无法复用门模型 | 给出 capability/adapter 边界，不伪造门级结果 |
| value 网络分布外退化 | 使用 direct 上界、guard 和训练域标签；分布内外分表 |
| 原生门分解规模爆炸 | 限定可执行规模，逻辑大规模与硬件小规模分层报告 |
| 截止期前实验过多 | 六条扩展轨至少做到可复现实验；只有跨过定量门的模块进入核心主张 |
| 旧论文包与竞赛包混淆 | 独立 `competition/`、结果命名空间和 verifier |

---

## 13. 声明边界

报告和演示中统一遵守：

- 使用“量子辅助”“含噪仿真”“给定硬件 profile 下”；
- 只有真实真机运行才能使用“真机实测”；
- 只有相同任务、相同预算的配对统计才能使用“提升/降低”；
- QAOA 未有端到端证据前不使用“量子加速”；
- 不声称全局最优、普适量子优势或完整 AES 攻击能力；
- 逻辑层、原生门层和含噪执行层的指标必须分栏报告。

---

## 14. 当前恢复点

用户已经确认由本项目继续推进以下方向：

1. 作品聚焦“密码量子 Oracle 智能综合与资源评估原型”；
2. 对外称“置换等变 policy/value 模型”，暂不称通用基础模型；
3. QAOA 是固定预算的 diversity batch scheduler，而不是同时动作 MWIS；
4. 采用 simulator-first、真机可选且不夸大的硬件路线。

四项选择的理由、影响和确认状态见 `ARCHITECTURE_DECISIONS_XA202609.md`。
服务器接手版冻结并通过核心测试后，按 M1–M5 恢复实现。六条扩展轨遵循
“全部形成可复现实验、过门再升主创新”的 D5 策略。
