# AI-SSHR 方案设计

## 目标定位

AI-SSHR 的目标不是让 AI 直接生成量子门序列，而是让 AI 学习 SSHR 中的经典空间结构选择规律：

```text
Boolean function / sparse support
        -> candidate parallelotopes
        -> AI ranking / pruning
        -> block synthesis
        -> correctness verification
```

这样可以保留 SSHR 的可证明等价性：AI 只负责选择经典侧的结构块，真正的量子线路仍由 `synth_block(P)` 确定性生成。

## 为什么做块搜索

直接在量子电路门级搜索会遇到三个问题：

- 搜索空间巨大：`X`、`CNOT`、`MCT`、控制位集合和门顺序组合爆炸。
- 正确性难保证：oracle 必须保持输入寄存器不变，只翻转输出位，任意门级搜索很容易破坏该结构。
- 学习信号稀疏：随机门序列很难快速接近目标 Boolean oracle。

Parallelotope 块搜索把每个 action 提升为一个语义明确的结构块：

```text
action = choose parallelotope P
effect = flip exactly vertices(P)
cost   = CNOT/T cost of synth_block(P)
```

因此搜索空间更小、特征更稳定、可解释性更强，并且 correctness 可以通过 parity/monotone 语义和仿真验证闭合。

## 双引擎架构

AI-SSHR 采用两个互补后端。

### 1. AI-Pruned WP-SCP

这是偏精确的后端，保留 SSHR-I 的 WP-SCP 奇偶覆盖约束，但用 AI 缩小候选集。

```text
full candidate set S
        -> AI score(P)
        -> keep top rho candidates + safe candidates
        -> solve WP-SCP ILP on S'
```

安全候选至少包括：

- 所有 on-set singleton，保证最坏情况下仍可行。
- 高维、高 overlap、低 cost 的基础候选。
- 后续可加入 SSHR-H 或 Beam 选中过的候选。

该引擎的价值不是数学上超过完整 ILP，而是在候选数很大或限时求解时减少变量规模，提高可运行性和稳定性。

### 2. AI-Guided Beam

这是偏快速的后端，用 AI 替代人工启发式排序。

```text
beam = [(A0, cost=0, path=[])]
while A != empty:
    generate valid candidates P
    score(A, P) with AI ranker
    expand top-k actions
    keep best beam-width states
```

MVP 先采用 monotone 语义：

```text
valid:  vertices(P) subset A
update: A <- A - vertices(P)
```

这样不会循环，正确性简单。后续可以扩展为 XOR-aware Beam：

```text
valid:  |A intersect P| / |P| >= R
update: A <- A symmetric_difference vertices(P)
```

但 XOR 版本需要状态缓存、深度限制和防振荡策略。

## AI 学习对象

AI 不学习量子门，而学习候选块的长期价值。

候选结构特征：

- `dim(P)`
- `|P|`
- basis support 分布
- common control 数
- 是否 singleton

成本特征：

- `block_cnot_cost(P)`
- `block_t_cost_rp(P)`
- cost per covered minterm

状态交互特征：

- `|A|`
- `|A intersect P|`
- `|A intersect P| / |P|`
- `|P - A| / |P|`
- 选择后 `|A'|` 变化

搜索特征：

- 当前累计 cost
- 剩余 active density
- 是否满足 monotone
- 是否满足 SSHR-H 阈值

第一版建议使用 tabular ranker：

```text
RuleRanker -> LightGBM/XGBoost/MLP ranker -> GNN/RL
```

先用可解释的规则打分跑通流程，再替换成训练模型。

## 训练数据来源

可从现有求解器蒸馏标签：

- `n=3,4`：完整 SSHR-I ILP 解作为强标签。
- `n=5,6`：限时 ILP、Beam、MCTS 解作为高质量标签。
- `n=7,8`：Beam/SSHR-H 自举生成弱标签。

AI-Pruned WP-SCP 标签：

```text
label(P) = 1 if P appears in a high-quality solution
```

AI-Guided Beam 标签：

```text
label(A, P) = ranking target among candidates under the same state
```

由于正样本很少，不建议做普通二分类。更适合做 ranking：在同一函数或同一状态内，把好候选排到坏候选前面。

## 对比对象

逻辑线路层面的对比对象：

- SSHR-H
- SSHR-H-paper
- Beam
- MCTS
- full SSHR-I
- time-limited SSHR-I
- AI-Guided Beam
- AI-Pruned WP-SCP
- ESOP / ESOP-ILP

核心指标：

- CNOT
- T-count
- ancilla
- runtime
- ILP gap
- correctness pass rate
- candidate keep ratio

## 核心论点

完整 ILP 在小规模且充分收敛时仍是全局最优参考，AI 不应声称数学上超过它。

AI-SSHR 的优势在实际约束下：

- 候选 parallelotope 数量随比特数快速增长。
- ILP 变量数和求解时间随候选数膨胀。
- Beam/MCTS 每步 action space 过大。
- AI 可以学习候选有效性，进行排序、剪枝和搜索引导。

更严谨的竞赛表述是：

> 小规模用完整 ILP 提供监督与最优参考；中大规模用 AI 进行候选排序、剪枝和 Beam 引导。在保证功能等价的前提下，以更低运行时间获得接近 ILP、优于人工启发式的线路质量。

