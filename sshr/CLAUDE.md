# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 运行环境

所有脚本均在 `mcts-qoracle` conda 环境下运行。由于 `conda run` 在此机器上存在权限问题，请使用直接路径：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python <script>.py

# 运行测试套件
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests/ -v

# 关键实验示例
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 8
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 5 --n 3 4 5 6
```

---

## 目录结构与文件说明

```
sshr/
├── 核心算法（根目录）
├── analysis/          调试阶段分析脚本
├── experiments/       论文复现与对比实验
│   ├── greedy/        SSHR-H 贪心启发式实验
│   ├── ilp/           ILP 精确求解实验（Table VI/VII）
│   └── mcts/          MCTS / Beam 搜索实验
├── debug/             历史调试脚本（一次性用途，不维护）
├── tests/             正确性测试
├── viz/               电路可视化
└── results/           实验结果文件（CSV）
```

---

## 根目录：核心算法文件

六个核心文件构成流水线，依赖顺序如下：

### `bool_func.py`
布尔函数与量子电路的基础数据结构。
- `BooleanFunction(n, truth_table_int)` — n 变量布尔函数，由整数真值表构造；`.onset` 返回 on-set 集合
- `QuantumCircuit(n_qubits)` — 量子电路，支持 `add_mct / add_cnot / add_x / add_block / simulate`
- `mct_cost(k)` — 标准 MCT 门代价（T-count / CNOT / Ancilla）
- `mct_cost_rp(k)` — 相对相位 Toffoli 代价（k=2 时 T=4）

### `parallelotope.py`
平行多面体数据结构。
- `Parallelotope(v0, basis)` — 由起点 v0 和基向量列表定义的 m 维平行多面体
- `.vertices()` — 返回 frozenset，包含 2^m 个顶点（XOR 展开）
- `.dim` — 平行多面体的维度
- 合法性条件：任意两个基向量的支撑集（非零位）不相交（Lemma 1）

### `parallelotope_enum.py`
平行多面体枚举算法。
- `enumerate_parallelotopes(universe, n)` — 在给定点集 universe 上枚举所有合法平行多面体
- 自底向上 BFS：先找 1 维线段（2 点），再扩展到高维；按维度**降序**输出；用顶点 frozenset 去重
- 关键性能参数：n=5 约 1539 个，n=6 约 10K，n=7 约 76K，n=8 约 609K

### `block_synth.py`
Algorithm 1：平行多面体 → 量子电路块。
- `synth_block(p, n)` — 将 m 维平行多面体 p 合成为电路块：CNOT 链 + X 门 + (n−m)-MCT + X 门 + 逆 CNOT 链
- `block_cnot_cost(p, n)` — 电路块的 CNOT 代价：`2×CNOT链长度 + MCT_CNOT(n−m)`
- `block_t_cost(p, n)` — 电路块的 T 代价：`MCT_T(n−m)`（控制位 <2 时为 0）
- `block_t_cost_rp(p, n)` — 使用相对相位 Toffoli 的 T 代价

### `sshr_h.py`
**Algorithm 2：SSHR-H 贪心启发式合成。**
- `sshr_h(bf, R=3/4)` — 对布尔函数 bf 进行合成，返回 QuantumCircuit
- 候选集 S 一次性从**全超立方体** {0..2^n-1} 枚举（`_full_hypercube_parallelotopes`，lru_cache 缓存）
- 每步选满足 `|A ∩ P| / |P| ≥ R` 的最高维候选；用 `A ^= vertices(P)` 更新（XOR 语义）
- 无候选时退出循环，剩余点以 dim-0 单点（n-MCT）处理
- **与论文差异**：论文 S 从当前 onset A 枚举（严格子集）；此实现用全超立方体，n≤6 时效果更好（−13%∼−17% T/CNOT），n≥7 时因 XOR 污染级联反而变差（+22%∼+30%）

### `sshr_i.py`
**Algorithm 3：SSHR-I ILP 精确求解。**
- `sshr_i(bf, objective="cnot", timeout=120)` — ILP 求解器合成，目标为 min CNOT 或 min T
- 建模为 WP-SCP（加权奇偶集覆盖问题）：on-set 每点覆盖奇数次，off-set 覆盖偶数次
- 仅使用 Gurobi；n≥6 时 ILP 不可行（超时）
- T 目标使用相对相位 Toffoli（T=4 for k=2）两阶段优化

### `sshr_mcts.py`
**SSHR-MCTS v1：UCT 蒙特卡洛树搜索（旧版，仅保留兼容）。**
- `sshr_mcts(bf, n_iter=500, ...)` — 介于 SSHR-H 和 SSHR-I 之间的折中方法
- **单调缩减语义**：约束 `vertices(P) ⊆ A`，A 严格缩小
- Rollout：Python 循环逐一检查 frozenset.issubset()，n=7 时约 28ms/rollout
- 渐进拓宽：`max_children = ceil(C_pw × N^alpha)`（默认 C_pw=2.0, alpha=0.5）

### `sshr_mcts_v2.py`
**SSHR-MCTS v2：Numpy 加速版 UCT（推荐使用）。**
- `sshr_mcts_v2(bf, n_iterations=1000, epsilon=0.0, n_rollouts=1, ...)` — drop-in 替代 v1
- **关键加速**：预计算 numpy 数组（P_lo, P_hi, P_sizes, P_costs），用 `(P & A) == P` 向量化有效性检验，n=7 时 rollout 19x 加速 → 总体 4-5x 加速
- **ε-greedy rollout**：epsilon>0 时随机探索动作（epsilon=0.1 时 T 额外改善 ~1%）
- 对比 sshr_h_paper：n=5 +3.4% T/+9.3% CNOT，n=6 +5.5%/+11.9%，n=7 +9.6%/+14.9%

### `sshr_beam.py`
**SSHR-Beam：Beam Search 合成（新增）。**
- `sshr_beam(bf, width=50, branch=10, objective='cnot')` — 宽度优先搜索
- 维护 `width` 条候选路径；每步为每条路径扩展最优 `branch` 个动作；按 (实际代价 + 贪心下界) 剪枝保留 top-k
- **优势**：n=5 比 mcts_v2 更快更好（T=3576 vs 3608）；n=6 beam(w=50,b=10) T=6920 优于 mcts_v2 T=7032
- **参数建议**：n≤6 用 width=50, branch=10；n=7 用 width=20, branch=5

### `baselines.py`
ESOP 和 XAG 基线合成方法，用于与 SSHR 对比。
- `esop_synth(bf)` — ESOP（积和式）合成，直接对 on-set 中的每个 product term 生成 MCT 门
- `xag_synth(bf)` — XAG（Xor-And-Inverter Graph）合成，借助辅助量子比特存储中间结果

### `esop_ilp.py`
ESOP ILP 精确求解，用于对比实验。
- 用 3^n 个 product-term cube 作为候选集，最小化 CNOT 数
- 证明 SSHR-I ≤ ESOP-ILP（SSHR 表示能力严格包含 ESOP）

### `npn_reps_n4.py`
n=4 的 222 个 NPN 规范代表元（预计算常量）。
- `NPN_REPS_N4` — 列表，包含 222 个真值表整数，覆盖 n=4 全部等价类
- 用于 n=4 的标准化对比实验（论文使用 221 个非零代表元）

---

## analysis/：分析脚本

开发过程中用于诊断和逼近论文结果的一次性脚本，不作为正式实验入口。

### `analysis/approach_paper.py`
系统测试各种改进策略，逼近论文 Table V/VI 数值。
- 策略 A：当前 sshr_h.py 实现
- 策略 B：从 A 内枚举 + 多种排序键（dim→T、cov→T 等）
- 策略 C：全超立方体 + 修正（无 fallback）+ 多种排序键
- 策略 D/E：互补函数技巧（|onset|>2^(n-1) 时先合成 NOT(f)）
- 策略 F：不同 R 阈值（0.5 ∼ 1.0）

### `analysis/diagnose_candidates.py`
诊断为何 tie-breaking 策略无效。
- 核心发现：`enumerate_parallelotopes(list(A), n)` 要求所有顶点在 A 内，排除了含 off-set 顶点的高效结构

### `analysis/analyze_sshr_h.py`
深度解析 SSHR-H 复现结果，逐函数分析门分布。

### `analysis/tiebreak_study.py`
研究不同 tie-breaking 策略（dim、T-cost、CNOT-cost、覆盖数等）对 n=3,4 结果的影响。

---

## experiments/：论文复现实验

### `experiments/run_tables.py`
主实验入口，复现论文 Table IV/V/VI/VII/VIII。
- `--tables 4 5 6 7 8`：指定运行哪些表
- `--n 3 4 5 6`：指定变量数
- `--seed 42`：随机种子（n≥5 时生成 2000 个随机函数）
- Table VIII（候选集大小）精确匹配论文

### `experiments/greedy/run_sshrh_n56.py`
专门运行 n=5,6 的 SSHR-H（2000 随机函数），对应 Table IV/V。

### `experiments/ilp/run_npn_n4.py`
对 n=4 的 221 个非零 NPN 代表元运行 SSHR-I，对应 Table VI n=4。

### `experiments/mcts/mcts_vs_greedy.py`
MCTS vs SSHR-H 大规模对比，n=3..8，每组 50 个随机函数。

### `experiments/ilp/mcts_ilp_gap.py`
MCTS vs ILP 差距分析，证明 SSHR-I 的最优性。

### `experiments/reproduction_summary.py`
全面复现报告（n=3,4），输出与论文各表的对比摘要。

### `experiments/run_mcts_eval.py`
MCTS 评估脚本，支持 `--n` 参数指定变量数。

### `experiments/evaluate.py`
通用评估函数，计算 T/CNOT/Ancilla 代价并与基线对比。

### `experiments/final_report.py`
生成最终复现报告，汇总所有算法在各 n 下的表现。

### `experiments/ilp/run_table6_n5.py`、`run_table7_n3.py`、`run_table7_n4.py`、`run_table7_n4_v2.py`
分别运行 Table VI（CNOT objective）和 Table VII（T objective）的单独实验脚本。

### `experiments/quick_*.py`
快速验证脚本，用于快速检查单个 n 的结果，无需跑完整 2000 个函数：
- `ilp/quick_n4.py`、`ilp/quick_n5.py`、`ilp/quick_sample.py` — ILP 快速验证
- `mcts/quick_mcts_compare.py`、`mcts/quick_n5_mcts.py` — MCTS 快速验证

### `experiments/ilp/run_comparison.py`、`ilp/run_n4_direct.py`
辅助对比脚本，直接输出进度信息的 n=4 SSHR-I 运行。

---

## tests/：正确性测试

### `tests/test_correctness.py`
pytest 测试套件，验证所有算法的电路正确性（`circuit.simulate(x) == bf(x)` 对所有输入成立）。

### `tests/test_mcts_correctness.py`
MCTS 快速正确性验证，对 n=3 全部 255 个非零函数运行 SSHR-MCTS 并验证输出，约 30 秒。

---

## viz/：可视化

### `viz/draw_circuit_fig5b.py`
绘制论文 Fig 5b 风格的电路图，对函数 ID=0x46B9 同时展示 SSHR-H / SSHR-I / SSHR-MCTS 三种方法的电路。

### `viz/draw_circuits.py`
通用电路图绘制脚本，用 matplotlib 展示 SSHR 方法的电路结构示意图。

### `viz/*.png`
预生成的电路图：`circuit_3bit.png`、`circuit_4bit.png`（三方法对比），以及论文风格示意图 `circuit_fig1~4_*.png`。

---

## debug/：历史调试脚本（不维护）

开发过程中的一次性调试文件，包括：
- `debug_sshr_h*.py` — 调试 sshr_h.py 的各版本行为
- `check_*.py` — 验证特定性质（dim-2 结构、NPN 等价、RP-Toffoli 代价等）
- `investigate_*.py`、`profile_*.py` — 性能分析与差距调查
- `test_sshr_h*.py`、`test_ordering.py` — 早期的非正式测试

---

## 算法语义关键区别

| 算法 | 更新规则 | 语义 |
|------|---------|------|
| SSHR-H / SSHR-I | `A ← A ⊕ vertices(P)` | XOR：off-set 点可能进入 A |
| SSHR-MCTS | `A ← A − vertices(P)`，要求 `vertices(P) ⊆ A` | 单调缩减：A 严格缩小 |

## MCT 门代价（Table II）

| 控制位数 k | T-count | CNOT | Ancilla |
|-----------|---------|------|---------|
| 1（等价 CNOT）| 0 | 1 | 0 |
| 2（Toffoli） | 7（标准）/ 4（相对相位）| 6 | 0 |
| 3 | 16 | 14 | 1 |
| ≥4 | 8k−8 | 4k−6 | ⌈(k−2)/2⌉ |

## 与论文对比结论

| n | ΔT | ΔCNOT | 原因 |
|---|----|-------|------|
| 3 | −17% | −13% | 全超立方体找到含 off-set 顶点的高维 parallelotope，合成为更低代价门 |
| 4 | −9% | −11% | 同上 |
| 5 | −15% | −13% | 同上，效果更显著 |
| 6 | −14% | −15% | 同上 |
| 7 | +22% | +28% | XOR 污染级联，off-set 点大量残留为 n-MCT 单点，代价反升 |
| 8 | +30% | +38% | 同上，候选集 609K，污染更严重 |

## 注意事项

- `sshr_i.py` 需要 Gurobi；n≥6 时 ILP 超时不可行
- `enumerate_parallelotopes` 是性能瓶颈：n=6 约 10K 候选，n=8 约 609K；sshr_h.py 用 `lru_cache` 对全超立方体结果缓存，同 n 的多个函数只枚举一次
- `QuantumCircuit.simulate(input_vec)` 逐门模拟，可用于正确性验证
- n≥5 的实验默认使用 2000 个随机函数（seed=42），与论文测试集一致
