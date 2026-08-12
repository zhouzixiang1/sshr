See CLAUDE.md for project documentation.

## 速查（AI agent 用）

- **Git 根**：本目录 `/Users/zhouzixiang/Desktop/tzb`
- **工作目录**：所有命令在 `experiments/` 下执行
- **主入口**：`experiments/src/synthesizers.py` 的 `synthesize(method, bf, config, seed, model_path)`
- **主环境**：`/opt/anaconda3/envs/mcts-qoracle/bin/python`（torch + PuLP）；SSHR-I 另需 `sshr` 环境（Gurobi）
- **冒烟测试**：`cd experiments && /opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py`
- **逻辑核心定位**：`synthesize(...)` 仍只做逻辑 X/CNOT/MCT 综合；E3 没有静默改变既有 method，也没有加入通用 Rz 旋转综合后端
- **E3 独立执行层**：`src/hardware/superconducting.py` 与 `noise.py` 在 synthetic heavy-hex-like profile 上完成 `rz/sx/x/cx` 精确分解、确定性最短路 SWAP、原生全基态等价和逐 shot Pauli trajectory；这不是 `synthesize(...)` 的逻辑成本模型
- **E3 反馈接入**：`src/search/execution_feedback.py` 以冻结 calibration 模型调整 MCTS 根动作效用；正式 held-out 结果为 NLL 差 `+0.001293`、95% CI `[-0.001170, 0.004719]`，未支持改善主张
- **E3 证据**：calibration/test bundle 分别为 `experiments/results/xa202609/20260811-e3-cal-native-feedback-v1-s310000/` 与 `experiments/results/xa202609/20260811-e3-test-native-feedback-v1-s410000/`
- **E4 AES 证据**：`experiments/results/xa202609/20260812-e4-aes-bidirectional-pilot-v1-s520000/` 覆盖 FIPS 197 S-box 8 坐标 × classical/QAOA 两变体；16/16 trial 的逻辑语义、原生门集、耦合和 bundle 校验通过，QAOA 8/8 direct、0 fallback
- **E4-v2 当前边界**：唯一权威 `e4_v2_execution_aware_v1` 已完成 12 个非 AES calibration 函数/72 候选与 AES 8 坐标 × 2 seeds × 4 arms 的 post-E4 frozen replication；64 trials、32/32 QAOA direct、两个 verifier 通过，但 primary native-2q 差 `-513.9375` 的 95% CI `[-2059.0625, 589.9375]` 跨 0，且 `generalization_claim=false`，不得写成 held-out 或改善
- **formal v4**：`20260812-foundation-v4-provenance-formal-s20260904` 从随机初始化闭合数据/命令/source/log/model-card/checkpoint SHA；checkpoint `5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7`，只证明 provenance，不是性能 evidence
- **E5 边界**：v1 首次 release 首行前 fail-closed、0 row；v1.1 有 90 行完整矩阵但 ASCON 0 个可调度 group，declared verifier/协议验收失败；V3 可移植负审计（snapshot `4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea`）在当前 Conda 与全新 venv 均为 20/20，learned continuous 最大绝对/相对漂移仅 `3.814697e-06`/`5.046907e-07`，离散选择、Plan/QASM/native/endpoint 均严格一致，但仍为 `protocol_acceptance=false`，当前无 accepted E5 endpoint
- **E6 当前边界**：`E6-MSO` 多输出共享表达式 mechanism MVP 已实现并独立复审；VectorANF、完整 partial-fanout、共享 monomial/semi-affine action、compute–fanout–uncompute、显式 workspace peak≤2、同池 conflict/QUBO greedy/exact/QAOA 已有 109 项相关回归；资源仅为 abstract logical X/CNOT/MCT proxy。隔离 v2 的冻结 formal-v4 trunk output/input/candidate-equivariant shared policy/value head、带 split registry/外部锁的 QAOA 最终测量 bitstring-count replay 合同、确定性单 arm head-only trainer，以及 development sealed-head schema/inference loader 均已实现并完成对抗测试；仍无真实 replay 训练 run、真实 trained/sealed head artifact、因果实验、formal runner/bundle/verifier/result 或性能证据，锁后 SHA 派生未见 n4/5 双射正式盲测尚未完成，598→581 仅开发观察
- **竞赛 demo**：`experiments/scripts/demo_competition.py` 单命令贯通 AES bit0、`foundation_nmcts`、direct QAOA、逻辑验证、synthetic-profile 原生/含噪报告；`verify_demo_output.py` 对持久化输出 13/13 检查通过，且 `hardware=false`、`performance_evidence=false`
- **clean install（历史快照）**：全新 CPython 3.11 venv 从 `experiments/environment/requirements/dev.txt` 安装，`pip check` 无冲突；更新后的 SHA-aware `scripts/verify_clean_install.py` 为 `ok=true` 且 checkpoint SHA 精确通过；当时树为 `217 passed in 62.50s`
- **clean install（当前树）**：`20260812-e5-v11-portable-fresh-validation-v2-s970000` 在全新 venv 中 9/9 命令通过，fresh-validation verifier 19/19；bundle snapshot `dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23`，外部 anchor SHA `036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686`；已由内部审计包外层 manifest 绑定
- **内部审计包**：权威内部 draft 位于 `docs/competition/submission/generated/ppt-cdb66ca7-pdf-f6a19cf8/XA-202609-internal-audit-draft/`，共 366 文件；tar 为 4,665,696 bytes，SHA-256 `86b1b75b287ea2f7d042e388215168d96d2de2600d3731a6e6dbc07e82844e45`。目录与 tar 在 poisoned-env 下均 PASS，tree digest 前后均为 `e850a3b9...` 且 cache 为 0；包内 fresh-v2 原生复验 19/19，绑定 8 个完整证据九件套；锁定 stdout 本机路径例外恰为 2 且不是运行依赖，外层 verifier 会将 `XA_E5_PROJECT_ROOT` 重绑定到包内 `experiments/`
- **当前验证**：当前开发树全套 `557 passed in 316.28s`；E6 head/replay/trainer/seal 四组对抗回归 `150 passed`。legacy smoke 与默认 `verify_clean_install.py` 最近一次均为 `ok`。锚定 fresh-validation V2 历史记录仍为 `383 passed in 295.779s`，冻结 PPT/Overleaf/PDF/内部审计包仍对应 pre-E6-v2 的 407-test 交付基线；安装回归、E3 两个 verifier、E4 verifier、demo verifier、E5 V3 20/20 与 fresh-validation V2 19/19 均通过
- **文稿/PPT 同步**：35 页当前中文主稿 PDF SHA-256 为 `f6a19cf8a7d2e245505777838a934f30219b378a063703784bf6cf535f908d8f`，Overleaf `origin/main` 为 `c5c6993d1589469a61dfe18000a313d798b1c02f`；当前 PPT SHA-256 为 `cdb66ca733a6783cd020fd7b9ab8c568e7a80ef876d1109330cb62b3084680ae`
- **主张边界**：内部审计包只证明当前 staging、外锚、清单与解包技术复验通过，属于 non-distributable internal audit，不是最终可提交包；final 仍因 7 份人工授权/身份文档与 4 个技术 blocker（外部性能证据、final frozen model、final model card、clean frozen commit）缺失而 fail-closed。E4 noisy endpoint 仅 5/4096 success，性能证据不足，且 AES 尺度未做逐 trial 原生全基态等价；无真机或真实校准证据，无量子优势；离子阱/光量子另外两路线、三路线统一 manifest 与实际 replay→trainer→policy/value 因果闭环仍未完成
- **两套布局**：当前工作树位于 `experiments/`（脚本在 `analysis/`、`scripts/`、`submission/`）；旧投稿 payload 已归档在 `misc/archive/experiments/`，其重建脚本为扁平布局设计
- **已修复的路径 bug**：`sshr_i.py:320` 裸 import、`synthesizers.py:28` STRUCTURE_GATE_MODEL 路径（`.parent` → `.parent.parent`）
