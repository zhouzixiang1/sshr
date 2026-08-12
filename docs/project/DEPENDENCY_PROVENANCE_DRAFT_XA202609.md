# XA-202609 依赖与代码谱系草案

> 审计日期：2026-07-28
> 状态：**DRAFT / NOT A LICENSE / NOT READY FOR DISTRIBUTION**
> 适用范围：XA-202609 目标原型当前开发路径
> 快照：Git `2d264f2`；Python 3.11.15

本文只记录当前可以由源码、安装元数据和 Git 历史证明的事实。它不是许可证、
法律意见、权利人授权书或最终 SBOM，也不能替代 `LICENSE`、
`THIRD_PARTY_NOTICES`、`CODE_PROVENANCE` 和模型/数据 provenance。

## 1. 范围与判定规则

本轮范围包括：

- `experiments/src/synthesizers.py` 公开综合入口；
- foundation policy/value、NMCTS、资源模型和逻辑 QASM 路径；
- `experiments/scripts/train_expert_iteration.py`；
- 与上述路径对应的测试；
- `experiments/models/boolean_oracle_fm_v3.pt`；
- 被目标路径直接调用的 `experiments/src/sshr_lib/` 文件。

以下概念严格区分：

- **直接依赖**：目标源码直接 `import` 的第三方 Python 包；
- **加载级依赖**：即使某种方法不执行，公开入口的顶层导入仍要求包可用；
- **环境中存在**：当前环境已安装，但目标源码没有直接使用；
- **计划依赖**：设计中准备采用，但尚未选型、安装或实现；
- **内部代码谱系**：文件在本仓库中的迁移和修改历史；
- **再分发权**：权利人或上游许可证明确允许随参赛包提供源码或二进制。

“仓库中存在”“Git 作者一致”“引用了论文”都不能单独证明再分发权。

## 2. 当前直接第三方依赖

| 作用域 | import / 发行版 | 当前版本 | 当前安装来源 | 当前许可证证据 | 结论 |
|---|---|---:|---|---|---|
| foundation、训练及神经路径 | `torch` / `pytorch` | 2.12.0 | Conda | Conda 包元数据标为 BSD-3-Clause；安装内容另带 LICENSE/NOTICE，Python `METADATA` 未提供 SPDX 字段 | 直接运行依赖；最终通知必须以冻结发行包的原始许可文件为准 |
| 旧基线及公开入口加载 | `numpy` | 2.4.6 | Conda | `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | 直接加载级依赖；包含多许可证组成 |
| MILP 基线及公开入口加载 | `scipy` | 1.17.1 | pip | 项目主体为 BSD-3-Clause；安装元数据还列出 OpenBLAS、LAPACK、GCC runtime、libquadmath 等 bundled notices | 直接加载级依赖；不能把整个已安装二进制简单写成单一 SPDX |
| 测试 | `pytest` | 9.0.3 | pip | MIT | 仅开发/验收依赖，不是原型运行依赖 |

### 2.1 为什么 NumPy 和 SciPy 仍是当前公开入口依赖

`src/synthesizers.py` 在模块加载时顶层导入旧综合基线，进而加载
`src/sshr_lib/sshr_beam.py` 和 `src/esop_milp.py`。因此当前执行：

```python
from src.synthesizers import synthesize
```

会加载 PyTorch、NumPy 和 SciPy。即使只选择 `foundation_nmcts`，NumPy 和
SciPy 目前仍是公开入口的加载级依赖。若未来改为延迟导入，依赖边界必须重新
实测，不能只按设计推断。

### 2.2 依赖较窄的子路径

- foundation 文件本身只直接依赖 PyTorch；
- 训练入口只直接依赖 PyTorch；
- 逻辑 OpenQASM 导出路径只使用 Python 标准库和项目内部模块；
- 标准库不进入第三方 SBOM。

## 3. 不应误列为当前直接依赖的组件

| 组件 | 当前环境/源码状态 | 当前结论 |
|---|---|---|
| Qiskit | 未安装，QAOA/原生门路径尚未选型 | 计划依赖；选型冻结前不得写入当前依赖清单 |
| Qiskit Aer | 未安装，含噪仿真尚未实现 | 计划依赖；选型冻结前不得写入当前依赖清单 |
| PuLP 3.3.1 | 已安装，目标范围源码未直接导入 | 环境包，不是当前目标路径直接依赖 |
| scikit-learn 1.9.0 | 已安装，目标范围源码未直接导入 | 环境包，不是当前目标路径直接依赖 |
| gurobipy | 当前环境未安装；仅旧 SSHR-I 可选路径使用 | 不进入主原型直接依赖；不得打包本机 Gurobi 许可证 |
| ABC、RevKit、CirKit 等 CLI | 外部或历史工具 | 不属于当前 Python 直接依赖；若未来纳入须单独记录安装与许可 |

QAOA、原生门和含噪仿真实现完成后，必须重新从实际 import、锁文件和安装产物
生成依赖清单，不能提前把预期 SDK 当作已验证事实。

## 4. `src/sshr_lib` 内部代码谱系

当前 8 个活动文件在提交 `85c4d01` 中从本仓库既有路径迁入
`experiments/src/sshr_lib/`。Git copy/rename 检测得到：

| 当前活动文件 | 仓库内部来源路径 | Git 相似度 | 可确认事实 |
|---|---|---:|---|
| `baselines.py` | `sshr/baselines.py` | R97 | 主要变化为命名空间导入 |
| `block_synth.py` | `gnn-sshr/src/sshr_core/block_synth.py` | R97 | 主要变化为命名空间导入 |
| `bool_func.py` | `gnn-sshr/src/sshr_core/bool_func.py` | R100 | 仓库内部精确复制 |
| `parallelotope.py` | `gnn-sshr/src/sshr_core/parallelotope.py` | R100 | 仓库内部精确复制 |
| `parallelotope_enum.py` | `sshr/parallelotope_enum.py` | R98 | 主要变化为命名空间导入 |
| `sshr_beam.py` | `sshr/sshr_beam.py` | R97 | 文档将 Beam Search 记录为本项目扩展 |
| `sshr_h.py` | `sshr/sshr_h.py` | R92 | 文档记录了与论文候选集定义的实现差异 |
| `sshr_i.py` | `sshr/sshr_i.py` | R97 | 此后另有求解、超时、warm-start 和导入修复等修改 |

这些内部来源路径最早只能追溯到初始提交 `497dc2c`。现有仓库没有提供该提交
之前的：

- 初始作者与贡献者声明；
- 上游代码仓库、版本或下载地址；
- 软件许可证、NOTICE 或书面授权；
- 是否使用论文附件、网页代码、私有代码或其他外部实现的说明；
- AI 辅助生成与改写范围；
- 学校、雇主、团队或资助项目对代码权利的确认。

仓库中的论文引用和 Algorithm/Lemma/Table 锚点能够证明算法思想来源，但不能
替代软件再分发许可。

### 4.1 当前合规结论

> 仓库内部复制和后续修改历史已经确认；外部源码来源没有被证实；初始作者、
> 权利归属和再分发授权尚待人工确认。

因此：

- 不能把这 8 个文件直接定性为未经许可复制的外部代码；
- 也不能凭初始提交、后续修改或 Git 作者信息认定其全部为独立原创；
- 不能通过给仓库新增一个 MIT `LICENSE`，自动解决这些文件的权利问题；
- 在来源闭环前，不得把该目录标为“已完成第三方合规”。

## 5. 模型组件状态

当前开发候选 `boolean_oracle_fm_v3.pt`：

| 项目 | 当前证据 |
|---|---|
| SHA-256 | `87904409966e6d9d18aae3711dff54d696608e6eefcf0e5cb5bb98ae96d4f57d` |
| 大小 | 254,587 bytes |
| 架构 | `in_channels=12`、`hidden=32`、`layers=2`、`mlp_hidden=128` |
| 参数量 | 60,450 |
| checkpoint 内模型 license | 未记录 |
| checkpoint 内训练命令、seed、split、日志、源码 SHA | 未记录 |
| 数据来源与再分发声明 | 未冻结 |

该 checkpoint 只能作为开发候选，不能作为最终可复现模型。最终模型必须由冻结
训练流程生成，并用模型卡、数据卡、训练 manifest 和 checksum manifest 共同
证明来源与可复现性。

## 6. 最终需形成的不同文件

这些文件职责不同，不得相互替代：

| 文件 | 作用 |
|---|---|
| `LICENSE` | 仅覆盖权利人确认可以按该许可证授权的项目内容 |
| `THIRD_PARTY_NOTICES.md` | 记录已确认第三方组件、版本、来源、许可证和必要通知 |
| `CODE_PROVENANCE.md/json` | 记录内部迁移、初始作者、外部来源、AI 辅助、修改历史、权利人与批准 |
| `SBOM.json` | 记录冻结环境中实际交付或安装的直接与传递依赖 |
| `MODEL_CARD.md/json` | 记录模型用途、结构、训练域、指标、限制和许可证 |
| `DATA_CARD.md/json` | 记录训练、验证、测试数据的生成方式、来源、切分、hash 与许可 |
| `CHECKSUMS.sha256` | 绑定最终源码、模型、数据、报告和归档内容 |

`THIRD_PARTY_NOTICES` 只能说明已经确认的第三方内容，不能修复来源未知代码的
再分发权；项目 `LICENSE` 也只能覆盖权利人有权授权的部分。

## 7. 闭环动作

### 7.1 需要负责人/初始作者人工确认

1. `497dc2c` 中初始 `sshr/*.py` 的实际作者和贡献者；
2. 是否复制、翻译或改写过论文附件、作者私下代码、网页代码或其他仓库；
3. 若使用外部代码，其 URL、版本、许可证和必要书面授权；
4. AI 在初始生成和后续修改中的具体范围；
5. 学校、雇主、团队、资助项目与竞赛条款下的权利归属和许可权限。

### 7.2 根据确认结果处理

- 若确认是团队基于论文独立实现：形成签字或批准的 provenance 声明，记录论文
  引用、作者、贡献、AI 辅助和关键提交；
- 若确认使用了外部代码：按文件记录上游和许可证，履行署名、通知、源码提供等
  义务；
- 若无法确认或无法获得授权：从论文的公开数学定义/伪代码进行洁净室最小重写，
  保留需求隔离、独立实现、语义测试和回归证据；
- 只有权属和来源闭环后，才由有权主体选择项目许可证。

### 7.3 工程闭环

1. 冻结最终 Python 和量子 SDK 选型；
2. 建立权威安装文件和可锁定环境；
3. 从干净环境生成直接/传递依赖 SBOM；
4. 保存每个冻结发行包的原始许可证与通知；
5. 冻结唯一模型、训练 manifest、数据卡和 checksum；
6. 在独立白名单 staging 中构建参赛 ZIP；
7. 对最终 ZIP 执行 clean-install、端到端、许可证、隐私、secret、路径和清单校验。

## 8. 当前放行结论

| 门 | 当前状态 | 放行条件 |
|---|---|---|
| 当前直接依赖识别 | **初步完成** | 功能与环境冻结后重新生成 |
| 传递依赖与最终 SBOM | **未完成** | 锁定环境并在干净环境解析 |
| `sshr_lib` 仓库内部谱系 | **完成** | 保留文件级证据 |
| `sshr_lib` 初始来源与再分发权 | **阻断** | 人工确认、外部许可或洁净室替代 |
| 项目许可证 | **阻断** | 权属确认后由有权主体批准 |
| 模型/数据 provenance | **阻断** | 冻结训练、数据、模型和许可记录 |
| 最终提交包合规 | **阻断** | 所有上述门关闭且最终 ZIP verifier 通过 |

在这些阻断项关闭前，本文件不得改名或表述为“最终 SBOM”“许可证已完成”或
“可直接提交”。
