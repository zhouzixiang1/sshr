# Resource-Constrained Neural MCTS Oracle Synthesis

## 当前范围

XA-202609 的主线是逻辑层 Boolean Oracle 综合：真值表到 ANF，候选因子动作，
policy/heuristic 排序，greedy/beam/NMCTS，Plan 发射为 X/CNOT/MCT，再以符号
模拟验证。等变 policy/value、固定预算 QAOA diversity scheduler 及其独立 MCTS
子边接入、逻辑 OpenQASM 3 边界均已有源码和测试；E2 已形成可核验的
ideal/shot/noisy QAOA 对照 bundle。公开 `synthesize(...)` 的资源目标仍停留在
逻辑 X/CNOT/MCT 层，没有被 E3 静默改成硬件成本或通用 Rz 旋转综合。

E3 在逻辑核心之外新增了可验证的超导模拟执行适配层：
`src/hardware/superconducting.py` 在 synthetic heavy-hex-like 局部耦合 profile
上将 X/CNOT/MCT 分解为 `rz/sx/x/cx`，执行确定性最短路 SWAP，并做独立原生
全基态等价验证；`src/hardware/noise.py` 逐 shot 运行带一/二比特 Pauli 错误与
readout flip 的 statevector trajectory。`src/search/execution_feedback.py` 将仅由
calibration 数据拟合并按 SHA 冻结的执行成本模型接入 MCTS 根动作效用。

该机制已经形成 calibration/test 隔离的正式证据，但 held-out 改善假设没有
通过：反馈 QAOA-shot 相对历史 QAOA-shot 的 Oracle task NLL 差为 `+0.001293`，
函数簇 bootstrap 95% CI 为 `[-0.001170, 0.004719]`。反馈确实改变选择与部分
最终 Plan，不能据此声称改善含噪端点。

E4 已将 8 个 FIPS 197 AES S-box 坐标贯通到同一 learned-policy 候选池、固定预算
classical/QAOA 调度、逻辑 Plan/QASM、synthetic-profile 原生映射和逐 shot 含噪
端点。16 条 trial 的语义、原生门集、耦合和 bundle 校验全部通过，QAOA 8/8
direct 且 0 fallback；但 noisy endpoint 仅 5/4096 success，不能支持性能改善，
AES 尺度也未运行逐 trial 原生全基态等价。

竞赛 CLI 已将这条链压缩为 AES bit0 单命令 demo；持久化输出的独立 verifier
13/13 通过，实际 QAOA 为 direct non-fallback。demo 明确记录
`hardware_execution=false`、`performance_evidence=false`，只证明当前树执行与
验证契约，不代替正式 E4 性能证据或离线 fallback 资产。

当时树的软件安装合同已经在全新 CPython 3.11 venv 中通过：从
`environment/requirements/dev.txt` 安装 exact pins 后 `pip check` 无冲突，默认
SHA-aware `scripts/verify_clean_install.py` 返回 `ok=true`，checkpoint SHA 精确通过；
隔离环境当时树为 `217 passed in 62.50s`。该历史快照不覆盖当前增量树，尚未绑定冻结 commit，也不是最终提交包验收。

E4-v2 已完成唯一权威 `e4_v2_execution_aware_v1` 协议的两阶段运行：12 个非 AES
函数/72 条候选用于 compile-only calibration，随后在 E4 已见的 AES 8 坐标上完成
2 seeds × 4 arms = 64 条 post-E4 frozen replication；32 条 QAOA 全部 direct，两个
verifier 均通过。primary native-2q 差为 `-513.9375`，95% CI
`[-2059.0625, 589.9375]`，不支持改善；`generalization_claim=false`。旧 noisy-primary
配置只作为 `superseded-test-only` fixture，不是生产配置。

formal v4 已从随机初始化形成 provenance-closed 训练 bundle，checkpoint SHA 为
`5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7`；这只闭合模型
身份，不是性能证据。E5-v1 首次 release 在首行前 fail-closed；v1.1 的 90 行矩阵
因 ASCON 0 个可调度 group 未通过 family-activity gate，独立负审计仍明确
`protocol_acceptance=false`。最终 V3 可移植负审计（bundle snapshot
`4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea`）在当前 Conda
与全新 venv 均以 20/20 通过；仅白名单 learned continuous 字段允许有限值容差，最大绝对/相对漂移为
`3.814697e-06`/`5.046907e-07`，离散选择、Plan/QASM/native/endpoint 均严格一致。
这证明负结论不是单一 Torch 构建产物，不改变协议失败；当前没有 accepted E5 endpoint。

E6-MSO 多输出共享表达式 mechanism MVP 已实现并独立复审：VectorANF、完整
partial-fanout、跨输出共享 monomial/semi-affine action、compute–fanout–uncompute、
显式 workspace peak≤2，以及同池同预算 greedy/exact/QAOA。资源口径仅为 abstract
logical X/CNOT/MCT proxy。隔离 v2 的冻结 formal-v4 trunk
output/input/candidate-equivariant shared policy/value head、带 split registry 和外部锁的
QAOA 最终测量 bitstring-count replay 合同、确定性单 arm head-only trainer，以及
development sealed-head schema/inference loader 均已实现并完成对抗测试。当前仍无真实
replay 训练 run、真实 trained/sealed head artifact、因果实验、formal
runner/bundle/verifier/result 或性能证据；锁后 SHA 派生未见 n4/5 双射 S-box 正式盲测
仍未完成，598→581 仅为开发观察。

先读：

- `docs/project/PROJECT_STATUS_XA202609.md`
- `docs/planning/EXPERIMENT_ROADMAP_XA202609.md`
- `docs/contracts/COMPETITION_ACCEPTANCE_MATRIX.json`

## 目录约定

| 目录 | 用途 |
|---|---|
| `docs/` | 项目设计、赛题、论文、竞赛报告、PPT、Overleaf 同步说明 |
| `experiments/` | 当前代码、测试、模型、配置、基准和 XA 结果；所有运行命令从这里执行 |
| `misc/` | 历史实验/文稿/投稿包、生成物、缓存和本机配置；默认不纳入干净提交 |

当前实验代码入口：

- `experiments/src/synthesizers.py::synthesize(method, bf, config, seed, model_path)`
- `experiments/src/synthesizers.py::synthesize_detailed(...)`：产生可验证的详细记录
- `experiments/scripts/run_p0_freeze.py`：从空目录生成合约闭环证据包
- `experiments/scripts/run_c0c7_pilot.py`、`run_prior_ablation.py`、`run_value_diagnostic.py`：当前 XA 专项实验
- `experiments/scripts/run_qaoa_scheduler_pilot.py`：E2 同池同预算 scheduler 对照与验证
- `experiments/scripts/run_hardware_feedback_eval.py`：E3 calibration/test 两阶段 runner
- `experiments/scripts/verify_hardware_feedback_bundle.py`：E3 九件套独立复验器
- `experiments/scripts/run_aes_bidirectional_pilot.py`：E4 AES 8 坐标双变体端到端 pilot
- `experiments/scripts/verify_aes_bidirectional_bundle.py`：E4 九件套独立复验器
- `experiments/src/search/execution_aware_utility.py`：E4-v2 root-only execution-aware utility core/adapter
- `experiments/scripts/run_e4_v2_execution_aware.py`、`verify_e4_v2_bundle.py`：E4-v2 两阶段 runner/verifier
- `experiments/scripts/train_foundation_v4.py`、`verify_foundation_v4_bundle.py`：formal v4 provenance 训练/复验
- `experiments/analysis/verify_e5_v11_negative_audit_bundle.py`：E5-v1.1 独立负审计及 V3 跨构建复验，不改变协议验收失败
- `experiments/analysis/verify_e5_v11_fresh_validation_v2.py`：外部 anchor SHA 约束下复验当前树全新安装证据
- `experiments/scripts/demo_competition.py`：竞赛 AES bit0 单命令演示
- `experiments/scripts/verify_demo_output.py`：演示输出的独立 hash/语义/主张复验器

历史 `results/`、旧 `submission_package/`、早期文稿版本已移动到 `misc/archive/`。
不要把它们搬回当前结果目录，也不要改写其中已生成的 manifest 或 checksum。

## 运行环境

| 环境 | 解释器 | 用途 |
|---|---|---|
| `mcts-qoracle` | `/opt/anaconda3/envs/mcts-qoracle/bin/python` | 核心合成、训练与测试 |
| `sshr` | `/opt/anaconda3/envs/sshr/bin/python` | 仅 Gurobi/SSHR-I 历史脚本 |

```bash
cd experiments
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests -q
/opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py
```

当前开发树全套为 `557 passed in 316.28s`；E6 head/replay/trainer/seal 四组
对抗回归为 `150 passed`。legacy smoke 与默认 `verify_clean_install.py` 最近一次均为 `ok`。
锚定 fresh-validation V2 的
全新 CPython 3.11 venv 记录仍为 `383 passed in 295.779s`；冻结 PPT、Overleaf、
PDF 和内部审计包仍对应 pre-E6-v2 的 407-test 交付基线。

## E3 冻结证据

- 配置：`experiments/configs/xa202609/e3_native_feedback_v1.json`
- Calibration：`experiments/results/xa202609/20260811-e3-cal-native-feedback-v1-s310000/`
- Held-out test：`experiments/results/xa202609/20260811-e3-test-native-feedback-v1-s410000/`
- 证据说明：`docs/competition/evidence/E3_NATIVE_FEEDBACK_EVIDENCE.md`

两个 bundle 的 `verifier.json` 均为 `ok=true`。从 `experiments/` 可独立重算：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_hardware_feedback_bundle.py \
  results/xa202609/20260811-e3-cal-native-feedback-v1-s310000
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_hardware_feedback_bundle.py \
  results/xa202609/20260811-e3-test-native-feedback-v1-s410000
```

## E4 AES 冻结 pilot

- Bundle：`experiments/results/xa202609/20260812-e4-aes-bidirectional-pilot-v1-s520000/`
- 范围：FIPS 197 forward S-box 8 坐标 × `classical_greedy/qaoa_shot`，16 trials、
  4096 noisy shots；QAOA attempted/succeeded/direct 为 8/8/8，0 fallback/repair
- 调度：同一冻结候选池上，QAOA exact-objective hit 为 8/8，greedy 为 3/8；
  两者选择 5/8 不同，但最终 logical QASM 仅 4/8 不同
- 资源：QAOA 逻辑 score 高 0.448%，原生总门低 2.827%，原生二比特门低 3.229%；
  配对样本仅 8 个，且 noisy success 为 classical 2/2048、QAOA 3/2048，不能据此
  声称性能改善

从 `experiments/` 独立复验：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_aes_bidirectional_bundle.py \
  results/xa202609/20260812-e4-aes-bidirectional-pilot-v1-s520000
```

## 竞赛单命令 demo

从仓库根运行；`--output` 必须指向空目录：

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

当前持久化输出包含 input、机器/人读报告、执行日志、manifest、checksum 和
verification；独立 verifier 13/13 为 `true`。回归测试
`tests/test_competition_demo.py` 已纳入当前通过的 557 项测试。clean-install 默认 verifier
也已在隔离环境执行完整临时 demo；尚未完成的是独立离线 deterministic fallback
资产和提交包验收。

## Clean-install 验收

依赖合同：

- `experiments/environment/requirements/core.txt`：CPython 3.11 核心 exact pins；
- `dev.txt`：核心依赖与 pytest；
- `quantum.txt`：可选 Qiskit/Aer/QNN 互操作；
- `optional-sshr-gurobi.txt`：可选 SSHR-I/Gurobi；
- `README.md`：venv/Conda 安装、平台边界与验收命令。

从 `experiments/` 运行当前树验收：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r environment/requirements/dev.txt
.venv/bin/python -m pip check
.venv/bin/python scripts/verify_clean_install.py
.venv/bin/python -m pytest tests -q
```

2026-08-12 的全新 venv 实测覆盖 exact versions/imports、SciPy MILP、PuLP、
60,450 参数 checkpoint、direct QAOA、synthetic native/noise、legacy smoke 与临时
完整 demo+独立 verifier；更新后的 SHA-aware 报告 `ok=true` 且 checkpoint SHA
精确通过，隔离环境当时树为 `217 passed in 62.50s`。
该 217 项记录保留为历史快照。锚定的 fresh-validation V2 历史记录由
`results/xa202609/20260812-e5-v11-portable-fresh-validation-v2-s970000/` 在空 venv
完成 9/9 命令、383 项测试与 19/19 独立复验；bundle snapshot 为
`dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23`，外部 anchor
SHA 为 `036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686`。
这只证明其锚定树的软件/证据可移植性，不是当前通过的 557 项回归、冻结提交或性能证据；
anchor 与 bundle 已进入内部审计包外层 manifest。内部 draft 位于
`docs/competition/submission/generated/ppt-cdb66ca7-pdf-f6a19cf8/XA-202609-internal-audit-draft/`，
共 366 文件；tar 为 4,665,696 bytes，SHA-256 为
`86b1b75b287ea2f7d042e388215168d96d2de2600d3731a6e6dbc07e82844e45`。目录与 tar
在 poisoned-env 下均 PASS，tree digest 前后均为 `e850a3b9...` 且 cache 为 0。包内
fresh-v2 原生复验 19/19，并绑定 8 个完整证据九件套（V3、fresh-v2 与 6 个
predecessor/source/link）；锁定 stdout 本机路径例外
恰为 2，均为不可变历史输出字节而非运行依赖。该 non-distributable draft 不是最终
提交包：final 仍因 7 份人工授权/身份文档和 4 个技术 blocker（外部性能证据、final
frozen model、final model card、clean frozen commit）缺失而 fail-closed。外层包 verifier 现在显式把
`XA_E5_PROJECT_ROOT` 重绑定到包内 `experiments/`，不再继承测试收集或调用环境的
污染值；对应 polluted-environment 回归已闭合。

`ResourceWeights` 的论文权重是 `T=1.0, CNOT=0.04, depth=0.015, gates=0.01,
ancilla=2.0`；新实验必须显式使用它们。默认 dataclass 的 CNOT/depth 权重不同。

## 重要边界

- 逻辑 resource score 不是硬件编译成本；不得外推为映射/噪声优势。
- E3 只证明 synthetic heavy-hex-like profile 上的分解、路由、模拟和反馈干预；
  它不是真机、真实设备校准或硬件性能证据，也不证明量子加速/量子优势。
- 当前反馈模型只调整根调度 utility；E6-v2 已实现带外部锁的 QAOA 最终测量
  bitstring-count replay 合同、确定性单 arm head-only trainer 和 development
  sealed-head loader，但尚无真实 replay 训练 run 消费 observation 并形成
  policy/value 因果结果；held-out CI 未过改善门，必须保留负结果。
- E4 证明 AES 端到端链路与 QAOA direct execution 可运行，不证明 AES 性能优势；
  5/4096 noisy success 太稀疏，AES 尺度的逐 trial 原生全基态等价也未执行。
- 离子阱 RXX/MS 路线、光量子 capability/unsupported-boundary 路线和三路线
  统一 profile manifest 尚未完成；不能用本次超导模拟结果代替。
- `foundation_nmcts` 是当前等变 policy/value 的兼容方法名，不是通用基础模型主张。
- `src/sshr_lib/` 的运行时内部迁移链已记录，但初始来源和再分发权仍待人工确认。
- 仓库暂无闭环开源许可证；默认按私有竞赛研发代码处理。
- `misc/archive/` 和 `misc/local-config/` 被 `.gitignore` 排除。不要执行 `git add -A`。

## 文稿与交付

中文主文稿在 `docs/papers/resource_nmcts/chinese/`，对应的 Overleaf Git 项目及
同步入口在 `docs/papers/resource_nmcts/overleaf/`。竞赛学术报告在
`docs/competition/report/`；最终 PPT 将放在 `docs/competition/slides/`。`v40`
仅是历史中间快照，后续只维护一份吸收有效 XA 证据的当前中文主稿，并同步到
Overleaf，不把 `v40` 作为独立终版继续分叉。35 页当前主稿已吸收 formal v4、
E4-v2、E5 可移植负审计/全新安装证据与 E6-MSO 方向，并通过 XeLaTeX clean build；
PDF SHA-256 为 `f6a19cf8a7d2e245505777838a934f30219b378a063703784bf6cf535f908d8f`，
Overleaf `origin/main` 已同步到 commit `c5c6993d1589469a61dfe18000a313d798b1c02f`；
当前 PPT SHA-256 为 `cdb66ca733a6783cd020fd7b9ab8c568e7a80ef876d1109330cb62b3084680ae`。
