# Resource-NMCTS — 面向量子布尔函数 Oracle 综合的资源约束神经蒙特卡洛树搜索

> 把“怎么拼一个量子 Oracle 线路”变成 AI 搜索问题：在 T-count / CNOT / 深度 / 门数 / 辅助比特这 5 个互相冲突的目标之间，自动搜索低资源、可验证的折中方案。
>
> **核心铁律**：AI 只负责“排序与调度”，正确性 100% 由数学验证保证。AI 再笨也不会产出错误线路。

本仓库包含两个交付物：
1. **期刊论文**（`resource_nmcts/paper_latex/` 英文 + `paper_latex_zh/` 中文，最新中文版为 v40）：纯逻辑层的资源约束神经 MCTS 综合器。
2. **竞赛作品**（`resource_nmcts/submission_competition/`，XA-202609 “量子+AI 双向赋能”）：在引擎上扩展合成硬件映射，做成可复现、可审计的交付。

> 本 README 是“讲清思路”的入门文档。详细的工具链/对比说明见 `resource_nmcts/README.md`（1400+ 行技术文档），完整项目指南见 `CLAUDE.md`。

---

## 一、它解决什么问题？

### Oracle 是什么

量子算法（如 Grover 搜索）里有个核心部件叫 **Oracle（神谕）**，它实现一个布尔函数 $f$ 的可逆版本：

```
|x⟩|y⟩  →  |x⟩|y ⊕ f(x)⟩
```

即：输入 $x$ 原样保留，把输出 $y$ 在 $f(x)=1$ 时翻转。给定任意布尔函数，怎么拼出实现它的可逆逻辑线路（只用 X / CNOT / 多控 Toffoli 门），这就是 **Boolean oracle synthesis**。

### 为什么是“难题”

拼这个线路要同时满足 5 个**互相打架**的目标：

| 目标 | 含义 | 为什么冲突 |
|------|------|-----------|
| **少 T 门**（T-count） | T 门需“魔法态蒸馏”，容错计算里最贵 | 想少用 T，往往得多用辅助比特 |
| **少 CNOT** | 两比特联动门，带来布线成本 | 想少 CNOT，可能 T 就变多 |
| **浅深度**（depth） | 能并行多少层，越浅越快 | 想浅，可能要重复计算 |
| **少门数** | 总积木数 | 和上面几个互相牵扯 |
| **少辅助比特**（ancilla） | 临时“工作台”量子比特，很稀缺 | 想省 T 或浅深度，往往要多借工作台 |

这不是“找一个最优解”，而是“**在 5 个冲突目标间找最好的折中**”。

### 现有方法的不足

已有工作大多**固定一种思路**：ESOP/XAG/LUT（擅长少 T，不管辅助比特）、CNOT 导向的 SSHR（CNOT 少但 T 多）、外部工具链（ABC/mockturtle/CirKit/RevKit，各有专长各管一摊）。它们把搜索空间限制在某一种表示里，难以在 5 个目标之间灵活折中。

---

## 二、整体思路（一句话 + 展开）

> **别固定思路。把“怎么拼”建模成一个大搜索问题，让 AI 在一个很大的可验证候选池里，自动找到多目标折中最好的方案。**

### 资源评分公式

用加权分数统一衡量 5 个目标（论文/竞赛用的冻结权重）：

```
score = 1.0·T + 0.04·CNOT + 0.015·depth + 0.01·gates + 2.0·ancilla
```

- **T=1.0 是锚**（魔法态蒸馏最贵，绝对主导）；
- **CNOT≈T/25、depth≈T/67**（便宜但不免费的连线/时间成本）；
- **ancilla=2.0**（持续占用资源，比单次 T 还贵）。

这套权重不是拍脑袋：`run_resource_sweep.py` 预设多套对立权重做扫描，`analyze_weight_robustness.py` 做敏感性审计验证“换权重后 T/score 优势仍成立”——结论不依赖单一权重。只有在纯 CNOT 权重下 SSHR 才反超（它是 CNOT 专精），这是诚实边界。

### 把函数变成“可搜索的状态”

输入布尔函数 $f$ 先转成 **ANF（代数正规形）**——一堆“变量相乘再异或”的项集合：

$$f = x_0x_1x_2 \oplus x_0x_1x_3 \oplus x_1x_2x_3 \oplus \dots$$

“状态” = 当前还没处理完的项集合 + 上下文（已分解几层、用了几个辅助比特）。“动作” = 选一个公因子提取分解。每走一步，项集合被拆成两个子问题，递归继续。

> 类比：像拆乱糟糟的线团，每“动作”一次抽出一根线头（因子），线团变成两个小线团再继续抽，目标是抽得越省料（资源越低）越好。

---

## 三、算法的 5 个阶段

```
布尔函数 f
   │ (转 ANF 项集合)
   ▼
[项集合] ──┐
          │ ① 神经先验给候选动作打分
          │ ② MCTS 在有限预算内探索动作组合
          │ ③ Frontier policy 选分解深度
          ▼
   [一堆候选分解方案]
          │
          ▼ ──────► ❹ 数学验证（ANF展开 / GF(2)模拟 / 真值表）
          │            ✗ 不过 → 扔掉回退
          │            ✓ 过  → 进候选池
          ▼
   [验证通过的候选池]
          │
          ├─ 普通版：按用户权重选最优
          └─ Pareto 版：5 套对立权重各搜 → Pareto 前沿 → 按权重选
                │
                ▼
          ❺ RL 预算管家：这次值得跑 Pareto 吗？（省 55.6% 开销）
                │
                ▼
   [最终线路]  ◄── 始终有 direct ANF 兜底（永不退化）
```

### 阶段 1：AI 搜索“怎么分解”（核心创新区）

三个 AI 部件协同：
- **神经动作先验**：小型 MLP（24维特征 → 128 → 128 → 128 → 1），看每个候选动作的结构特征（变量共现密度、递归降次潜力、增益效率…），给它打直觉分排序。
- **MCTS**：AlphaGo 式搜索，在有限预算（默认 96 次仿真）内探索动作组合，用 PUCT 公式在“利用已知好步”和“探索 AI 看好的新步”间平衡。
- **Frontier policy**：另一个小模型，判断当前项集合适合用多深的分解（depth-1/2/3/4）。

### 阶段 2：数学验证（铁律！最关键的设计）

**任何 AI 方案都必须过数学验证关，否则扔掉。** 三层验证：
1. **plan ANF 验证**：分解计划展开回多项式，检查是否等于原函数；
2. **GF(2) 符号模拟**：模拟每个门，检查输入/输出/辅助线吻合；
3. **完整真值表验证**：小函数把 $2^n$ 种输入全跑一遍逐点核对。

> **为什么聪明**：把“创造性（AI 搜索）”和“可靠性（数学验证）”完全解耦。AI 出错只会“没那么优”，绝不会产出错误线路。这让算法可解释、可审计——在容错要求极严的量子计算领域是巨大优势。

### 阶段 3：Pareto 归档（避免单一偏好看漏好解）

普通版用一套权重搜索。**Pareto 版故意用 5 套对立权重**（极端省 T / 极端省辅助比特 / 重 CNOT-depth / 重门数 / 均衡），各跑一遍凑出结构多样的候选池，再用“支配”关系剔除全面更差的解，得到 **Pareto 前沿**（每种折中下的最优），最后按用户真实权重挑。

### 阶段 4：RL 预算管家（fitted-Q，最明确的强化学习）

Pareto 搜索效果好但慢。一个上下文 bandit + fitted-Q 小网络看函数特征 + base 结果，决定“这次值得跑 Pareto 吗”：值就跑（搏更好），不值就停（省时间）。

### 阶段 5：始终保底（guard）

候选池永远塞一个最朴素的 baseline（direct ANF）。哪怕所有花哨搜索失败，结果也**不会比最笨的方法差**。

---

## 四、MCTS 和 Pareto 怎么结合

**Pareto 是“调度员”，MCTS 是它工具箱里的“精搜专员”之一。**

```
pareto_resource_nmcts（Pareto 搜索，外层）
   ├─ 派 5 支“口味不同”的搜索队（不同权重）
   │     └─ 每支队调用多种综合方法：
   │          • affine_nmcts / mcts_factor        ← 含 MCTS（仅 n≤10）
   │          • fprm_greedy / fprm_linear_pair …  ← 不含 MCTS 的确定性方法
   └─ 所有正确解汇总成候选池 → Pareto 过滤 → 按权重选
```

- **base `resource_nmcts`** 在 n≤10 时直接调 `mcts_factor`、`affine_nmcts`（synthesizers.py:1483, 1443）；
- **Pareto 版**在 active/t_sparse 队里调 `affine_nmcts`、`mcts_factor`（synthesizers.py:1551-1553）；
- MCTS 慢但能找到贪心找不到的好解；贪心快但可能漏。Pareto 把它们全跑一遍，解全倒进池子，让 Pareto 前沿综合各家之长。

---

## 五、消融实验：每个部件到底有多大用（基于原始 CSV）

论文专门有“搜索控制归因”章节（v40 第 511–577 行）+ 消融表 `tab:ablation`，**逐组件量化贡献**，且结论是**反过度宣称**的——主动证明 AI 贡献有限，主要功劳在搜索空间设计。

### 贡献分解（177 个 n≤6 传统函数，配对比较）

| 组件 | 消融对照 | score W/L/T | 平均 Δscore |
|------|---------|-------------|------------|
| **Affine 搜索空间** | Affine greedy vs 固定坐标 MCTS | 165/88/68 | **−12.12%** |
| → 加神经精炼 | Neural refine over affine greedy | 65/0/257 | −1.08% |
| → 加 guard | Guarded Affine-NMCTS over no-guard | 88/0/234 | −1.74% |
| **Full Affine-NMCTS** | (vs 固定坐标 MCTS) | 165/0/156 | **−14.82%** |
| **Pareto archive** | Pareto over Resource-NMCTS | 68/0/109 | **−3.26%** |
| **MCTS（净贡献）** | Resource-NMCTS vs no-MCTS portfolio | 54/0/123 | **−1.44%** |
| 神经先验 | Learned prior vs no-prior | 39/0/138 | −1.10% |
| 神经先验（随机对照） | vs 同预算随机先验均值 | 17/8/152 | −0.15% |

> **注意**：v40 正文（513 行）的 14.82% 和消融表的 −12.12% **都对，是不同对比**——前者是“Full Affine-NMCTS”（完整版，含神经+guard），后者是中间步骤“Affine greedy”（纯贪心）。它们是递进关系：贪心 −12.12% → 加神经 −1.08% → 加 guard −1.74% → 合计 −14.82%。不是数据矛盾。

**解读**：最大增益（−12~15%）来自 affine 搜索空间设计（**非 AI**）；MCTS 是增量级（−1.44%）；神经先验很小（同预算随机先验几乎打平，−0.15%）。这使论文能精确回答“你的 AI 到底有多大用”，避免被质疑过度宣称。

### fitted-Q 预算策略（最明确的 RL 贡献）

在 160 个完全没见过的测试函数上：策略只对 71 个决定跑 Pareto → **省 55.6% 昂贵搜索，保留 94.90% 质量增益**，相对 always-Pareto 的 regret 仅 0.506%。

---

## 六、实验结论（据实，不夸大）

### 强项（显著）

- 相对 direct ANF：T-count **−72.25%**，score **−67.80%**（n≤6，177 函数）。
- 相对 ESOP-MILP：score W/L/T = **167/3/7**，平均 **−29.84%**；T −32.77%。
- AES S-box 8 比特（n=8）：T-count 约减半，score 改善 48–54%。
- 中等规模真值表 n=7–12：49/49 全部正确，改善 50.5–52.87%。
- 外部工具链（ROS-LUT/mockturtle/CirKit/RevKit phase）：score 全面领先。

### 边界（项目主动承认）

- **CNOT**：SSHR 更少（CNOT 专精）；
- **depth**：CirKit 更浅；
- **辅助比特**：RevKit CLI 用得更少；
- **小函数 T-count**：公开 STG 最优库更低。

### 主张（克制、严谨）

不是“我全胜”，而是：**在匹配的逻辑层任务上，T-count 和加权资源分数更低，且质量-搜索开销可控、可审计。**

### 范围边界

引擎严格停留在**逻辑 MCT 级**（X/CNOT/MCT），**不做硬件映射/路由/噪声建模**，**无独立 Rz 旋转综合后端**。竞赛论文加的硬件映射是“无校准合成 Target”，禁止用真机名称/真实保真度措辞。

---

## 七、项目结构

```
sshr/
├── README.md                  ← 本文件（入门讲思路）
├── CLAUDE.md                  ← 完整项目指南（AI 协作参考）
├── AGENTS.md                  ← AI agent 速查
├── .gitattributes             ← 强制 *.sh/*.py 用 LF（Windows 兼容）
├── _archive/                  ← 此前 4 个研究轨道（只读归档：sshr/ai-sshr/gnn-sshr/rl-mcts）
└── resource_nmcts/            ← 主工作目录（所有命令在此下执行）
    ├── src/                   ← 核心库（~10000 行）
    │   ├── synthesizers.py    ← 公开入口 synthesize(method, bf, config, seed, model_path)
    │   ├── nmcts_solver.py    ← PUCT/MCTS 求解器
    │   ├── neural_policy.py   ← 神经动作先验（ActionNet MLP）
    │   ├── factor_plan.py     ← ANF 分解计划与候选动作生成
    │   ├── resource_model.py  ← 多目标资源成本模型
    │   └── sshr_lib/          ← 自包含 SSHR-H/Beam/I 基线
    ├── scripts/               ← 训练器(8 个 train_*.py) + 实验驱动 + 外部工具探针
    ├── analysis/              ← ~135 个只读审计脚本（竞赛硬化层）
    ├── tests/                 ← 冒烟测试 + 专项测试
    ├── models/                ← 22 个训练好的 .pt 模型
    ├── results/               ← 实验数据（465 CSV + 7 DuckDB）
    ├── paper_latex/           ← 英文论文
    ├── paper_latex_zh/        ← 中文论文（最新 v40）
    ├── submission_competition/← XA-202609 竞赛交付
    └── README.md              ← 技术文档（1400+ 行工具链说明）
```

---

## 八、如何运行

> 详细环境说明见 `CLAUDE.md`。本机为 Windows，主环境是 conda `mcts-qoracle`。

### 环境

- **主环境**：conda `mcts-qoracle`（torch 2.9.1+cu128 + qiskit 2.5/aer + pulp + duckdb + scipy）。
- **导入顺序约束**：必须 `import torch` 先于 `import qiskit_aer`（否则 shm.dll WinError 127）。
- 直接调 `python.exe`（非 `conda activate`）时需前置 `KMP_DUPLICATE_LIB_OK=TRUE`。
- **Gurobi 不可用**：Windows 无 Gurobi（SSHR-I 走 SciPy milp / PuLP）；Gurobi 仅在 macOS `sshr` 环境。

### 快速验证

```bash
cd resource_nmcts
python tests/tests_smoke.py            # 冒烟测试（核心综合全方法族 + 验证）
python scripts/run_experiments.py --preset smoke   # 小规模实验
```

### 导入测试

```bash
cd resource_nmcts
python -c "from src.synthesizers import synthesize; print('OK')"
```

---

## 九、核心设计哲学

这个算法里有 4 类 AI 部件，但它们**全部遵循同一个铁律**：

> **AI 永远只在“搜索控制”层工作（排序、选深度、定预算），永远不参与“正确性”判定。正确性 100% 由数学验证保证。**

这意味着：
- 神经先验打错分？→ 只会让搜索多走弯路，最终结果不会错；
- Frontier policy 选错深度？→ 可能漏掉一点优化，产出依然正确；
- fitted-Q 决定不跑 Pareto？→ 只是放弃潜在的质量提升，结果还是正确的 base 线路。

**这是本工作在量子计算（容错要求极严）领域最聪明的设计：大胆用 AI 的创造力，用数学的确定性兜底。**

---

## 十、参考与引用

- 论文：`resource_nmcts/paper_latex/`（英文）、`paper_latex_zh/resource_nmcts_zh_manuscript_v40.tex`（中文最新版）。
- 核心相关工作：SSHR（Zheng 2025, CNOT 导向）、ROS（Meuli 2020）、XAG（Meuli 2022）、ABC、mockturtle、CirKit、RevKit、Caterpillar。
- 学习式综合对照：ShortCircuit、Gumbel AlphaZero、MonteQ、Q-PreSyn、Stab-QRAM、BDD2Seq。

> 本项目只主张匹配逻辑层任务上的低 T-count、低加权资源分数和可审计的质量-搜索开销控制；不主张普遍 CNOT/depth/ancilla 支配、全局最优性、完整 ROS 复现或硬件映射优势。
