# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供项目指导。

## 项目概述

**Resource-Constrained Neural MCTS Oracle Synthesis** — 基于逻辑层的 AI 搜索框架，用于布尔函数量子 Oracle 线路的资源约束综合。

核心思路：将布尔函数 Oracle 表示为 ANF/XAG 风格的符号分解方案，使用神经增强的 MCTS 搜索最优的 compute/uncompute 计划，支持 T/CNOT/Depth/Gates/Ancilla 多目标资源优化。

## 目录结构

Git 仓库根是本目录（`/Users/zhouzixiang/Desktop/tzb`），工作目录是 `resource_nmcts/`。所有命令都从 `resource_nmcts/` 下执行。

| 目录 | 用途 |
|------|------|
| `resource_nmcts/src/` | 核心库（anf_utils, resource_model, factor_plan, nmcts_solver, neural_policy, synthesizers 等，共 ~4700 行） |
| `resource_nmcts/src/sshr_lib/` | 自包含的 SSHR 依赖（平行多面体枚举、SSHR-H/I/Beam 基线、MCT 成本表，~1500 行） |
| `resource_nmcts/scripts/` | 运行和训练脚本（18 个 `run_*.py`, 8 个 `train_*.py`） |
| `resource_nmcts/analysis/` | 123 个只读 CSV 的分析/审计脚本（`analyze_*.py`） |
| `resource_nmcts/submission/` | 投稿工具（`make_*`, `validate_*`, `rebuild_*`） |
| `resource_nmcts/tests/` | 冒烟测试（`tests_smoke.py`） |
| `resource_nmcts/models/` | 18 个训练好的 PyTorch 模型（`.pt`）+ 3 个门控配置（`.json`） |
| `resource_nmcts/results/` | 实验数据（166 个 raw CSV, summary, manifest, analysis md） |
| `resource_nmcts/paper_latex/` | 英文投稿（ACM TQC 格式，三套：v1/anonymous/acm_tqc） |
| `resource_nmcts/paper_latex_zh/` | 中文手稿（v2~v40 历史版本，最新 v40） |
| `resource_nmcts/submission_package/` | 投稿材料包（`dist/*.tar.gz` 是最终产物） |
| `resource_nmcts/benchmark_exports/` | 导出的基准文件（BLIF, PLA, truth-JSON，给外部工具链） |
| `resource_nmcts/tools/` | mockturtle BLIF→XAG C++ 探针 |

归档项目在 `_archive/` 目录（只读参考，含此前 4 个研究轨道）。

## 开发环境

| 环境 | 解释器路径 | 用途 |
|---|---|---|
| `mcts-qoracle` | `/opt/anaconda3/envs/mcts-qoracle/bin/python` | 核心合成、训练、大部分脚本 |
| `sshr` | `/opt/anaconda3/envs/sshr/bin/python` | ILP/Gurobi 相关脚本 |

Gurobi 仅安装在 `sshr` 环境，许可证路径 `~/.gurobi/gurobi.lic`。

## 常用命令

### 导入测试

```bash
cd resource_nmcts
/opt/anaconda3/envs/mcts-qoracle/bin/python -c "
from src.synthesizers import synthesize
from src.resource_model import ResourceWeights
from src.factor_plan import SearchConfig
print('All imports OK')
"
```

### 冒烟测试

```bash
cd resource_nmcts
/opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py
```

### 运行实验

```bash
cd resource_nmcts
./scripts/run_experiments.py --preset smoke
```

### 投稿重建

```bash
cd resource_nmcts
bash submission/rebuild_submission_package.sh
```

## 核心架构

### 表示层

- **ANF（代数范式）**：布尔函数表示为 GF(2) 上的单项式集合，通过 `anf_utils.py` 的快速 Möbius 变换计算
- **分解计划**（`factor_plan.py`）：树形 compute/uncompute 结构 — 提取共享子项作为临时合取，用 logical-AND 计算，Clifford 门反计算
- **资源成本**（`resource_model.py`）：多目标成本模型（T, CNOT, Depth, Gates, Ancilla），可配置权重

### 搜索层

- **NMCTS 求解器**（`nmcts_solver.py`）：递归 PUCT/MCTS，状态 = (residual terms, prefix, ancilla count)，动作 = 分解操作
- **神经策略**（`neural_policy.py`）：3 层 MLP 动作打分器（12 维输入 → 96 隐藏 → 1 分数），用作 MCTS 的先验
- **综合器**（`synthesizers.py`）：对外统一的 `synthesize()` 接口，支持 direct_anf、greedy_factor、neural_mcts、resource_nmcts、pareto_resource_nmcts 等方法

### 扩展

- **仿射搜索**（`affine_search.py`）：可逆线性变换预条件的输入搜索
- **FPRM 搜索**：固定极性 Reed-Muller 展开搜索
- **屏幕门控**：高维函数的结构判断和深度选择策略
- **Phase/Rz 说明**：核心 `src/` 里**没有**独立的 Rz 旋转门综合后端。"phase" 仅以三种形式出现：(1) FPRM 输入极性搜索（Reed-Muller 固定极性）；(2) 相对相位 Toffoli 成本选项（2 控制 T=4 而非 7）；(3) `logical_and` 门模式（低 T compute + 0-T uncompute）。高精度旋转综合（Ross-Selinger 级）不在引擎内，相关分析在 `analysis/` 目录。

### 基线后端

- **SSHR-H/SSHR-I/SSHR-Beam**（`src/sshr_lib/`）：基于平行多面体的贪心、ILP（Gurobi）、束搜索综合。只有 SSHR-H 和 SSHR-Beam 进了 `synthesize()` dispatch；SSHR-I 因依赖 Gurobi 走独立外部脚本
- **ESOP MILP**（`esop_milp.py`）：精确 ESOP 求解器（SciPy milp，纯 Python 无需许可证）
- **Cube Search**（`cube_search.py`）：ESOP 风格立方体搜索
- **外部工具链**：ABC AIG/XAG/LUT, mockturtle, CirKit, RevKit, Caterpillar (通过 `scripts/run_external_baselines.py`)

## 关键设计决策

- 项目**不依赖**外部 `src/sshr/` 目录 — 所有 SSHR 依赖已复制到 `src/sshr_lib/` 并修改导入路径
- 使用 `resource_nmcts/` 作为工作目录（非 `src/`），所有脚本从项目根目录运行
- 训练模型保存在 `models/`，可通过 `NeuralScorer(model_path)` 加载
- **两套布局**：当前工作树是分层版（脚本分散在 `analysis/`/`scripts/`/`submission/`）；`submission_package/dist/*.tar.gz` 是扁平版（审稿人拿到、能跑的）。rebuild/verify 脚本为扁平布局设计，在分层工作树直接跑会失败
- **逻辑层定位**：成本模型严格停留在逻辑 MCT 级（X/CNOT/MCT），不做硬件映射/路由/噪声。depth 是 CNOT 数的顺序代理，t_depth 是 `(T+3)//4` 的阶段代理
- 加权目标默认 `score = 1.0·T + 0.04·CNOT + 0.015·depth + 0.01·gates + 2.0·ancilla`

## 已知问题（已修复）

- ~~`src/sshr_lib/sshr_i.py:320` 裸 import `from parallelotope import`~~ → 已改为 `from src.sshr_lib.parallelotope import`（import 路径迁移遗漏）
- ~~`src/synthesizers.py:28` `STRUCTURE_GATE_MODEL` 路径 `.parent / "models"` 解析到不存在的 `src/models/`~~ → 已改为 `.parent.parent / "models"`（导致结构门控永远不加载）
- `src/bool_func.py` 是影子副本/死代码（无任何模块 import 它，引擎实际用 `src.sshr_lib.bool_func`）
- `circuit_resource_cost`（synthesizers.py）的 depth 计算恒为 0（死代码，主路径未用）
- 无 `requirements.txt`/`environment.yml`，依赖关系仅通过命令行里的 conda 绝对路径隐式表达

## 归档项目

`_archive/` 包含此前的 4 个研究轨道，仅供查阅：

| 子目录 | 内容 |
|--------|------|
| `sshr/` | 原始 SSHR 核心实现 |
| `ai-sshr-experiment/` | AI 引导 SSHR 原型（规则排序器, LightGBM, XOR-Beam） |
| `gnn-sshr/` | GNN 候选剪枝项目 |
| `rl-mcts-experiment/` | RL+MCTS 块搜索概念验证 |
| `papers/` | 参考文献 PDF |
| `tex-paper/` | 稀疏量子态制备论文 |
| `legacy-drafts/` | 早期设计文档 |
