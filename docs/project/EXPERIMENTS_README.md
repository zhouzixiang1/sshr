# Resource-NMCTS current experiment workspace

当前可运行工作目录是 `../../experiments/`。它只保存当前 XA-202609 的代码、测试、
模型、冻结配置和已选择的证据 bundle；旧实验和旧投稿材料在 `../../misc/archive/`。

从仓库根执行：

```bash
cd experiments
/opt/anaconda3/envs/mcts-qoracle/bin/python -c "from src.synthesizers import synthesize; print('imports ok')"
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests -q
/opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py
```

当前开发树全套为 `557 passed in 316.28s`；E6 head/replay/trainer/seal 四组
对抗回归为 `150 passed`。legacy smoke 与默认 `verify_clean_install.py` 最近一次均为
`ok`。其中新增的
安装合同回归覆盖 repository-relative quick self-check；完整 clean-install 验收
仍应使用默认模式执行 smoke 与临时竞赛 demo。

## 安装与自检

最小依赖合同位于 `environment/requirements/`。CPython 3.11 的核心复现环境
使用 `core.txt`，测试环境使用 `dev.txt`；SSHR-I/Gurobi 与 Qiskit 互操作均为
可选分组，不是竞赛 demo 的前置条件。完整的全新虚拟环境命令、平台边界和依赖
说明见 `environment/requirements/README.md`。

已有环境可先执行秒级自检：

```bash
cd experiments
python scripts/verify_clean_install.py --quick
```

安装验收应去掉 `--quick`；默认模式还会运行 legacy smoke，并在临时目录执行、
独立复验完整竞赛 demo。通过只证明离线软件合同，不验证 Gurobi licence、Qiskit、
真实校准或量子硬件。

2026-08-12 已在全新 CPython 3.11 venv 中从 `dev.txt` 安装；`pip check` 无冲突，
默认 `verify_clean_install.py` 返回 `ok=true`。它覆盖 exact versions/imports、SciPy
MILP、PuLP、60,450 参数 checkpoint、direct QAOA、synthetic native/noise、legacy
smoke 和临时完整 demo+独立 verifier；更新后的 SHA-aware verifier 精确验证
checkpoint SHA，隔离环境当时树全套为 `217 passed in 62.50s`。该历史快照不覆盖
当前增量树，也不是冻结 commit 或最终提交包验收。

锚定的 fresh-validation V2 历史记录：
`results/xa202609/20260812-e5-v11-portable-fresh-validation-v2-s970000/` 在空 venv
完成 9/9 命令、`383 passed in 295.779s` 和 19/19 独立复验。bundle snapshot 为
`dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23`；外部 anchor
`configs/xa202609/e5_v11_portable_fresh_validation_v2.anchor.json` 的 SHA-256 为
`036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686`。该证据只证明
该锚定树的软件安装与证据复验合同；它不是当前 557 项回归。anchor 与完整 bundle
已由内部审计包外层 manifest 绑定。内部 draft 位于
`docs/competition/submission/generated/ppt-cdb66ca7-pdf-f6a19cf8/XA-202609-internal-audit-draft/`，
共 366 文件；tar 为 4,665,696 bytes，SHA-256 为
`86b1b75b287ea2f7d042e388215168d96d2de2600d3731a6e6dbc07e82844e45`。目录与 tar
在 poisoned-env 下均 PASS，tree digest 前后均为 `e850a3b9...` 且 cache 为 0。包内
fresh-v2 原生复验 19/19，并绑定 8 个完整证据九件套（V3、fresh-v2 与 6 个
predecessor/source/link）；锁定 stdout 本机路径例外
恰为 2，均为历史输出字节而非运行依赖。报告 PDF SHA-256 为
`f6a19cf8a7d2e245505777838a934f30219b378a063703784bf6cf535f908d8f`，PPT SHA-256 为
`cdb66ca733a6783cd020fd7b9ab8c568e7a80ef876d1109330cb62b3084680ae`，Overleaf 为
`c5c6993d1589469a61dfe18000a313d798b1c02f`。该 non-distributable internal draft
不是最终提交包，不能据此声称冻结提交复现、性能改善、硬件执行或量子优势；
final 仍因 7 份人工授权/身份文档和 4 个技术 blocker（外部性能证据、final frozen
model、final model card、clean frozen commit）缺失而 fail-closed。外层包 verifier 显式将 `XA_E5_PROJECT_ROOT` 重绑定到包内
`experiments/`，不再继承污染的调用环境；对应 polluted-environment 回归已闭合。

阅读顺序：

- [项目状态](../docs/project/PROJECT_STATUS_XA202609.md)
- [实验路线](../docs/planning/EXPERIMENT_ROADMAP_XA202609.md)
- [技术设计](../docs/project/TECHNICAL_DESIGN.md)
- [验收矩阵](../docs/contracts/COMPETITION_ACCEPTANCE_MATRIX.json)

公开入口为 `experiments/src/synthesizers.py::synthesize(...)`，仍只覆盖逻辑
X/CNOT/MCT Oracle 综合；逻辑 OpenQASM 3 交换适配器位于 `src/hardware/qasm.py`。
E3 是独立执行适配层，不会静默改变该入口的资源模型：

- `src/hardware/superconducting.py`：synthetic heavy-hex-like profile 上的
  `rz/sx/x/cx` 精确分解、确定性最短路 SWAP、原生全基态等价验证；
- `src/hardware/noise.py`：实际逐 shot statevector/Pauli trajectory 与 readout
  flip，而不是用资源 proxy 冒充含噪执行；
- `src/search/execution_feedback.py`：用 calibration-only、SHA 冻结的岭回归
  执行成本模型调整 MCTS 根动作效用。

固定预算 scheduler 已由 `src/search/diversity_scheduler.py`、
`src/search/qaoa_scheduler.py` 和 `src/search/mcts_scheduler.py` 实现，并接入
`src/nmcts_solver.py` 的独立根 action edge。可复现实验入口为：

```bash
cd experiments
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/run_qaoa_scheduler_pilot.py \
  --run-id 20260810-e2-qaoa-scheduler-reproduction
```

runner 的默认参数与冻结配置 `configs/xa202609/e2_qaoa_scheduler_v1.json` 一致；
输出目录拒绝覆盖，复验时必须使用新的 `--run-id`。

当前冻结证据为
`results/xa202609/20260810-e2-qaoa-scheduler-v1-s120000/`，对应说明见
`../docs/competition/evidence/E2_QAOA_SCHEDULER_EVIDENCE.md`。E2 证明 QAOA-shot
在冻结候选池上改善局部组合目标，但端到端资源分数相对 greedy 的函数簇 95%
置信区间跨过 1；不得写成稳定端到端收益或量子加速。

## E3：原生执行反馈

冻结配置为 `configs/xa202609/e3_native_feedback_v1.json`，正式证据为：

- Calibration：`results/xa202609/20260811-e3-cal-native-feedback-v1-s310000/`
- Held-out test：`results/xa202609/20260811-e3-test-native-feedback-v1-s410000/`
- 证据说明：`../docs/competition/evidence/E3_NATIVE_FEEDBACK_EVIDENCE.md`

Calibration 使用 12 个 `n=4` 函数和 56 个根动作观测；test 使用 12 个真值表
SHA 完全不相交的 `n=4` 函数、2 个搜索 seed 和 4 个变体，共 96 条 trial。
两个 bundle 的独立 verifier 均为 `ok=true`，可从本目录重算：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_hardware_feedback_bundle.py \
  results/xa202609/20260811-e3-cal-native-feedback-v1-s310000
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_hardware_feedback_bundle.py \
  results/xa202609/20260811-e3-test-native-feedback-v1-s410000
```

预注册主比较没有支持改善：反馈 QAOA-shot 相对历史 QAOA-shot 的 held-out
Oracle task NLL 差为 `+0.001293`，函数簇 bootstrap 95% CI 为
`[-0.001170, 0.004719]`。因此当前只可称为“反馈机制已接入并接受留出检验”，
不可称为含噪表现改善。

## E4：AES 双向端到端 pilot

正式 bundle：
`results/xa202609/20260812-e4-aes-bidirectional-pilot-v1-s520000/`。它覆盖 FIPS
197 forward S-box 的 8 个坐标、`classical_greedy/qaoa_shot` 两种调度器，共
16 条 trial 和 4096 noisy shots。全部 Plan/circuit/Oracle 语义、原生门集、耦合
约束和 bundle checksum 校验通过；QAOA attempted/succeeded/direct 为 8/8/8，
0 fallback/repair。

同一冻结候选池上，QAOA 的 exact-objective hit 为 8/8，greedy 为 3/8；两者
selection 在 5/8 坐标上不同，最终 logical QASM 在 4/8 坐标上不同。QAOA 平均
逻辑 score 高 0.448%，原生总门低 2.827%，原生二比特门低 3.229%，配对
W/L/T 为 1/3/4、2/2/4、2/2/4。noisy success 仅 classical 2/2048、QAOA
3/2048，总计 5/4096，证据过稀，不支持含噪性能改善。

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_aes_bidirectional_bundle.py \
  results/xa202609/20260812-e4-aes-bidirectional-pilot-v1-s520000
```

E4 已完成密码 Oracle 端到端 pilot；其当前树单命令竞赛 demo 也已实现并通过
独立复验，clean-install 也已通过。尚未完成的是独立离线 fallback 资产与冻结提交
复现；E4-v2 已完成，但它是 post-E4 replication，不是新 held-out。

## 竞赛单命令 demo

从仓库根运行；输出目录必须预先不存在：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/scripts/demo_competition.py \
  --case aes_sbox_bit0 \
  --synthesizer foundation_nmcts \
  --scheduler qaoa_diversity \
  --hardware superconducting_noise \
  --output experiments/demo/output
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/scripts/verify_demo_output.py \
  experiments/demo/output
```

持久化输出位于 `demo/output/`，包含 input、机器/人读报告、执行日志、manifest、
checksum 和 verification。独立 verifier 13/13 通过；QAOA 实际 direct 且无
fallback。输出显式记录 `hardware_execution=false` 和
`performance_evidence=false`，只用于展示链路与核验契约。对应回归测试
`tests/test_competition_demo.py` 已通过，并纳入当前开发树通过的 557 项测试。

## E4-v2：正式 post-E4 frozen replication

`src/search/execution_aware_utility.py` 已实现 synthetic execution-aware utility
core 与 root rollout adapter：对既有根动作完成 scorer-free rollout，验证逻辑
语义，编译 native 资源代理，再把冻结惩罚提供给 classical/QAOA 共用的调度入口。
`tests/test_execution_aware_utility.py` 已覆盖组件审计、确定性、候选置换、SHA 绑定、
fail-closed、根节点边界和两类调度共用 adjusted utility。

唯一权威配置是 `configs/xa202609/e4_v2_execution_aware_v1.json` 及其 protocol
lock；旧 noisy-primary 分支仅保留明确标注的 test-only superseded fixture。正式
calibration bundle
`results/xa202609/20260812-e4-v2-frozen-replication-v1-s530000-cal/` 覆盖 12 个
非 AES 函数、72 条候选记录，compile-time only 且 verifier `ok=true`。正式 test
bundle `results/xa202609/20260812-e4-v2-frozen-replication-v1-s530000-test/` 覆盖
AES 8 坐标 × 2 seeds × 4 arms = 64 trials；32 条 QAOA 全部 direct-unrepaired，
0 repair/fallback，独立 verifier `ok=true`。

primary native-2q 差（execution-aware QAOA minus historical QAOA）为 `-513.9375`，
按坐标聚类的 95% CI 为 `[-2059.0625, 589.9375]`；secondary greedy 差为
`-1110.3125`，CI `[-3176.3125, 514.4375]`。两者均跨 0，noisy 384 shots 为
0 success 且只作诊断。AES 已在 E4 中出现，所以本实验明确
`generalization_claim=false`；不能写成 held-out、性能改善、硬件或量子优势。

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_e4_v2_bundle.py \
  results/xa202609/20260812-e4-v2-frozen-replication-v1-s530000-cal
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_e4_v2_bundle.py \
  results/xa202609/20260812-e4-v2-frozen-replication-v1-s530000-test
```

## formal v4 与 E5 验收边界

formal v4 bundle
`results/xa202609/20260812-foundation-v4-provenance-formal-s20260904/` 从随机初始化
训练，没有加载 v3；208 条训练/验证记录只来自 `n=6,7`，注册的 4/5/8 比特密码
宽度和 crypto truth-table SHA 被排除，evaluation 模块未访问。checkpoint SHA 为
`5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7`；数据、命令、
源码、日志、模型卡和 checkpoint 哈希闭环。该 bundle 只证明 provenance，不是
性能证据。

E5-v1 preflight/seal 通过后在首次 release 第一条 ASCON trial 前 fail-closed，完成
0 行且无 endpoint。v1.1 在不改模型、权重、预算、seed 与五臂的条件下产出 90 行
ASCON/PRESENT 矩阵，但 ASCON 可调度 group 为 0，declared verifier 的
family-activity gate 失败；独立 negative audit 虽重建 90/90 行，仍明确
`protocol_acceptance=false`、`performance_claim_supported=false`。因此当前没有
accepted E5 endpoint，ASCON/PRESENT 已观察后只作 development。

最终 V3 可移植负审计 bundle
`results/xa202609/20260812-e5-v11-portable-negative-audit-v3-s950000/` 在当前 Conda
与上述全新 venv 均通过 20/20，bundle snapshot 为
`4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea`。仅白名单 learned continuous 字段以
`rtol=1e-6, atol=5e-6` 比较且必须有限；实测最大绝对/相对漂移为
`3.814697e-06`/`5.046907e-07`，候选结构/顺序、选择、QAOA 离散输出、Plan、QASM、
native、endpoint 与 summary 均严格一致。该跨构建一致性只加固负结论的可移植性，
不改变 `protocol_acceptance=false`，也不是性能、硬件或优势证据。

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_foundation_v4_bundle.py \
  results/xa202609/20260812-foundation-v4-provenance-formal-s20260904
/opt/anaconda3/envs/mcts-qoracle/bin/python analysis/verify_e5_v11_negative_audit_bundle.py \
  results/xa202609/20260812-e5-v11-negative-audit-v1-s950000
/opt/anaconda3/envs/mcts-qoracle/bin/python analysis/verify_e5_v11_negative_audit_bundle.py \
  results/xa202609/20260812-e5-v11-portable-negative-audit-v3-s950000
/opt/anaconda3/envs/mcts-qoracle/bin/python analysis/verify_e5_v11_fresh_validation_v2.py \
  results/xa202609/20260812-e5-v11-portable-fresh-validation-v2-s970000 \
  --anchor configs/xa202609/e5_v11_portable_fresh_validation_v2.anchor.json \
  --expected-anchor-sha256 036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686
```

## E6-MSO 当前开发边界

E6-MSO 多输出共享表达式 mechanism MVP 已实现并独立复审：`VectorANF` 跨输出
共享 monomial/semi-affine action，完整枚举 partial-fanout target 子集，以
`compute–fanout–uncompute` 和整程序显式 workspace peak≤2 实现；greedy/exact/QAOA
在同一个 conflict-aware pool/QUBO 与同一预算下比较，QAOA phase 只接收冻结 QUBO，
再对测量结果进行可行筛选/repair/fallback 分账。资源仅为 abstract logical
X/CNOT/MCT proxy，不包含 MCT 隐式分解 ancilla 或硬件精确资源主张。

隔离 v2 还实现并对抗测试了四项开发合同：一是冻结 formal-v4 scalar trunk、仅训练
薄 head 的 output/input/candidate-equivariant shared policy/value；二是把 QAOA 最终
测量 bitstring-count observation 与 random/greedy/exact 对照绑定到 split registry、
外部锁和完整 ITT 记账；三是每次只训练一个 source arm、固定日程的确定性 head-only
trainer；四是 development sealed-head schema 与窄范围 inference loader。replay 合同
不是 optimizer trajectory replay；当前仍无真实 replay 训练 run、真实 trained/sealed
head artifact、因果实验、formal runner/bundle/verifier/result 或性能证据。
正式盲测只使用 protocol lock 后由 SHA 派生、此前未见的 `n=4/5` 双射 S-box，且不
按 candidate 是否存在筛选。`598→581` 是开发观察，不是正式 evidence。

能力边界：这些结果仅来自 synthetic heavy-hex-like profile 和 NumPy 模拟器，
无真机或真实校准证据，也不证明量子优势。离子阱、光量子两条适配路线及三路线
统一 manifest 尚未完成；QAOA 最终测量 observation 经外部锁验证后被 trainer
真实消费并更新 policy/value 的因果闭环也尚未运行。E4 在 AES 尺度没有逐 trial 运行原生全基态等价；其逻辑 Oracle 语义
已对 256 个输入和两个目标值穷举验证，原生层只做了声明范围内的映射契约与采样
含噪端点，不得混称为 AES 原生层穷举等价。
