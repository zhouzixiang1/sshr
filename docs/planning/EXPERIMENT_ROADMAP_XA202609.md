# XA-202609 后续实验推进路线

> 状态日期：2026-08-12
>
> 推进原则：在保证证据质量的前提下尽快形成可交付闭环，不以固定日期或版本号
> 切断迭代
>
> 工作目录：`experiments/`
>
> 新实验输出：`experiments/results/xa202609/<run_id>/`

## 1. 核心论点与边界

本项目要证明的是：在严格 Boolean Oracle 等价验证约束下，置换等变
policy/value 能改善 Neural MCTS 的资源—时间折中；QAOA 可作为固定预算的
多样化子节点调度器；逻辑线路可在明确硬件 profile 下完成原生映射、理想等价
验证和含噪仿真反馈。

边界：当前已有逻辑层综合底座、开发态 policy/value、逻辑 QASM，以及通过 E2
验证的固定预算经典/QAOA scheduler 与 NMCTS 独立子边接入。E2 只支持“QAOA
改善冻结候选池中的局部组合目标”；其端到端资源 CI 跨过 1。E3 已在 synthetic
heavy-hex-like profile 上形成超导原生分解、路由、逐 shot Pauli trajectory 和冻结
根效用反馈的最小闭环，但 held-out NLL 差为 `+0.001293`，95% CI
`[-0.001170, 0.004719]`，主改善假设未获支持。仍不得使用“量子优势”“量子加速”、
“真机效果”“通用基础模型”或“完整三路线硬件闭环”等表述；真机、真实校准、
离子阱/光量子路线、三路线统一 manifest 和 policy/value replay 均未完成。

E4 已将 FIPS 197 AES S-box 8 坐标贯通到 learned-policy 同池调度、逻辑验证、
synthetic-profile 原生映射与逐 shot 含噪采样：16 条 trial 全部通过语义/门集/耦合
与 bundle 校验，QAOA 8/8 direct、0 fallback。该 pilot 的 noisy success 只有
5/4096，且 AES 尺度没有逐 trial 原生全基态等价，因此只证明链路可执行和调度
干预真实发生，不支持性能改善或硬件优势。

formal v4 已从随机初始化完成 provenance-closed 训练，checkpoint、数据、排除集、
命令、源码、日志和模型卡均以 SHA 绑定；这只建立模型身份，不是性能证据。
E4-v2 的正式结果是 post-E4 AES frozen replication，而不是 held-out：64 条四臂
trial 与 verifier 通过，但 native-2q primary 差 `-513.9375` 的 95% CI
`[-2059.0625, 589.9375]` 跨 0。E5-v1 在首次 release 的首行前 fail-closed；
v1.1 虽保留 90 行完整矩阵并由事后负审计重建，ASCON 可调度 group 为 0，未通过
family-activity gate。因此没有 E5 accepted endpoint，ASCON/PRESENT 已观察后只可
作为 development 资产。最终 V3 跨构建负审计在当前 Conda 与全新 venv 均为
20/20；learned continuous 最大绝对/相对漂移为 `3.814697e-06`/`5.046907e-07`，
其余离散选择与下游工件严格一致。该可移植性结果只加固负结论，仍为
`protocol_acceptance=false`，不支持性能、硬件或量子优势主张。

## 2. 立即冻结的范围

竞赛 P0 只保留四条主链：

1. 等变 policy/value Neural MCTS；
2. QAOA fixed-budget diversity scheduler；
3. 超导 simulator-first 原生门/路由/噪声反馈，辅以离子阱资源映射和光量子
   capability boundary；
4. AES/SM4/PRESENT/ASCON 等密码 Oracle 案例及单命令演示。

GFlowNet、离散扩散、QNN、LLM Agent、Web UI 和自研 router 暂停进入主线。
只有 P0 形成完整 raw/summary/manifest/verifier 后，才允许恢复其中一条扩展轨。

## 3. 阶段与验收门

### P0-A：接手冻结与实验契约（基础契约已完成，最终冻结待 clean Git）

任务：

- 明确新私有竞赛仓库与旧 `sshr` 远端的关系，不把当前竞赛代码推到旧公开远端；
- 将当前开发源码、专项测试和唯一候选 checkpoint 纳入可审查版本；
- 保持 `../contracts/COMPETITION_ACCEPTANCE_MATRIX.json` 与状态文档一致；
- 固定 Python、依赖、CPU/GPU、Git SHA、资源权重与随机种子记录；
- 定义 `DetailedSynthesisResult`、`PlanTrace` 和 `ExperimentManifest`，保留 Plan、
  线路、搜索轨迹、验证结果和 provenance；
- 所有新 runner 写入本路线规定的独立 run 目录。

验收产物：

- core tests 与 smoke 全通过；
- `p0-freeze` run 目录包含完整 manifest、verifier 和 checksums；
- 从空输出目录可重复生成同一小样例；
- Git 状态与目标 remote/branch 有明确记录。

停止条件：基础测试、语义验证或输出追溯任一失败时，不启动大矩阵实验。

### P0-B：先判定 AI 是否真的有效（pilot 已完成）

按顺序运行三个小实验：

1. **Prior diagnostic**：`shuffled / model / rollout-oracle` 同实例、同预算比较；
2. **Value diagnostic**：value head 同时对比部署时 greedy target、训练时
   MCTS-achieved target 和 constant predictor；
3. **C0–C7 pilot**：`n=6,7,8` 小样、至少 2 个 MCTS seed，验证 policy、value、
   progressive widening 的因果拆分和结构化输出。

验收门：

- 所有线路正确率 100%；
- model prior 必须稳定优于 shuffled，且报告其捕获 oracle headroom 的比例；
- value head 必须优于 constant predictor，并明确训练/部署 target drift；
- C5 相对 C0/C6 的质量、时间、节点数和模型调用均可追溯。

降级：若 prior 不优于 shuffled，停止扩大训练，先修数据/动作排序；若 value 不优于
constant 或 target drift 明显，关闭 learned value，保留 policy-only；若 C5 无稳定
净收益，不把等变模型列为核心创新。

### P0-C：formal v4 provenance 已闭环；C0–C7/外部性能门仍进行中

- 先用验证集选择 simulation budget 和 `widen_c`，随后冻结配置；
- 主矩阵：135 个非密码函数 × C0–C6 × 3 seeds，共 2,835 次求解；
- C7 仅跑诊断子集；
- ID、OOD、结构化函数和 AES 坐标分表，不混合平均；
- 报告 score、T、CNOT、depth、ancilla、wall time、节点数、模型调用、W/L/T、
  配对均值/中位数和 95% bootstrap CI；
- formal v4 已形成唯一 provenance-closed evaluation candidate：从随机初始化、
  `n=6,7` 的 208 条记录、完整密码宽度/真值表排除、训练命令/seed/source/log/
  model-card/checkpoint SHA 与 CPU 单线程合同；checkpoint SHA 为
  `5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7`；
- 下一门仍是完整 C0–C7 与独立协议评价。训练 holdout 和 E5 未接受行都不能作为
  v4 性能证据。

验收门：完整 raw/summary/manifest/verifier/checksum；空目录重跑通过；每个摘要数
可回溯到 raw 行。

### P0-D：QAOA diversity scheduler（E2 受限验证已完成）

已完成：

1. 冻结 candidate pool、utility、redundancy、`B_requested=4`、`B_eff` 与 `K=10`；
2. random、top-B、greedy、exact 四条经典路径；
3. 小 K 全 bitstring 罚项能量恒等式、固定基数排序和 exact 最优解审计；
4. ideal、shot、noisy NumPy statevector QAOA，分别记录 direct、repair、fallback；
5. 将选出的 B 个动作作为彼此独立的 MCTS 根 action edge 接入，每次 simulation
   只评估一个 edge，排除 edge 访问数保持为 0；
6. 冻结 E2 bundle、manifest、checksums 与 24/24 verifier。

E2 使用 `n=8,9` 各 10 个 held-out 函数、3 个 MCTS seed、7 种调度器，共 420
条 trial；三种 QAOA 模式共 180 次调用、180 次成功、0 fallback。QAOA-shot
把 exact-objective 命中率从 greedy 的 65.0% 提高到 81.7%，objective regret
从 0.007694 降到 0.002288；但端到端资源分数相对 greedy 的函数簇 95% CI
`[0.998476, 1.000921]` 跨过 1。

因此 E2 已从 missing 转为“已实现并完成受限验证”，但不能声称稳定端到端收益。
E3-v1 已把冻结的原生/含噪执行校准模型接入 utility，但 held-out 端点没有改善。
E4 已完成 AES 8 坐标同池复验，QAOA attempted/succeeded/direct 为 8/8/8，
0 fallback/repair；冻结池 exact-objective hit 为 8/8，高于 greedy 的 3/8，但
逻辑 score 高 0.448%，没有形成端到端收益。E4-v2 execution-aware 四臂冻结复验
也已完成：32 条 QAOA 行全部 direct-unrepaired、0 fallback/repair，但 primary
native-2q CI 跨 0。它是 AES 已在 E4 出现后的 replication，不能改写为 held-out
或 generalization。剩余核心任务是 E6-MSO 的同池 QAOA 与 policy/value replay；
不用经典 fallback 成绩冒充 QAOA 成绩，也不把 E3/E4/E4-v2 负向端点改写成改善。

### P0-E：原生门、路由与噪声反馈（E3/E4-v2 均完成受限检验，改善未获支持）

E3-v1 已完成：

- 保持 `synthesize(...)` 的 X/CNOT/MCT 逻辑核心不变，在独立执行层完成
  `rz/sx/x/cx` 精确分解与 synthetic heavy-hex-like profile 上的确定性最短路 SWAP；
- 在加噪前做独立 statevector 全基态等价验证，held-out test 为 96/96；
- 实际逐 shot 运行一/二量子位 Pauli trajectory 与 readout bit-flip；
- calibration 与 test 真值表隔离，只从 calibration 拟合并按 SHA 冻结 ridge 模型，
  test 端不重拟合且不把 test outcome 用入 utility；
- calibration bundle：
  `results/xa202609/20260811-e3-cal-native-feedback-v1-s310000/`；
- test bundle：
  `results/xa202609/20260811-e3-test-native-feedback-v1-s410000/`；
  两个独立 bundle verifier 均为 `ok=true`。

E3-v1 主比较中，反馈相对历史 QAOA-shot 的 NLL 差为 `+0.001293`，按 12 个函数
聚类的 95% CI 为 `[-0.001170, 0.004719]`。反馈改变了部分根选择与 Plan，但没有
支持含噪端点改善主张。

E4-v2 已把 native 2q count 与 native depth 的 compile-time proxy 写入共享根
utility。calibration 只覆盖 12 个非 AES `n=8` 函数和 72 条候选，未访问 noisy/
replication outcome；随后在 E4 已出现过的 AES 8 坐标、2 seeds、4 arms 上完成
64 条 frozen replication。两个 bundle 的独立 verifier 均 `ok=true`，32 条 QAOA
行全部 direct-unrepaired；primary native-2q 差 `-513.9375`，95% CI
`[-2059.0625, 589.9375]`，不支持改善。noisy 384 shots 为 0 success，只作诊断。

因此该阶段下一步不是重复 E4-v2，也不是把 AES 称为新 held-out。execution-aware
feedback 暂保留为经审计的受限机制；policy/value replay 必须在 E6-MSO 中作为独立
因果阶段验证，不把“接入根效用”写成“模型已学习执行反馈”。若以后重新检验原生
端点，必须使用锁后生成、此前未见且不按 candidate 可用性筛选的新实例。

离子阱全连接/RXX-MS 映射、光量子 capability boundary 和三路线统一 manifest
仍未完成；真机与真实设备校准也不在 E3-v1 证据范围内。

后续原生端点验收门：语义正确率 100%；逻辑、原生和含噪指标分栏；超时、路由失败和
不支持实例显式计数；预注册的 held-out CI 支持改善才升级主张。若分解规模爆炸，
限制实验规模，不伪造大规模物理结果。

### P0-F：密码案例与端到端演示（E4 已完成；E5 无 accepted endpoint）

- AES S-box 8 个坐标已冻结；ASCON/PRESENT 已被 E5 release 观察，后续只作
  development，不再称 unseen holdout；
- 每个案例输出 logical plan/QASM、native QASM、资源指标、验证结果和 trace；
- 已用单命令贯通输入 → policy/value NMCTS → scheduler → 验证 → native/noise →
  报告，并用独立 verifier 复验持久化输出；
- 待补完全离线的 deterministic fallback 资产，并与真实 QAOA 结果分开标记。

E4 正式 bundle
`results/xa202609/20260812-e4-aes-bidirectional-pilot-v1-s520000/` 已完成：FIPS
197 S-box 8 坐标 × classical/QAOA 两变体共 16 trials、4096 shots；全部逻辑
语义、原生门集、耦合约束和 bundle verifier/checksum 通过。QAOA 8/8 direct，
selection 在 5/8 坐标改变并传到 4/8 logical QASM；QAOA 相对 classical 的
逻辑 score 为 +0.448%，原生总门为 -2.827%，原生二比特门为 -3.229%。配对样本
很小，noisy success 仅 classical 2/2048、QAOA 3/2048，不能据此声称改善。

当前树竞赛 demo 已接受验收矩阵规定的 AES bit0、`foundation_nmcts`、
`qaoa_diversity` 和 `superconducting_noise` 参数，实际执行 direct QAOA、无
fallback，并产出固定 input、机器/人读报告、日志、manifest、checksum 和
verification。独立 verifier 13/13 通过；输出明确 `hardware=false`、
`performance_evidence=false`。clean install 已在全新 CPython 3.11 venv 中通过；
直接剩余项是绑定最终冻结 commit 和补独立离线 fallback 资产。E4-v2 已正式运行
但只支持 post-E4 replication 的负向边界。

E5-v1 的 preflight/seal 通过后，首次 release 在首条 ASCON direct-root case 上因旧
scheduler-presence 契约 fail-closed，0 行完成、无 endpoint。v1.1 在不改变模型、
权重、预算、seed 与五臂的前提下补齐 90 行 ITT 记账；其 declared verifier 因
ASCON `schedulable_group_count=0` 和 family-activity gate 失败而 `ok=false`。独立
negative audit 证明 90 行可按事后归一化契约重建，但仍明确
`protocol_acceptance=false`、`performance_claim_supported=false`。因此 E5 的
ASCON primary 0 差和 PRESENT secondary 均不得进入 accepted performance claims。

V3 可移植负审计
`results/xa202609/20260812-e5-v11-portable-negative-audit-v3-s950000/` 已在当前
Conda 与全新 venv 各自通过 20/20，bundle snapshot 为
`4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea`；仅白名单 learned continuous 字段允许有限值
`rtol=1e-6, atol=5e-6` 容差，候选结构/顺序、选择、QAOA 离散输出、Plan/QASM/
native/endpoint/summary 均严格一致。锚定 fresh-validation V2
`results/xa202609/20260812-e5-v11-portable-fresh-validation-v2-s970000/` 完成 9/9
命令、全新 venv 383 项测试与 19/19 独立检查；bundle snapshot 为
`dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23`，外部 anchor
SHA 为 `036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686`。下一步只
将 anchor 与 8 个完整证据九件套（V3、fresh-v2 与 6 个 predecessor/source/link）
纳入内部 submission 外层 manifest，现已完成。
内部 draft
`docs/competition/submission/generated/ppt-cdb66ca7-pdf-f6a19cf8/XA-202609-internal-audit-draft/`
共 366 文件；tar 为 4,665,696 bytes，SHA-256 为
`86b1b75b287ea2f7d042e388215168d96d2de2600d3731a6e6dbc07e82844e45`；目录与 tar
在 poisoned-env 下均 PASS，tree digest 前后均为 `e850a3b9...` 且 cache 为 0；包内
fresh-v2 原生复验 19/19。锁定 stdout 本机路径例外恰为 2，且仅是不可变历史输出
字节，不是运行依赖。该内部验收不等于冻结 commit、最终可提交包或科学性能端点。

### P0-G：E6-MSO 多输出共享表达式（当前核心实验方向）

1. 用 `VectorANF` 表达多输出 Boolean Oracle，在输出坐标之间枚举共享 monomial 与
   semi-affine action；
2. 以 `compute–fanout–uncompute` 和最多 2 个 clean ancilla 发射线路，逐输入验证
   所有输出与 ancilla 回零；
3. 在同一候选池上建立 conflict-aware QUBO，固定 pool、utility、redundancy、K/B、
   simulation 与 seed，公平比较 greedy、exact、QAOA；
4. 隔离 v2 已实现冻结 formal-v4 scalar trunk 的 output/input/candidate-equivariant
   shared policy/value thin head，以及带 split registry/外部锁的最终测量 replay 结构
   合同；下一步接入严格 head-only trainer，训练/封印 head，再用真实等预算 QAOA
   最终测量 bitstring-count observation 做因果消融，不能把它称为 optimizer trajectory；
5. ASCON/PRESENT 只作开发调试。正式盲测在 protocol lock 后由 SHA 派生此前未见的
   `n=4/5` 双射 S-box；抽样不能按 candidate pool 是否非空筛选，degenerate case
   必须进入 ITT 记账；
6. mechanism MVP 已实现并通过独立整改复审：partial-fanout 枚举、纯冻结 QUBO
   phase、可行样本后筛选/repair/fallback、解析罚项门和抽象资源口径均有回归；
   isolated v2 head/replay 也只承认开发接口合同。`598→581` 是 prototype 观察，
   不进入报告结果表。

E6 验收门：多输出语义 100%；共享 action、uncompute 与 ancilla contract 可重建；
classic/exact/QAOA 同池同预算；direct/repair/fallback/degenerate 完整分账；冻结
training/replay/evaluation split；九件套 bundle 与独立 verifier。未跨门时不升级
AI4Q/Q4AI 性能主张，更不声称真机、量子加速或量子优势。

### P0-H：报告、PPT、演示和提交冻结（与 E6 并行）

- XA 专用中文技术报告，不复用旧论文包冒充竞赛报告；
- 每个数字绑定 evidence manifest；
- 安装文档已在全新 CPython 3.11 venv 逐条执行，默认 verifier `ok=true`；证据已
  进入内部审计包，最终仍需绑定 clean frozen commit；
- 基于既有竞赛模板完成 5–10 分钟 PPT，使用同一 claim-to-evidence 数字；
- demo 脚本、固定样例输入/输出与独立 verifier 已完成；待补离线 fallback 资产；
- 366 文件内部白名单 staging、manifest/checksums、SBOM-LITE、provenance/status 已生成；
  目录与 tar poisoned-env verifier 均 PASS，tree digest 前后一致、0 cache，包内 fresh-v2 为 19/19；
- 外层 package verifier 将 `XA_E5_PROJECT_ROOT` 显式重绑定到包内 `experiments/`，
  不继承测试收集或调用环境的污染值；polluted-environment 回归已闭合；
- final 模式继续因人工授权/身份材料、final frozen model、accepted external performance
  evidence 与 clean frozen commit 缺失而 fail-closed；权威计数为 7 份人工授权/身份
  文档与 4 个技术 blocker，该 draft non-distributable。

进入最终候选阶段后只允许修复、复验、补人工字段和打包；在此之前，所有已经
通过验收门的实质结果应立即进入唯一中文主稿、Overleaf 和 PPT，不等待人为版本号。

## 4. 下一批立即执行的实验

| 顺序 | Run track | 目的 | 当前入口 | 阻塞 |
|---:|---|---|---|---|
| 完成（机制层） | `e6-mso-mechanism` | 完成多输出共享表达式、显式 workspace peak≤2 与 compute–fanout–uncompute 语义闭环 | mechanism MVP 已实现并独立复审；109 项相关回归和 smoke 通过；598→581 仅开发观察 | 无 formal runner/result；不能只降低 `min_factor_count`，也不能把抽象 MCT proxy 写成硬件资源 |
| 2 | `e6-mso-shared-policy-qaoa` | 建立 output-equivariant AI4Q 与同池等预算 Q4AI | isolated frozen-formal-v4 shared head 与 final-measurement replay 外锁/split 合同已实现并测试 | active head-only trainer、训练/封印 checkpoint、真实四臂 replay、公平预算和因果消融 |
| 3 | `e6-mso-blind-bijection` | 在未见多输出双射 S-box 上做正式验收 | 待 protocol lock | 锁后 SHA 派生 n4/5 双射；不按 candidate 筛选；九件套 bundle/verifier |
| 4 | `e1-c0c7-full` | 冻结最终 AI for Quantum 核心证据 | formal v4 provenance 已闭环，旧 pilot/policy gate 已完成 | 完整 C0–C7 与 accepted external performance gate |
| 5 | `ppt-demo-final` | 从同一证据链维护答辩 PPT 与演示交付 | 中文主稿、E1--E4 bundle、已验证 demo/clean install | 吸收 E4-v2/E5 负向边界和后续 E6 有效证据；离线 fallback/冻结绑定 |
| 6 | `p0-freeze-final` | 固定环境、SHA、权重、语义回归 | `scripts/run_p0_freeze.py` | clean Git 与最终依赖 |
| 完成 | `e2-scheduler` | 经典四路与 QAOA 公平比较 | `scripts/run_qaoa_scheduler_pilot.py` | 420 trials；24/24 verifier；端到端 CI 跨 1 |
| 完成但不升级主张 | `e3-native-feedback-v1` | synthetic-profile 原生/含噪反馈最小闭环 | calibration/test 两阶段 bundle | 96/96 原生等价；NLL `+0.001293`，CI 跨 0；改善未过门 |
| 完成但性能证据不足 | `e4-aes-end-to-end` | AES S-box 8 坐标逻辑→QAOA→原生/含噪 pilot | `scripts/run_aes_bidirectional_pilot.py` | 16 trials；QAOA 8/8 direct；verifier/checksum 通过；noisy 5/4096 |
| 完成但不支持改善 | `e4-v2-frozen-replication` | execution-aware 四臂 post-E4 AES 复验 | canonical v1 config + calibration/test bundle | 64 trials；32 QAOA direct；primary CI 跨 0；generalization=false |
| provenance 完成，性能未验收 | `foundation-v4-formal` | 冻结 AI 模型身份与训练谱系 | formal bundle/self-check | checkpoint SHA 已闭环；仍缺 accepted external performance endpoint |
| 失败并保留 | `e5-v1-first-release` | 外部密码家族首次 release | preflight/seal + archive failure record | 首行前 fail-closed，0 row、无 endpoint，表已 release |
| 完整矩阵但协议不接受 | `e5-v1.1-negative-audit` | 修正 degenerate 记账并保留负证据 | 90-row bundle + independent negative audit | ASCON 0 schedulable group；declared verifier/acceptance=false |

## 5. 统一中文主稿与 Overleaf 主线

`v40` 仅是旧逻辑层内容的历史中间快照，不是独立终版，也不再与竞赛报告维护
两条彼此竞争的最终稿。后续只维护一份当前中文学术主稿，并以 Overleaf 为交付
主线：

- 吸收 `v40` 中经审计仍成立的问题定义、方法、基线和历史结果；
- 将 E1 policy/value 的正负证据和 E2 QAOA scheduler 结果按科学问题组织进正文，
  不写成实验时间线或模块清单；
- E2 只写“局部组合目标改善、端到端 CI 跨 1”，不得改写为资源稳定提升；
- E3-v1 写为“synthetic-profile 机制已验证但主改善假设失败”，不得写成真机、
  真实校准、稳定端点改善或 policy/value 已学习反馈；
- E4 写为“AES 端到端语义与执行契约已验证、QAOA 干预真实发生，但性能证据
  不足”，不得用 5/4096 的稀疏成功计数或小样本原生门均值主张优势；
- formal v4 只写为“训练 provenance 闭环的 evaluation candidate”，不得用内部
  training holdout 或 E5 未接受行主张跨家族性能；
- E4-v2 写为“post-E4 frozen replication；primary native-2q CI 跨 0”，不得写成
  held-out、generalization 或 endpoint improvement；
- E5 必须同时写首次 release fail-closed、v1.1 family-activity 验收失败和独立负审计，
  不得只摘录 90 行中的 effect estimate；
- E5 V3 只可写为跨构建负结论可移植，必须同时保留 `protocol_acceptance=false`；
  fresh V2 只证明当前树安装/验证合同，不得写成性能、硬件或冻结提交证据；
- E6 只有通过锁后盲测与独立 verifier 的结果才进入正文；598→581 只留开发记录；
- 每次形成实质更新后同步唯一主稿到 Overleaf，并验证可编译性；
- 最终 PPT 从同一 claim-to-evidence 主线抽取内容，避免与主稿数字漂移。

当前 35 页主稿已吸收 formal v4、E4-v2 post-E4 负结果、E5 首次失败/v1.1 未验收/
V3 可移植负审计与当前树全新安装证据，以及 E6-MSO 方向。XeLaTeX clean build 无
overfull、未定义引用或致命错误；PDF SHA-256 为
`f6a19cf8a7d2e245505777838a934f30219b378a063703784bf6cf535f908d8f`，Overleaf
`origin/main` 已同步到 commit `c5c6993d1589469a61dfe18000a313d798b1c02f`；当前 PPT
SHA-256 为 `cdb66ca733a6783cd020fd7b9ab8c568e7a80ef876d1109330cb62b3084680ae`。
后续继续以该工作树为唯一交付主线。

## 6. 每个 run 的最低完成定义

每个 run 必须包含：

```text
run.json
raw.jsonl
summary.json
verifier.json
events.jsonl
stdout.log
stderr.log
artifacts.manifest.json
checksums.sha256
```

其中 `run.json` 至少记录：run_id、track、Git SHA、dirty diff hash、Python/依赖、
硬件、dataset/split SHA、checkpoint SHA、config、seed、开始/结束时间和退出状态。
没有 verifier 或不能从 raw 重算 summary 的运行，不得进入报告。

## 7. 当前执行快照（2026-08-12）

- 目录入口已完成重构与断链验收；当前开发树 Conda 完整测试 `501 passed in 318.53s`，
  legacy smoke 与默认 clean-install verifier 通过；锚定 fresh-validation V2 的全新
  venv 记录保持 `383 passed in 295.779s`。
- 已新增 `DetailedSynthesisResult`、稳定 `PlanTrace`、逻辑 IR/QASM JSON adapter、
  `ExperimentManifest` 与拒绝覆盖/路径穿越的 `ArtifactBundle`。
- 首个 bundle：
  `experiments/results/xa202609/20260809-p0-freeze-contract-v1-s202609/`；
  direct 与 foundation 两条记录的 Oracle、Plan ANF、circuit ANF 检查均通过，bundle
  checksum verifier 通过，未出现本机绝对路径。
- 该 bundle 只证明证据链可运行，不能用于宣称 H1 的模型收益；prior 与 value
  diagnostic 已接入同一 artifact contract，随后已进入 C0--C7 pilot。
- `20260809-e1-prior-pilot-v3-s1-oraclev3` 已完成 9 个 case、单 solver seed：model
  相对 shuffled 的逐实例归一化 score 平均低 3.16%，W/L/T 为 8/1/0，捕获完全
  禁用 learned value/scorer 的 classical rollout 排序 headroom 的 54.1%；该
  headroom 仅针对冻结的 model-selected top-K shortlist，不是全合法动作的完美
  policy 上界。三层逻辑验证与 bundle verifier 全通过；更早 bundle 保留但其
  oracle 实现或措辞已废止。
- `20260809-e1-value-pilot-v3-s1` 已完成 382 个 held-out 搜索状态：部署目标 MAE
  为 0.06378，constant predictor 为 0.17331（2.72 倍），$R^2=0.7693$，训练/
  部署 target drift 为 -0.00386；bundle verifier 通过。
- 两者仍是单 seed、小样 pilot，只允许决定继续进入 C0--C7，不得写成泛化或
  端到端收益结论。
- 因果接线审计发现 legacy solver 会把 policy scorer 同时带入 greedy rollout；
  已新增独立 `rollout_scorer`，旧行为保持默认，C0--C7 显式固定 heuristic rollout。
- validation 先冻结 simulation=12，再选择 term-count inference gate=96。修正后的
  validation 中，C1 policy-only 平均改善 1.88%，C2 value-only 退化 0.79%，C5
  learned policy+value+progressive 退化 0.26%；因此当前关闭 learned value 和
  progressive 组合，不按原 C5 配置放大。
- 独立 test bundle `20260809-e1-policy-gate-test-v3-t96-v2` 覆盖 $n=6$--9、
  每尺度 2 个函数、3 个搜索 seed。按函数聚类的 gated C1/C0 score ratio 均值
  0.96415，95% cluster bootstrap 区间 [0.93739,0.98970]，W/L/T=4/0/4；平均
  time ratio 1.1336。收益集中在 $n=8,9$（6.59%/7.75%），$n=6,7$ 为 tie。
- 该 test 只有 8 个独立函数；区间和尺度分解仍是 pilot 证据。下一步只放大
  gated policy-only，并保留 value 负结果，不把 24 行 seed 重复当作 24 个独立样本。
- E2 bundle `20260810-e2-qaoa-scheduler-v1-s120000` 已完成 20 个 held-out
  函数、7 种调度器、3 个 MCTS seed 的 420 条 trial；三种 QAOA 模式共 180 次
  成功调用且 0 fallback，24/24 verifier 与 checksum 通过。QAOA-shot 的局部
  exact-objective 命中率为 81.7%，高于 greedy 的 65.0%，但端到端资源比值的
  函数簇 95% CI 跨 1；只支持局部组合目标改善。
- E3 calibration bundle
  `20260811-e3-cal-native-feedback-v1-s310000` 覆盖 12 个 $n=4$ 函数和 56 条
  根动作候选；冻结 ridge 模型的 calibration MAE 为 0.04571，独立 verifier
  `ok=true`。
- E3 test bundle `20260811-e3-test-native-feedback-v1-s410000` 覆盖 12 个与
  calibration 真值表不相交的函数、4 个变体和 2 个搜索 seed，共 96 条 trial；
  96/96 通过 Plan、circuit、Oracle 与原生全基态等价，独立 verifier `ok=true`。
- E3 反馈相对历史 QAOA-shot 的 NLL 差为 `+0.001293`，函数簇 95% CI
  `[-0.001170, 0.004719]`；反馈机制确实改变部分搜索决策，但未支持 held-out
  含噪端点改善。
- E4 bundle `20260812-e4-aes-bidirectional-pilot-v1-s520000` 覆盖 AES 8 坐标
  × 2 variants、16 trials 和 4096 noisy shots；QAOA 8/8 direct、0 fallback，
  全部语义/原生门集/耦合/bundle 校验通过。QAOA frozen-pool exact hit 8/8 对
  greedy 3/8，但 noisy success 总计仅 5/4096，性能证据不足。
- 竞赛单命令 demo 已实跑 AES bit0 的完整缩小链路；QAOA direct non-fallback，
  持久化输出独立 verifier 13/13 通过，且明确 hardware/performance evidence 均为
  false。`test_competition_demo` 已进入当前 501 项全套测试。
- E4 已进入中文主稿，Overleaf 已同步 commit `9745a76`。
- formal v4 bundle `20260812-foundation-v4-provenance-formal-s20260904` 已从随机
  初始化完成训练，208 条 `n=6,7` 数据与密码宽度排除、训练命令/source/log/
  model-card/checkpoint SHA 闭环；checkpoint SHA 为
  `5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7`，但不构成
  性能 evidence。
- E4-v2 calibration/test bundle 已正式完成：12 个非 AES calibration 函数、72 条
  候选记录；AES 8 坐标 × 2 seeds × 4 arms = 64 trials，32 条 QAOA 全部 direct，
  primary native-2q 差 `-513.9375`、95% CI `[-2059.0625,589.9375]`。它是 post-E4
  replication，`generalization=false`，改善未获支持。
- E5-v1 preflight/seal 通过后在首次 release 首行前 fail-closed，0 row、无 endpoint；
  v1.1 产出 90 行完整矩阵，但 ASCON 无可调度 group，declared verifier 不通过。
  独立 negative audit 重建 90/90 行，同时确认 `protocol_acceptance=false`。
- E5 V3 跨构建负审计在当前/全新环境均为 20/20，最大 absolute/relative learned-float
  drift 为 `3.814697e-06`/`5.046907e-07`，所有离散/下游工件严格一致；协议仍未接受。
- E6-MSO 已完成并独立复审机制 MVP；隔离 v2 frozen shared head 与最终测量 replay
  结构合同已实现并测试，但 active trainer、训练/封印 head、真实 replay 因果实验、
  锁后 SHA 派生未见双射 S-box runner/bundle/verifier 尚未完成，598→581 不作正式证据。
- clean install 已在全新 CPython 3.11 venv 从 exact-pinned `dev.txt` 安装并通过
  `pip check`；默认 `verify_clean_install.py` 为 `ok=true`，覆盖 SciPy MILP、PuLP、
  60,450 参数 checkpoint、direct QAOA、synthetic native/noise、legacy smoke 与
  临时完整 demo+独立 verifier；更新后的 SHA-aware verifier 精确验证 checkpoint
  SHA，隔离环境当时树为 `217 passed in 62.50s`；这是历史快照，不覆盖当前增量树。
- 锚定 fresh-validation V2 在空 venv 完成 9/9 命令、383 项测试与 19/19 独立检查；
  snapshot `dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23` 由外部
  anchor SHA `036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686`
  约束；内部 submission 外层 manifest 绑定与目录/tar verifier 已完成。
- 权威内部 audit draft 共 366 文件、tar 4,665,696 bytes，tar SHA-256 为
  `86b1b75b287ea2f7d042e388215168d96d2de2600d3731a6e6dbc07e82844e45`；目录与 tar
  poisoned-env verifier 均 PASS，tree digest `e850a3b9...` 前后一致且 0 cache；包内
  fresh-v2 19/19，含 8 个完整证据九件套（V3、fresh-v2 与 6 个 predecessor/source/link）；
  锁定 stdout 路径例外恰为 2 且非运行依赖。
- 外层 package verifier 已把 `XA_E5_PROJECT_ROOT` 重绑定到包内 `experiments/`；
  污染环境下的顺序依赖回归已闭合。
- final submission 仍因 7 份人工授权/身份文档与 4 个技术 blocker（外部性能证据、
  final frozen model、final model card、clean frozen commit）缺失而 fail-closed；
  该内部 draft non-distributable。
- 下一步是 E6-MSO head-only trainer/真实 replay/盲测闭环、离线 fallback、冻结提交绑定和最终
  文稿/PPT/提交包验收，不是重复 E4-v2、重复 E5 已 release 家族或把负结果改写成优势。
