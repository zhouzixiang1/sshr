# XA-202609 密码量子 Oracle 原型技术设计

> **范围更正（2026-07-28）：** 竞赛执行范围与完成定义以
> `PROJECT_BLUEPRINT_XA202609.md` 为准。本文第 4 节原 MWIS 方案将多个
> `FactorAction` 错误解释为可同时施用；现有 Plan 实际是二叉 factor/rest
> 递归。实现时必须采用“固定 B 的 utility-diversity batch scheduler”，选中
> 动作各自建立独立 MCTS 子节点，不得实现旧的同时动作语义，也不得在没有
> 证据时使用“量子加速”表述。
> `ARCHITECTURE_DECISIONS_XA202609.md` 中 D1–D5 已确认。服务器接手快照
> 验证后恢复施工。文中开发期测量只用于诊断，不能替代冻结 manifest 下的
> 正式竞赛实验。

> **E3 状态更正（2026-08-11）：** 超导模拟路线的最小闭环已经实现并通过
> 冻结 calibration/test 验收：逻辑 X/CNOT/MCT 经自研 NumPy 执行层分解为
> `rz/sx/x/cx`，在合成 heavy-hex-like 耦合图上作确定性最短路 SWAP 路由，
> 通过独立原生全基态等价检查，并用实际 Pauli statevector trajectories 生成
> 含噪标签。冻结反馈确实改变根动作和 Plan，但 held-out NLL 差为
> `+0.001293`，95% CI `[-0.001170, 0.004719]`，未支持改善假设。该证据不是
> Qiskit/Aer、真实设备标定、真机或量子优势，也不等于 policy/value replay 更新。

> 版本 1.1 · 2026-08-11 · 基线提交 `2d264f2`
> 权威输入：`PROJECT_BLUEPRINT_XA202609.md`、`ARCHITECTURE_DECISIONS_XA202609.md`
> 和 `../contracts/COMPETITION_ACCEPTANCE_MATRIX.json`。研究计划与扩展备忘录仅作背景。

---

## 目录

1. [现有系统接口契约](#1-现有系统接口契约)
2. [L1 置换等变结构化 policy/value 模型](#2-l1-置换等变结构化-policyvalue-模型)
3. [L3a AlphaZero 搜索内核](#3-l3a-alphazero-搜索内核)
4. [L3b QAOA 辅助的多样化 MCTS 扩展调度](#4-l3b-qaoa-辅助的多样化-mcts-扩展调度)
5. [L2a GFlowNet 多目标采样（可淘汰实验轨）](#5-l2a-gflownet-多目标采样可淘汰实验轨)
6. [L4 硬件适配与标定](#6-l4-硬件适配与标定)
7. [L5a 布尔结构–量子资源探索图谱（P1 赛后研究）](#7-l5a-布尔结构量子资源探索图谱p1-赛后研究)
8. [目录结构与模块划分](#8-目录结构与模块划分)
9. [实验协议](#9-实验协议)
10. [里程碑与验收](#10-里程碑与验收)

---

## 1. 现有系统接口契约

改造必须保持旧方法行为和既有逻辑层结果的可复现性；旧结果只作为回归资产，
其数据量不能替代 XA-202609 新闭环的独立实验与 manifest。

### 1.1 核心数据结构(`src/factor_plan.py`)

```python
@dataclass(frozen=True)
class SearchConfig:
    weights: ResourceWeights            # 五目标权重
    max_factor_ancilla: int = 4         # 递归嵌套时的活跃辅助线预算
    max_factor_size: int = 5            # 因子最大变量数
    candidate_top_k: int = 24           # 候选动作截断
    min_factor_count: int = 2
    use_relative_phase: bool = True
    mcts_simulations: int = 96
    neural_mcts_simulations: int = 128
    max_polarities: int = 384
    gate_mode: str = "mct"
    neural_prior_weight: float = 1.0
    greedy_eval_limit: int = 1

@dataclass(frozen=True)
class FactorAction:
    factor: int                # 变量子集的位掩码
    group: frozenset[int]      # 能被 factor 整除的项；只用于冗余度，不是冲突判据
    residuals: frozenset[int]  # group 中各项除掉 factor 后的余项
    rest: frozenset[int]       # 不能被 factor 整除的项 = terms - group
    immediate_gain: float      # ★ L3b 的顶点权重
    prior: float               # 启发式先验 + 神经加成
    linear: bool = False
    affine_const: bool = False

@dataclass
class Plan:
    kind: str                  # "direct" | "factor"
    terms: frozenset[int]
    cost: ResourceCost
    factor: int = 0
    group: Optional["Plan"] = None
    rest: Optional["Plan"] = None
    affine_const: bool = False
    def score(self, weights) -> float: ...
```

```python
# src/resource_model.py
@dataclass
class ResourceCost:
    T: int = 0
    CNOT: int = 0
    gates: int = 0
    depth: int = 0
    explicit_ancilla: int = 0
    peak_ancilla: int = 0
    def score(self, w) -> float:
        return w.t*T + w.cnot*CNOT + w.depth*depth + w.gates*gates + w.ancilla*peak_ancilla
```

**竞赛/论文 profile**：
`score = 1.0·T + 0.04·CNOT + 0.015·depth + 0.01·gates + 2.0·peak_ancilla`。
这不是 `ResourceWeights` dataclass 的默认值；训练和实验必须显式传入，避免
静默切换评价目标。

### 1.2 神经网络的两个集成点

**集成点 A —— 动作打分(现状)**

`candidate_actions()`(`src/factor_plan.py:379`)在返回前调用:

```python
if neural_scorer is not None and actions:
    features = [action_features(...) for action in actions]   # 24 维手工特征
    scores = neural_scorer.score_many(features)
    actions = [replace(a, prior=a.prior + w * s) for a, s in zip(actions, scores)]
actions.sort(key=lambda a: (-a.prior, -a.immediate_gain, ...))
```

同样的模式在 `factor_plan.py` 的 **459 / 610 / 760 / 874** 四处重复(对应 greedy / beam / root-beam / root-child-beam 四条路径)。

> **⚠️ 施工修正(2026-07-27)**:本文档 v1.0 原写"实现 `score_many()` 契约即可零改动接入"——**这是错的**。`action_features()` 是在**调用点**计算的,只实现 `score_many(features)` 的 scorer 永远拿不到原始项集,等变编码器完全失效。
>
> **实际做法**:把重复 4 次的 20 行块提取为 `_apply_neural_prior()`(`src/factor_plan.py`),在内部按能力分发:
> - scorer 暴露 `score_actions(terms, prefix_len, live_ancilla, actions, direct_total, config)` → 走结构化协议,拿到原始项集
> - 否则回退 `score_many(action_features(...))` → 旧 checkpoint 行为**字节级不变**
>
> 这反而**减少**了重复。已用 12 行历史结果验证旧路径完全一致(见 §9.4)。

**集成点 B —— Value 估计（开发态已接入）**

`NeuralMCTSSolver` 在传入 `value_estimator` 时使用
`LearnedValueEstimator`，并支持 batch prefetch、缓存和 progressive widening；
不传时仍保留经典 `greedy_plan()` rollout。当前实现已接入
`foundation_nmcts`，但正式 C0–C7 因果实验尚未冻结。

### 1.3 被替换的 24 维手工特征

`action_features()`(`src/factor_plan.py:900`)返回:

| # | 特征 | # | 特征 |
|---|---|---|---|
| 0 | `len(terms)` | 12 | `mean_factor_var_freq` |
| 1 | `mean(degrees)` | 13 | `max_factor_var_freq` |
| 2 | `max(degrees)` | 14 | `pair_density` |
| 3 | `prefix_len` | 15 | `mean_var_freq` |
| 4 | `live_factor_ancilla` | 16 | `var_freq_std` |
| 5 | `factor.bit_count()` | 17 | `degree_concentration` |
| 6 | `len(group)` | 18 | `residual_overlap` |
| 7 | `len(rest)` | 19 | `gain_per_term` |
| 8 | `mean(residual_degrees)` | 20 | `degree_reduction` |
| 9 | `max(residual_degrees)` | 21 | `rest_avg_degree` |
| 10 | `gain / direct_total` | 22 | factor 变量选择性 |
| 11 | `len(group)/len(terms)` | 23 | factor 变量覆盖比例 |

**全是聚合标量,丢弃了项集的结构。** L1 用等变编码器直接消费结构。

### 1.4 不变量(改造中必须持续成立)

1. 小规模用 `verify_oracle` 做完整真值表验证；规模实验分别调用
   `verify_plan_anf` 和 `verify_circuit_anf` 做 Plan/发射线路符号验证
2. `tests/tests_smoke.py` 输出 `smoke ok`
3. 现有 `results/raw_*.csv` 可用旧代码路径复现(**新方法作为新 method 名加入,不改旧方法行为**)

---

## 2. L1 置换等变结构化 policy/value 模型

> **当前范围：** 竞赛 P0 只有共享等变主干、action policy 头和 value 头。
> 下文的 affine/screen/budget/nonlinearity 多任务头与自监督预训练属于 P1
> 研究扩展，未实现前不得把当前 v3 checkpoint 称为通用“基础模型”，也不得
> 声称已经替代 18 个专用模型。
> `foundation` / `foundation_nmcts` 仅是当前兼容性代码标识；报告、界面和
> 演示统一称“置换等变 policy/value 模型/搜索”。

### 2.1 状态编码

MCTS 状态是 `(terms: frozenset[int], prefix_len: int, live_factor_ancilla: int)`。

**项集 → 二值矩阵**

```
terms = {0b0111, 0b1010, 0b0011}   # 3 个项
n = 4                              # 变量数

M ∈ {0,1}^{T×n},  M[t,v] = 1 ⟺ 第 t 个项包含变量 v

M = [[1,1,1,0],
     [0,1,0,1],
     [1,1,0,0]]
```

**关键性质**

| 轴 | 对称性 | 理由 |
|---|---|---|
| 行(项) | **置换不变** | `terms` 是集合,行序无意义 |
| 列(变量) | **置换等变** | 变量重标号 ⟹ 最优分解同构重标号 |
| T, n | **可变尺寸兼容** | 参数不按项数或变量索引绑定；不等于已证明跨尺度泛化 |

**上下文特征**(广播到每个 cell 作为额外通道):
`prefix_len`、`live_factor_ancilla`、`max_factor_ancilla - live_factor_ancilla`(剩余辅助线预算)、五个资源权重(归一化)。

> **权重作为输入是有意为之**：它提供条件化的架构接口，但当前 v3 只在论文
> 权重 profile 上训练。只有完成多权重训练和 held-out profile 对照后，才能
> 声称一个模型适配 t-only / cnot-only / balanced / ancilla-tight 等偏好。

**尺寸通道 `SIZE_CHANNELS = 3`(施工中发现的必需项,2026-07-27)**

上表“可变尺寸处理”有一个代价：主干里每一次池化都是 mean
（`masked_pool`），这是一套参数可接受不同 T/n 的来源，也让主干对行重数
严格不变。开发期测试把每一行复制 1x→8x，输出到小数点后 9 位相同，说明
模型本身数不出单项式个数；这不是跨尺度泛化证据。

而可达成本比强烈依赖这个数。754 个 held-out 状态、冻结主干上的岭回归验证:

| 回归器 | MAE | R² |
|---|---|---|
| 仅全局特征 | 0.0678 | +0.780 |
| **仅 3 个尺寸标量** | 0.1129 | **+0.517** |
| 全局特征 + 尺寸 | **0.0554** | **+0.839** |

三个标量单独就有 R²=0.52。**这是不变性,不是欠拟合——加容量补不了**(实测 4x 参数的模型 value loss 反而没改善)。

因此追加三个广播通道:`log1p(T)`、ANF 密度 `T/2ⁿ`、`n`。密度是有结构含义的量:n=6 的 60 个单项式接近满展开,n=12 的 60 个是稀疏的,两者是不同的问题。

保留 mean 池化（**可变尺寸处理方式**不变），只把尺寸作为显式标量喂进去；
广播常数不破坏 `S_T × S_n` 等变性，三个等变性测试原样通过。

> 回归测试见 `tests/test_equivariance.py::test_state_size_is_visible`。它守的是一个**非**不变性,写法上有陷阱:第一版断言"不同 |T| 的主干输出必须不同",负向对照显示**不触发**——不同大小的随机项集内容本就不同,尺寸通道全零也能过。正确写法是**固定膜矩阵、只改尺寸通道**。
>
> ⚠️ 通道布局变更会作废旧 checkpoint(9 → 12),`FoundationScorer.from_checkpoint` 已加显式报错。

### 2.2 等变主干:可交换矩阵层

采用 Hartford et al. (ICML 2018) 的 exchangeable matrix layer。对输入张量 `X ∈ R^{T×n×C_in}`,单层为:

```
Y[t,v,:] = σ( X[t,v,:]·Θ₁
            + (1/n)·Σ_{v'} X[t,v',:]·Θ₂        # 行池化(对该项的所有变量)
            + (1/T)·Σ_{t'} X[t',v,:]·Θ₃        # 列池化(对该变量的所有项)
            + (1/(T·n))·Σ_{t',v'} X[t',v',:]·Θ₄ # 全局池化
            + b )
```

其中 `Θ₁..Θ₄ ∈ R^{C_in×C_out}`,`b ∈ R^{C_out}`。

**这是 S_T × S_n 等变线性层的完备参数化**——任何同时对行置换和列置换等变的线性映射都可写成这个形式。参数量与 T、n 无关，因此前向接口兼容可变尺寸；这不等于 checkpoint 已经证明跨 n 泛化。

**当前 v3**：输入通道 12、`L = 2`、`C = 32`、head MLP hidden 128，
共 60,450 参数。`L = 6, C = 128` 只可作为未来容量扩展候选，不能写成
当前 checkpoint 架构。层间采用 LayerNorm、残差和 GELU。

**可选增强**:把行/列池化替换为注意力(axial attention,两轴均**不加位置编码**以保持置换对称性)。表达力更强但更慢。**建议先用池化版本跑通,再评估是否需要注意力。**

### 2.3 下游头

主干输出 `H ∈ R^{T×n×C}`。定义三种池化:
- `h_term[t] = mean_v H[t,v,:]` ∈ R^{T×C}
- `h_var[v] = mean_t H[t,v,:]` ∈ R^{n×C}
- `h_global = mean_{t,v} H[t,v,:]` ∈ R^C

---

#### 头 1:因子选择 policy(两个阶段)

**阶段 1 —— 判别式(drop-in 替换 24 特征,零风险)**

对每个候选 `FactorAction a`:

```
z_a = MLP([ pool_{t ∈ a.group} h_term[t] ,
            pool_{v ∈ bits(a.factor)} h_var[v] ,
            h_global ,
            a.immediate_gain / direct_total ,
            |a.group| / |terms| ,
            log1p(|a.group|) / 8 ,
            log1p(|terms|) / 8 ])
```

实现结构化 `score_actions(terms, ..., actions, direct_total, config)` 契约。
`factor_plan._apply_neural_prior()` 按能力分发；旧 scorer 才回退到
`score_many(action_features(...))`。Foundation scorer 的 `score_many()` 会
主动报错，因为平坦特征不包含原始项集。

**阶段 2 —— 生成式(真正超越重排序)**

```
logits_v = MLP(h_var[v])  ∈ R^n         # 逐变量
```

因子 = 变量子集,按 logits 采样/取 top-k 生成候选,再用**合法性过滤**(该因子必须整除 ≥ `min_factor_count` 个项)。

生成式的价值:当 `candidate_actions()` 的枚举在高 n 上爆炸时(`_subsets(term, max_factor_size)` 对每个项枚举子集),生成式可以**跳过枚举直接提议**。

> **先做阶段 1**。阶段 2 是 L1 的延伸目标,不是 T0 判据。

---

#### 头 2:Value

```
v = MLP(h_global)  ∈ (-3, 0)
```

`prefix_len`、活跃/剩余辅助线、资源权重和尺寸标量已经作为广播通道进入
`h_global`。目标为 `log(achieved_score/direct_score)`，见 §3.2。

---

#### 头 3:Affine 变换提议(替代枚举)

现状:`src/affine_search.py` 用有界枚举(budget 32/128)搜索可逆矩阵 `A`。诚实的消融显示 affine 搜索贡献了 60.92%/61.83% 的增益,但 wide-128 相对 budget-32 只多买到 0.60% —— **枚举已饱和**。

设计:输出 `n×n` 的 logit 矩阵,按行采样构造 `A`,用 GF(2) 高斯消元检查可逆性,不可逆则重采样。

```
A_logits = MLP_pairwise(h_var)  ∈ R^{n×n}
```

**这是把最大的经典贡献者转成 AI 贡献者的关键一步。**

---

#### 头 4:screen 深度门控

替代现有 5 个 depth 模型(`boolean_screen_depth_*.pt`)。输出 depth ∈ {1,2,3,4} 的分类分布。

---

#### 头 5:搜索预算控制

替代 `mcts_budget_policy.pt`(fitted-Q 控制器)。输出是否追加 Pareto 搜索的二分类 + 预期收益估计。

---

#### 头 6:函数属性回归(服务 L5a + 预训练)

输出 ANF 度、项数、**非线性度**、direct ANF 的 T-count。

### 2.4 预训练

> **P1 研究扩展，非竞赛 P0。** 当前没有 pretraining 实现或对应 checkpoint。
> 随机 ANF 可生成大量训练样本，但高质量搜索标签仍有显著计算成本。

#### 目标 1:Affine 轨道对比学习 【本问题特有,不是套模板】

**原理：** `f(x)` 与 `f(Ax+b)`（`A` 为 GF(2) 上可逆矩阵）属于同一
affine 轨道，可作为结构相关的正样本候选。但一般 affine wrapper 有 CNOT/
depth 成本，因此“同轨道 = 同综合难度”并不严格成立；训练目标需要显式加入
wrapper cost，实验也必须检验轨道内资源差异。

```python
f  = random_anf(n, density)
A, b = random_invertible_affine(n)
f_pos = apply_affine(f, A, b)      # 复用 src/affine_search.py 的既有实现
f_neg = random_anf(n, density)     # 批内其他样本作负例

loss_contrastive = InfoNCE(enc(f), enc(f_pos), {enc(f_neg_i)}, τ=0.07)
```

**这个目标直接编码了问题的核心对称性。** 一个能把 affine 轨道映射到相近嵌入的编码器,天然学会了"什么样的结构差异是本质的、什么是坐标选择的假象"。

#### 目标 2:掩码项重建

随机掩掉 15% 的项,从剩余项预测被掩项的变量集合(多标签 BCE)。

#### 目标 3:真值表距离回归(DeepGate2 式功能感知)

采样函数对 `(f, g)`,预测其真值表 Hamming 距离(归一化)。迫使嵌入捕获**功能**而非仅结构。

#### 目标 4:属性回归

预测 ANF 度、项数、非线性度、direct T-count。标签由现有代码直接计算。

#### 总损失

```
L = λ₁·L_contrastive + λ₂·L_mask + λ₃·L_ttdist + λ₄·L_props
初值 λ = (1.0, 0.5, 0.5, 0.3)
```

#### 预训练数据规模

| 项 | 值 |
|---|---|
| n 分布 | 4–64,按 `1/n` 加权采样(小 n 更多,便于算真值表标签) |
| 密度分布 | 均匀采样 ANF 密度 ∈ [0.05, 0.5] |
| 样本量 | 起步 10⁶ 个函数,视收敛调整 |
| 真值表标签 | 仅 n ≤ 20 计算(位并行,可承受) |

### 2.5 微调

预训练后,各下游头用监督数据微调:
- 因子选择 policy:MCTS 访问计数(见 §3.3 expert iteration)
- Value:实际达成分数
- Affine 提议:枚举搜索的最优 `A` 作教师
- 深度门控 / 预算控制:现有 5 个模型的输出作教师(蒸馏),再用真实标签微调

### 2.6 P1 扩展验收判据

| # | 判据 | 说明 |
|---|---|---|
| 1 | 等变性单元测试通过 | 见 §9.1 |
| 2 | 一个模型替代专用模型的可行性 | 仅在每个下游任务均有正式对照后成立 |
| 3 | 覆盖 n=4..64,含训练时未见的 n | 零样本迁移 |
| 4 | 预训练 vs 随机初始化显著更优 | 证明"基础模型"非噱头 |

**降级路径**:多任务训不稳 → 退回单任务(policy+value),判据降为 1/3;仍不行 → 只保留 value head + 现有 24 特征。

---

## 3. L3a AlphaZero 搜索内核

### 3.1 现状问题

`src/nmcts_solver.py` 的 `_simulate()`:

```python
if st.visits: q = st.q
else: q = self._rollout_action_cost(key, action)   # → _greedy_value() → greedy_plan()
```

`_greedy_value()` 跑一次完整的经典贪心分解。这既是**运行时瓶颈**,又是**神经先验显得无用的原因**——一个足够好的贪心 rollout 会掩盖 prior 的价值。这正是消融显示"+91% 运行时换 1.47% score"的机制。

### 3.2 Value 目标归一化 【关键设计】

**求解器是 minimize 方向**(与 AlphaZero 的 maximize 相反),且不同 n 的 score 量级差几个数量级(n=4 约 10¹,n=64 约 10⁴)。直接回归 score 会让大 n 主导梯度。

**目标**:

```
z = log( achieved_score / direct_score )
```

性质:
- 恒 `≤ 0`(`direct_plan` 总是可行解,搜索只会更好)
- 有界(实测 achieved/direct ∈ [0.3, 1.0] ⟹ z ∈ [-1.2, 0])
- 使用相对值后目标尺度更稳定，具备跨 n 训练的条件；是否泛化必须按冻结
  checkpoint 的训练域和 held-out 实验逐尺度验证，不能由公式直接推出

**预测转换回 score**:

```python
predicted_score = direct_score * exp(clamp(v_pred, -3.0, 0.0))
```

### 3.3 Direct feasible-upper-bound guard

```python
def _value(self, key: StateKey) -> float:
    node = self._node(key)
    direct = node.direct.score(self.config.weights)
    if self.value_net is None:
        return self._greedy_value(key)              # 旧路径
    v = self.value_net.predict(key)                 # ∈ (-∞, 0]
    return direct * math.exp(min(v, 0.0))           # ★ 恒 ≤ direct
```

`direct_plan` 永远是可行解，最终 plan 可以保留不差于 direct 的方案。这个
guard 只保证语义正确和 direct 基线保护，**不保证**不差于旧 greedy/MCTS
路径；学习 value 可能错误地改变搜索分配。产品 portfolio 若要求不退化，需
显式加入 classical guard；科研消融仍必须单独报告无 guard 的叶子方法。

### 3.3b `_build_best` 的指数爆炸陷阱 【施工中发现,必读】

**症状**:接入 value net 后,n=4 的实例都跑不完(>2 分钟)。

**根因**:`_build_best()` 用估值决定是否递归重建子树:

```python
if est >= best_score: continue          # 剪枝
group = self._build_best(group_key)     # 否则递归进整棵子树
```

经典 `_greedy_value()` 返回**实际可达**分数,剪枝有效。而 value net 返回的是"可能达到"的乐观下界(未训练时约 `0.18 × direct`),**几乎恒小于 `best_score` ⟹ 每个动作都递归 ⟹ 指数爆炸**。

**修复**:用 value net 时,`_build_best` 只对**搜索中实际访问过**(`st.visits > 0`)的动作递归。未访问动作没有搜索证据,不该凭乐观估计触发全子树重建;这把重建限制在已探索的树内。`value_estimator=None` 时逻辑**完全不变**。

**教训**:admissible 下界保护了 `_simulate` 的正确性,却没保护 `_build_best` 的**复杂度**。乐观估值在"选择"阶段是安全的,在"剪枝"阶段是危险的。

### 3.4 Expert Iteration 循环

```
初始化:policy/value ← L1 预训练权重
repeat:
  ① 自我对弈:在训练函数集上跑 MCTS(用当前网络)
     收集 (state, π, z):
       π = 该节点各动作的归一化访问计数
       z = 该子树最终达成的 log(achieved/direct)
  ② 训练:
       L_policy = CrossEntropy(policy(state), π)
       L_value  = MSE(value(state), z)
       L = L_policy + L_value + 1e-4·||θ||²
  ③ 评估:新网络 vs 旧网络,在 held-out 函数集上比 score 与运行时
     若新网络不劣 → 接受,否则回滚
until 收敛或预算耗尽
```

**训练/验证/测试函数集必须严格无重叠**——沿用项目已有的 320/160/160 划分惯例(`mcts_budget_policy` 用的就是这个)。

### 3.4b 施工实测:开销从哪来(2026-07-27)

用 cProfile 剖了一次 n=7 求解(48 simulations),累计时间分布:

| 调用 | 累计 | 次数 |
|---|---|---|
| `solve` 总计 | 6.045s | 1 |
| `_greedy_value` | **5.287s (87%)** | 22912 |
| `candidate_actions` | 5.652s | 4315 |
| `_apply_neural_prior` | 4.460s | 4314 |
| 等变主干 forward | 2.461s | 3322 |

**关键发现:`greedy_plan` 是带着 `neural_scorer` 递归调用的**,所以每层贪心 rollout 都在跑动作打分器。这就是现有 learned prior "+91% 运行时"的真正机制——**不是打分器本身贵,是它被 rollout 递归放大了**。

推论:value net 替掉 rollout 后,打分器不再被递归调用,这个乘数消失。**两项改造必须一起上才有意义**,单独上任一项都会更慢。

**已做的三处性能修复**

| 修复 | 效果 |
|---|---|
| `terms_to_matrix` 向量化(原为逐元素 Python 双循环赋值) | 编码快 9.8x |
| `subset_pool` 改为单次 matmul(原为逐动作 `index_select`) | 池化快 2.0x |
| `FoundationScorer` 加状态级打分缓存 | n=8 开销 +847% → +410% |

**仍未解决**:一次求解访问约 4000 个不同状态,每个都需一次编码器前向(~0.5ms),构成 ~2s 的地板。标准解法是 **batched leaf evaluation**(AlphaZero 的做法:收集叶子状态批量求值),需要重构 `_simulate` 为可批量化形式。列为 N1 的后续优化项。

### 3.4c 中间状态:batched leaf evaluation 做完了,但没赢(2026-07-27)

先按 AlphaZero 的标准做法实现了批量叶子求值:`_prefetch_action_values` 在节点展开时把所有候选分支状态一次性收集,经 `collate_states` padding+masking 后单次前向。**数值上验证与逐个求值完全一致**(5 种形状,最大偏差 1.192e-07)。

效果是真的:单状态成本 **812µs → 245µs**(3.3x)。但总时间反而更差。墙钟分解(n=7,96 simulations,无 profiler 失真)说明了原因:

| 项 | 时间 | 次数 | 单次 |
|---|---|---|---|
| 总计 | 3.314s | | |
| 网络合计 | 2.912s (**88%**) | | |
| ├ action prior | 0.732s | 901 | 812µs |
| └ value(已批量) | 2.180s | 824 批 | 2645µs / 批(**均批 10.8**) |

**批量压的是单次成本,压不动调用次数。** 一次 n=7 求解要 8900 次 value 求值。

> cProfile 在这里会骗人:它报告每次 `linear` 80µs,实测隔离基准是 13µs。所有性能判断都改用 `perf_counter` 墙钟。

### 3.4d 真正的瓶颈与解法:渐进拓宽(2026-07-27)

把 `_rollout_action_cost` 展开后,结构一目了然:

```
_rollout_action_cost(a) = gates(a) + V(residuals) + V(rest)
```

而 `select_key` 里 `min()` 会对**每个未访问动作**求值 —— 所以每节点 **2A 次** value 调用是写死在选择逻辑里的。这是经典求解器的遗留:贪心 rollout 便宜到可以给所有候选定价,神经网络不行。AlphaZero 从不这样做,它靠 policy prior 决定看哪些动作。

**改动**(`nmcts_solver.py`):引入 `_considered_width(node)`,只有 `actions[:width]` 可被选中,`width = widen_c · √visits`。`candidate_actions` 返回的动作**已按 prior 降序排好**,所以窗口直接消费 prior 的排序。无 value estimator 时返回全部动作,经典路径行为完全不变(12 例回归验证:score 逐位相同)。

**这一处同时解决了两个判据**:

- **判据 2(运行时)**:调用量降一个量级
- **判据 3(不可消融)**:prior 排低的动作**根本不会被求值**,而不是"晚一点探索"。误排序直接损失搜索质量,不再被首访穷举悄悄纠正

**归因必须用 2×2,不能用单因素扫描** —— 这里我先踩了坑,记下来:

最初只扫了 `widen_c`(固定 value net),得到 2.0 → 不拓宽只差 1.4pp,据此写下"拓宽只花 1.3 个百分点"。**这是把条件效应当成主效应读了。** 补做同实例 2×2(n=6/7/8 各 3 例,四格 prior 完全相同,只变两个因子):

| | 经典 rollout | 学习 value net |
|---|---|---|
| **穷举** | 14.14s / 基准 | 12.90s / **+2.68%** |
| **拓宽** | 5.04s / **+4.57%** | 4.26s / +5.93% |

- 拓宽单独 **+4.57%**(不是 1.3%),value net 单独 **+2.68%**
- 两者合计 +5.93% < 相加的 +7.25%,**次可加**——两种误差重叠。这正是单因素扫描会低估拓宽代价的原因:value net 已经把分数推高后,拓宽的边际代价自然变小
- value net 单独几乎不提速(14.14→12.90,仅 1.10x);**这个尺度上速度主要来自拓宽**(14.14→5.04,2.8x)

**但 rollout 的成本是复合的,大 n 会翻转**(两格均开拓宽,只变 value 来源):

| n | 项数 | 经典 rollout | value net | 加速 | score 差 |
|---|---|---|---|---|---|
| 8 | 125 | 1.28s | 1.11s | 1.16x | +1.13% |
| 9 | 250 | 6.54s | 2.12s | 3.08x | +2.01% |
| 10 | 535 | 26.80s | 4.94s | 5.42x | +0.25% |
| 11 | 1013 | 68.50s | 7.92s | **8.65x** | +0.69% |

**两个组件在不同尺度上各自挣到位置**:小 n 拓宽主导速度,大 n value net 主导(加速比单调 1.16→8.65),且大 n 上 value net 的质量代价降到 1% 以下。

**四配置对照**(随机 ANF,48 simulations,每例独立进程,上限 90s):

| n | 项数 | A | B | C | C vs A | score A / C |
|---|---|---|---|---|---|---|
| 5 | 17 | 0.018s | 0.028s | 0.027s | 0.64x | 122 / 122 |
| 6 | 27 | 0.065s | 0.096s | 0.086s | 0.76x | 250 / 250 |
| 7 | 69 | 1.146s | 1.734s | **0.434s** | **2.64x** | 707 / 765 |
| 8 | 125 | 6.831s | 5.237s | **1.075s** | **6.35x** | 1490 / 1774 |
| 9 | 250 | 23.761s | 16.436s | **3.119s** | **7.62x** | 3680 / 3969 |
| 10 | 535 | **>90s** | 70.482s | **11.078s** | **>cap** | — |

加速比随 n 单调上升(2.64 → 6.35 → 7.62),**n=10 上基线跑不完而 C 用 11s 完成**——这才是这条路线的真实价值:网络成本随项数近似线性,贪心 rollout 的成本是复合的。

> **诚实边界**:C 列用的是**随机初始化**的模型,score 比基线差 8–19%。速度判据已达成且趋势正确;质量判据取决于训练(§3.4e)。不应把 C 列的 score 当作最终结果引用。

### 3.4e Expert iteration 实跑与消融:判据 3 **未达成**,但拿到了为什么(2026-07-27)

**训练**(`scripts/train_expert_iteration.py`,已补齐 docstring 承诺但原先缺失的策略头训练;trunk 前向经 `collate_states` 批量化):8 轮,每轮 48 个自弈函数(n=4..8),hidden=32/layers=2。自弈刻意**不用** value net,走经典 rollout——它是 expert,慢但目标质量高。

```
[init]   holdout 664.67 (未训练)
[iter 1] value=0.01417 policy=1.5464  holdout 661.53 (-0.47%) accept
[iter 4] value=0.00949 policy=1.5466  holdout 658.85 (-0.07%) accept
[iter 5] value=0.00888 policy=1.6875  holdout 658.48 (-0.05%) accept
[iter 6..8] 连续 reject
```

累计仅 **-0.93%**,第 6 轮起收敛停滞。

**消融**(`scripts/run_prior_ablation.py`,n=6/7/8 各 3 例)。关键是**三列而非两列**:

| 变体 | vs shuffled |
|---|---|
| shuffled(打乱排序,其余完全相同) | 0.00% |
| **model(本 checkpoint)** | **+0.37%** |
| **oracle(按经典 rollout 真值排序)** | **−2.32%** |

先确认不是接线问题:实测神经项的离散度(1.7–5.9)比启发式 prior(0.20–0.36)大 5–30 倍,**神经分数完全主导排序**,且改变了哪 24 个动作能进候选池(`candidate_top_k` 在加 prior 之后才截断)。

所以结论是模型质量,不是管道:

- **排序确实有价值** —— oracle 拿到 −2.32%(旁证:n=8 那例 oracle 得 1490.0,与基线 A 的 1490 完全一致,即完美排序 + value net 可恢复基线质量)
- **但天花板只有 2.32%**,而本 checkpoint 吃到 **0%**(+0.37%,比随机还略差)

> **只报 model 列会误导。** prior 打平 shuffle 既可能是模型弱,也可能是排序在这个搜索里本就无关紧要——两者要求完全相反的应对。只有 oracle 列能区分,所以三列必须一起报。

### 3.4f value 头精度诊断:连否三个假设,定位到架构失明(2026-07-27)

诊断工具固化在 `scripts/run_value_diagnostic.py`。三个假设依次被实测否定,记下来是因为**每一个当时看起来都很合理**:

| 假设 | 判决 | 证据 |
|---|---|---|
| 训练目标 ≠ 部署用途 | ❌ 否定 | 352 个状态上两者差 **0.0032** log 单位 |
| 目标有采样噪声 | ❌ 否定 | 种子间 MAE=**0.0001**;48 vs 384 次模拟 MAE=**0.0000**(目标是确定性的) |
| 容量不足 | ❌ 否定 | 4x 参数(235k)value loss 0.0109,并不优于小模型 0.0103,且连续 reject |

真正的原因是 §2.1 记的**均值池化导致的尺寸失明**——属于架构不变性,不是训练问题。已修(`SIZE_CHANNELS`),正在重训验证。

以下是修复前的测量,保留作为对照基线:

先验证一个怀疑:训练目标(`collect_samples` 取 `min(stat.q)`,MCTS 达成值)与部署用途(替代 `_greedy_value` 返回的 `greedy_plan` 分数)是否是同一个量?**不是问题** —— 352 个 held-out 状态上两者仅差 **0.0032 log 单位**。

| 对照 | 网络 MAE | 常数预测器 MAE | R² |
|---|---|---|---|
| vs greedy 值(部署用途) | 0.0786 | 0.1667 | **+0.652** |
| vs MCTS 达成值(训练目标) | 0.0825 | 0.1714 | +0.655 |

网络比常数预测器好 2.1x,**不是垃圾,但 MAE 0.079 log 单位 ≈ 8% 分数误差**,与部署时的质量差距同量级。另有系统性**乐观偏置 −0.047**(预测低于真值),在最小化搜索里是危险方向(参见 §3.3b)。

**等时间预算下拓宽救不回来** —— n=10 上基线 A 要 112.24s,我们给到 14.43s(仍是 7.8x 余量)把 `widen_c` 一路开到 32:

| widen_c | 时间 | vs A |
|---|---|---|
| 2 | 5.21s | +4.67% |
| 8 | 9.75s | +4.94% |
| 16 | 11.52s | +3.79% |
| 32 | 14.43s | +3.47% |

`widen_c ≥ 8` 时根节点已把全部 24 个候选看完(`candidate_top_k=24`),**分数在 +3.5% 处平台化**。差距不是"看得不够多",是**被错误的 value 引导**——多搜也没用。

**对研究计划的修正(三个独立测量同向)**:policy prior 的天花板 ≤2.3%(§3.4e oracle 列);value net 主效应 +2.68%(§3.4d 2×2);等预算下质量平台在 +3.5%。**杠杆在 value 头精度,不在 policy 头,也不在搜索预算。**

具体下一步及其预算依据:n=10 上当前配置 5.21s vs 基线 112s,有 **21x 余量**可换容量。实测 `hidden=96/layers=4` 推理比 `32/2` 慢 3.0x(14.56ms vs 4.85ms,参数 235k vs 60k),换完仍剩约 7.8x 加速——买得起。已加 `--selfplay-prior heuristic`:value 目标来自经典 rollout、**不依赖模型**,所以自弈不必跑大模型前向(大 trunk 下这是数量级差异,且首轮模型还是随机的,启发式 prior 反而更强)。

### 3.5 验收判据与**当前实测结论**

| # | 判据 | 状态 | 实测 |
|---|---|---|---|
**修复尺寸失明后的最新结果**(checkpoint `models/boolean_oracle_fm_small.pt`,hidden=32/layers=2,种子流与训练不相交,每尺寸 3 个实例):

| n | 加速 vs A | score vs A | score vs 启发式穷举 |
|---|---|---|---|
| 7 | 3.67x | +1.51% | +1.73% |
| 8 | **7.82x** | **−6.41%** | **−7.57%** |
| 9 | 6.15x | +2.26% | **−0.55%** |
| 10 | 4.41x | +2.48% | +1.20% |

| # | 判据 | 状态 | 实测 |
|---|---|---|---|
| 1 | score 不劣于现有 `and_resource_nmcts` | ⚠️ **部分达成** | n=8 优于基线 6.41%、n=9 优于启发式 0.55%;n=7/10 仍差 1.5%/2.5% |
| 2 | **运行时相对现有 learned prior 路径下降** | ✅ **达成** | 3.67x–7.82x,n=8 上同时更快更好 |
| 3 | **消融:去掉后 score 显著变差** | ⚠️ **分布内达成** | n≤8:model −2.04% vs shuffled,捕获 oracle 空间的 **48.5%**;n=9:**+2.48%,比随机还差** |

**容量是幌子,信息才是关键**:同样加了尺寸通道,`hidden=32/layers=2`(60k 参数)全面优于 `hidden=64/layers=3`(119k)——后者 n=8 只有 2.71x 加速且 score +1.06%,前者 7.82x 且 −6.41%。多出的容量没买到质量,只吃掉了速度。

### 3.4g 动作头尺寸修复:分布内接近 oracle,**迁移仍未修好**(2026-07-27)

按 §2.1 同样的模式给 `ActionScoringHead` 补了绝对规模(`NUM_SCALARS` 2→4,加 `log1p(|group|)`、`log1p(|T|)`),训练与推理共用 `adapter.action_scalars()`。checkpoint `models/boolean_oracle_fm_v2.pt`。

**同一 checkpoint 内的尺度对比(这是唯一无混淆的比较)**:

| | 捕获 oracle 排序空间 |
|---|---|
| 分布内 n=6,7,8 | **95.9%**(model −2.65% vs shuffled,oracle −2.76%) |
| 分布外 n=9 | **−93.1%**(model +3.96%,oracle −4.25%) |

分布内几乎达到完美排序,分布外仍**比随机差**。

**我的结构性解释是错的。** 我原以为"两个标量都是比值、绝对规模不可见"导致不迁移;补上绝对量后分布内大幅改善而分布外纹丝不动(−88.7% → −93.1%)。这是**过拟合到训练尺寸区间**的特征,不是缺特征——需要覆盖目标尺度的训练数据,加特征解决不了。

**部署数字**(v2,种子流与训练不相交,每尺寸 3 例):

| n | 加速 vs A | score vs A | vs 启发式穷举 |
|---|---|---|---|
| 7 | 2.46x | **−0.42%** | −0.20% |
| 8 | 2.84x | **−5.64%** | −6.82% |
| 9 | 4.35x | +6.16% | +3.24% |
| 10 | 3.97x | +5.16% | +3.85% |

> ⚠️ **两个方法学缺陷,影响可比性**
>
> 1. **accept/reject 门在噪声上选模型**:holdout 仅 20 个函数,实测迭代间摆动达 **±11%**(v2 的 iter 4 是 +11.20%,iter 5 是 −1.81%)。"best holdout" 这个数字不可引用,结论一律以独立实例的评测为准。
> 2. **v1 已无法复测**:动作头输入维从 98 变成 100,兼容性检查会拒绝旧 checkpoint。因此 v1↔v2 的差异同时掺杂代码改动与选点噪声,**不可归因**。跨版本的表只能各自作为当时状态读,不能相减。

### 3.4h 覆盖假设验证:迁移问题是数据不是架构(2026-07-28)

§3.4g 的否定结果指向"过拟合训练尺寸区间"。直接检验:训练区间从 n=4..8 扩到 **4..10**,其余不变(`models/boolean_oracle_fm_v3.pt`)。同时把 holdout 从 20 加到 40,修掉 §3.4g 记的选点噪声问题。

**排序捕获 oracle 空间**:

| | v2(训 n≤8) | v3(训 n≤10) |
|---|---|---|
| n=9 | **−93.1%**(比随机差) | **+23.5%** |
| n≤8 | 95.9% | 78.7% |

**符号翻转** —— n=9 从"比随机排序还差"变成真正有帮助。假设成立:**迁移失败是训练数据覆盖问题,不是架构缺陷,也不是特征缺失**(§3.4g 补绝对规模标量对迁移毫无作用,已验证)。分布内从 95.9% 退到 78.7% 是预期代价,容量摊到了更宽的尺寸范围。

holdout 加倍后训练也更可信:**六轮全部接受、单调下降**(1270.47 → 1180.47,−7.08%),不再出现 v2 那种 −6.4%/+11.2% 的摆动。这一轮每轮 −0.4%~−0.8% 的稳定改善,在 20 个函数的 holdout 上会被完全淹没。

**部署结果**(种子流与训练不相交,n=8/9 各 3 例,n=10/11 各 2 例):

| n | 加速 vs A | score vs A | vs 启发式穷举 |
|---|---|---|---|
| 8 | 2.70x | **−2.49%** | **−3.70%** |
| 9 | 4.33x | **−1.58%** | **−4.29%** |
| 10 | 4.26x | +2.69% | +1.40% |
| 11(分布外) | 5.28x | +0.37% | +2.50% |

n=9 从 v2 的 +6.16% 变为 −1.58%。n=11 虽在训练区间外,也已接近基线持平(+0.37%)——边界不只是平移,扩到 n=10 让 n=11 也大幅改善。

> ⚠️ n=11 有 1 例因基线 A 超过 240s 上限被丢弃,均值只有 1 个实例支撑,证据弱。

**判据总评**:

| # | 判据 | 状态 |
|---|---|---|
| 1 | score 不劣于基线 | ✅ **n=8/9 达成**(−2.49% / −1.58%);n=10/11 仍差 2.7%/0.4% |
| 2 | 运行时下降 | ✅ **达成**,全尺度 2.70x–5.28x |
| 3 | 消融:去掉后显著变差 | ✅ **达成**,n≤8 捕获 78.7%、n=9 捕获 23.5%,均为正 |

**n=8/9 上三条判据同时达成。** 剩余方向:n≥10 的排序质量(捕获比例随尺度下降),以及把覆盖继续外推的成本——自弈用经典 rollout,n=10 每函数约 13s,再往上成本陡增。

**先前的问题记录(已解决,保留过程):policy 头不跨尺度迁移。**

| | value 头 | policy 头 |
|---|---|---|
| 分布内 (n≤8) | MAE 0.0799 / R² +0.684 | −2.04%(捕获 48.5%) |
| 分布外 (n=9) | **MAE 0.0497 / R² +0.879** | **+2.48%(捕获 −88.7%)** |

value 头在分布外反而更准(所以不是外推问题),policy 头则退化到比随机差。结构上的原因和刚修好的是**同一个,只低一层**:`ActionScoringHead` 用 `subset_pool` 对 group 行做均值池化,而它拿到的两个标量 `immediate_gain/direct_total` 和 `len(group)/len(terms)` **都是比值**——同样 20 项的 group,n=6(27 项)时是 0.74,n=9(250 项)时是 0.08,落在完全不同的区间。动作的绝对规模对该头不可见。

**诚实总结**:速度那半边论点成立且趋势正确(value net 加速比随 n 单调 1.16→8.65x,这是"网络成本近线性 vs rollout 成本复合"的直接体现);质量那半边不成立。

判据 1/3 的失败**已定位到同一处**——value 头精度(R²=0.652,MAE 0.079 log 单位),且三个独立测量互相印证(§3.4f)。这不是"再训久一点"能糊过去的,也不是加搜索预算能救的(等预算实测平台在 +3.5%);它需要更大的模型/数据规模。**正在验证**:`hidden=96/layers=4`(参数 4x)+ 启发式自弈,训 n=4..8,留 n=9..11 检验跨尺度迁移——后者同时是等变架构"一个 checkpoint 覆盖多尺度"主张的直接检验。

---

## 4. L3b QAOA 辅助的多样化 MCTS 扩展调度

QAOA 不是赛题资格门槛。D3 已确认，固定预算调度器、NumPy statevector
ideal/shot/noisy QAOA 和 NMCTS 独立子边接入均已实现，并由 E2 冻结 bundle
完成受限验证。QAOA 优于经典方法不是完成条件，在线正确性仍由确定性的
greedy diversity 降级路径保障。

### 4.0 当前实现与证据边界

当前源码映射为：

| 模块 | 已实现职责 |
|---|---|
| `src/search/diversity_scheduler.py` | random/top-B/greedy/exact、QUBO 构造、能量与可行集审计 |
| `src/search/qaoa_scheduler.py` | 固定深度 NumPy statevector QAOA、ideal/shot/noisy 采样与 repair |
| `src/search/mcts_scheduler.py` | utility/redundancy 适配、QAOA 调用资格、显式 fallback 与诊断 |
| `src/nmcts_solver.py` | 冻结根候选池、独立 action edge、每次 simulation 单 edge 评估 |
| `scripts/run_qaoa_scheduler_pilot.py` | 同池同预算 E2 矩阵、artifact bundle 与 verifier |

E2 `20260810-e2-qaoa-scheduler-v1-s120000` 覆盖 20 个 held-out
Boolean 函数、7 种调度器、3 个 MCTS seed，共 420 条 trial。三种 QAOA 模式
共尝试 180 次且全部成功、0 fallback；20/20 候选池 QUBO 审计、全部三层语义
验证和 24/24 verifier 均通过。

局部目标上，QAOA-shot 的 exact-objective 命中率为 81.7%，greedy 为 65.0%；
regret 分别为 0.002288 和 0.007694。但 QAOA-shot 的端到端资源分数相对
greedy 比值为 0.999734，函数簇 95% CI `[0.998476, 1.000921]`，跨过 1。
因此已证明的是“量子子程序改善冻结池中的组合选择质量”，尚未证明稳定的
最终 Oracle 资源改善，更未证明量子加速。当前 `noisy` 仅为 2% 独立测量
比特翻转，不是原生门、路由或门级噪声证据。

### 4.1 语义边界

对固定 `terms`，每个 `FactorAction a` 定义一个**独立的二叉决策**：

```text
terms = a.group ⊎ a.rest
```

选择动作后，`a.residuals` 和 `a.rest` 分别成为 factor/rest 两条递归分支。
现有 `Plan`、`factor_cost()` 和 emitter 都没有“在同一状态同时施用多个
FactorAction”的语义。

因此：

- `a.group ∩ b.group != ∅` 不能被解释为一般动作兼容性；
- `max_factor_ancilla` 约束递归嵌套时的活跃辅助线，不等于同层 batch 大小；
- 调度器选出的动作不能合并成一个新 Plan，也不能共享 `new_rest`；
- 每个动作必须保持独立子节点、独立成本和独立语义验证。

实测候选动作的 group-overlap 图在 `n=8/10` 上接近完全图，旧 MWIS 会退化为
单动作选择。这一事实进一步否定了同时动作方案。

### 4.2 调度目标

令 \(K\) 为 progressive widening、合法性过滤和截断后冻结的候选动作数。
调度器从中选择固定预算 \(B_{\mathrm{eff}}\) 个动作，分别建立子节点：

\[
\max_x
\sum_i u_i x_i-\gamma\sum_{i<j}r_{ij}x_ix_j,
\qquad
\sum_i x_i=B_{\mathrm{eff}}.
\]

`B_requested` 必须是正整数，并定义
\(B_{\mathrm{eff}}=\min(B_{\mathrm{requested}},K)\)：

- \(K=0\)：返回空集合，记录 `skipped_no_candidates`；
- \(0<K\le B_{\mathrm{requested}}\)：选择全部 \(K\) 个动作，记录
  `skipped_budget_covers_pool`；
- 只有 \(K>B_{\mathrm{requested}}\) 且节点满足深度等调用条件时，才执行
  QAOA 或其他选择求解器。

manifest 必须记录 \(K\)、requested/effective B、调用资格、跳过原因、repair
和 fallback。下文的 \(B\) 均指 \(B_{\mathrm{eff}}\)。

其中：

- \(u_i\) 是动作效用，主版本使用预测 action cost 相对 direct cost 的改进量，
  再归一化到稳定尺度；
- \(r_{ij}\) 是动作冗余：

\[
r_{ij}
=\alpha J(group_i,group_j)
+(1-\alpha)J(rest_i,rest_j);
\]

- \(\gamma\) 控制质量和多样性的权衡；
- \(B\) 是明确的扩展预算，所以等式基数约束在这里有合法语义。

`immediate_gain` 和未标定的 learned prior 不能直接作为无界 QUBO 系数；它们
必须经过方向校验、归一化和有限值检查。

### 4.3 QUBO 与 Ising 映射

最小化形式：

\[
E(x)
=-\sum_i u_i x_i
+\gamma\sum_{i<j}r_{ij}x_ix_j
+\rho\left(\sum_i x_i-B_{\mathrm{eff}}\right)^2.
\]

实现必须提供：

1. 从 \((u,r,B_{\mathrm{eff}},\gamma,\rho)\) 生成线性项和二次项；
2. 定义
   \(F(x)=\sum_i u_ix_i-\gamma\sum_{i<j}r_{ij}x_ix_j\)，对全部小规模
   bitstring 验证
   \(E_{\mathrm{QUBO}}(x)=-F(x)+\rho(\sum_i x_i-B_{\mathrm{eff}})^2\)，
   并核对实现记录的常数偏置；
3. 对所有满足 \(\sum_i x_i=B_{\mathrm{eff}}\) 的 bitstring，验证最小化
   QUBO 与最大化直接目标 \(F\) 给出完全一致的排序和最优解；
4. 对长度正确、二进制且有限但基数错误的 sample，执行确定性修复为恰好
   \(B_{\mathrm{eff}}\) 个动作，并单独统计 repair；
5. 在小规模冻结实例上确认罚系数足以使全局最低能量落在可行集；
6. 记录常数偏置，避免用遗漏常数的 energy 比较不同问题实例。

### 4.4 必须具备的求解路径

| 求解器 | 作用 |
|---|---|
| random-B | 随机多样性基线 |
| utility top-B | 不考虑冗余的质量基线 |
| greedy diversity | 每次选择边际目标最大的动作，默认 fallback |
| exact diversity | 小规模枚举或分支定界，给出最优目标值及其他方法的 optimality gap/regret |
| QAOA | ideal/shot/noisy 三种执行方式，作为量子辅助调度路径 |

QAOA 不能成为正确性单点故障。处理顺序必须明确：

- 长度正确、二进制且有限但基数错误的 sample 先做确定性基数修复；该结果仍
  记为 QAOA 输出，并记录 `qaoa_repaired`；
- sample 缺失、格式错误、不可修复、优化异常或超时，才在线回退到
  greedy diversity，并记录 `qaoa_fallback`；
- exact diversity 只作为小规模审计 oracle 和 gap 基线，不作为默认在线
  fallback。

### 4.5 集成到 MCTS

调度器限制当前节点允许首次评估的动作集合，不改变动作递归语义：

```python
def _scheduled_indices(self, node, width):
    actions = node.actions[:width]
    utility = self._action_utilities(node.key, actions)
    selected = self.scheduler.select(actions, utility, batch_size=self.batch_size)
    return selected.indices
```

每个 `selected index` 仍调用现有单动作：

```text
_rollout_action_cost(key, action)
_evaluate_action_recursive(key, action, depth)
```

`SearchNode.stats[index]` 也继续独立累计。调度器不得创建 `multi_factor Plan`。

第一版只在根节点或浅层、候选数达到阈值时调用 QAOA。因深度、候选数或预算
策略而未调用时使用 greedy，并记录为 `qaoa_not_invoked`，不能计入 QAOA
失败 fallback，以避免扭曲成功率和模拟器开销。

每个调度 manifest 至少包含：

`K`、`B_requested`、`B_eff`、`qaoa_eligible`、`qaoa_attempted`、
`qaoa_succeeded`、`repaired`、`repair_reason`、`fallback_used`、
`fallback_reason`、`fallback_solver`、`raw_qaoa_objective`、
`effective_objective`、`shots`、`seed` 和完整墙钟时间。

### 4.6 学习反馈链

仅仅让 MCTS 调用 QAOA 是“量子子程序辅助 AI 搜索”，还不是算法级闭环。
完整反馈需要：

```text
policy/value 生成效用
→ QAOA 选择扩展 batch
→ MCTS 获得已验证的访问分布和资源回报
→ 轨迹进入 replay buffer
→ expert iteration 更新 policy/value
```

报告必须分别评估“只调度、不更新模型”和“调度轨迹参与下一轮训练”。

### 4.7 验收判据

1. 对全部小规模 bitstring 验证含罚项能量恒等式，并在固定基数可行集上验证
   QUBO 与直接目标的排序和最优解一致；
2. random/top-B/greedy/exact/QAOA 五路径使用同一冻结节点集；
3. 覆盖 \(K=0\)、\(K<B_{\mathrm{requested}}\)、
   \(K=B_{\mathrm{requested}}\) 和 \(K>B_{\mathrm{requested}}\)；
4. ideal/shot/noisy QAOA 都必须有至少一次非 fallback 的直接执行证据；
5. 分开报告 not-invoked、repair 和 fallback，以及 objective gap、最优命中率、
   冗余、qubit、深度、两量子位门、shots、优化时间和端到端 search time；
6. QAOA 接入前后都保持逻辑线路 100% 验证通过；
7. 只有公平预算和墙钟证据成立时才能使用“加速”，否则统一称“量子辅助”；
8. QAOA 不优于经典方法时保留负面结果，不用经典 fallback 的成绩冒充 QAOA。

E2 已满足 1--8 的固定池/逻辑层受限验收门。E3 随后完成了 calibration/test
隔离的执行回报重校 utility，并证明反馈会改变搜索干预；但 held-out 主比较未过
改善门。算法级双向学习仍需完成 §4.6 的 replay buffer → expert iteration，且不得
用 E3 的标定内拟合精度代替 held-out 因果收益。

---

## 5. L2a GFlowNet 多目标采样（可淘汰实验轨）

本轨进入 XA-202609 实现与公平实验，但只有跨过预先登记的 hypervolume、
有效率、多样性和墙钟门槛后才进入核心创新；否则作为负结果附录交付。

### 5.1 动机

现有 `pareto_resource_nmcts` 是**启发式** Pareto 归档:递归调用叶子方法,用 Pareto 前沿选最优。Multi-Objective GFlowNet(Jain et al., ICML 2023)正是为"生成多样的 Pareto 最优候选"设计的**原理性**方法。

项目的五目标资源模型(T/CNOT/depth/gates/peak_ancilla)天然是多目标问题。

### 5.2 设计

- **状态**:与 MCTS 相同,`(terms, prefix_len, live_ancilla)`
- **动作**:`FactorAction`,或终止(转 `direct_plan`)
- **奖励**:`R(plan) = exp(−β · score(plan, w))`,其中 `w` 从权重单纯形采样(preference-conditioned)
- **训练**:Trajectory Balance 损失
- **编码器**：复用 L1 主干；当前只暴露资源权重条件接口，preference
  conditioning 尚未训练或验证

### 5.3 与 MCTS 的关系

**互补而非替代**:GFlowNet 提供多样性(按奖励正比采样,一次给出前沿上的多个点),MCTS 提供深度优化(单点精化)。

组合方式:GFlowNet 采样 N 个多样方案 → MCTS 精化 top-k。

### 5.4 验收

相对现有 Pareto 归档,**hypervolume 更大**,或同等 hypervolume 下更快。

---

## 6. L4 硬件适配与标定

### 6.1 L4a 适配管线

```
Plan ──emit_plan_to_circuit──► X/CNOT/MCT 序列              [现有]
     ──逻辑交换────────────► OpenQASM 3（保留 MCT）          [现有]
     ──① profile 感知分解──► rz/sx/x/cx 原生线路             [E3 v1 已实现]
     ──② layout/routing───► synthetic profile + shortest SWAP [E3 v1 已实现]
     ──③ 原生 artifact─────► 映射线路、拓扑、门集和参数清单   [E3 v1 已实现]
     ──④ 理想验证/含噪─────► 全基态等价 + Pauli trajectories  [E3 v1 已实现]
```

**① MCT → 实际门分解：** 现有 `resource_model.py` 只计算历史逻辑资源代理，
且 `logical_and` 分支可能包含测量/前馈式非对称 uncompute 假设。实际 emitter
不能被强迫逐门匹配该代理。报告必须同时保留：

- 历史逻辑资源代理，用于旧实验可比性；
- 实际分解/transpile 后的门数、深度和噪声结果。

两层指标之间只做标定和相关性分析，不宣称逐门相等。

硬件兼容使用非等强的三条证据路线：

1. **超导可执行路线**：局部耦合图、CX/ECR 类双量子位门、
   placement/routing/SWAP、理想与含噪仿真，以及 held-out 反馈标定；
2. **离子阱适配路线**：全连接 profile、RXX/MS 类相互作用、原生资源映射和
   理想层等价验证；不强制含噪仿真或真机；
3. **光量子边界路线**：形成输入能力、adapter 可行性和 unsupported-boundary
   表；该分支终止于能力边界，不进入门模型 transpile，也不伪造统一门级结果。

E3 v1 使用自研、严格限域的确定性最短路 SWAP router，只处理已经分解的
1/2-qubit 静态 Oracle、SWAP 插入和 layout 更新；它不是通用 placement/routing
方案。Qiskit `transpile`/SABRE 仍是后续超导/门模型路线的强基线候选，
Oracle-aware noise-weighted window router 也是 E3-v2 候选。当前 Qiskit 未安装且
依赖尚未冻结；任何最终第三方 SDK 都必须通过许可证、环境锁定和干净安装验证。
Clifford+T 仍可作为逻辑资源参考，不作为三条路线共同的强制中间层。

验收分成两级，必须分别报告：

1. **逻辑层**：`verify_oracle`、逻辑 IR 与保留 MCT 的 OpenQASM 交换保真；
2. **原生层**：实际分解和映射后、加噪前，用独立 unitary、statevector、
   truth-table 或符号检查验证严格等价。

### 6.2 L4b 噪声模型标定（simulator-first）

项目历史 `depth` 是“CNOT 数的顺序代理”，`t_depth_proxy` 是 `(T+3)//4` 的
阶段代理；E3 v1 首次增加独立的原生深度、原生双比特门和含噪任务 NLL，三者
与历史逻辑代理分栏保存，不声称逐门相等。

**E3 v1 实测：** 12 个固定 `n=4` calibration 函数产生 56 条候选观测和
57,344 noisy shots；12 个真值表 SHA 完全互斥的 test 函数形成 96 条
历史/反馈 utility × greedy/QAOA-shot trial 和 98,304 noisy shots。按函数留一
交叉验证选择 `alpha=10`，完整 calibration 拟合 MAE=0.04571、R²=0.8995、
Spearman=0.8472；但 test 上反馈 QAOA-shot 相对历史 QAOA-shot 的 NLL 差为
`+0.001293`，95% CI `[-0.001170, 0.004719]`，故主改善假设未获支持。96/96
线路通过 Plan/Circuit/Oracle 与原生全基态等价验证。

**E3-v2 做法：** 仅在 calibration 内加入编译前可得的原生 1q/2q、SWAP、
depth 与 duration 特征，联合选择正则和反馈尺度，再在新的 `n=5`/结构化/AES
held-out 函数上测试。Qiskit Aer 是候选对照，不是当前冻结依赖。可进一步分析：

```
fidelity ~ f(T, CNOT, depth, gates, peak_ancilla)
```

**产出**：历史逻辑资源、编译前原生特征与含噪任务 NLL 的相关/干预证据；
不能只报告标定内相关系数。

**必须写明的边界**:仿真噪声模型无法覆盖串扰、参数漂移、读出误差相关性等真实效应,结论仅"在给定噪声模型下成立",**不可外推为真机结论**。这符合赛题"避免夸大、明确限制条件"的要求。

**可选延伸**:用回归系数重新拟合 `ResourceWeights`,再综合,量化改进(数据级闭环,作为 L3b 算法级闭环的补充)。

---

## 7. L5a 布尔结构–量子资源探索图谱（P1 赛后研究）

本节不进入 XA-202609 当前源码、排期、实验、演示或交付门。

### 7.1 理论背景

Stab-QRAM(arXiv 2509.26494)证明:仿射布尔函数 `f(x) = Ax + b` 可用无辅助线的 CNOT+X 线路实现,**零 T-count**;并**明确把非仿射布尔数据列为开放问题**。

本引擎处理任意非仿射函数，并已有 Affine-FPRM 预条件搜索，因此可以探索
结构指标与资源的关系。但没有证据表明非线性度单独决定 T-count，不能预设
存在单调“定律”。

### 7.2 度量定义

**非线性度**(密码学标准):

```
NL(f) = min over all affine g of  d_H(f, g)
```

`d_H` 为真值表 Hamming 距离。仿射函数 `NL = 0`;bent 函数取最大 `2^{n-1} − 2^{n/2−1}`。

**Affine defect**(本项目定义,即 affine 搜索实际在最小化的量):

```
AD(f) = min over invertible A of  |{非线性 ANF 项 of f(Ax)}|
```

### 7.3 实验设计

| 步骤 | 内容 |
|---|---|
| 1 | 构造覆盖全谱的函数族:仿射(NL=0)→ 低 NL → 中 → bent/近 bent |
| 2 | 对每个函数计算 `NL`、`AD`,并用引擎综合得 T-count |
| 3 | 回归 T-count vs NL、T-count vs AD |
| 4 | 验证 Affine-FPRM 搜索确实降低 `AD` |
| 5 | 报告多变量关系、置信区间和负面结果；只有证据充分时再讨论上下界 |

### 7.4 现有结果的重新语境化 【这是最漂亮的部分】

| 现有结果 | 在新框架中的位置 |
|---|---|
| **AES S-box**(T-count 减半 48–54%,完整 2⁸ 验证) | **高端锚点** —— S-box 按高非线性度设计 |
| Affine 消融(60.92%/61.83% 增益) | **低端** —— 接近仿射的函数收益最大 |
| Stab-QRAM | **`AD = 0` 的退化情形** |
| exact XAG 乘法复杂度(12/72 达全局 T 下界) | **下界锚点** |

**四个已有结果被统一进一条理论曲线。** 这是零额外实验成本的理论增值。

---

## 8. 目录结构与模块划分

```
experiments/
├── src/
│   ├── foundation/                 【已有开发态 —— L1】
│   │   ├── __init__.py
│   │   ├── encoding.py             # frozenset[int] → T×n 张量 + 上下文通道
│   │   ├── equivariant.py          # 可交换矩阵层、主干
│   │   ├── heads.py                # action/value 双头
│   │   └── adapter.py              # score_actions / predict_log_ratio
│   ├── search/
│   │   ├── value_net.py            # 已有 learned value + cache/batch
│   │   ├── diversity_scheduler.py  # 已有：random/top-B/greedy/exact/QUBO
│   │   ├── qaoa_scheduler.py       # 已有：NumPy ideal/shot/noisy QAOA
│   │   ├── mcts_scheduler.py       # 已有：scheduler 适配、repair/fallback 诊断
│   │   └── execution_feedback.py   # 已有：冻结成本模型与置换不变结构特征
│   ├── hardware/
│   │   ├── qasm.py                 # 已有：逻辑 MCT OpenQASM 交换格式
│   │   ├── superconducting.py      # 已有：原生分解、synthetic profile 与路由
│   │   └── noise.py                # 已有：实际 Pauli statevector trajectories
│   ├── nmcts_solver.py             # 已接 value、scheduler 与可选执行反馈
│   ├── factor_plan.py              # 已接结构化 prior 协议
│   ├── synthesizers.py             # 已有 foundation_nmcts 开发入口
│   └── ...                         (其余不动)
├── scripts/
│   ├── train_expert_iteration.py   # 已有开发态
│   ├── run_prior_ablation.py       # 已有开发态
│   ├── run_qaoa_scheduler_pilot.py # 已有：E2 runner/bundle/verifier
│   ├── run_hardware_feedback_eval.py # 已有：E3 calibration/test runner
│   └── verify_hardware_feedback_bundle.py # 已有：独立 E3 verifier
├── tests/
│   ├── tests_smoke.py              【保持通过】
│   ├── test_equivariance.py
│   ├── test_foundation_adapter.py
│   ├── test_value_net.py
│   ├── test_synthesizers_foundation.py
│   ├── test_qasm_export.py
│   ├── test_diversity_scheduler.py
│   ├── test_qaoa_scheduler.py
│   ├── test_mcts_scheduler.py
│   ├── test_nmcts_scheduler_integration.py
│   ├── test_execution_feedback.py
│   ├── test_noise_backend.py
│   └── test_e3_artifacts.py
└── models/
    ├── boolean_oracle_fm_v3.pt     # 当前候选 checkpoint
    └── MODEL_CARD.md               # 待建：训练域、参数、SHA、限制
```

**改造原则：** 新增为主、保持旧 method 行为和实验结果可复现；新模块通过
显式 method/scheduler/profile 名称进入，不静默改变旧 portfolio。

---

## 9. 实验协议

### 9.1 等变性单元测试(L1 的第一道关)

```python
def test_variable_permutation_equivariance():
    """变量重标号 ⟹ 输出同构重标号"""
    terms = random_terms(n=8, count=12)
    perm = random_permutation(8)
    terms_p = apply_var_permutation(terms, perm)

    out   = model.var_logits(terms)      # ∈ R^8
    out_p = model.var_logits(terms_p)    # ∈ R^8

    assert allclose(out_p, out[perm], atol=1e-5)

def test_term_permutation_invariance():
    """项是集合,顺序不应影响输出"""
    terms = random_terms(n=8, count=12)
    assert allclose(model.value(terms),
                    model.value(shuffle_term_order(terms)), atol=1e-5)

def test_variable_shape_compatibility():
    """只验证同一参数接口可处理不同 T/n，不验证统计泛化"""
    for n in (4, 16, 64):
        for t in (3, 50):
            model.value(random_terms(n, t))   # 不应抛异常
```

### 9.2 数据划分

沿用项目既有惯例(`mcts_budget_policy` 用的 320/160/160),**训练/验证/测试严格无重叠,按函数名精确去重**。

### 9.3 评测协议 【不可违反】

`summary_large_neural_prior.csv` 的 `all_scores_identical=True` 暴露了一个陷阱:**portfolio guard 并行跑多个叶子方法取最优,系统性冲掉 AI 效果**。这就是 n=8/n=10 零结果的真正原因,不是模型不行。

因此任何新 AI 组件的评测**必须**:

| 要求 | 理由 |
|---|---|
| 在**叶子方法层面**报告,不是 portfolio 之后 | 否则 guard 会掩盖效果 |
| 同时报 score **和**运行时 | 现有 +91% 是硬伤,只报 score 是自欺 |
| 保留零收益的负面结果 | 项目在这点上一直做得好,应继续 |
| 配对比较,按函数名匹配 | 沿用现有 W/L/T 口径 |

### 9.4 回归保护

每次改动后必须:
1. `tests/tests_smoke.py` → `smoke ok`
2. 抽样复现若干 `results/raw_*.csv` 的历史行,确认旧方法行为未变
3. 三层验证(ANF 符号 / 发射线路 / 真值表)全部通过
4. 原生路径的分解与映射线路在加噪前必须通过独立理想等价验证；E3 正式
   test bundle 已完成 96/96 全基态等价，后续任何 profile 变化都必须重新验收

---

## 10. 里程碑与验收

完整日期与交付门见 `PROJECT_BLUEPRINT_XA202609.md`。本节记录服务器迁移前
开发快照；D1–D5 已确认，未完成项在服务器快照验证后转为施工任务。

### M1—— AI 核心冻结

- [x] `src/foundation/encoding.py`、`equivariant.py`、action/value heads
- [x] `score_actions()` 结构化 prior 协议
- [x] learned value、batch prefetch 和 progressive widening
- [x] `foundation_nmcts` 公开开发入口
- [x] 当前树全套测试 203 项与 legacy smoke 通过
- [ ] 冻结唯一推荐 checkpoint、模型卡、训练/测试 manifest 和 SHA
- [ ] C0–C7 因果矩阵生成正式 raw/summary/manifest

### M2—— 量子辅助调度

- [x] utility/redundancy 定义和归一化
- [x] random/top-B/greedy/exact 四条经典/诊断路径
- [x] 全 bitstring 罚项能量恒等式与固定基数可行集排序等价
- [x] \(K=0\)、\(K<B_{\mathrm{requested}}\)、
  \(K=B_{\mathrm{requested}}\)、\(K>B_{\mathrm{requested}}\) 边界和
  not-invoked/repair/fallback 分离
- [x] ideal/shot/noisy QAOA 路径及 direct non-fallback 证据
- [x] 接入 MCTS 独立子节点调度并保持 100% 语义验证
- [x] E2 420-trial bundle、24/24 verifier 与 checksum
- [ ] replay buffer → expert iteration 的反馈实验

### M3—— 原生门与含噪反馈

- [x] 逻辑 MCT OpenQASM 3 交换格式
- [x] 超导 synthetic profile 原生分解、最短路 SWAP、理想等价和可执行含噪仿真（E3 v1）
- [ ] 离子阱风格全连接 profile 的 RXX/MS 类原生资源映射与理想等价
- [ ] 光量子 capability/adapter/unsupported-boundary 表
- [ ] 三路线 profile 参数 manifest，且不把逻辑 QASM 测试冒充原生层验证
- [x] calibration/test 函数隔离的反馈标定（E3 v1；主改善假设未获支持）

### M4—— 竞赛交付

- [ ] 独立 `competition/` staging 和干净环境
- [ ] 单命令端到端原型
- [ ] 专用技术报告 PDF、安装使用文档、演示材料
- [ ] 报名表、许可/IP 说明和人工字段
- [ ] 独立 verifier 解包验证全部通过

### 全局完成门

七类交付物必须全部有证据。等变 policy/value 单测、逻辑 QASM 或旧论文结果
中的任一单项都不能代表竞赛原型完成。

---

## 附录 A:关键设计决策记录

本表记录已经确认的选择及其边界。

| 决策 | 理由 |
|---|---|
| 用可交换矩阵层而非 GNN | 状态天然是 T×n 矩阵,S_T×S_n 等变有完备参数化;GNN 需人为构图 |
| value 目标用 `log(achieved/direct)` | 跨训练尺度更稳定；实际泛化范围仍需独立测试 |
| 保留 `direct_plan` 可行上界 | 保证可行 direct 方案不丢失，不保证不差于旧 greedy/MCTS |
| QAOA 选择固定 B 个多样动作 | 每个动作独立成为 MCTS 子节点，保持现有 Plan 语义 |
| 自研 Oracle 专用路由，Qiskit SABRE 作强基线 | 严格限域并用等时间、多 seed、等价性实验决定是否升级 |
| simulator-first、真机可选 | 赛题允许仿真；必须明确 simulator-only 边界 |
| adapter 实现 `score_actions()` | 等变 scorer 需要原始项集；旧 scorer 保留 flat-feature fallback |
| 资源权重作为模型输入 | 提供条件化接口；v3 尚未证明多权重泛化 |
| QNN 只做小规模 value residual | 4–6 qubit 与同输入同参数 MLP 公平比较；未过门即降为附录 |

## 附录 B:参考文献

**表示 / 基础模型**
- Hartford et al., *Deep Models of Interactions Across Sets*. ICML 2018 —— S_T×S_n 可交换矩阵层
- A Survey of Circuit Foundation Model. *ACM TODAES* (2025)
- The Dawn of AI-Native EDA: Large Circuit Models. arXiv:2403.07257
- DeepGate2/3/4 —— 功能感知电路表示学习(真值表距离监督)

**搜索 / 闭环**
- Quantum-enhanced MCTS for combinatorial optimization (AtomTreeSearch). arXiv:2606.30415 —— **L3b 直接依据**
- Quantum Policy Iteration via Amplitude Estimation and Grover Search. arXiv:2206.04741
- AlphaCNOT: Learning CNOT Minimization with Model-Based Planning. arXiv:2604.13812
- Equivariant RL for Clifford Quantum Circuit Synthesis. arXiv:2605.10910

**生成模型**
- Jain et al., *Multi-Objective GFlowNets*. ICML 2023 —— **L2a 依据**

**理论锚点**
- Stab-QRAM: A Clifford-Only Quantum Oracle for Affine Boolean Data. arXiv:2509.26494 —— **L5a 的开放问题来源**
- Quantum circuit optimization with AlphaTensor. *Nature MI* 7 (2025)
- Does provable absence of barren plateaus imply classical simulability? *Nature Comms* (2025)

**(完整列表见 `RESEARCH_PLAN_AI4Q_Q4AI.md` §7 与 `DELIVERABLES.md` §9)**
