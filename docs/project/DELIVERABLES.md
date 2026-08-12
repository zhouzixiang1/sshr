# 历史研究扩展备忘录（非 XA-202609 施工清单）

> **状态说明（2026-07-28）：历史扩展清单。** 当前权威交付范围与完成定义见
> `PROJECT_BLUEPRINT_XA202609.md`。下文把 `FactorAction` 解释为可以同时
> 施用的一组动作，并据此构造 MWIS；这与现有二叉 factor/rest Plan 的语义
> 不一致。新的设计是固定批量的 utility-diversity 子节点调度，每个动作独立
> 成为 MCTS 子节点。下文有关“同时施用”“经典 MWIS 必然改进”和“量子加速”
> 的表述均已废止。
> `ARCHITECTURE_DECISIONS_XA202609.md` 中 D1–D4 已于 2026-08-09 确认；本文
> 仍只作为历史备忘录，不再授权或阻塞功能施工。正式交付门、排期和验收只以
> 统一蓝图、当前路线和验收矩阵为准。

> 更新:2026-07-27 · 配套 `RESEARCH_PLAN_AI4Q_Q4AI.md`
> 面向:**竞赛作品(XA-202609,2026-09-15)** + **2–3 篇论文**

---

## 0. 当前核心：一条主链、两条增强链

**主链（已具开发基础）：**

```text
等变 policy/value → Neural MCTS → 低资源、严格等价的量子 Oracle
```

**量子辅助链（待实现）：**

```text
动作效用/冗余 → 固定 B 的 diversity QUBO → QAOA 采样
→ B 个彼此独立的 MCTS 子节点
```

QAOA 不求同时动作 MWIS，不改变 `Plan`、辅助线成本或 emitter 语义。完整学习
闭环还需要把 MCTS 的已验证回报送入 replay buffer，再由 expert iteration
更新 policy/value；没有训练更新时只称“量子子程序辅助 AI 搜索”。

**执行反馈链（待实现）：**

```text
逻辑 Oracle → 原生门/拓扑/含噪仿真 → 成本标定 → 重新综合
```

推荐采用 simulator-first，真实量子硬件作为可选增强；该路线仍待 D4 确认。
所有 QAOA 结果必须与 random、top-B、greedy、exact 同预算对照；没有证据前
不使用“量子加速”。

---

## 1. 历史扩展架构（非 XA-202609 施工主线）

XA-202609 的 P0 主线只有：等变 policy/value NMCTS、QAOA diversity
scheduler、原生门/含噪反馈和密码 Oracle 场景。下图中的 GFlowNet、扩散模型、
LLM agent 和通用 QML 套件均为赛后研究储备，不进入 2026-09-15 完成门。

```
┌─────────────────────────────────────────────────────────┐
│ L6 智能体层  LLM 编排:策略选择、实验设计、报告生成        │
├─────────────────────────────────────────────────────────┤
│ L5 应用层    密码 Oracle 成本 · QML 数据加载 · 结构资源图谱│
├─────────────────────────────────────────────────────────┤
│ L4 硬件层    MCT→实际分解→原生门→路由→含噪仿真→标定     │
├─────────────────────────────────────────────────────────┤
│ L3 搜索层    AlphaZero(policy+value+自改进)              │
│              ★ QAOA 多样化 batch 调度 + 学习反馈          │
├─────────────────────────────────────────────────────────┤
│ L2 生成层    GFlowNet 多目标 Pareto 采样 · 扩散模型整计划 │
├─────────────────────────────────────────────────────────┤
│ L1 表示层    置换等变 policy/value 模型                   │
└─────────────────────────────────────────────────────────┘
```

该图只保存赛后研究候选，不用于当前架构、工时、里程碑、演示或创新点计数。

---

## 2. 交付清单

### 🔴 推荐竞赛 P0（待 D1–D4 确认）

| 编号 | 内容 | 层 | 当前状态 |
|---|---|---|---|
| **L1** | 置换等变 policy/value 模型冻结与正式消融 | 表示 | 有开发基础，未冻结 |
| **L3a** | policy/value NMCTS 与 expert iteration | 搜索 | 部分实现，正式证据缺失 |
| **L3b** | QAOA 多样化扩展调度 | 搜索 | 只有设计 |
| **L4a** | 原生门分解、映射与独立等价性 | 硬件 | 只有逻辑 QASM |
| **L4b** | 含噪仿真、资源标定与反馈 | 硬件 | 未实现 |
| **L5b** | 密码 Oracle 场景包 | 应用 | 未冻结 |
| **D0** | 原型、实验、报告、文档、演示与合规包 | 交付 | 未完成 |

里程碑和完成定义统一见 `PROJECT_BLUEPRINT_XA202609.md` M1–M5 与
`../contracts/COMPETITION_ACCEPTANCE_MATRIX.json`，不再使用旧 T0/T1 分档判断完成。

---

#### L1 · 置换等变 policy/value 模型 【竞赛 P0 地基】

当前交付范围是共享等变主干、action policy 头和 value 头。下文多任务头与
大规模自监督预训练属于论文 P1，未实现前不把 v3 称为通用“基础模型”，也
不把“替代 18 个专用模型”列入 9 月 15 日最低交付门。

**当前 P0 已实现的模型范围**
```
项集状态 (T×n 二值矩阵)
        ↓
S_T × S_n 可交换矩阵主干
  · 对项置换不变 · 对变量置换等变 · 接受可变 T,n
        ↓
两个下游头(共享主干):
  ├── 因子选择 policy      ← 替代 24 手工特征
  └── value(资源分数预测)  ← 近似替代部分贪心 rollout
```

**P1 多任务研究假设（未实现）**
```
  ├── affine 变换提议       ← 替代枚举(原 A4)
  ├── screen 深度门控        ← 替代 5 个 depth 模型
  ├── 搜索预算控制           ← 替代 fitted-Q 控制器
  └── 非线性度 / T-count 预测 ← 服务 L5
```

**大规模自监督预训练**(这是"基础模型"名副其实的关键)
- **affine 轨道对比学习（P1）**：同轨道函数可作结构相关样本，但 affine
  wrapper 不是免费，必须把 wrapper cost 纳入目标，不能假设同综合难度
- 真值表距离预测(DeepGate2 式功能感知监督)
- 掩码项重建(masked monomial modeling)
- 辅助回归:ANF 度、项数、非线性度、direct ANF 的 T-count
- 数据:随机 ANF 无限量生成,标签便宜

**P1 判据**
1. `[x]` 变量重标号等变性单元测试
2. `[ ]` 一个模型替掉现有 18 个 `models/*.pt`，且各任务不劣于专用模型
3. `[ ]` 覆盖 n=4..64，并验证训练时未见规模的零样本迁移
4. `[ ]` 预训练显著提升下游收敛速度或最终质量

**降级**:多任务训不稳 → 退回单任务(policy+value),判据降为 1/3;仍不行 → 只保留 value head + 现有特征

**P0 产物**：`src/foundation/` 当前 action/value 实现、唯一冻结 checkpoint、
机器可读模型卡、训练/数据 manifest、SHA 和 C0–C7 结果。`pretrain` 与多任务
对比只属于 P1。

---

#### L3a · AlphaZero 内核

替换 `src/nmcts_solver.py:83` 的 `_greedy_value()`;expert iteration(MCTS 访问计数作 policy 目标,实际达成分数作 value 目标)。

**要点**：求解器是 **minimize** 方向，value 目标用
`z = log(achieved_score/direct_score)`；保留 `direct_plan` 可行上界。
它保证 direct 方案不丢失，但不保证不差于旧 greedy/MCTS，产品模式如需
不退化必须显式运行 classical guard。

**判据(底线,守不住整个改造失败)**
- `[~]` 开发期小样例显示部分尺度运行时下降；正式多 seed manifest 未完成
- `[~]` n=8/9 有初步不可消融信号；C0–C7 独立测试尚未完成

---

#### L4a · 硬件适配层

Plan → 逻辑 X/CNOT/MCT → 逻辑 OpenQASM 3 交换文件（已有，MCT 保留）
→ 显式 MCT 分解 → profile 原生门 → placement/routing → 映射后原生线路
artifact（待建）→ 理想等价验证 → 含噪仿真。

硬件兼容采用非等强的三条证据路线：

1. **超导可执行路线**：局部耦合图、CX/ECR 类双量子位门、SWAP/路由、理想
   与含噪仿真及反馈标定；
2. **离子阱适配路线**：全连接 profile、RXX/MS 类相互作用、原生门与资源映射、
   理想层等价验证；不强制含噪仿真或真机；
3. **光量子边界路线**：给出输入能力、adapter 可行性和 unsupported-boundary
   表，不把门模型 Oracle 伪装成可直接映射的光量子原生线路。

天衍或其他真实硬件只作为不阻塞里程碑的可选附录。

**不自研路由器。** Qiskit 是候选 SDK，但当前未安装且依赖尚未冻结；最终选型
须通过许可证、环境锁定和干净安装验证。创新集中在综合层。

**判据**：端到端跑通，分别完成逻辑 QASM 交换保真检查，以及实际原生门分解
和映射后的独立 unitary、truth-table 或符号等价性验证；超导 profile 至少在
参数可追溯的理想/含噪仿真器上跑通。

---

### 🟠 推荐的量子增强 P0（待 D3 确认）与独立 P1 储备

QAOA 路径不是赛题参赛资格门槛。若 D3 获确认，可运行的 QAOA 路径列为本
项目高分目标 P0；其效果优于经典方法不是完成条件，在线正确性由 greedy
fallback 保证，exact 只作为小规模审计 oracle。除 QAOA、硬件反馈和密码场景
外，下表其他生成式方向均不进入竞赛主线。

| 编号 | 内容 | 层 | 范围 |
|---|---|---|---|
| **L3b** | **QAOA 多样化扩展调度 + 学习反馈** | 搜索 | 推荐竞赛 P0，待 D3 |
| **L4b** | 含噪仿真 + 资源模型标定 | 硬件 | 推荐竞赛 P0，待 D4 |
| **L5b** | 密码安全场景包 | 应用 | 推荐竞赛 P0，待 D1 |
| **L2a** | GFlowNet 多目标 Pareto 采样 | 生成 | P1，不排入本届竞赛 |
| **L5a** | 布尔结构–量子资源探索图谱 | 应用 | P1，不排入本届竞赛 |

---

#### L3b · QAOA 多样化扩展调度 【★ 双向赋能增强项】

**做什么**

1. 对候选动作计算效用 \(u_i\)；
2. 用 group/rest Jaccard 定义冗余 \(r_{ij}\)；
3. 在固定 batch 预算 \(B\) 下优化
   \(\sum_i u_ix_i-\gamma\sum_{i<j}r_{ij}x_ix_j\)；
4. 用 random、top-B、greedy、exact、QAOA 五条路径求解同一问题；
5. 选中动作各自成为独立 MCTS 子节点，不合并为同时动作 Plan；
6. 将 MCTS 访问分布和已验证资源回报写入 replay buffer，比较是否参与下一轮
   expert iteration。

**为什么有价值**

- QAOA 在 AI 搜索的一个明确决策点真实介入，而不是附加展示线路；
- exact 解给出可量化的 objective gap，避免只看主观“多样性”；
- classical fallback 保证 QAOA 失败不会破坏原型可用性；
- replay-buffer 更新把“量子辅助搜索”推进为可测的学习反馈链。

**判据**

- 对全部小规模 bitstring 验证罚项能量恒等式，并在固定基数可行集上验证
  QUBO 排序与直接目标完全一致；
- ideal/shot/noisy QAOA 均有 qubit、深度、2Q 门、shots、优化时间记录；
- 相同冻结节点集上对比 objective gap、repair、冗余和采样熵；
- 接入 MCTS 后继续保持 100% Oracle 语义验证；
- 模拟器开销与纯搜索开销分列；
- QAOA 不如经典方法时保留负面结果，不使用“加速”或“量子优势”。

**产物**：`src/search/diversity_scheduler.py`、`src/search/qaoa_scheduler.py`、
`scripts/run_qaoa_scheduler_eval.py` 和独立 raw/summary/manifest。

---

#### L2a · GFlowNet 多目标 Pareto 采样 【P1 赛后研究】

本节不进入 XA-202609 当前源码、排期、实验、演示或交付门。

**动机**:项目已有 `pareto_resource_nmcts`——一个**启发式** Pareto 归档。Multi-Objective GFlowNet(MOGFN, Jain et al. 2023)正是为"生成多样的 Pareto 最优候选"设计的,是同一目的的**原理性替代**。

**做什么**:训练 GFlowNet 按奖励正比采样分解方案,天生给出多样的 Pareto 前沿;与现有启发式归档对照。

**为什么算创新而非堆砌**:项目的多目标资源模型(T/CNOT/depth/gates/ancilla)天然是多目标问题,而当前用启发式归档处理。GFlowNet 把它变成一个**有理论基础的生成模型**,且与 MCTS 互补(GFlowNet 采样多样性,MCTS 深度优化)。

**判据**:相对现有 Pareto 归档,前沿覆盖更广(hypervolume)或同等覆盖下更快

---

#### L5a · 布尔结构–量子资源探索图谱 【P1 探索】

Stab-QRAM(arXiv 2509.26494)证明仿射布尔函数零 T-count,**明确把非仿射留作开放问题**。本引擎处理任意非仿射函数。

- 采用密码学标准**非线性度**(到最近仿射函数的 Hamming 距离,bent 函数取最大)
- 定义 **affine defect** = `min_A (f(Ax) 的非线性 ANF 项数)`,即 affine 搜索实际在最小化的量
- 同时分析非线性度、代数次数、ANF 密度、乘法复杂度、affine defect 与资源；
  允许非单调和负面结果，不预设单一“定律”
- **现有结果重新语境化**:AES S-box(按高非线性度设计,T-count 减半 48–54%)是高端锚点,affine 消融是低端,Stab-QRAM 是 defect=0 退化情形

---

#### L4b · 噪声模型验证 + 资源模型标定 【simulator-first】

项目的 depth 是"CNOT 数顺序代理"、t_depth 是 `(T+3)//4` 阶段代理,**从未被任何执行层验证**。

**改用噪声模型仿真**：取 n=4–6 oracle，在参数可追溯的超导噪声仿真器
（Qiskit Aer 是候选实现，不是当前冻结依赖）上测保真度，回归分析逻辑层
预测与仿真保真度。

**产出**:"逻辑层资源代理与含噪执行保真度相关系数 r = 0.XX"

**与真机版的差距(须在报告中写明)**:仿真噪声模型无法覆盖串扰、参数漂移、读出误差相关性等真实效应,因此结论是"在给定噪声模型下成立",不能外推为真机结论。**这符合赛题"避免夸大、明确限制条件"的要求。**

---

#### L5b · 密码安全场景包

AES S-box 扩展到更多密码原语的 Oracle 成本表；对 Grover 类密码分析做分层
资源估计，分别报告 Oracle 逻辑资源、超导 profile 映射资源及明确假设下的
算法级外推，不称完整密码攻击端到端实测；后量子密码迁移窗口只作边界明确的
情景讨论。

---

### 🟡 赛后研究候选（不计入本届竞赛加分、工时或演示）

| 编号 | 内容 | 层 | 工时 | 说明 |
|---|---|---|---|---|
| **L2b** | 扩散模型一次性生成整个分解计划 | 生成 | 4 周 | 对标 arXiv 2506.01666(量子线路多模态扩散)、AC-Refiner(算术线路条件扩散)。与 L2a 目的重叠,**二选一即可** |
| **L3c** | 量子振幅估计加速 value 估计 | 搜索 | 3 周 | 有**可证二次加速**理论基础(arXiv 2206.04741 量子策略迭代);比 L3b 理论更强但工程更难 |
| **L6** | LLM 智能体编排 | 智能体 | 2–3 周 | 仅作赛后调研，不进入 XA-202609 作品 |
| **L5c** | QML oracle 套件(决策树推理 oracle 等) | 应用 | 2 周 | 强化双向性 |
| **A5** | AlphaTensor-Quantum / BDD2Seq 对照 | — | 2 周 | **论文投稿前必做**,竞赛可省 |

---

### ⚪ T3 —— 明确放弃

| 项 | 理由 |
|---|---|
| 自研量子比特路由器 | 使用经环境和许可验证的现成 SDK；Qiskit 仅为候选 |
| 变分 QML / QNN / 贫瘠高原 | 无 barren plateau ⟹ 可经典模拟(*Nature Comms* 2025);与引擎零关联 |
| 官方 ROS 全流程复现 | 项目原有 future work |
| 高精度 phase/Rz 旋转综合 | 同上 |
| 端到端量子优势主张 | 赛题明文要求"避免夸大" |

---

## 3. 工时与并行

本节是历史扩展范围的容量估算，不是本届竞赛排期。XA-202609 只为统一蓝图
M1–M5 分配人员；GFlowNet、扩散、LLM、QML 套件不分配本届人员或工期。

**总工时估算**

| 档 | 工时(串行) |
|---|---|
| T0 | 13–15 周 |
| T1 | 15–16 周 |
| T2 | 13–14 周 |
| **合计** | **41–45 周(单人)** |

**竞赛允许 10 人团队**,四条轨道技能栈基本独立,可大幅并行:

| 轨道 | 负责 | 人数建议 |
|---|---|---|
| **A 表示/生成** | L1, L2a, (L2b) | 3–4 |
| **B 搜索** | L3a, L3b, (L3c) | 2–3 |
| **C 硬件/实验** | L4a, L4b, L5b | 2–3 |
| **D 理论/应用** | L5a, L5c, (L6) | 1–2 |

上述 41–45 周只说明历史“大而全”方案超出截止期，不能用于承诺本届交付。
当前关键路径和日期只见统一蓝图；晋级后的新增工作也必须单独审批，不能自动
恢复本节研究储备。

---

## 4. 赛后论文拆分假设（非交付或发表承诺）

下表只表示可能的论证单元；是否足以形成论文取决于正式实验、新颖性检索和
同行评审，不能按模块数量预先认定“三篇”。

| 论文 | 主张 | 依赖 |
|---|---|---|
| **I. AI4Q** | 置换等变 policy/value + 自改进 Oracle 搜索 | L1 + L3a |
| **II. 量子-经典协同** | QAOA 多样化扩展调度及学习反馈边界 | L3b + L4a/b |
| **III. 硬件反馈** | 布尔结构–资源图谱 + simulator-calibrated Oracle 成本 | L5a + L4b + L5b |

论文 II 只有在 replay-buffer 更新和公平基线实验完成后才可称闭环；没有真实
真机数据时必须写成 simulator study。

---

## 5. 做不完时还剩什么

| 情况 | 竞赛 | 论文 |
|---|---|---|
| 推荐 P0 全部完成并通过七类交付门 | 完整目标原型，真机仍可选 | 再按证据评估论文拆分 |
| QAOA 不优于经典方法但路径正确可运行 | 保留负面结果，不声称加速或优势 | 不影响 AI4Q 结果本身 |
| 任一推荐 P0 技术链或七类交付物缺失 | 只能标为未完成或降主张，不能冒充完整原型 | 仅保留已有证据支持的子问题 |

**两条边界：**

1. 赛题最低交叉赋能链由 AI→量子综合满足，不得把 QAOA 或真机误写成参赛
   资格门槛；
2. 若 D1–D4 获确认，本项目自定完成门是 policy/value NMCTS、可运行 QAOA
   路径、原生门/含噪反馈、密码场景和七类交付全部有证据。任何一轨失败只能
   降低主张，不能声称项目整体完成。

---

## 6. 诚实评估:哪些是真创新,哪些是趋势跟随

| 项 | 定性 |
|---|---|
| **L1 置换等变 policy/value** | 核心创新候选；需 C0–C7 消融证明不可消融 |
| **L3b QAOA 多样化调度** | 核心创新候选；需 exact gap、端到端效果和学习反馈证据 |
| **L4a/L4b 原生门与含噪反馈** | 核心创新候选；需独立等价性、三类硬件路线证据及 held-out 闭环 |
| **L5a 布尔结构–资源图谱** | P1 探索性贡献；不计入本届竞赛核心创新 |
| L3a AlphaZero 内核 | **扎实但非范式级**。2017 年技术搬到新领域,必要但不足以撑起全部主张 |
| L2a GFlowNet | **原理性升级**,但 MOGFN 已存在,属正确应用 |
| L2b 扩散模型 | **趋势跟随**。与 L2a 目的重叠,二选一 |
| L3c 量子振幅估计 | 理论最强(可证二次加速)但 NISQ 上难兑现,**高风险** |
| L6 LLM 智能体 | **趋势跟随**。竞赛展示价值 > 学术价值 |

**竞赛叙事建议**：三项核心创新固定为 L1、L3b、L4a/L4b；L5b 是应用落点，
L5a 及其他生成方向只作赛后储备。

---

## 7. 立即行动

**推荐技术路线（待 D4 确认）：simulator-first，真机可选；不把真机列入最低
验收。** 报名状态、学校主体和 IP/人工提交字段必须在合规包冻结前由团队提供
可核对材料，不能只依据本规划文字判定完成。确认前继续暂停相关功能开发。

1. **【本周】** 组队(≤10 人),按 A/B/C/D 四轨分工
2. **【方向门】** D1–D4 获确认后，再按蓝图启动对应技术轨
3. **【环境门】** SDK 选型后先完成许可证、锁文件和干净安装验证，再搭建仿真环境

---

## 8. 评测协议(不可违反)

`summary_large_neural_prior.csv` 的 `all_scores_identical=True` 暴露:**portfolio guard 取多方法最优,系统性冲掉 AI 效果**。

任何新 AI 组件必须:在**叶子方法层面**报告(非 portfolio 之后)· 同时报 score **和**运行时 · 保留零收益的负面结果。

---

## 9. 新增参考文献

**闭环 / 量子辅助搜索**
- Quantum-enhanced Monte Carlo Tree Search framework for combinatorial optimization (AtomTreeSearch). arXiv:2606.30415 **← L3b 的直接依据**
- Quantum Policy Iteration via Amplitude Estimation and Grover Search. arXiv:2206.04741(可证二次加速,L3c 依据)
- Quantum RL with Dynamic-Circuit Qubit Reuse and Grover-Based Trajectory Optimization. arXiv:2509.16002(IBM Heron 真机)

**基础模型 / 表示**
- A Survey of Circuit Foundation Model. *ACM TODAES* (2025)
- The Dawn of AI-Native EDA: Opportunities and Challenges of Large Circuit Models. arXiv:2403.07257
- Hartford et al., Deep Models of Interactions Across Sets. ICML 2018(S_T×S_n 可交换矩阵层)

**生成模型**
- Jain et al., Multi-Objective GFlowNets. ICML 2023 **← L2a 依据**
- Synthesis of discrete-continuous quantum circuits with multimodal diffusion models. arXiv:2506.01666
- AC-Refiner: Arithmetic Circuit Optimization Using Conditional Diffusion Models. arXiv:2507.02598

**LLM 智能体**
- QAgent: LLM-based Multi-Agent System for Autonomous OpenQASM programming. arXiv:2508.20134
- AutoEDA: EDA Flow Automation through Microservice-Based LLM Agents. arXiv:2508.01012

**(其余见 `RESEARCH_PLAN_AI4Q_Q4AI.md` §7)**
