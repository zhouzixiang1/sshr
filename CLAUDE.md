# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供项目指导。

## 项目概述

**Resource-Constrained Neural MCTS Oracle Synthesis** — 基于逻辑层的 AI 搜索框架，用于布尔函数量子 Oracle 线路的资源约束综合。

核心思路：将布尔函数 Oracle 表示为 ANF/XAG 风格的符号分解方案，使用神经增强的 MCTS 搜索最优的 compute/uncompute 计划，支持 T/CNOT/Depth/Gates/Ancilla 多目标资源优化。

## 目录结构

| 目录 | 用途 |
|------|------|
| `src/` | 核心库（neural_policy, nmcts_solver, synthesizers, factor_plan 等） |
| `src/sshr_lib/` | 自包含的 SSHR 依赖（平行多面体枚举、SSHR-H/I/Beam 基线、MCT 成本表） |
| `scripts/` | 运行和训练脚本（`run_*.py`, `train_*.py`） |
| `analysis/` | 123 个分析/审计脚本（`analyze_*.py`） |
| `submission/` | 投稿工具（`make_*`, `validate_*`, `rebuild_*`） |
| `tests/` | 测试文件 |
| `models/` | 21 个训练好的 PyTorch 模型 |
| `results/` | 实验数据（CSV, JSON, Markdown） |
| `paper_latex/` | 英文投稿（ACM TQC 格式） |
| `paper_latex_zh/` | 中文手稿（v6~v40 历史版本） |
| `submission_package/` | 投稿材料包 |
| `benchmark_exports/` | 导出的基准文件（BLIF, PLA, JSON） |

归档项目在 `_archive/` 目录（只读参考）。

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
- **Phase/Rz 后端**：逻辑层到相位旋转的映射
- **屏幕门控**：高维函数的结构判断和深度选择策略

### 基线后端

- **SSHR-H/SSHR-I**（`src/sshr_lib/`）：基于平行多面体的贪心和 ILP 综合
- **ESOP MILP**（`esop_milp.py`）：精确 ESOP 求解器
- **Cube Search**（`cube_search.py`）：ESOP 风格立方体搜索
- **外部工具链**：ABC AIG/XAG/LUT, mockturtle, CirKit, RevKit, Caterpillar (通过 `scripts/run_external_baselines.py`)

## 关键设计决策

- 项目**不依赖**外部 `src/sshr/` 目录 — 所有 SSHR 依赖已复制到 `src/sshr_lib/` 并修改导入路径
- 使用 `resource_nmcts/` 作为工作目录（非 `src/`），所有脚本从项目根目录运行
- 训练模型保存在 `models/`，可通过 `NeuralScorer(model_path)` 加载

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
