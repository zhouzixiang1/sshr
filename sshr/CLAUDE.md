# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

---

## 运行环境

脚本需在指定 conda 环境下运行，两个环境用途不同：

| 环境 | 路径 | 用途 |
|---|---|---|
| `mcts-qoracle` | `/opt/anaconda3/envs/mcts-qoracle/bin/python` | SSHR-H / MCTS / Beam / 测试 |
| `sshr` | `/opt/anaconda3/envs/sshr/bin/python` | **SSHR-I ILP（需 Gurobi）** |

`conda run` 在此机器上有权限问题，始终使用直接路径。

关键依赖：**Gurobi**（`gurobipy`）仅在 `sshr` 环境中安装。WLS Academic License ID=2742516，位于 `~/.gurobi/gurobi.lic`（已通过 `~/gurobi.lic` symlink 生效）。

---

## 目录布局规则（强制）

```
sshr/
├── *.py                   ← 核心算法库（根目录，不创建子包）
├── experiments/           ← 正式实验脚本（可复现论文结果）
│   ├── run_*.py           ← 每个脚本独立运行，命名 run_<目的>.py
│   └── checkpoints/       ← ILP 断点续传文件（自动生成，勿手改）
├── results/               ← 实验输出（CSV / TXT）
│   ├── comparison/
│   └── mcts/
├── tests/                 ← pytest 单元测试，仅测正确性
├── viz/                   ← 可视化脚本
└── _archive/              ← 废弃/调试脚本归档（保留历史，不维护）
    ├── debug/
    ├── analysis/
    └── experiments_old/
```

### 规则

1. **核心算法文件只放根目录**。新增算法直接在根目录创建 `sshr_xxx.py` 或 `xxx.py`，不建子包（会破坏现有 import）。

2. **正式实验脚本只放 `experiments/`**，命名 `run_<目的>.py`，无子目录。一个脚本对应一类实验，支持 `--n`、`--timeout` 等参数。

3. **调试/探索性脚本不放 `experiments/`**。临时脚本跑完就删，或归档到 `_archive/`，不提交到核心路径。

4. **结果输出到 `results/`**，按类别（`comparison/`、`mcts/` 等）存放，不放在 `experiments/` 里。

5. **`_archive/` 只增不减**，归档进去的文件不再编辑，历史参考用。

---

## 常用命令

```bash
# 测试（正确性验证）
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests/ -v

# Table V：SSHR-H / Beam / MCTS 对比
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 5 --n 3 4 5 6

# MCTS / Beam 对比
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/mcts_beam_compare.py --n 3 4

# Table VI / VII：SSHR-I ILP 复现（必须用 sshr 环境）
/opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_tables.py --n 3 4 --timeout 30
/opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_tables.py --n 5 --timeout 120 --cnot-only

# ILP 断点续传（进程被杀后可恢复）
# n≤4: 30s/函数；n=5: 120s/函数；n≥6: 7200s/函数（sshr_i 自适应，无需显式传 --timeout）
/opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_checkpoint.py --n 5 --objective cnot
/opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_checkpoint.py --n 6 --objective cnot --fns 20  # 建议先跑少量验证
```

---

## 核心算法文件（根目录）

### 数据结构层

**`bool_func.py`**
- `BooleanFunction(n, tt)` — n 变量布尔函数，tt 为整数真值表；`.onset` 返回 on-set 列表
- `QuantumCircuit(n_qubits)` — 量子电路，`add_mct / add_cnot / add_x / add_block / simulate`
- `mct_cost(k)` — 标准 MCT 门代价（T / CNOT / Ancilla）

**`parallelotope.py`**
- `Parallelotope(v0, basis)` — m 维平行体，起点 v0，基向量列表 basis（支撑集两两不相交）
- `.vertices()` → frozenset，共 2^m 个顶点

**`parallelotope_enum.py`**
- `enumerate_parallelotopes(universe, n)` — BFS 枚举，n=5→1539，n=6→10299，n=7→75905

### 合成层

**`block_synth.py`** — Algorithm 1：平行体 → 电路块（CNOT链 + X门 + (n−m)-MCT + 逆）
- `synth_block(p, n)` → QuantumCircuit
- `block_cnot_cost(p, n)` = 2×CNOT链 + MCT_CNOT(n−m)
- `block_t_cost(p, n)` = MCT_T(n−m)

**`sshr_h.py`** — Algorithm 2：SSHR-H 贪心启发式
- `sshr_h(bf, R=0.75)` — 每步选满足 `|A∩P|/|P| ≥ R` 的最高维候选；`A ^= vertices(P)` 更新（XOR 语义）
- 候选集从**全超立方体**枚举（`lru_cache` 缓存，同 n 只算一次）

**`sshr_h_paper.py`** — 论文严格版 SSHR-H，候选集从当前 onset A 枚举

**`sshr_i.py`** — Algorithm 3：SSHR-I ILP 精确求解
- `sshr_i(bf, objective="cnot", timeout=120)` → QuantumCircuit
- 建模为 WP-SCP（on-set 奇数次覆盖，off-set 偶数次）
- 求解器优先级：Gurobi → HiGHS → PuLP
- T 目标：两阶段（Stage1 最小化 RP-T，Stage2 固定 T 预算后最小化 CNOT）

**`sshr_mcts_v2.py`** — SSHR-MCTS v2（numpy 加速 UCT，推荐）
- `sshr_mcts_v2(bf, n_iterations=1000)` — 单调缩减语义（`vertices(P) ⊆ A`）
- numpy 向量化有效性检验，4–5x 快于 v1

**`sshr_beam.py`** — SSHR-Beam（Beam Search）
- `sshr_beam(bf, width=50, branch=10, objective='cnot')` — n≤6 优于 MCTS

**`baselines.py`** — ESOP / XAG 基准合成

**`esop_ilp.py`** — 精确 ESOP ILP（Gurobi），用于对比

### 数据层

**`npn_reps_n4.py`**
- `NPN_REPS_N4` — 222 个 NPN 代表元（含零函数），对每个等价类选 SSHR-I CNOT 代价更低的 f 或 NOT(f)
- `NPN_REPS_N4_ORIGINAL` — 原始 BFS 规范形式（参考用）
- 约定：使用 `NPN_REPS_N4` 跑 SSHR-I CNOT 目标可精确复现论文 CNOT=4696

**`paper_data.py`** — 论文 Table IV–VIII 参考数据 + 我们的复现结果

---

## experiments/ 脚本说明

**`run_tables.py`** — Table V：SSHR-H / Beam / MCTS 对比（`--tables 5 --n 3 4 5 6`）

**`run_ilp_tables.py`** — Table VI/VII：SSHR-I ILP 复现
- `--n` 指定变量数，`--timeout` 每函数 ILP 超时（n≤4 建议 30s，n≥5 建议 120s）
- `--cnot-only` / `--t-only` 只跑单一目标
- T 目标自动使用 RP-Toffoli 计数（k=2 MCT → T=4）

**`run_ilp_checkpoint.py`** — 断点续传版 ILP
- 每函数保存进度到 `checkpoints/ilp_n{n}_{obj}_fns{k}_seed{s}.json`
- 进程被杀后用 `--resume` 恢复（默认开启），`--no-resume` 重新开始

**`mcts_beam_compare.py`** — MCTS vs Beam 大规模对比

---

## 算法关键参数与对比

| 算法 | 更新语义 | n≤6 效果 | n≥7 |
|------|---------|---------|-----|
| SSHR-H | XOR（off-set 可污染 A） | −13%∼−17% vs 论文 | 超时/变差 |
| SSHR-I | XOR（ILP 精确）| 最优 | 超时 |
| SSHR-MCTS v2 | 单调缩减（A 严格缩小）| 中间 | 可用 |
| SSHR-Beam | 单调缩减 | 优于 MCTS | 慢 |

| k 控制位 | T（标准）| T（RP）| CNOT | Ancilla |
|---------|---------|--------|------|---------|
| 1（CNOT）| 0 | 0 | 1 | 0 |
| 2（Toffoli）| 7 | **4** | 6 | 0 |
| 3 | 16 | 16 | 14 | 1 |
| ≥4 | 8k−8 | 8k−8 | 4k−6 | ⌈(k−2)/2⌉ |

---

## 复现结果（已验证）

### Table VI — CNOT objective

| n | 我们 CNOT | 论文 CNOT | Δ |
|---|----------|---------|---|
| 3 | **3232** | 3232 | 0（精确匹配）|
| 4 | **4696** | 4696 | 0（精确匹配）|
| 5 | **75202** | 78562 | −4.3% |

n=4 关键：必须用 `NPN_REPS_N4`（最优互补代表元），而非原始 BFS 规范形式。

### Table VII — T objective（RP-Toffoli 计数）

| n | 我们 RP-T | 论文 RP-T | Δ | 我们 CNOT | 论文 CNOT | Δ |
|---|---------|---------|---|---------|---------|---|
| 3 | **2752** | 2832 | −2.8% | **3232** | 3579 | −9.7% |
| 4 | **4856** | 5742 | −15.4% | **4698** | 5838 | −19.5% |

两阶段 ILP 同时优于论文 T 和 CNOT，源于 Stage2 在最优 RP-T 预算下进一步最小化 CNOT。
