# XA-202609 服务器开发接手报告

> 快照日期：2026-07-28
> 项目状态：IN PROGRESS
> 目标仓库：`git@github.com:zhouzixiang1/xa202609-oracle.git`（私有、干净导入）
> 历史工作区基线：`2d264f23bbdcfaf7bf844beefb7df58af90b7b37`
> 服务器工作目录：`experiments/`

## 0. 接手结论

当前项目已经具备一个可运行、可验证的逻辑层 Boolean Oracle 综合底座，并有
开发态的置换等变 policy/value NMCTS 和逻辑 OpenQASM 3 适配器。

当前项目**还不是完整竞赛原型**。QAOA、多硬件原生门转换、routing、含噪
仿真反馈、GFlowNet、离散扩散、QNN、LLM Agent 和 Web UI 均尚未完成。

服务器接手后最优先的任务不是立即训练大模型，而是补齐统一结果契约、
实验 manifest、环境锁和 CI，再分别实现算法轨。

## 1. 迁移方式

### 1.1 为什么不用旧远端继续开发

原工作区远端是：

```text
git@github.com:zhouzixiang1/sshr.git
```

审计发现：

- 仓库名仍是旧研究名 `sshr`，已不能准确代表 XA-202609 项目；
- Git 历史约 2.2GB；
- 历史中连续提交过多版约 39–43MB 的压缩包；
- 旧历史包含已填写作者、邮箱、机构和邮寄地址的元数据文件；
- 当前远端是公开仓库；
- 当前新增的等变模型、硬件适配器、测试和 XA 文档尚未完整进入旧远端。

因此本次不覆写旧远端、不做 force-push，而是创建新的私有仓库并做一次干净
源码导入。服务器只克隆新仓库。

### 1.2 历史资料如何保留

原工作区不删除，继续作为完整历史归档。服务器仓库排除：

- 2.1GB `misc/archive/`；
- 1.8GB 第三方构建树；
- 107MB 历史 `results/` raw 数据；
- 75MB `benchmark_exports/`；
- 旧论文版本与 LaTeX 中间文件；
- 旧投稿压缩包；
- 私人投稿元数据；
- 本机缓存、日志和绝对路径产物。

详见 `../archive/ARCHIVE_INDEX.md`。

## 2. 最终竞赛目标

2026-09-15 前交付：

1. 可运行的密码量子 Oracle 智能综合与资源评估原型；
2. 可复现实验和完整原始证据；
3. 完整源码、冻结模型和模型卡；
4. XA-202609 技术报告 PDF；
5. 安装与使用文档；
6. 演示材料和离线 fallback；
7. 合规提交包、SBOM、checksum 和独立 verifier。

核心双向赋能链：

```text
AI for Quantum
等变 policy/value + NMCTS
  └─> 低资源逻辑 Oracle

Quantum for AI
QAOA utility-diversity scheduler
  └─> 多样化 MCTS 子节点和训练数据

Hardware feedback
native decomposition + routing + noisy simulation
  └─> 物理资源/成功率反馈给搜索和训练
```

六条附加实验轨：

1. GFlowNet；
2. 离散扩散；
3. QNN；
4. Oracle 专用自研路由器；
5. 受限 LLM Agent；
6. 证据化 Web UI。

六条都要形成实现和公平实验；只有通过定量门的模块才进入最终核心主张。

## 3. 当前代码架构

### 3.1 逻辑数据流

```text
BooleanFunction
→ Möbius transform
→ ANF terms
→ candidate_actions
→ heuristic / neural policy
→ greedy / beam / MCTS
→ binary Plan
→ emit_plan_to_circuit
→ X / CNOT / MCT circuit
→ verify_oracle
→ SynthesisResult
```

### 3.2 关键对象

| 对象 | 文件 | 当前作用 |
|---|---|---|
| `BooleanFunction` | `src/sshr_lib/bool_func.py` | 真值表和 Boolean 原语 |
| `SearchConfig` | `src/factor_plan.py` | 搜索与资源参数 |
| `FactorAction` | `src/factor_plan.py` | 一次 factor/rest 二叉分解 |
| `Plan` | `src/factor_plan.py` | compute/uncompute 二叉计划 |
| `NeuralMCTSSolver` | `src/nmcts_solver.py` | neural prior/value、PUCT、progressive widening |
| `ResourceWeights` | `src/resource_model.py` | T/CNOT/depth/gates/ancilla 权重 |
| `SynthesisResult` | `src/synthesizers.py` | 当前摘要返回对象 |
| `FoundationScorer` | `src/foundation/adapter.py` | 等变 policy/value 适配器 |
| `LearnedValueEstimator` | `src/search/value_net.py` | learned value 与缓存 |
| `LogicalCircuitIR` | `src/hardware/qasm.py` | 逻辑线路与 OpenQASM 3 边界 |

### 3.3 公开入口

```python
synthesize(method, bf, config, seed, model_path)
```

位置：

```text
experiments/src/synthesizers.py
```

当前支持历史 direct、greedy、beam、NMCTS、FPRM、affine、cube、ESOP、
SSHR-H/Beam 和 portfolio 路径，以及开发态 `foundation_nmcts`。

## 4. 已完成能力

### 4.1 逻辑 Oracle 综合

具备：

- truth table → ANF；
- shared factor 提取；
- compute/uncompute Plan；
- direct、greedy、beam 和 MCTS；
- logical MCT 成本模型；
- emitted circuit Boolean 语义验证；
- 多种传统和历史 AI 基线。

当前逻辑门域：

```text
X / CNOT / MCT
```

### 4.2 等变 policy/value 开发候选

当前模块：

```text
src/foundation/
├── encoding.py
├── equivariant.py
├── heads.py
└── adapter.py

src/search/value_net.py
scripts/train_expert_iteration.py
scripts/run_prior_ablation.py
scripts/run_value_diagnostic.py
```

当前模型：

```text
models/boolean_oracle_fm_v3.pt
SHA-256: 87904409966e6d9d18aae3711dff54d696608e6eefcf0e5cb5bb98ae96d4f57d
参数量: 60,450
状态: development candidate
```

已知限制：

- 训练命令、数据 split、seed 和 source SHA 未完整保存在 checkpoint；
- 当前只支持 `gate_mode="mct"`；
- 尚无冻结 C0–C7 正式实验；
- 开发记录不能作为竞赛最终提升数字；
- `FoundationScorer` 当前默认 CPU。

### 4.3 逻辑 OpenQASM 3

`src/hardware/qasm.py` 已实现：

- X/CNOT/MCT gate validation；
- immutable `LogicalCircuitIR`；
- OpenQASM 3 序列化；
- MCT 保留为 `ctrl(k) @ x`；
- 逻辑统计和需要分解标记。

它没有实现：

- MCX/MCT 原生分解；
- Clifford+T 或设备 basis；
- layout、placement、routing、SWAP；
- ideal/shot/noisy execution；
- 物理 fidelity 或成功率。

## 5. 当前验证证据

2026-07-28 原工作树实测：

```text
python -m pytest tests -q
36 passed

python tests/tests_smoke.py
smoke ok
```

36 项包括：

- `test_equivariance.py`：6；
- `test_foundation_adapter.py`：7；
- `test_qasm_export.py`：14；
- `test_synthesizers_foundation.py`：3；
- `test_value_net.py`：6。

注意：`tests/tests_smoke.py` 不符合 pytest 默认 `test_*.py` 文件名模式，必须
独立运行。

这组结果只证明：

- 逻辑底座没有被当前开发改坏；
- 等变接口满足当前范围内的不变/等变契约；
- v3 可以从公开入口加载；
- 逻辑 QASM exporter 符合当前边界。

它不证明模型效果、QAOA、native、routing 或 noise。

## 6. 当前完全缺失的模块

- QAOA diversity scheduler 源码；
- random/top-B/greedy/exact/QAOA 五路公平实现；
- QUBO 罚项验证和 shot/noisy QAOA；
- MCX/MCT 原生分解；
- `NativeCircuitIR`；
- `HardwareProfile`；
- Qiskit routing 和自研 router；
- Aer ideal/shot/noisy runner；
- noise feedback；
- GFlowNet；
- discrete diffusion；
- QNN；
- Agent backend；
- React frontend；
- 竞赛 CLI；
- `competition/` 正式交付树；
- XA 专用技术报告、PPT 和最终提交包。

## 7. 第一优先级公共接口

当前 `SynthesisResult` 只保留：

```text
method, cost, time_s, correct, terms, gates, n_qubits
```

综合完成前已有的 Plan、circuit、search trace、verification details、config、
seed 和 model SHA 会被丢弃。这会阻断后续全部模块。

服务器端第一批改动应新增：

```text
src/contracts/
├── synthesis.py       # DetailedSynthesisResult
├── search.py          # SearchState / PlanTrace / SchedulerResult
├── circuit.py         # LogicalCircuitIR / NativeCircuitIR
├── hardware.py        # HardwareProfile / RouteTrace
├── experiment.py      # ExperimentManifest
└── artifacts.py       # ArtifactBundle
```

兼容策略：

- 旧 `synthesize()` 保持摘要行为；
- 新增 `synthesize_detailed()`，或在旧结果上增加可选详细字段；
- 新竞赛链只使用详细接口；
- 所有详细对象都可 JSON 序列化并有稳定 schema version。

## 8. 六条扩展轨接入说明

### 8.1 GFlowNet

定位：偏好条件的完整 Plan 候选生成器。

状态不是单个 `StateKey`，而是：

```text
partial Plan + pending subproblem stack
```

原因：一次 `FactorAction` 会产生 residual 和 rest 两棵递归分支。

最低实现：

- 合法动作环境；
- `DIRECT` 终止动作；
- trajectory balance；
- resource preference conditioning；
- verified Plan 采样；
- GFlowNet → NMCTS 精化。

进入主创新的最低门：

- 生成有效率 100%；
- 32 样本 unique verified Plan ≥25%；
- 同预算 hypervolume ≥ NMCTS +5%，或同 HV 开销下降 ≥20%；
- 3 seeds，paired bootstrap 95% CI 不跨 0。

### 8.2 离散扩散

定位：expert Plan 条件的离散掩码去噪 proposal。

统一表示：

```text
node_type + absolute factor_bits + affine flag
```

不能使用动态 candidate rank token，因为 masked prefix 下 rank 不再定义。

最低门：

- raw validity ≥85%；
- repair 后 ≥99.9%；
- repair 率 ≤15%；
- 32 样本 unique ≥25%；
- 相对 BC best-of-32 ≥2%，或 diffusion→NMCTS HV ≥3%。

### 8.3 QNN

定位：4–6 qubit 的 classical value residual，不替换等变主干。

建议：

- 冻结等变 global embedding；
- train-only scaler/PCA 压到 4 或 6 维；
- `EstimatorQNN` 连续残差；
- 参数量匹配 MLP 和 ridge 对照；
- exact → 1024 shots → 4096 shots → frozen noise。

最低门：

- 相对同参数 MLP held-out MAE 改善 ≥3%；
- 固定搜索预算 score 改善 ≥0.5% 或 time-to-quality 下降 ≥10%；
- 4096 shots 保留 ≥80% exact 增益；
- 未过门不得声称量子优势。

### 8.4 Oracle 专用路由器

对外名称：

```text
Oracle-aware noise-weighted window router
```

严格范围：

- 输入已经分解为 1/2-qubit gates；
- 静态 Boolean Oracle；
- 连通 gate-model coupling graph；
- 只做 initial placement、SWAP 插入和 layout 更新；
- 不做动态电路、脉冲、串扰或任意自定义门。

强基线：

- BasicSwap；
- LookaheadSwap；
- Qiskit Sabre/LightSABRE；
- preset level 3；
- 小规模 exact/A* 可行时启用。

最低门：

- connectivity 和 gate-set 100%；
- 小规模 Operator/穷举等价 100%；
- 等墙钟至少一项主要指标显著优于 SABRE；
- 另一项 2Q count/depth 中位退化 ≤5%；
- noisy success 提升 ≥2 个百分点，或 noise proxy 与成功率显著相关。

### 8.5 受限 LLM Agent

Agent 只负责：

- 读取案例和 schema；
- 生成受约束实验计划；
- 调用 plan validator；
- 提交需要审批的 experiment plan；
- 读取 verified summary；
- 解释 verifier failure；
- 生成带 evidence link 的结果说明。

禁止：

- 任意 shell；
- 任意路径文件读写；
- 修改源码、数据集、验证器和 checkpoint；
- 删除/覆盖实验；
- 读取密钥；
- 自己判定实验成功。

关键门：

- 未授权动作率 0；
- 审批绕过率 0；
- hallucinated-success rate 0；
- 数值结论 evidence link rate 100%。

### 8.6 Web UI

建议页面：

1. Dashboard；
2. Oracle Workbench；
3. Live Run；
4. Experiments & Compare；
5. Evidence；
6. Offline Demo。

建议技术：

- FastAPI；
- SQLite WAL + 独立 worker；
- REST + SSE；
- React + TypeScript + Vite；
- Cytoscape.js；
- Apache ECharts；
- Playwright。

UI 只读统一 artifact bundle，不能在浏览器中生成另一套指标。

## 9. 服务器环境

### 9.1 建议资源

```text
OS: Ubuntu 22.04 / 24.04
Python: 3.11
CPU: >=16 vCPU
RAM: >=64GB
SSD: >=200GB free
GPU: NVIDIA, >=24GB VRAM recommended
```

若正式并行训练扩散/GFlowNet，建议 48GB VRAM 或独立训练节点。

### 9.2 依赖分组

```text
experiments/environment/requirements/core.txt
experiments/environment/requirements/dev.txt
experiments/environment/requirements/quantum.txt
experiments/environment/requirements/research.txt
experiments/environment/requirements/server.txt
```

当前测试只验证 core + dev。quantum/research/server 是下一阶段环境契约，不代表
对应功能已经存在。

### 9.3 一键核心环境

```bash
git clone git@github.com:zhouzixiang1/xa202609-oracle.git
cd xa202609-oracle
./scripts/bootstrap_server.sh
```

可选组：

```bash
XA_INSTALL_QUANTUM=1 ./scripts/bootstrap_server.sh
XA_INSTALL_RESEARCH=1 ./scripts/bootstrap_server.sh
XA_INSTALL_SERVER=1 ./scripts/bootstrap_server.sh
```

NVIDIA 服务器应先按 CUDA 版本安装正确的 PyTorch wheel；不要直接复制 macOS
MPS 环境。

### 9.4 当前本机环境参考

```text
Python             3.11.15
torch              2.12.0
numpy              2.4.6
scipy              1.17.1
PuLP               3.3.1
pytest              9.0.3
scikit-learn       1.9.0
```

主环境当前没有 Qiskit、Aer、Qiskit ML、TorchGFN、FastAPI 或前端依赖。

## 10. GPU 接手注意

当前代码不会自动使用服务器 GPU：

- `FoundationScorer` 默认 CPU；
- 旧 `NeuralScorer` 默认 CPU；
- Expert Iteration 当前以 CPU/单进程逻辑为主。

服务器第一轮性能改造应增加：

- `--device cpu|cuda|mps|auto`；
- checkpoint `map_location` 契约；
- batch size；
- data loader workers；
- search process count；
- BLAS/OpenMP thread 上限；
- GPU/CPU 混合流水线；
- OOM 降级和可重入 checkpoint。

不要在设备支持之前，仅凭“服务器有 GPU”宣称训练已加速。

## 11. 实验与 provenance 契约

每次运行至少生成：

```text
results/xa202609/<run_id>/
├── run.json
├── raw.jsonl
├── summary.json
├── verifier.json
├── events.jsonl
├── stdout.log
├── stderr.log
├── artifacts.manifest.json
└── checksums.sha256
```

`run.json` 至少包含：

- source commit；
- dirty patch hash；
- Python、OS、CPU/GPU、依赖锁；
- dataset hash 和 split；
- config；
- seed；
- checkpoint hash；
- exact argv；
- start/end；
- fallback/repair；
- verifier version。

实验状态：

```text
DRAFT
→ VALIDATED
→ AWAITING_APPROVAL
→ QUEUED
→ RUNNING
→ VERIFYING
→ SUCCEEDED
```

异常：

```text
FAILED_TRANSIENT
FAILED_SEMANTIC
NEEDS_REVIEW
CANCELLED
```

只有 verifier 通过的运行能进入最终报告。

## 12. 当前已知技术陷阱

### 12.1 资源权重

正式口径：

```python
ResourceWeights(
    t=1.0,
    cnot=0.04,
    depth=0.015,
    gates=0.01,
    ancilla=2.0,
)
```

裸 `SearchConfig()` 的默认 CNOT/depth 权重不同。正式脚本必须显式传值。

### 12.2 `SynthesisResult` 丢失详细对象

这是最优先接口瓶颈，见第 7 节。

### 12.3 声明变量宽度

`FoundationScorer.required_num_vars()` 当前从活跃 terms/actions 最高 bit 推断
宽度。声明但未出现在当前 ANF 的变量可能丢失。统一 IR 必须显式保留
`n_declared`。

### 12.4 action cache

当前 action cache key 没有覆盖全部 config/weights。跨配置复用同一 scorer
前必须扩充 key 或清 cache。

### 12.5 候选池因 prior 改变

神经 prior 排序发生在 `candidate_top_k` 截断之前。错误排序会真实改变候选池，
公平消融必须冻结预算并单独比较 prior、widening 和 value。

### 12.6 value 范围保护

`LearnedValueEstimator` 不高于 direct feasible score 的保护不是 admissible
lower bound，也不是最优性证明。

### 12.7 旧 `circuit_resource_cost`

`synthesizers.py` 中一个旧 helper 的 depth 路径会得到 0，当前主路径未使用。
新硬件层不得复用，应以实际 scheduled circuit 重新计算。

### 12.8 实验 runner 路径

本次迁移已修复 `scripts/run_experiments.py` 的默认模型/结果目录，使其指向
项目根的 `models/` 和 `results/`，不再错误指向 `scripts/` 子目录。

### 12.9 AES 脚本

本次迁移已把 AES benchmark：

- 从影子 `src.bool_func` 切换到 `src.sshr_lib.bool_func`；
- 改为显式竞赛资源权重；
- 增加输出目录创建。

旧 AES 结果仍不能自动升级为 XA 正式证据，必须按冻结协议重跑。

## 13. 安全、隐私和许可证

### 13.1 不能进仓库

- API keys；
- 天衍平台 token；
- Gurobi license；
- 报名表；
- 个人邮箱、电话、邮寄地址；
- `.env`；
- 本机 Conda 绝对路径；
- 第三方构建缓存；
- 私人投稿 metadata answers。

### 13.2 当前许可证风险

当前没有闭环的项目级开源许可证。新仓库必须保持 private。

`src/sshr_lib/` 的内部迁移链已记录，但初始作者和再分发权仍待人工确认。
竞赛共同 IP 条款不能替代第三方许可证审计。

### 13.3 对外声明边界

不得声称：

- 量子优势；
- 指数加速；
- 真机效果；
- 通用量子路由器；
- 全局 Pareto 最优；
- QNN 优于经典 AI；
- GFlowNet 或扩散必然优于 NMCTS；
- 支持所有超导、离子阱和光量子设备。

除非相应证据、统计和适用边界已经形成。

## 14. Git 工作流

新服务器仓库建议：

```text
main                       # 通过验收的集成状态
codex/contracts-ir         # 统一契约
codex/qaoa-scheduler       # QAOA 调度
codex/native-noise         # 原生门与噪声
codex/gflownet             # GFlowNet
codex/discrete-diffusion   # 离散扩散
codex/qnn-value            # QNN residual
codex/oracle-router        # 自研路由器
codex/agent-ui             # Agent 和 UI
```

规则：

- 每条轨单独 PR；
- 每个 PR 带测试、实验 schema 和退出门；
- 禁止 `git add -A` 混入 raw、私有数据和缓存；
- 大模型和 raw 使用 artifact storage；
- 合并前跑 core tests、smoke、secret scan 和文件体积检查。

## 15. 建议 CI

第一版 GitHub Actions：

1. Python 3.11；
2. 安装 `experiments/environment/requirements/dev.txt`；
3. import smoke；
4. `pytest tests -q`；
5. 独立 `python tests/tests_smoke.py`；
6. 检查 >20MB 新文件；
7. 检查绝对路径和 secrets；
8. 检查 `docs/contracts/COMPETITION_ACCEPTANCE_MATRIX.json` schema。

量子和 UI 测试使用可选 job，避免阻塞 core；进入正式集成后再升为 required。

## 16. 服务器开发顺序

### Phase 0：接手冻结

- 克隆私有仓库；
- 验证 SHA；
- 建立 Python 3.11 环境；
- 跑 36 tests + smoke；
- 记录服务器硬件和 CUDA；
- 建立 CI；
- 冻结环境 lock。

### Phase 1：共同底座

- `DetailedSynthesisResult`；
- `PlanTrace` / `PlanTensor`；
- `NativeCircuitIR`；
- `HardwareProfile`；
- `ExperimentManifest`；
- `ArtifactBundle`；
- verifier 和 deterministic hash。

### Phase 2：原目标主链

- 唯一等变模型冻结；
- C0–C7；
- QAOA 五路调度；
- native decomposition；
- Qiskit SABRE baseline；
- Aer ideal/shot/noisy；
- held-out feedback。

### Phase 3：六条扩展轨

- GFlowNet；
- discrete diffusion；
- QNN residual；
- Oracle router；
- Agent；
- UI。

各轨两轮调参仍不过门即停止扩张，保留负结果。

### Phase 4：竞赛实验

- 随机 ANF；
- 稀疏/稠密结构函数；
- AES、SM4、PRESENT、ASCON 坐标；
- ID/OOD；
- 3–5 seeds；
- 固定终端评价次数和 wall-clock；
- raw/summary/manifest/verifier；
- bootstrap CI、Pareto HV、W/L/T。

### Phase 5：交付

- 竞赛 CLI；
- 本地 UI；
- 离线 demo；
- 技术报告 PDF；
- 使用文档；
- PPT；
- staging；
- SBOM；
- checksum；
- 解包 verifier；
- 最终白名单压缩包。

## 17. 接手后第一天清单

```bash
git clone git@github.com:zhouzixiang1/xa202609-oracle.git
cd xa202609-oracle
git rev-parse HEAD
./scripts/bootstrap_server.sh

cd resource_nmcts
python scripts/run_experiments.py --help
python scripts/run_aes_sbox_benchmark.py --help
```

然后记录：

```text
uname -a
python --version
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
python -m pip freeze
```

在上述验证完成前，不启动长训练。

## 18. 接手验收表

| 项目 | 接手时预期 |
|---|---|
| 私有仓库可克隆 | 必须 |
| 无旧 2GB Git 历史 | 必须 |
| 无私人 metadata answers | 必须 |
| 无 API key/许可证 | 必须 |
| 核心 import | 通过 |
| pytest | 36 passed |
| standalone smoke | `smoke ok` |
| v3 checkpoint SHA | 匹配 |
| README 与状态文件 | 当前且一致 |
| QAOA/native/noise | 明确标记未实现 |
| 六条扩展轨 | 明确标记未实现与退出门 |
| 历史大数据 | 有本机归档索引 |

## 19. 权威文档顺序

出现冲突时按以下顺序理解：

1. `../contracts/COMPETITION_ACCEPTANCE_MATRIX.json`：最终完成判据；
2. `PROJECT_BLUEPRINT_XA202609.md`：总体目标、路线和实验；
3. `ARCHITECTURE_DECISIONS_XA202609.md`：已确认范围；
4. `PROJECT_STATUS_XA202609.md`：当前事实；
5. 本接手报告：服务器迁移和开发顺序；
6. `TECHNICAL_DESIGN.md`：技术候选规格；
7. `RESEARCH_PLAN_AI4Q_Q4AI.md`：历史研究规划。

任何历史论文、旧结果或旧提交包都不能覆盖上述当前状态。
