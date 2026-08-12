# XA-202609 项目当前状态总表

> 快照日期：2026-08-13
> 历史 Git 基线：`2d264f23bbdcfaf7bf844beefb7df58af90b7b37`
> 状态：**IN PROGRESS / formal v4 provenance 已闭环 / E4-v2 未支持改善 / E5 无已接受端点 / E6-D2 resource-gain teacher 已修复 source-label mechanism 但仍略弱于 greedy / 当前全套 631 项通过**
> 用途：回答“当前做什么、完成了什么、还缺什么、什么证据才算完成”
> 权威完成门：`../contracts/COMPETITION_ACCEPTANCE_MATRIX.json`

## 1. 当前结论

项目已有一个可工作的**逻辑层 Boolean Oracle 综合底座**，并新增了：

- 置换等变 policy/value 模型及 `foundation_nmcts` 开发入口；
- learned value 接入 NMCTS 的开发路径；
- random/top-B/greedy/exact 与 NumPy statevector QAOA 固定预算调度器；
- scheduler 到 NMCTS 独立根 action edge 的受控接入及 E2 冻结证据；
- 逻辑 X/CNOT/MCT OpenQASM 3 交换适配器；
- 独立于 `synthesize(...)` 的超导执行层：在 synthetic heavy-hex-like profile 上完成
  `rz/sx/x/cx` 精确分解、确定性最短路 SWAP、原生全基态等价和逐 shot Pauli
  trajectory；
- 冻结 calibration 模型接入 MCTS 根动作效用的 E3 最小反馈闭环；
- E4 已贯通 FIPS 197 AES S-box 8 坐标、同池 classical/QAOA 调度、逻辑验证、
  synthetic-profile 原生映射与逐 shot 含噪端点；
- E4-v2 已完成 12 个非 AES calibration 函数与 AES 8 坐标的四臂冻结复验；
- formal v4 从随机初始化训练，训练数据、排除集、命令、源码、日志、模型卡与
  checkpoint 已形成哈希闭环；
- E5 已保留首次 release 失败、v1.1 完整 90 行矩阵与事后负审计；协议验收失败，
  没有已接受的外部密码家族性能端点；
- E5 V3 可移植负审计在当前 Conda 与全新 venv 均通过 20/20，离散输出严格一致，
  仅白名单 learned continuous 字段出现受限数值漂移；该证据不改变协议失败；
- E6-MSO 多输出共享表达式 Boolean Oracle 已完成机制 MVP 与独立整改复审，并在
  代码提交 `e850c0c`、结果提交 `8cc5f3c` 上完成单研究者确定性四臂 development
  实验：64 个 n6/n7 training case、32 个 n4/n5 whole-vector heldout cluster；
- D1 将该 run 的失败定位到旧 action-marginal teacher；D2 在全新且三层 orbit
  不相交的 train/structured/OOD split 上只改用正整程序 resource-gain credit，
  structured/OOD 的 gain-QAOA 对 permuted control 分别为 `delta Y=-0.1688789442`
  （32/0/0）和 `-0.1535114735`（31/1/0）；
- 全新 CPython 3.11 venv 从 exact-pinned `dev.txt` 安装后通过 `pip check`、默认
  clean-install verifier、完整临时 demo 和隔离环境全套测试；
- fresh-validation V2 以外部 anchor SHA 约束 9/9 历史命令与 19/19 独立检查；锚定
  fresh venv 记录保持 383 项，且外部 anchor/bundle 已由内部审计包绑定；
- 权威内部审计 draft 共 366 文件，tar 为 4,665,696 bytes，目录与 tar 在
  poisoned-env 下均 PASS；tree digest 前后均为 `e850a3b9...` 且 cache 为 0，包内
  fresh-v2 原生复验 19/19，并绑定 8 个完整证据九件套；锁定 stdout 本机路径例外
  恰为 2 且不是运行依赖；外层 verifier 将 `XA_E5_PROJECT_ROOT` 重绑定到包内
  `experiments/`，污染环境回归已闭合；
- E6 四臂 bundle 从语料重建、四臂重训到 heldout 全链路的独立 verifier 11/11；
  所有语义检查通过且无 fallback/degraded。当前测试计数以本文件 4.5 节为准。

但完整竞赛原型尚未形成：

- E3 只覆盖 synthetic heavy-hex-like profile，且 held-out 主改善假设未获支持；
  没有真机、真实校准、离子阱/光量子执行链或三路线统一 manifest；
- E4 AES noisy endpoint 仅 5/4096 success，AES 尺度也未做逐 trial 原生全基态
  等价，不能支持性能改善；
- E4-v2 是 **post-E4 AES frozen replication**，AES 已在 E4 中出现，不能称
  held-out 或 generalization；其 primary native-2q CI 跨 0，不能支持改善；
- formal v4 只闭合训练 provenance，不是性能证据；E5-v1 首次 release 在首行前
  fail-closed，E5-v1.1 又因 ASCON 无可调度根动作而未通过 family-activity gate；
- E5 V3 只证明同一负结论跨 Torch/数值构建可复验；`protocol_acceptance=false`、
  `experiment_completed=false`，不能升级为性能、硬件或量子优势主张；
- E6-D2 的 resource-gain teacher 已将 QAOA source-label 关联转化为 structured/OOD
  的一致主效应，且语义 100%、0 fallback/degraded；但 QAOA 臂在两 split 上仍略弱于
  greedy anchor。这只是 development mechanism repair，不是 formal、generalization、
  performance 或量子优势证据，且不改写早期 legacy replay 的负结果；
- AES bit0 已封装为当前树单命令竞赛 demo，持久化输出与独立 verifier 已通过；
  clean install 也已在全新 venv 通过，内部审计 staging 的目录/归档复验已通过，
  但尚未绑定 clean frozen commit，且没有独立离线 fallback 资产；
- 最终包仍因人工授权/身份材料、final frozen model、accepted external performance
  evidence 与 clean frozen commit 缺失而 fail-closed；源码权属与许可证尚未闭环。

因此，当前准确定位是：

> **逻辑综合底座 + provenance-closed formal v4 候选 + 已验证的 QAOA 固定预算调度原型
> + synthetic-profile 原生/含噪反馈最小闭环 + 已验证语义与契约的 AES 端到端
> pilot；E3、E4-v2 均未证明反馈改善，E5 没有通过预声明验收门，E6-D2
> 修复了 resource-aligned replay mechanism 但尚未超过 greedy；真实
> 硬件、离线 fallback 和提交闭环仍未完成；当前树单命令 demo 与隔离 clean
> install 已实现并独立复验，但尚不构成冻结提交复现。**

## 2. 目标与方向门

推荐目标是“密码量子 Oracle 智能综合与资源评估原型”，包含三条技术轨：

1. 等变 policy/value 网络引导低资源 Oracle 综合；
2. QAOA 在固定预算下调度高效且多样的独立 MCTS 子节点；
3. 原生门转换、硬件 profile 和含噪仿真反馈。

**G0 参赛门已通过**：用户于 2026-07-28 确认已经报名并审核通过，并确认
接受“获奖团队与发榜单位共同拥有知识产权”的竞赛条款。报名表、学校和联系
方式属于私有提交材料，没有复制到公开工作树。既有代码的来源、许可证和
再分发权仍是独立合规事项，不能由该确认替代。

四项方向已经由用户给出的持续目标确认：

| 决策 | 推荐选择 | 状态 |
|---|---|---|
| D1 作品范围 | 密码量子 Oracle 综合与资源评估 | **CONFIRMED** |
| D2 模型定位 | 置换等变 policy/value，不称通用基础模型 | **CONFIRMED** |
| D3 QAOA 角色 | 固定预算 diversity batch scheduler | **CONFIRMED** |
| D4 硬件证据 | simulator-first，真机可选 | **CONFIRMED** |

新增六条扩展轨采用 D5：GFlowNet、离散扩散、QNN、Oracle 专用自研路由器、
受限 LLM Agent 和证据化 UI 全部推进到“实现 + 公平基线 + 可复现实验”；
只有跨过各自定量门的模块才进入最终核心创新，未过门的保留为负结果。

## 3. 仓库与运行入口

| 项目 | 当前事实 |
|---|---|
| Git 根 | 当前 `tzb/` 目录 |
| 工作目录 | `experiments/` |
| Python | `/opt/anaconda3/envs/mcts-qoracle/bin/python` |
| 公开 Python 入口 | `src/synthesizers.py::synthesize(...)` |
| 当前入口行 | `synthesize` 位于 `src/synthesizers.py:2024`（行号会随 E6 开发移动，以函数名为准） |
| 逻辑门域 | X / CNOT / MCT |
| 当前主环境直接加载依赖 | PyTorch 2.12.0、NumPy 2.4.6、SciPy 1.17.1 |
| 测试依赖 | pytest 9.0.3 |
| Qiskit / Aer | 当前未安装，不是现状依赖 |

当前逻辑数据流：

```text
BooleanFunction
→ Möbius 变换得到 ANF
→ 枚举 FactorAction
→ 启发式或 policy/value 打分
→ greedy / beam / NMCTS 构造 Plan
→ emit_plan_to_circuit
→ X/CNOT/MCT 逻辑线路
→ verify_oracle
→ SynthesisResult
```

逻辑 QASM 是尚未接入公开入口的独立分支：

```text
逻辑 QuantumCircuit
→ LogicalCircuitIR
→ OpenQASM 3 字符串
```

## 4. 当前确实能运行的能力

### 4.1 旧逻辑综合底座

当前公开入口仍支持 direct、greedy、beam、NMCTS、SSHR、ESOP 等历史方法。
旧结果和审计文件可用作回归资产，但不能证明新竞赛闭环完成。

### 4.2 等变 policy/value 开发入口

现有开发模块：

| 模块 | 当前用途 |
|---|---|
| `src/foundation/encoding.py` | ANF 项集和上下文转 `T×n×12` 张量 |
| `src/foundation/equivariant.py` | `S_T × S_n` 可交换矩阵主干 |
| `src/foundation/heads.py` | action policy 与 state value 头 |
| `src/foundation/adapter.py` | `FoundationScorer` 结构化适配器 |
| `src/search/value_net.py` | learned value、范围保护与缓存 |
| `scripts/train_expert_iteration.py` | 自博弈和 policy/value 联合训练 |
| `src/synthesizers.py` | `foundation_nmcts` 开发分发入口 |

2026-07-28 使用实际 v3 checkpoint、固定 paper weights、seed 3 和小规模
majority(4) 做了一次入口冒烟：

```json
{
  "method": "foundation_nmcts",
  "correct": true,
  "terms": 5,
  "gates": 9,
  "n_qubits": 6,
  "T": 48,
  "CNOT": 62,
  "depth": 62,
  "explicit_ancilla": 1,
  "peak_ancilla": 2
}
```

这只能证明“v3 能通过当前入口生成并验证一个逻辑线路”，不能证明模型优于
基线、跨尺度泛化或比赛效果。

v3 当前身份：

| 项 | 当前证据 |
|---|---|
| 状态 | development candidate，不是最终模型 |
| SHA-256 | `87904409966e6d9d18aae3711dff54d696608e6eefcf0e5cb5bb98ae96d4f57d` |
| 参数量 | 60,450 |
| 架构 | 12 输入通道、hidden 32、2 层、MLP hidden 128 |
| 支持门域 | 仅 `gate_mode="mct"` |
| 训练命令/seed/split/log/source SHA | checkpoint 中缺失 |
| 正式 C0–C7 结果 | 缺失 |

formal v4 训练 bundle 位于
`results/xa202609/20260812-foundation-v4-provenance-formal-s20260904/`。该模型从
固定 seed 的随机初始化开始，没有加载 v3；共 60,450 参数，训练/验证记录仅来自
`n=6,7` 的 208 个样本，完整排除注册的 4/5/8 比特密码输入宽度且未访问 evaluation
模块。checkpoint SHA-256 为
`5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7`，dataset SHA-256
为 `4b8e1e02d74f5ebd1d121431bca49266e39123c0b3d09c4e9d8967ebfa3af33f`；三轮训练中
第 1、2 轮通过内部验证门，第 3 轮被拒绝并回滚，独立 self-check 全部通过。

这使 v4 成为 **provenance-closed evaluation candidate**，但内部训练 holdout 只是
accept/reject gate，不是外部性能证据。E5 也没有产出被协议接受的外部密码端点，
所以 v4 目前不能称最终性能模型或通用基础模型。“参数和接口兼容可变 T/n”仍不
等于“已证明跨 n 或跨密码家族泛化”。

当前还存在五个需要在冻结前解决或显式限制的技术风险：

1. adapter 从当前 ANF terms/actions 的最高 bit 推断 `n`；声明但未出现在当前
   状态中的变量可能被漏掉，尺寸和密度通道会偏小；
2. learned value 的 direct-score 范围保护不是可采纳下界或最优性保证；
3. policy 排序发生在 `candidate_top_k` 截断之前，错误排序会真实缩小搜索空间；
4. action cache key 没有覆盖所有 config/weights；公开入口每次新建 scorer，
   但外部跨配置复用同一 scorer 需要清 cache；
5. formal v4 已闭合训练 provenance，但完整 C0--C7、独立盲测和 replay 因果消融
   仍缺失；不能用训练 holdout 或未通过 E5 验收的行升级性能主张。

### 4.3 逻辑 OpenQASM 3

`src/hardware/qasm.py` 当前能够：

- 校验 X、CNOT、MCT 逻辑门和量子位索引；
- 生成 OpenQASM 3；
- 将 MCT 保持为 `ctrl(k) @ x`；
- 输出逻辑门统计、最大控制数和需要 MCX 分解的标志；
- 主动拒绝伪造的 `gate_mode="native"`。

`qasm.py` 这一逻辑交换模块本身不能：

- 分解 MCT/MCX；
- 产生 Clifford+T 或设备原生门；
- placement、layout、routing 或 SWAP；
- 运行 ideal、shot 或 noisy backend；
- 生成物理资源、成功率或 fidelity；
- 把执行指标反馈给搜索。

该模块当前没有接入 `synthesize()` 或竞赛 CLI。E3 使用下述独立执行层处理逻辑
线路，没有静默改变已有 method 的逻辑成本模型。

### 4.4 E3 synthetic-profile 原生执行与反馈

`src/hardware/superconducting.py` 与 `src/hardware/noise.py` 已在 synthetic
heavy-hex-like profile 上实现：

- X/CNOT/MCT 到 `rz/sx/x/cx` 的精确分解，其中多控门使用 ancilla-free
  parity-phase 分解；
- 确定性最短路 SWAP 路由、终态 layout 解码和原生资源统计；
- 独立 statevector 全基态等价验证；
- 每 shot 实际运行的一/二量子位 Pauli trajectory 与 readout bit-flip，而非只对
  汇总概率做后处理。

`src/search/execution_feedback.py` 用 calibration 函数拟合冻结 ridge 执行成本模型，
再只在真值表不相交的 held-out 函数上调整 MCTS 根动作效用。两阶段正式证据为：

- calibration：
  `results/xa202609/20260811-e3-cal-native-feedback-v1-s310000/`，12 个 $n=4$
  函数、56 条根动作候选，独立 verifier `ok=true`；
- test：
  `results/xa202609/20260811-e3-test-native-feedback-v1-s410000/`，12 个不相交
  $n=4$ 函数、96 条配对 trial，96/96 通过 Plan、circuit、Oracle 与原生全基态
  等价检查，独立 verifier `ok=true`。

反馈确实改变了部分根动作与最终 Plan，但 `feedback_qaoa_shot` 相对
`historical_qaoa_shot` 的 Oracle task NLL 差为 `+0.001293`，按函数聚类的 95% CI
为 `[-0.001170, 0.004719]`，主改善假设未获支持。该结果证明的是 synthetic
profile 上最小反馈机制可执行且可审计，不是真机结果、真实设备校准、policy/value
更新、量子加速或量子优势。

### 4.5 当前测试

2026-08-13 实际执行：

```text
python -m pytest tests -q
631 passed in 411.04s
0 fail/error
submission targeted: 10/10 passed

python tests/tests_smoke.py
smoke ok (real 7.04s)

python scripts/verify_clean_install.py
ok=true (real 30.59s; hardware/performance=false)
```

当前测试已覆盖等变 policy/value、artifact contract、逻辑 QASM、经典 diversity
scheduler、QUBO 恒等式、ideal/shot/noisy NumPy QAOA、调度适配器及 NMCTS
独立子边接入，并新增原生分解、拓扑路由、全基态等价、逐 shot 门级噪声、冻结
反馈模型、E3 artifact contract、E4 AES bundle contract 与竞赛 demo 输出契约。
覆盖范围仍限于 synthetic profile；不覆盖真机、真实校准或离子阱/光量子执行链。

### 4.6 E4 AES 双向端到端 pilot

正式 bundle：
`results/xa202609/20260812-e4-aes-bidirectional-pilot-v1-s520000/`。它覆盖 FIPS
197 forward S-box 的 8 个坐标和 `classical_greedy/qaoa_shot` 两种变体，共
16 条 trial、4096 noisy shots。learned policy 在全部根节点启用，learned value
按 E1 门禁关闭；两变体使用同一冻结候选池和固定子边预算。QAOA attempted、
succeeded、direct 均为 8/8，0 fallback/repair。

16/16 trial 的 Plan ANF、circuit ANF、全真值表 Oracle、可逆目标语义、原生门集、
耦合约束均通过，独立 verifier 与 checksum 通过。冻结池 exact-objective hit 为
QAOA 8/8、greedy 3/8；两者选择在 5/8 坐标不同，最终 logical QASM 在 4/8
坐标不同，说明 Quantum for AI 调度干预真实发生并传到部分线路。

这些变化尚不能升级为性能主张。QAOA 相对 classical 的逻辑 score 高 0.448%，
配对 W/L/T 为 1/3/4；原生总门低 2.827%、原生二比特门低 3.229%，对应 W/L/T
均为 2/2/4。含噪成功计数仅 classical 2/2048、QAOA 3/2048，总计 5/4096，
统计信息过稀。AES 尺度没有逐 trial 执行原生全基态等价；逻辑语义已穷举验证，
原生层只支持声明范围内的门集/耦合契约与采样含噪端点。

### 4.7 竞赛单命令 demo

`scripts/demo_competition.py` 已接受矩阵规定的
`aes_sbox_bit0 / foundation_nmcts / qaoa_diversity / superconducting_noise` 参数，
从输入契约贯通 learned policy、direct QAOA 调度、逻辑语义、synthetic-profile
原生映射、seeded noisy trajectory 和人类可读报告。`scripts/verify_demo_output.py`
对 `experiments/demo/output/` 的 input、report、execution log、manifest、checksum
与内层证据 bundle 独立复验，13/13 checks 为 `true`。

该 demo 实际记录 QAOA direct non-fallback，同时明确
`hardware_execution=false`、`performance_evidence=false` 和
`quantum_advantage_claimed=false`；缩小后的演示数字只证明执行/验证契约，不能
替代 E4 正式性能证据。`tests/test_competition_demo.py` 已通过并纳入此前 557 项完整
通过基线；当前全套为 `631 passed in 411.04s`。
默认 clean-install verifier 已在隔离环境执行临时完整 demo；当前缺口是独立离线
deterministic fallback 资产和提交包验收。

### 4.8 E4-v2 execution-aware frozen replication

`src/search/execution_aware_utility.py` 已实现 root-only execution-aware utility：
对每个现有根 `FactorAction` 完成 scorer-free greedy rollout，先做 Plan/circuit ANF
验证，再在声明的 synthetic heavy-hex-like profile 上编译 native 1q/2q、SWAP、
depth 与 duration proxy；可选风险模型和惩罚权重均以 SHA 冻结。runner-facing
`RootRolloutExecutionUtilityAdjuster` 把同一 adjusted utility 提供给 classical 与
QAOA 根调度路径，不改公开 `synthesize(...)` 接口，也不接收 held-out noisy outcome。

`tests/test_execution_aware_utility.py` 已验证组件审计、zero-weight identity、候选
置换等变、profile/model SHA 绑定、非有限值与错位 fail-closed、root-only 边界、
rollout 语义，以及 classical/QAOA 共用 adjusted utility。唯一权威协议为
`configs/xa202609/e4_v2_execution_aware_v1.json` 及其 protocol lock；被替代的
noisy-primary 草案只作为明确标注的 test-only 回归夹具存在，不是可运行权威。

正式 calibration bundle
`results/xa202609/20260812-e4-v2-frozen-replication-v1-s530000-cal/` 覆盖 12 个
非 AES `n=8` 函数和 72 条候选记录，只使用 compile-time native proxy，未访问
replication/noisy outcome；权重与 protocol lock 均按 SHA 冻结，verifier `ok=true`。
正式 replication bundle
`results/xa202609/20260812-e4-v2-frozen-replication-v1-s530000-test/` 覆盖 AES 8
坐标 × 2 solver seeds × 4 arms，共 64 条 trial；32 条 QAOA 行全部
direct-unrepaired，0 repair/fallback，语义、同池、固定预算、原生/含噪契约和独立
verifier 均通过。

primary `execution_aware_qaoa_shot - historical_qaoa_shot` 的 native 2q 均值差为
`-513.9375`，按 AES 坐标聚类的 95% bootstrap CI 为
`[-2059.0625, 589.9375]`，W/L/T=`2/1/5`；secondary greedy 差为 `-1110.3125`，
CI `[-3176.3125, 514.4375]`，同样跨 0。noisy 端点 384 shots 中 0 success，只作
诊断。由于 AES 坐标已在 E4 中出现，本实验明确是 post-E4 frozen replication，
`generalization_claim=false`；统计不支持性能改善、硬件、量子加速或量子优势主张。

### 4.9 formal v4 与 E5 外部密码家族审计

E5-v1 的 preflight 与 seal 均通过：formal v4、12 行 `n=6,7` compile-only
calibration、固定 10q synthetic profile、冻结权重与未访问 ASCON/PRESENT 的边界
均有独立 verifier。首次 release 随后在 `ASCON bit0 / seed1` 的第一条 trial 上
fail-closed：结构动作池为空，旧 runner 错把“无需调度的 direct root”当成缺失
scheduler。该尝试 0 行完成、没有 endpoint 或性能结果，且 ASCON/PRESENT 表已在
release 时被加载，因此之后不能称 pristine unseen-table evaluation。

E5-v1.1 只修正 degenerate direct-root 的记账语义，保持 checkpoint、权重、搜索/
QAOA 预算、seed、五臂与 endpoint 不变。它产出 ASCON 5 坐标 + PRESENT 4 坐标 ×
2 seeds × 5 arms = 90 行完整矩阵，逻辑语义与 native 契约均通过；但 ASCON 的
可调度 group 为 0，PRESENT 仅 6 个，`each_family_has_schedulable_activity=false`。
因此 declared verifier 的 family-activity 与四臂公平验收为 false，
`experiment_completed=false`、`performance_claim_supported=false`。随后独立负审计
重建了 90/90 行并通过自身证据校验，但仍明确 `protocol_acceptance=false`；ASCON
primary 的 0 差与任何 PRESENT secondary 数值都不是已接受性能端点。

最终 V3 可移植负审计 bundle
`results/xa202609/20260812-e5-v11-portable-negative-audit-v3-s950000/` 在当前 Conda
与全新 venv 均通过 20/20，bundle snapshot 为
`4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea`。仅预先白名单的 learned continuous 字段按
`rtol=1e-6, atol=5e-6` 比较且必须有限，实测最大绝对/相对漂移为
`3.814697e-06`/`5.046907e-07`；候选结构/顺序、选择、QAOA 离散输出、Plan、QASM、
native、endpoint 与 summary 均严格一致。该证据只说明负审计不是单一 Torch 构建
的偶然产物，不改变 `protocol_acceptance=false` 或任何性能主张边界。

锚定 fresh-validation V2 bundle
`results/xa202609/20260812-e5-v11-portable-fresh-validation-v2-s970000/` 的 9/9 命令
和 19/19 独立检查通过；全新 venv 为 `383 passed in 295.779s`。bundle snapshot
为 `dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23`，外部 anchor
SHA 为 `036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686`。调用者必须
在 bundle 外保护该 anchor；现在已由
`docs/competition/submission/generated/ppt-cdb66ca7-pdf-f6a19cf8/XA-202609-internal-audit-draft/`
的外层 manifest 绑定。该 draft 共 366 文件，tar 为 4,665,696 bytes，SHA-256 为
`86b1b75b287ea2f7d042e388215168d96d2de2600d3731a6e6dbc07e82844e45`；目录与 tar
在 poisoned-env 下均 PASS，tree digest 前后均为 `e850a3b9...` 且 cache 为 0。包内
fresh-v2 原生复验 19/19，并收录 8 个完整证据九件套（V3、fresh-v2 与 6 个
predecessor/source/link）。全包只允许恰好 2 个锁定
stdout 本机路径例外，均位于历史 `raw.jsonl` 的 `stdout.text`，不是运行依赖。
外层包 verifier 还显式将 `XA_E5_PROJECT_ROOT` 重绑定到包内 `experiments/`，避免
继承测试收集或调用环境的污染值；对应 polluted-environment 回归已闭合。
这仍只是锚定树的软件/证据可移植性与 non-distributable internal staging 证明，
不是当前增量树的最终全套、最终可提交包或科学性能证据；final 仍因 7 份
人工授权/身份文档与 3 个固定技术 blocker（外部性能证据、final frozen model、
final model card）缺失而 fail-closed；仅当仓库 dirty 时再增加第 4 个
`repository_not_clean_frozen_commit` blocker。

### 4.10 E6-MSO：多输出共享表达式 Boolean Oracle

E6-MSO 从逐坐标 scalar ANF 转向 `VectorANF`，在多个输出间共享
monomial/semi-affine action，以 `compute–fanout–uncompute` 和最多 2 个 clean
ancilla 实现共享计算。机制 MVP 已通过独立复审：合法 partial-fanout、同池
conflict/QUBO、greedy/exact/QAOA、可行样本分账和 abstract logical X/CNOT/MCT
proxy 均有回归；该资源口径不是硬件编译成本。

在此基础上，代码提交 `e850c0c` 与结果提交 `8cc5f3c` 完成了极简单研究者
确定性 development 实验。一个 runner 按固定顺序训练四臂：random replay、greedy
repeated-selection replay、QAOA final-measurement replay 与 permuted-label control。
训练语料为 64 个 n6/n7 case；heldout development 评估为 32 个 n4/n5 whole-vector
cluster。head logits 只作 top-K 排序，后续 exact scheduler 使用四臂共用的原始解析
utility，避免把 logit 的任意平移混入 endpoint。

五文件 bundle 位于
`results/xa202609/20260812-e6-q4ai-causal-v1-full-s20260912/`，绑定 clean source
`e850c0c`，snapshot 为
`18b758ac3e432a5d4e9f0ba1f8be7e17bd1b848b6212234eea9d2e842d4cc76a`。

主比较 QAOA-control 的资源比 Y 差为 `+0.0949778`（越低越好），95% CI
`[0.0696384, 0.1237673]`，双侧 sign-flip `p=9.9999e-6`，W/T/L=`0/3/29`，
n4/n5 分层均为正，`claim_supported=false`。QAOA 与 random endpoint 32/32 相同，
且各有 31/32 空选择。random、greedy、QAOA、control 四臂 mean Y 依次为
`0.99917168`、`0.77563923`、`0.99917168`、`0.90419388`；greedy 不是等计算对照，
只作描述性信号。32/32 heldout cluster 的
语义检查通过且无 fallback/degraded。独立 verifier 11/11，通过重建训练语料、重训
四个 head、重跑 model→top-K→scheduler→emission→semantics→statistics 全链路。

该结果仅是固定训练语料、初始化与 seed 下的 synthetic development conditional
负证据；formal/performance/generalization/hardware/advantage 均为 false。runner 用时
140.32 秒，独立 full verifier 用时 145.03 秒；这些时间不是速度性能证据。它是诊断
基线而非可接受终点。D1 机制诊断只用于确定改法；随后必须实现 resource-aligned
QAOA replay，并在全新未调参 evaluation 上以匹配预算相对 strongest greedy 达到
paired `delta Y<0`、95% CI upper `<0`、语义 100%、0 fallback；不得在当前 heldout
上事后调参。
`598→581` 仍只保留为早期开发观察。

### 4.11 E6-D2：resource-gain replay teacher

D1 显示旧 QAOA action-marginal label 与 raw resource utility 反相关。D2 因而只做
一个机制变化：对每个 QAOA 最终测量 bitstring 计算正整程序 resource gain，将
`count × gain` credit 分配到其选中动作并归一化；control 对同一 source credit 做
固定动作置换。两个主臂均冻结 formal-v4 trunk、使用相同初始化、64 个训练 group、
1,024 次样本呈现、`value_loss_weight=0`，下游统一为 arm-neutral raw-utility exact
scheduler。

全新 train/structured/OOD seed 为 `20261011/20261012/20261013`，在 vector、
whole-vector cluster、orbit cluster 三层均 0 overlap，且没有复用旧 E6 heldout。
fresh structured expanded-cap256 中 `gain-QAOA - gain-permuted` 的资源比差为
`-0.1688789442`，W/T/L=`32/0/0`；structured diagnostics 完成后打开的 OOD endpoint
为 `-0.1535114735`，W/T/L=`31/1/0`。matched-6 view 只诊断 teacher/model 对齐，
expanded/OOD view 均不使用 teacher 标签。所有 endpoint 语义验证通过且
fallback/degraded 为 0。

gain-QAOA 的 structured/OOD 平均 `Y` 为 `0.7470455/0.8116278`，仍略高于 greedy
anchor 的 `0.7410552/0.7928633`。因此当前证据支持“resource-gain target 修复了
source-label mechanism”，不支持 strongest-greedy 性能提升。五文件 bundle 为
`results/xa202609/20260813-e6-d2-resource-gain-teacher-v1-full-s20261011/`，snapshot
`b16715196ff1e456184eaae6654f73f28c12454c5190d288384739f8bc1576c1`；
formal/performance/generalization/hardware/advantage 均为 false。

## 5. 核心技术轨状态

| 技术轨 | 状态 | 已有证据 | 关键缺口 |
|---|---|---|---|
| 等变 policy/value NMCTS | **provenance-closed candidate; performance unaccepted** | v3 pilots；formal v4 provenance；E6-D2 resource-gain teacher 在 fresh structured/OOD 上均优于 permuted control | D2 仍略弱于 greedy；E5 仍无 accepted endpoint，formal performance 与 final model 仍缺 |
| QAOA diversity scheduler | **implemented + validated local mechanism; endpoint improvement unsupported** | E2 420 trials、E4 8/8 direct、E4-v2 32 QAOA direct；E6-D2 source-label 主差 structured/OOD 均为负 | source-label mechanism 已修复，但尚未超过 greedy，也无等算力或 formal performance 证据 |
| native/noise feedback | **synthetic-profile minimum loop validated; improvement unsupported** | 超导原生分解/路由、逐 shot Pauli trajectory、E3 两阶段、E4-v2 compile-time execution utility | 真机/真实校准、离子阱/光量子路线、三路线 manifest；E3/E4-v2 改善区间均未过门 |
| E6-MSO 多输出共享 Oracle | **development mechanism repaired; performance unaccepted** | D2 64 train + 32 structured + 32 OOD；gain-QAOA 对 permuted 为 `-0.1688789442/-0.1535114735`，W/T/L=`32/0/0` 与 `31/1/0`；语义全过、0 fallback | 仍略弱于 greedy；formal performance、匹配预算和 final model 均未闭合 |

### 5.1 QAOA 当前事实

当前已实现：

- `src/search/diversity_scheduler.py`：random、top-B、greedy、exact、QUBO 构造与
  小规模全 bitstring 审计；
- `src/search/qaoa_scheduler.py`：固定深度 NumPy statevector ideal/shot/noisy
  QAOA，保留 direct、repair 与 fallback 分账；
- `src/search/mcts_scheduler.py` 与 `src/nmcts_solver.py`：把选中的动作作为独立
  根 action edge 分配 simulation，不生成破坏 Plan 语义的多动作计划；
- `scripts/run_qaoa_scheduler_pilot.py` 与冻结配置
  `configs/xa202609/e2_qaoa_scheduler_v1.json`；
- 证据 bundle：
  `results/xa202609/20260810-e2-qaoa-scheduler-v1-s120000/`。

E2 覆盖 held-out `n=8,9` 各 10 个函数、3 个 MCTS seed 和 7 种调度器，共
420 条 trial。QAOA 三种模式共 180 次调用、180 次成功、0 fallback；其中 ideal
25 次 direct、35 次 repair，shot/noisy 各 60 次 direct。全部 Plan ANF、circuit
ANF 与全真值表 Oracle 验证通过，QUBO 审计覆盖 20/20 个候选池，artifact verifier
为 24/24。

QAOA-shot 将 exact-objective 命中率从 greedy 的 65.0% 提高到 81.7%，regret 从
0.007694 降到 0.002288；但端到端资源分数相对 greedy 的函数簇比值为 0.999734，
95% CI `[0.998476, 1.000921]`，跨过 1。故当前只证明局部组合选择质量改善，
不证明稳定的最终 Oracle 资源收益、量子加速或硬件优势。E3 已把冻结执行校准
模型接入根动作 utility，但 held-out 含噪端点没有改善。E4 已完成 AES 8 坐标
复验并证明 QAOA direct 调度会改变部分最终线路；E4-v2 的 post-E4 四臂冻结复验
也已完成，但 native-2q primary CI 跨 0。E5-v1.1 没有通过 ASCON family-activity
验收门，因此当前仍没有被协议接受的外部密码端点。E6-D2 已在全新 split 上修复
resource-gain teacher 的 source-label 机制，但 gain-QAOA 仍略弱于 greedy anchor，
不能提升为性能或量子优势结论。

### 5.2 硬件三路线当前事实

| 路线 | 当前证据 | 完成门 |
|---|---|---|
| 超导 | synthetic heavy-hex-like profile 上的 `rz/sx/x/cx` 分解、最短路 SWAP、96/96 held-out 原生等价、逐 shot Pauli trajectory 和冻结根效用反馈 | E3-v2 原生特征、更大 held-out 干预、真实设备校准；当前主改善假设未获支持 |
| 离子阱 | 无 | 全连接 profile、RXX/MS 类资源映射、理想层等价 |
| 光量子 | 无 | capability/adapter/unsupported-boundary 表，不伪造统一门结果 |

三路线统一 manifest 尚未形成。真机不属于推荐最低完成门；如果以后获得真机
数据，只能独立标注为可选附录，不能反向把当前 synthetic profile 称为硬件实测。

## 6. 七类交付物状态

| 交付物 | 当前状态 | 当前证据 | 距离完成 |
|---|---|---|---|
| 可运行原型 | **partial validated in current tree** | `foundation_nmcts`、QAOA 根节点调度、E4-v2 四臂复验、逻辑 QASM、E3/E4 原生/含噪链路、单命令 demo、隔离 clean install，以及 E6-D2 resource-gain runner | E5 无 accepted endpoint；E6-D2 仍略弱于 greedy；仍缺离线 fallback |
| 可复现实验 | **partial** | E2、E3、E4、E4-v2、formal v4、E5 证据链与 E6/D2 五文件 bundle 均可核验；当前全套 `631 passed in 411.04s`，submission 10/10；锚定 fresh 记录为 383 项 | 三路线统一 manifest 未完成 |
| 完整源码与模型 | **incomplete** | 开发源码；formal v4 的数据/训练/源码/log/model-card/checkpoint 哈希闭环 | v4 尚无 accepted 外部性能端点；主要文件未冻结；许可证与再分发权未闭环 |
| 技术报告 PDF | **synchronized through E6-D2** | 39 页唯一中文主稿已吸收 E6 legacy 负结果与 D2 mechanism repair；PDF SHA-256 `f6826f61595e5a7de9b311a13e6027b061c99323fbbdc626196986a7c3cbda95`，Overleaf `cb6962eab16974ce7a5734ae43094a15abf99138` | formal/performance 边界已审校；旧内部审计包仍为 pre-E6 baseline |
| 安装使用文档 | **validated current tree; historical anchor retained** | exact-pinned requirements；当前全套 `631 passed in 411.04s`；锚定 fresh V2 为 9/9、383 tests、19/19，V3 为 20/20 | 内部包仍绑定 pre-E6-v2 的 407-test 交付基线 |
| 演示材料 | **partial validated** | 单命令 demo 与独立 verifier 13/13 通过；14 页 PPT 已同步 E6 legacy 负结果与 D2 mechanism repair，14/14 notes/[Sources] 与结构/渲染 QA 均通过，SHA-256 `fa7b319fa620a37a62302be24c04ed70fb432be91d7d0fafbd8cf2e08377412f` | 仍缺独立离线 fallback 资产与 final 分发授权 |
| 合规提交包 | **internal audit draft technical PASS; final fail-closed** | 权威 non-distributable staging 共 366 文件、4,665,696-byte tar；目录/tar poisoned-env verifier PASS；tar SHA `86b1b75b…`；tree digest `e850a3b9...` 前后一致且 0 cache；包内 fresh-v2 19/19 | 缺 7 份人工授权/身份文档与 3 个固定技术 blocker；仓库 dirty 时另加第 4 个；不能作为最终可提交包分发 |

日期说明：当前主稿内容与 PDF 已更新至 2026-08-13；封面保留的
`2026-08-12` 是竞赛稿登记日期，不随后续修订日期滚动。

七项必须全部有可检查证据；任一单测、旧论文或逻辑 QASM 都不能代表整体完成。

## 7. 实验资产现状

当前 XA 结果与历史结果已物理分离：

| 位置 | 数量 | 含义 |
|---|---:|---|
| `experiments/results/xa202609/` | 当前证据与明确失败/未验收 bundle | P0/E1、E2、E3、E4、E4-v2、formal v4、E5 链与 E6 五文件 development bundle；完成性必须读对应 verifier，不能按目录存在判断 |
| `misc/archive/experiments/xa202609-development/` | 探索、被替代和首次 release 失败记录 | 参数/阈值扫描、被替代配置及 E5-v1 首次 fail-closed 记录；只读 provenance |
| `misc/archive/experiments/resource_nmcts-results/` | 891 个平铺文件 | 旧逻辑综合、外部基线、论文和提交审计资产 |

旧结果可以保护旧行为、提供基线候选和复用分析工具；它们不能证明 XA 的等变
模型正式泛化、真机/三路线执行闭环，也不能代替 E2/E3 或 XA 最终 manifest。

## 8. 版本控制、环境和合规状态

E6 legacy 实验的源码与结果提交为 `e850c0c` 和 `8cc5f3c`；D2 普通开发代码由
`46a370f`/`51288b1` 收口，五文件结果提交为 `5da75a4`。本轮文档/主稿
同步完成后应直接提交并以 `git status --short` 验证干净，单研究者开发只采用普通
Git 与五文件结果合同：

- 目录已分为 `docs/`、`experiments/`、`misc/`；历史平铺结果和旧投稿包已移入本机归档；
- `docs/competition/report/` 已有可编译草稿，`experiments/demo/` 已有实跑输出和
  verifier；内部审计 draft 已形成并通过目录/归档技术复验，但 final 模式仍 fail-closed；
- XA 新实验只写入 `experiments/results/xa202609/<run_id>/`。

环境：

- `experiments/environment/requirements/{core.txt,dev.txt}` 固定当前 CPython 3.11
  核心/测试 exact pins，`quantum.txt` 与 `optional-sshr-gurobi.txt` 是明确可选分组，
  `README.md` 给出 venv/Conda 命令；`environment/environment.yml` 与核心 pins 对齐；
- 当前仍无通用 lockfile、`pyproject.toml` 或 Dockerfile；当前树 fresh-validation 已通过，
  外部 anchor 已由内部审计 manifest 绑定，但安装证据尚未绑定 clean frozen commit；
- `misc/archive/external-tools/` 中的环境文件不能作为项目安装方式；
- 当前公开入口因 eager imports 同时需要 PyTorch、NumPy 和 SciPy；
- Qiskit、Aer、Gurobi 均不在主环境。

E2 QAOA 使用主环境中的 NumPy statevector 后端，不依赖 Qiskit/Aer。备用 `sshr`
环境中偶然存在 Qiskit 2.4.1 和 Aer 0.17.2，但仓库当前没有调用，也没有锁文件
或许可证清单；这不能算硬件仿真 SDK 已选型或原生执行环境已准备。

合规：

- 没有经权利人批准的项目 `LICENSE`；
- 旧元数据中的 MIT 声明不能构成授权；
- `src/sshr_lib` 的仓库内部迁移链已确认，但初始来源、权利归属和再分发授权
  待人工确认；
- 已跟踪的旧提交元数据含真实身份字段，最终源码包必须隔离；
- v3 没有完整训练 provenance；formal v4 已闭合技术 provenance，但 v3/v4 的最终
  再分发批准与许可仍缺失；
- 旧论文 tar 不能复用为竞赛包。

## 9. 证据等级

后续状态更新统一使用以下等级：

| 等级 | 含义 | 当前例子 |
|---|---|---|
| A-install 软件安装验收（范围受限） | 全新隔离环境、exact pins、`pip check`、SHA-aware 安装 verifier 与全套测试通过 | 历史快照为 217 passed；锚定 fresh V2 为 383 passed、19/19，V3 跨构建为 20/20；当前开发树为 `631 passed in 411.04s` |
| A-full 已冻结可复现 | 固定 commit/依赖/数据/seed、原始结果和 verifier 全通过 | 当前仍无完成冻结 commit 的 XA 全项目复现 |
| B 当前树实测 | 当前工作树可运行，有明确命令和输出 | E6-D2 五文件 development bundle；E6 legacy verifier 11/11；E2/E3/E4/E4-v2 verifier；formal v4 self-check；E5 V3 portability（20/20） |
| C 开发记录 | 有可复验开发结果，但未跨性能门 | E6 legacy 负基线与 D2 mechanism repair；E6-MSO prototype 598→581；E5-v1.1 未接受 effect estimates |
| D 设计/实现中 | 只有规格或尚未闭环的改进实验 | E6-D2 matched-compute formal evaluation；离子阱/光量子路线、三路线 manifest |
| E 人工确认 | 必须由团队、学校或权利人批准 | 报名与竞赛 IP 条款已确认；许可证、`sshr_lib` 初始来源仍待确认 |

最终报告的主要数值必须达到 A；B/C 只能作为开发过程记录，D 不能写成已实现。

## 10. 已确认的执行顺序

1. **M1 AI provenance（formal v4 已闭环）**：保持唯一 v4 candidate、训练/数据/
   source/log/model-card SHA；下一门是独立、协议接受的性能评价，不把内部 holdout 当结果；
2. **M2 QAOA 调度（E2 pilot 已通过）**：保留当前经典/QAOA/独立子节点证据；
   E3 没有改善 held-out 端点；E6-D2 修复 teacher mechanism 但仍略弱于 greedy；
3. **M3 E4-v2（formal replication 已完成，改善未获支持）**：保留 post-E4、
   `generalization=false`、primary CI 跨 0 和 noisy 仅诊断的完整边界，不再把它列为
   待运行 held-out 实验；
4. **M4 E6-MSO 多输出共享 Oracle（机制、legacy 对照与 D2 修复已完成）**：VectorANF、共享
   action、compute–fanout–uncompute、2 clean ancilla 语义、同池 conflict/QUBO 与
   deterministic replay→trainer→endpoint 链已闭环；D2 source-label mechanism 已修复；
5. **M5 E6 formal performance（当前最优先）**：在新数据上以匹配预算 strongest greedy
   检验 D2，要求 paired `delta Y<0`、95% CI upper `<0`、语义 100%、0 fallback；
6. **M6 AES/E5 证据表达**：保留 E4 的受限正/负证据和 E5 的失败/未验收事实；
   CLI/demo 已独立复验，继续完成离线 fallback；
7. **M7 交付整理**：clean install、跨构建审计与内部目录/tar verifier 已完成；当前
   实验先保持普通 Git 提交和干净工作树，最终提交包、离线 fallback 与人工授权/许可/IP
   材料在性能门通过后集中处理；
8. 离子阱、光量子及三路线统一 manifest 在主线闭环后补齐；它们当前未完成，
   不作为 E3-v1 已验证范围。

GFlowNet、扩散模型、QNN、Oracle 专用路由器、受限 LLM Agent 和 UI 作为
可淘汰实验轨并行推进；它们不因“已经写入计划”而自动成为核心创新。

## 11. 相关权威文档

- 统一目标与实验：`PROJECT_BLUEPRINT_XA202609.md`
- 已确认方向：`ARCHITECTURE_DECISIONS_XA202609.md`
- 完成门：`../contracts/COMPETITION_ACCEPTANCE_MATRIX.json`
- 技术候选规格：`TECHNICAL_DESIGN.md`
- 模型卡：`experiments/models/MODEL_CARD_boolean_oracle_fm_v3.md`
- 合规审计：`COMPLIANCE_READINESS_XA202609.md`
- 依赖与代码谱系：`DEPENDENCY_PROVENANCE_DRAFT_XA202609.md`

本文件只描述当前证据，不把设计或计划写成已实现功能。
