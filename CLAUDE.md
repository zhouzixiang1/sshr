# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在本仓库中工作提供指导。

## 仓库概述

本仓库包含量子计算领域的独立研究项目及相关扩展：

1. **`sshr/`**: 对 SSHR 算法的复现与扩展（"CNOT Oriented Synthesis for Small-Scale Boolean Functions Using Spatial Structures of Parallelotopes", Zheng等, 2025）。该代码使用平行多面体覆盖生成布尔函数的量子预言机（Oracle）线路。
2. **`tex/`**: 论文《针对稀疏量子态制备的最优线路研究》的 LaTeX 源码，采用 CjC 期刊格式及 GB/T 7714 参考文献标准。
3. **`ai_sshr_experiment/`**: AI-SSHR 实验目录，旨在利用 AI（剪枝或 Beam Search 引导）替代传统启发式搜索，而不是直接让 AI 学习量子门。

## 开发环境

必须使用 conda 解释器的绝对路径，因为该机器上的 `conda run` 存在权限问题。

| 环境 | 解释器路径 | 用途 |
|---|---|---|
| `mcts-qoracle` | `/opt/anaconda3/envs/mcts-qoracle/bin/python` | SSHR-H, MCTS, Beam search, 测试 |
| `sshr` | `/opt/anaconda3/envs/sshr/bin/python` | SSHR-I ILP, ESOP ILP (需要 Gurobi) |

**注意**：Gurobi (`gurobipy`) **仅**安装在 `sshr` 环境中。WLS 学术许可证路径为 `~/.gurobi/gurobi.lic`。

## 常用命令

### 测试
使用 MCTS 环境运行正确性测试：
```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest sshr/tests/ -v
```

### 运行实验
正式实验脚本位于 `sshr/experiments/` 目录下，输出结果保存在 `sshr/results/` 中。
```bash
# 统计平行多面体搜索空间大小 (Table VIII)
/opt/anaconda3/envs/mcts-qoracle/bin/python sshr/experiments/run_tables.py --tables 8

# 对比 SSHR-H / Beam / MCTS (Tables IV/V)
/opt/anaconda3/envs/mcts-qoracle/bin/python sshr/experiments/run_tables.py --tables 4 5 --n 3 4 5 6

# 复现 SSHR-I ILP 结果 (需要 Gurobi)
/opt/anaconda3/envs/sshr/bin/python sshr/experiments/run_ilp_tables.py --n 3 4 --timeout 30

# 支持断点续传的 ILP 运行
/opt/anaconda3/envs/sshr/bin/python sshr/experiments/run_ilp_checkpoint.py --n 5 --objective cnot
```

### 编译 LaTeX 论文
由于文档加载了 `xeCJK` 和 CjC 宏包，必须使用 XeLaTeX 编译。
```bash
cd tex
mkdir -p build
xelatex -interaction=nonstopmode -output-directory=build main_template.tex
cd build && BIBINPUTS=..: BSTINPUTS=..: bibtex main_template
cd ..
xelatex -interaction=nonstopmode -output-directory=build main_template.tex
xelatex -interaction=nonstopmode -output-directory=build main_template.tex
```

## 架构与代码结构

### 1. SSHR 实现 (`sshr/`)
`sshr/` 内部采用扁平化结构（无子包）。
- **数据与几何层 (`bool_func.py`, `parallelotope.py`, `parallelotope_enum.py`)**: 将真值表建模为整数（位掩码 = 最小项集合），通过顶点和基向量表示平行多面体。`enumerate_parallelotopes` 使用 `lru_cache` 进行缓存。
- **合成层 (`block_synth.py`)**: 将平行多面体块编译为量子线路。
- **算法层 (`sshr_*.py`)**:
  - `sshr_h.py`: 贪心启发式算法（XOR 更新语义）。
  - `sshr_i.py`: 基于 ILP 的奇偶覆盖求解器。
  - `sshr_mcts_v2.py`: Numpy 加速的 MCTS 算法（单调子集移除语义）。
  - `sshr_beam.py`: Beam search 算法（单调子集移除语义）。
- **组织规则**:
  - 在对比状态转移时，**不要**混用 XOR 语义和单调（Monotone）语义。
  - `experiments/` 目录只能包含可复现的正式脚本（如 `run_<purpose>.py`）。
  - 输出文件必须存放在 `results/` 中。
  - 临时或调试脚本应删除或移至 `_archive/`。

### 2. AI-SSHR 方案 (`AI_SSHR_DESIGN.md`)
AI-SSHR 旨在用学习到的排序器（rankers）替代 SSHR 中的人工启发式空间评估。
- **双引擎架构**:
  1. **AI-Pruned WP-SCP**: 通过 AI 打分将 ILP 候选池缩小至高价值目标及安全单例，使得大 $n$ 规模下的 WP-SCP 变得可行。
  2. **AI-Guided Beam**: 替代 Beam Search 中的手动启发式规则。
- AI 不直接学习底层的量子门序列，而是评估候选的平行多面体结构特征（如维度、重叠度、CNOT/T 成本）及其在当前 active 目标集下的效用。

### 3. LaTeX 资源 (`tex/`)
- `main_template.tex` 是单一的主文件。
- 依赖本地样式文件（`CjC.cls`, `gbt7714-numerical.bst`, `captionhack.sty`, `picins.sty`）。
- 图片存放在 `tex/figure/`。
- `build/` 目录已被 git 忽略，请勿提交生成的 PDF 或辅助编译文件。