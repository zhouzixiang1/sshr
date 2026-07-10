# RL+MCTS 量子布尔函数综合方法:研究蓝图

> 读者:SSHR 作者本人。这份文档诚实指出 new-idea.pdf 当前形态在问题建模、可扩展性、新颖性上的硬伤,并给出一条与仓库现有资产强耦合、可向 ShortCircuit 等先验工作清晰区分的修正路线。

---

## 1. 一句话定位

**new-idea 当前写法在解一个与 SSHR 不同的、且自身不自洽的问题(量子态制备 `U(G)|0⟩=|T⟩`),而不是 SSHR 的可逆 oracle 综合(`O_f|x⟩|b⟩=|x⟩|b⊕f(x)⟩`)。两者的输入空间、输出空间、可逆性要求三者全不同。**

- SSHR 综合的是 **(n+1)-比特 bit-flip oracle**:作用在任意输入 `|x⟩` 上的可逆置换,CNOT/T 计数由 onset 上的奇偶覆盖(WP-SCP)诱导。
- new-idea 形式化的是 **n-比特态制备**:输入固定为 `|0⟩^⊗n`,目标是某个"计算基态叠加" `|T⟩`。
- 这是两个不同课题。**如果 new-idea 要对齐 SSHR**,必须改成 bit-flip oracle 设定并在 CNOT/T 计数上对齐;**如果坚持态制备**,则不能共享 SSHR 的 baseline、NPN 数据集和评价指标,且要独立论证 `|T⟩` 的可实现性(见 §3.1)。

**核心判断**:new-idea 的算法范式(AlphaZero policy+value+MCTS)已被 ShortCircuit 在经典域完整覆盖;它真正可信的增量空间在 **"问题设定(量子 oracle + 量子度量)" 叠加 "动作空间几何化(SSHR 平行体 macro-action)"**,而非"又一个 AlphaZero for circuits"。

---

## 2. 方法还原(8 个组件:它说了什么 + 还缺什么)

| # | 组件 | new-idea 说了什么 | 还缺什么(critical 缺口标 ⚠) |
|---|------|-------------------|------------------------------|
| 2.1 | 问题建模 | MDP:状态 `(T, U_t)`,动作=选门,转移 `U_{t+1}=gate·U_t`,找 `U(G)|0⟩^⊗n=|T⟩` | ⚠ `|T⟩` 无显式数学定义(归一化常数/相位约定/比特映射全缺),三种解读各有致命问题(见 §3.1) |
| 2.2 | 状态表示 | 输入=`[T 向量(2^n) ⊕ Re(U_t)展平 ⊕ Im(U_t)展平]`,维度 `2+2·2^n·2^n` | ⚠ 维度爆炸:n=6→8256,n=7→32896,n=8→131328;MLP 在 1e5 维稠密输入上训不动。"PCA/自编码器降维"是甩锅占位符,无消融 |
| 2.3 | 动作空间 | 选一个量子门(类型+作用比特),`|库|×C(n,2)`(双比特)或 `|库|×n`(单比特) | ⚠ CNT 库含 Toffoli(三比特 CCNOT)却按 `C(n,2)` 算,漏掉 `C(n,3)` 项;复杂度 `O(L·|A|)` 严重低估(实际含网络前向) |
| 2.4 | 奖励 | 终止稀疏 `R_final=+1 if F=1 else −1`;过程 `r_step=−λ` | ⚠ `λ` 无标定方法;`λ·L > 2` 时最优策略退化为"空线路拿 0";离散门库下 `F=1` 几乎不可达,reward 信号近乎全为 −1 |
| 2.5 | 双网络 | 共享主干;`π_θ=Softmax`→MCTS 先验 P;`V_ϕ=Tanh∈[−1,1]` | `V_ϕ` 用 Tanh∈[−1,1] 与 `z−λ·L`(可远小于 −1)尺度冲突;终态 ±1 与 rollout `−λL` 量纲不一致,会污染 Q |
| 2.6 | MCTS | AlphaZero 式 PUCT select/expand/模拟/backup;输出 `π=N/ΣN` | ⚠ "模拟(node)"默认策略缺失;未用 `V_ϕ(leaf)` 做叶估值(AlphaZero 标准做法),价值网络被浪费;Q 更新 `Q+=z−V_ϕ(s_node)` 非常规(疑似 bug,未做 1/N 归一,Q 会单调膨胀) |
| 2.7 | 训练 loss | `L=(z−V_ϕ(s))² − πᵀ log π_θ + λ‖θ‖²` | 缺 entropy bonus(主干 Tanh 下易塌缩);**无 SL 预训练阶段**(ShortCircuit 用 ABC 最优解做 SL bootstrap 来对抗 reward sparsity);正则符号 `λ` 与步惩罚 `λ` 复用导致记号混淆 |
| 2.8 | 门库 | CNT{NOT,CNOT,Toffoli} / 通用 / Clifford+T 三选 | 库选择未与问题对齐:Clifford+T 下 `U(G)|0⟩` 系数落在 `Q(ζ_8)` 上,`F=1` 几乎不可达;CNT 下又丢失了通用性 |

---

## 3. 致命问题清单(按严重度排序)

### ⚠ 3.1 【critical】`|T⟩` 的定义在数学上不自洽
**问题**:PDF 只说"真值表对应的计算基态叠加",未给归一化/相位/比特映射。三种解读各有硬伤:
- (a) 振幅编码 `|T⟩=Σ_x T(x)|x⟩`:**非归一化、不可逆**。置换门(CNOT/Toffoli/X)在酉群上,绝不可能把单位向量 `|0⟩^⊗n` 映到非单位向量。方法与门库自相矛盾。
- (b) 相位编码 `|T⟩=Σ_x (−1)^{T(x)}|x⟩`:此即 phase oracle,**与 SSHR 的 phase-oracle 视角同构**——那 new-idea 只是换搜索视角,非新问题。
- (c) 稀疏态制备:仅对 `||T||_0=1` 的单点函数平凡,对一般布尔函数不适用。

**修复方案**:采用 SSHR 的 **bit-flip oracle** 设定。在 `n+1` 比特上找 `G` 使 `U_G|x⟩|0⟩=|x⟩|f(x)⟩` 对所有 `x` 成立。验证用 `tests/test_correctness.py` 的 `circuit_implements`(经典模拟,`O(2^n)`,`F∈{0,1}` 离散可判),**彻底避开浮点酉矩阵等价判定**。优化目标改为 CNOT/T 计数,与 SSHR 一致。

### ⚠ 3.2 【critical】`U_t` 全酉矩阵展平 = 维度灾难 + 内存炸裂
**问题**:状态 `2×2^n×2^n` 维。n=8 单节点 fp32 即 524KB;MCTS 树 1e4 节点 → n=8 时 5.24GB,1e5 节点 → 52GB。且 MLP 在 1e5 维稠密输入上 sample-inefficient。

**修复方案**:**根本不要存 `U_t`**。采用 SSHR 已验证的状态表示:
- 状态 = 当前 onset 位掩码(整数,`n=8` 仅 256 bit=32 字节)+ 候选平行体集合特征。
- MCTS 节点只存 `(A_mask, cost_so_far, path)`,Ut/电路按需在叶节点重建(正是 `sshr_mcts_v2.py` 的做法)。
- 这样临界 n 可推到 **8+**(受限于候选枚举而非表示)。

### ⚠ 3.3 【critical】奖励极稀疏 → credit assignment 与价值网络双重失败
**问题**:n≥4 时正确线路深度常达几十(门级更深)。随机门序列 `F=1` 概率指数级趋 0,早期 rollout 几乎全 `z=−1`,`V_ϕ` 收敛到 −1 后梯度消失。

**修复方案**(两层):
1. **不在门级建 MDP**,在"块"级建:每步选一个 parallelotope 块 P,奖励 = 该块覆盖的有效 onset 顶点数 − 块成本,状态 A 单调缩减,每步都有明确有界奖励信号(直接复用 `sshr_mcts_v2.py` 的 `reward=−total_cost` 与 `_backpropagate`)。
2. 若坚持门级:用 dense shaping reward,`z=ΔF`(每步给 `|Tr(U_t† U_target)|/2^n` 增量);并禁止"空线路"作为可接受终止。

### ⚠ 3.4 【critical】与 ShortCircuit 严重重叠 + 缺 SL 预训练
**问题**:ShortCircuit (arXiv:2408.09858v2, Huawei Noah's Ark) 已完整占据"AlphaZero policy+value + MCTS + truth-table 输入 + 自博弈"范式(摘要明写 "an AlphaZero variant to handle the double exponentially large state space and the reward sparsity",PUCT 公式逐字符一致)。new-idea **连 SL 预训练都没有**,反而更弱。

**修复方案**:放弃"方法层面=AlphaZero for circuits"卖点。三个差异化支柱(详见 §5、§7):
- (a) **目标度量量子化**:T-count/CNOT/T-depth(对标 XAG/XORAX/SSHR),而非 AIG size。
- (b) **动作空间几何化**:平行体 macro-action,候选 `O(10^4)` 而非 `O(10^7)` 享受 `2^m` 压缩。
- (c) **SL bootstrap**:用 SSHR-I 的 n≤6 最优 ILP 解做 teacher(模仿学习/DAGGER),`reward` 从 ±1 改为 `−block_cost` 增量 + 终态覆盖全部 onset 的 bonus。

### ⚠ 3.5 【serious】Algorithm1 Q 更新增量 `z−V_ϕ(s_node)` 非常规,疑似 bug
**问题**:AlphaZero 标准是 `Q(s,a)=mean(z)`,增量 `(z−Q_old)/N`。new-idea 把 `V_ϕ` 当 baseline 做差(类似 actor-critic advantage),但:(a) `V_ϕ` 训练目标又是 `V_ϕ→z`,`V_ϕ` 收敛后 `z−V_ϕ→0`,Q 项失效、退化为纯先验采样;(b) baseline 应是 `V_ϕ(s_parent)`(动作前),非 `s_node`(动作后);(c) 未说明是否做 `1/N` 归一,Q 会单调膨胀。

**修复方案**:改回标准 AlphaZero `Q ← (Q·N+z)/(N+1)`。若确需 advantage baseline,职责分离:`advantage=z−V_ϕ(s_parent)` 仅用于选择打分,不混入 Q 累加。文中给出消融。

### ⚠ 3.6 【serious】MCTS "模拟" 阶段策略缺失,叶估值浪费价值网络
**问题**:Algorithm1 第15行 `z←模拟(node)` 后只补"可采用随机走子"。门级随机 rollout 几乎不可能命中 `F=1`,z 退化为常数 −1。未用 `V_ϕ(leaf)` 做叶估值。

**修复方案**:AlphaZero 式叶估值 `z←V_ϕ(s_leaf)`,跳过 rollout,或 `z=r·V_ϕ+(1−r)·rollout` 混合。rollout policy 用仓库已有的 `greedy_rollout`(按覆盖/成本贪心选块),而非门级随机走子。

### ⚠ 3.7 【serious】门级搜索是错误的抽象层次
**问题**:仓库 `sshr_beam.py` / `sshr_mcts_v2.py` 已在"块"空间搜索(动作=parallelotope P,`A←A−vertices(P)` 单调缩减),Table V 显示 n≤6 优于 MCTS,可扩展到 n=7。new-ircuit 选了最难的路径:在原始门级上 RL+MCTS,违反仓库 `AI_SSHR_DESIGN.md` 列出的三条门级搜索禁忌(空间爆炸、正确性难保证、信号稀疏)。

**修复方案**:动作 = parallelotope 块(由 `synth_block` 确定性编译为线路),在此抽象上接 `π_θ/V_ϕ`。这是 §4-§5 的核心。

### ⚠ 3.8 【minor】三比特门漏算 + 度量尺度不一致
- CNT 库含 Toffoli 却按 `C(n,2)` 算,漏 `|CCNOT|·C(n,3)` 项;`|A|` 与复杂度 `O(L·|A|)` 系统性低估。
- `V_ϕ` 用 Tanh∈[−1,1] 与 `z=−λ·L`(可远小于 −1)尺度冲突。

**修复方案**:动作空间公式补三比特项 `|A| += |CCNOT|·C(n,3)`;`V_ϕ` 输出层改线性头 + clip,或全程归一化回报 `z=2F−1∈[−1,1]`,步惩罚写 `−λ·L/L_max`,显式 `λ≤1/L_max`。

---

## 4. 与仓库的整合蓝图

| 仓库组件 | 复用方式 | 接到 new-idea 哪个组件 | 预期收益 |
|----------|----------|------------------------|----------|
| `sshr_mcts_v2.py` `_Engine._valid_numpy`(L115-126,single/double/object 三档 uint64 向量化) | 直接调 | RL 环境 `step()/valid_actions()` | 状态转移 `O(1)`,远超新写 frozenset 循环 |
| `sshr_mcts_v2.py` `_MCTSNode` + UCT + progressive widening + anytime + 全局最优跟踪 | 复用骨架,把 `_simulate` 贪心 rollout 换成 `V_ϕ(s)` 单次前向 | new-idea 的 MCTS 主体 | 升级为 AlphaZero 式,无需重写搜索栈 |
| `parallelotope_enum.enumerate_parallelotopes`(lru_cache 按 n) | 直接调 | 动作空间(候选块来源) | 候选 `O(10^4)` 而非 `O(10^7)` 门组合 |
| `block_synth.synth_block` + `block_cnot_cost`/`block_t_cost` + `mct_cost`(Table II,含 RP-Toffoli k=2→T=4) | 直接调 | reward 的 cost 函数;块→门的确定性投影 | 解析成本无需模拟线路;`2^m` 几何压缩 |
| `sshr_i.py` `_solve_ilp_gurobi(... cutoff, warm_start_indices)` + `sshr_i(bf, warm_start_circuit=...)` | RL 解 → MIPStart + Cutoff | **反向反哺 ILP**(new-idea→SSHR 通道) | n≥7 ILP 从"超时"变"可能可行";warm-start 保底 RL 解 |
| `ai_sshr_experiment/data_collector.py` 4 个 teacher(ILP set-membership / beam step-choice / xor_beam / random_xor) | 直接复用 CSV | 策略/价值网络的 **SL 预训练 bootstrap** | 避免 RL 冷启动稀疏奖励崩溃 |
| `ai_sshr_experiment/feature_extractor.candidate_features`(32 维候选×状态联合特征) | 拼接作输入 | `π_θ`/`V_ϕ` 输入特征 | overlap/cover_ratio/cost_per_overlap 是现成的局部价值先验 |
| `ai_sshr_experiment/rankers.RuleRanker`(dim=4,cover=3,removal=0.5,cost=0.08,off=2,singleton=1.5) | L2 正则锚点 | `π_θ` 输出层初始化 | 好的解析先验,加速收敛 |
| `gnn-sshr/src/data/graph_builder.build_bipartite_graph` + `CandidatePruner.forward`(cand_h 已验证 n=3 recall 0.58→0.75) | freeze + projection,或端到端微调 | `π_θ`/`V_ϕ` **输入编码层** | 唯一直接命中"多变量电路状态表征学习"的现成资产 |
| `sshr_beam.py` `_BeamEngine.greedy_lb` + `top_k_actions` | `V_ϕ` 替代 greedy_lb;`π_θ` top-K 替代 top_k_actions | Beam/MCTS 的动作裁剪 | n≥6 候选爆炸(n=6→10299, n=7→75905)的剪枝 |
| `npn_reps_n4.py`(222 个 n=4 代表元)+ `paper_data.py`(n=4 CNOT=4696 参考值) | 训练集 + eval 基线 | 数据扩增 + 评估 | 无需自建数据集;NPN 类内共享价值标签 |

### 高杠杆 3 件套(必做)
1. **动作从"门"换成"平行体块"**(§4 第 3-5 行):候选 `O(10^4)`,享受 `2^m` 压缩,这是与 ShortCircuit 唯一可信的差异化方向。
2. **RL 解 → SSHR-I MIPStart 反哺**(§4 第 5 行):即使 ILP 在 budget 内证不出更优,warm-start 也保证 RL 解作为输出底线,且可能让 n≥7 ILP 可行。
3. **SL bootstrap + NPN 扩增**(§4 第 6、10 行):用 ILP teacher 做行为克隆预训练,NPN 类内数据扩增,对标 ShortCircuit 的两阶段训练。

---

## 5. 重新设计建议:几何先验引导的 AlphaZero for Quantum Oracle Synthesis

### 推荐的"修正版方法"
> **重新定位论文标题**:从"基于强化学习与 MCTS 的量子布尔函数综合方法"改为"**几何先验引导的层级化 AlphaZero:面向量子 Oracle 综合的平行体宏动作搜索**"。

**架构(自底向上)**:

```
┌─────────────────────────────────────────────────────────┐
│ 顶层:AlphaZero 式 MCTS(动作 = 选平行体块 P)            │  ← 复用 sshr_mcts_v2 骨架
│  - select: PUCT = Q + c·P(s,a)·√ΣN/(1+N)               │
│  - expand: 只展开 π_θ top-K(K=branch,非 progressive widening)│
│  - evaluate: z ← V_ϕ(s_leaf),跳过 rollout              │
│  - backup: Q ← (Q·N+z)/(N+1) [标准 AlphaZero,非残差]    │
├─────────────────────────────────────────────────────────┤
│ 网络层:共享主干 + 双头                                  │
│  - 输入:GNN 编码(HeteroGraphSAGE cand_h ⊕ parity_h)   │  ← freeze gnn-sshr
│        ⊕ 32 维标量特征(feature_extractor)              │
│        ⊕ 当前 onset 位掩码 A(int)的 embedding           │
│  - π_θ:对候选块打分(softmax over valid blocks)        │
│  - V_ϕ:估计从 A 出发的剩余最优 CNOT/T 成本(线性头)    │
├─────────────────────────────────────────────────────────┤
│ 底层:block_synth.synth_block(块→门的确定性投影)        │  ← 复用仓库
└─────────────────────────────────────────────────────────┘
```

**关键设计决策**:
- **状态**:onset 位掩码 `A`(整数)+ 候选块集合 S 的特征。**不存 `U_t`**。
- **动作**:选一个 parallelotope 块 P(候选 idx),`A←A−vertices(P)`(monotone 语义,保证 rollout 必终止)。
- **奖励**:`z=−Σ block_cost`(负累计成本,λ 隐含在成本函数里,天然有界)。终态覆盖全部 onset 给 bonus。
- **训练**:两阶段。**Stage 1 SL**:用 SSHR-I 的 n≤6 最优 ILP 解做行为克隆(`(s, optimal-block-action)` 标签)+ `V_ϕ` 用 `opt_cost` 做监督回归。**Stage 2 RL**:self-play 微调(policy gradient + KL 约束防遗忘)+ TD/贝尔曼自举。
- **问题设定**:bit-flip oracle(`n+1` 比特),CNOT/T 计数为目标。
- **数据扩增**:NPN 等价类归一化(`npn_reps_n4.py`),类内样本共享价值标签。
- **反哺**:RL 解 → SSHR-I MIPStart + Cutoff,闭环。

### 为什么这版更强
1. **状态维度从 `2×2^n×2^n` 压到 2 个整数**,n=8 可用(受限于枚举而非表示)。
2. **奖励稠密**(每步 `−block_cost`),`V_ϕ` 可学。
3. **SL bootstrap** 避开 reward sparsity 冷启动崩溃。
4. **monotone 语义** 避免 n≥7 XOR 级联污染(SSHR-H/I 的天花板)。
5. **2^m 几何压缩** + GNN 结构先验,搜索效率结构性优于裸门级。

### 与 ShortCircuit 的区分度(核心)
| 维度 | ShortCircuit | 本修正版 |
|------|-------------|----------|
| 问题 | 经典 AIG 综合 | 量子 Oracle 综合 |
| 目标度量 | AIG size | T-count/CNOT/T-depth |
| 动作 | 选两个节点生成 AND | 选平行体块(几何 macro-action) |
| 状态 | truth-table 节点向量 | onset 位掩码 + GNN 候选嵌入 |
| 门库 | AND/INV | CNOT/T/MCT(经 block_synth 投影) |
| 归纳偏置 | AIG 结构 | **平行体几何 + `2^m` 压缩** |

**这既非 ShortCircuit(经典 AIG)、也非 SSHR-MCTS(无学习)、也非 GNN-SSHR(无 RL/MCTS 内联),构成真正的三方空白增量。**

---

## 6. 实验路线图

### Phase 0:基准复现与基础设施(1-2 周)
- **目标**:确认 baseline 数字对齐 paper,搭好 RL 环境。
- **实验**:
  - 复现 SSHR-H/SSHR-I/SSHR-Beam/SSHR-MCTS v2 在 n=3,4,5,6 上的 CNOT/T 总和,对齐 `paper_data.py`(n=4 CNOT=4696, RP-T=4856)。
  - 跑 `tests/test_correctness.py` 确认 `circuit_implements` 验证器可用。
- **数据集**:n=3 全 255 非零函数 + `npn_reps_n4.py` 全 222 类。
- **风险**:Gurobi license;n=5 全量 ILP teacher 需 50-70h(已知瓶颈)。
- **回退**:n=5 用 NPN 代表元子集;n=6 用 SSHR-Beam 解近似 teacher。

### Phase 1:小规模消融(n=3,4)— 验证修正版设计(2-3 周)
- **目标**:证明"块级 + SL + GNN 先验"在 n=3,4 上有效。
- **实验**:
  1. **动作粒度消融**:门级 vs 块级(本修正版) → 比较 `V_ϕ` 收敛曲线、最终 CNOT。
  2. **SL bootstrap 消融**:有/无 SL 预训练 → 比较 reward sparsity 下的成功率。
  3. **状态表示消融**:`U_t` 展平 vs onset 位掩码 + GNN → 比较训练时间、内存。
  4. **Q 更新消融**:`z−V_ϕ(s_node)` vs 标准 `(z−Q)/N` → 验证 §3.5 bug 修复。
- **baseline**:SSHR-I(n≤4 精确最优)+ SSHR-Beam + SSHR-MCTS v2。
- **指标**:CNOT 数、T 数、深度、成功率(%)、wall-clock。
- **通过门槛**:n=4 上修正版 ≥ SSHR-I 最优解的 95%,且优于 SSHR-MCTS v2。

### Phase 2:规模化(n=5,6,7)— 主攻 SSHR-I 失效区(3-4 周)
- **目标**:证明修正版在 n≥7(ILP 失效、XOR 级联污染区)有增量。
- **实验**:
  1. n=5,6 全量 / 采样,对标 SSHR-I 与 ShortCircuit 复现。
  2. **n=7 关键实验**(论文核心 claim):修正版 vs SSHR-Beam(monotone 语义同,但无学习)→ 证明学习带来的增益。
  3. **ILP 反哺实验**:RL 解 → SSHR-I MIPStart,看能否让 n=7 ILP 在 budget 内可行。
- **数据集**:n=5/6 NPN 代表元 + 随机采样;n=7 随机采样(候选 75905,需 GNN 剪枝)。
- **baseline**:SSHR-Beam、SSHR-MCTS v2、ShortCircuit 复现(适配量子度量)。
- **指标**:CNOT 数、T 数、深度、成功率、ILP warm-start 加速比。
- **风险**:n=7 GNN 推理延迟 200-500ms,需缓存/轻量化;n=8 候选 609441,object-array fallback 慢。
- **回退**:n=7 用 numba uint64×4 或 Python bigint + 位运算批处理替换 object 数组(定向工程增量)。

### Phase 3:对比与可扩展性(n=8 + 跨方法对比)(2-3 周)
- **目标**:全面对比,定位论文结论。
- **实验**:
  1. n=8(候选 609441)可扩展性测试 + 工程优化。
  2. 与 ShortCircuit/Circuit Transformer/XAG 的跨域对比(适配量子度量)。
  3. T-count vs CNOT 目标切换消融。
- **baseline**:所有 SSHR 变体 + ShortCircuit + XAG 编译。
- **指标**:CNOT 数、T 数、T-depth、ancilla、成功率、wall-clock、ILP 加速比。

---

## 7. 与 Prior Art 的差异化定位(Delta 表)

| 方法 | 问题 | 动作 | 状态 | 目标度量 | 学习 | 与本修正版的 Delta |
|------|------|------|------|----------|------|---------------------|
| **ShortCircuit** | 经典 AIG | 选两节点生成 AND | truth-table 节点向量 | AIG size | AlphaZero SL+RL | **本版:量子 Oracle + 平行体几何 macro-action + 量子度量** |
| **Circuit Transformer** | 经典逻辑 | token 生成 | transformer hidden | 门数 | 纯监督 + masking | 本版:RL 在线搜索 + 块级动作 |
| **INVICTUS** | 经典逻辑 | 选 ABC recipe | recipe 序列 | ADP | 离线 RL + MCTS | 本版:量子域 + 几何候选 |
| **BDD2Seq** | 可逆合成 | 选变量序 | GNN 图 | Quantum Cost | GNN + beam | 本版:RL 自博弈 + 块级 |
| **PWMCTS** | QAOA ansatz | 选采样方案 | PQC | 能量/CNOT | 纯 MCTS(无 RL) | 本版:RL 双网络 + oracle 综合 |
| **MCTS-QAOA** | QAOA 参数 | 选 γ,β | 参数树 | 能量 | 纯 UCT | 本版:RL + 离散块动作 |
| **XAG/XORAX** | 量子编译 | 无(规则) | XAG 图 | T-count | 无 | 本版:RL 学习 + 几何候选 |
| **SSHR-H/I** | 量子 Oracle | 平行体块 | onset 掩码 | CNOT/T | 无(贪心/ILP) | 本版:**加 RL 双网络 + ILP 反哺** |
| **SSHR-MCTS/Beam** | 量子 Oracle | 平行体块 | onset 掩码 | CNOT/T | UCT(无先验) | 本版:**加 π_θ/V_ϕ 学习先验** |
| **GNN-SSHR** | 候选筛选 | 无(打分) | 异构图 | CNOT/T(间接) | GNN 监督 | 本版:**加 RL/MCTS 内联 + 价值网** |

**论文一句话定位**:首个**几何先验引导的层级化 AlphaZero**,在 SSHR 平行体 macro-action 上做 RL/MCTS,用 GNN/LightGBM 先验 + ILP 监督价值网 + NPN 扩增,主攻 SSHR-I 失效的 n≥7,并以 RL 解反哺 ILP warm-start。

---

## 8. 立即可做的 3 件事(本周可启动)

1. **定锚问题设定 + 写一段"问题对齐"修复稿**(半天)。
   - 把 `U(G)|0⟩=|T⟩` 改为 bit-flip oracle `U_G|x⟩|0⟩=|x⟩|f(x)⟩`。
   - 写明 `|T⟩` 弃用理由(振幅编码不可逆、相位编码等价 phase oracle)。
   - 用 `bool_func.py` / `tests/test_correctness.py:circuit_implements` 作验证器,在文档里固化。
   - **产出**:`new-idea-v2.md` §1(问题建模),供后续所有章节引用。

2. **跑通 SSHR-MCTS v2 + SSHR-Beam baseline,固化 n=3,4,5 数字**(1-2 天)。
   ```bash
   cd /Users/zhouzixiang/Desktop/tzb/src/sshr && \
   /opt/anaconda3/envs/mcts-qoracle/bin/python experiments/mcts_beam_compare.py --ns 3 4 5
   ```
   - 对齐 `paper_data.py`(n=4 CNOT=4696)。
   - 导出 `(func_tt, opt_cost, opt_blocks)` 作 SL teacher CSV。
   - **产出**:`data/teacher_n3_n4.csv`,Phase 1 消融的 ground truth。

3. **搭最小可行 RL 环境骨架(块级动作 + onset 状态,先不接网络)**(2-3 天)。
   - 复用 `sshr_mcts_v2._Engine._valid_numpy` 做 `step()/valid_actions()`。
   - reward = `−block_cnot_cost(P)`(monotone 语义,A 严格缩减,episode 必终止)。
   - 随机 agent 跑通 n=3 全 255 函数,确认环境正确性(成功率应 100%,因为单例保证覆盖)。
   - **产出**:`src/rl_oracle/env.py` + 一个 `random_agent.py` 冒烟测试。

> 这 3 件事完成后,即可在 §5 修正版架构上接 GNN 编码层 + SL 预训练,正式进入 Phase 1。

---

**最后一句诚实评估**:new-idea.pdf 当前形态有 4 个 critical-blocker(`|T⟩` 不自洽、`U_t` 维度爆炸、奖励不可用、与 ShortCircuit 重叠),按原文写法**不可直接实现、不可复现、过不了 2026 年顶会 novelty 关**。但仓库现有资产(SSHR 几何候选 + MCTS 骨架 + GNN/LightGBM 先验 + ILP teacher + NPN 数据)提供了**一条清晰的、与所有 prior art 都不重叠的修正路径**——几何先验引导的层级化 AlphaZero。按 §5-§6 执行,2-3 个月可产出可投稿的实验结果。