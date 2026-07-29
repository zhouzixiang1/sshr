# Boolean Oracle 综合与硬件感知量子编译：强对比文献矩阵

更新时间：2026-07-22。该矩阵服务于 XA-202609 竞赛文档的相关工作、实验设计和结论审计；BibTeX 键见 `references.bib`，23 条正文引用的逐条核验结果见 `literature_verification_audit.json`、`.csv` 与 `.md`。

## 1. 先固定“比较的是不是同一件事”

当前项目的主要输入是 Boolean 函数，目标语义为位翻转 Oracle

\[
|x\rangle|y\rangle\mapsto |x\rangle|y\oplus f(x)\rangle .
\]

逻辑层在 ANF/FPRM 因子计划上搜索，输出 X/CNOT/MCT；Resource-NMCTS 以启发式或学习先验引导候选选择。硬件层目前把逻辑线路映射到显式但**合成的** line/grid/heavy-hex 等耦合图，并检查门基、耦合边及等价性。它尚不等于真实设备校准感知编译，也没有完整 Clifford+T/Rz 旋转综合后端。

因此文献被分成四类：

- **D（直接可比）**：输入语义同为 Boolean/量子 Oracle，输出资源可以在统一门集和 ancilla 规则下重跑。
- **S（搜索机制可比）**：MCTS、RL 或生成模型相近，但目标对象不是本项目的 Boolean Oracle。
- **P（后综合可比）**：从已有线路开始做 T-count、ZX 或其他重写，不承担函数到 Oracle 的前端综合。
- **H（硬件层可比）**：做布局、路由、校准感知或硬件排序；必须先冻结同一逻辑线路才可公平比较。

“作者报告”仅描述原论文实验，不能转化为本项目已胜出的证据。当前结果只有在相同函数、预算、门分解、拓扑、种子和验证门槛下重跑后，才能写成本项目与某篇论文的定量胜负。

## 2. Boolean Oracle、ESOP/ANF 与 MCT 综合

| 文献（状态） | 原问题、表示与主要指标 | 与本项目真正可比的维度 | 不可比边界 | 竞赛文档可用的谨慎表述 |
|---|---|---|---|---|
| `gupta2006pprm` Gupta, Agrawal & Jha, TCAD 2006；DOI 已核验；**D** | 用 PPRM 表示和因子共享构造可逆逻辑线路，核心操作落到 generalized Toffoli；关注量子代价、门数与共享结构。 | ANF/PPRM 项、公共因子复用、MCT 控制数分布；可在相同真值表和同一 MCT 分解表下比较。 | 原文面向一般可逆函数/置换；本项目多为单输出 bit-flip Oracle。若 ancilla、负控制或量子代价表不同，数字不能直接并列。 | “经典 PPRM 因子共享已证明代数结构会决定 Toffoli 级资源；本项目把这一结构选择扩展为受资源目标约束的搜索问题。”不能写“首次发现因子共享”。 |
| `fazel2007esop` Fazel, Thornton & Rice, PACRIM 2007；DOI 已核验；**D** | 把 ESOP 立方项直接转为 Toffoli cascade，讨论项序与门级代价。 | `direct_anf`/ESOP 是最低限度直接基线；可比项数、MCT 数、分解后的 CNOT/T、深度。 | ESOP 立方、极性和输出约定必须一致；仅比较高层 Toffoli 数会掩盖不同控制数的巨大分解差异。 | “ESOP-to-Toffoli 是最直接的 Oracle 实现路径之一，因此 Direct-ANF/ESOP 必须保留为透明基线，而非只与复杂学习方法比较。” |
| `wille2009bdd` Wille & Drechsler, DAC 2009；DOI 已核验；**D（部分）** | BDD 分解支持较大可逆函数综合；强调可扩展性以及由图结构得到的级联线路。 | 可比较综合成功率、运行时间、峰值内存，以及统一分解后的门资源。 | BDD 变量序、一般多输出可逆规格与本项目的小规模真值表/单输出 Oracle 不同；不能只拿门数证明全面优于。 | “BDD 路线提供规模扩展参照，而 ANF/FPRM 搜索更强调小中规模函数上的代数因子与资源权衡。” |
| `meuli2019multiplicative` Meuli et al., ICCAD 2019；DOI/arXiv 已核验；**D** | 以 XOR-AND 网络的 multiplicative complexity 连接 AND 数、T-count 与 ancilla；还讨论 SAT 支持的空间—T 交换。 | 同一 Oracle 语义下的 T-count、AND/MCT 非线性节点、峰值 ancilla 与运行时间。 | 本项目 X/CNOT/MCT 的 T-count 是经选定 Toffoli 分解得到的代理；没有冻结分解模板时，不可与论文的 Clifford+T 构造直接比。 | “AND/乘法复杂度为低 T-count Oracle 提供了理论支点；本项目需同时报告 MCT 级与固定 Clifford+T 分解后的资源，不能用加权总分替代 T-count。” |
| `meuli2020ros` Meuli et al., EPTCS 2020；DOI/arXiv 已核验；**D（强）** | ROS 用资源感知 LUT mapping 和 SAT garbage management 自动综合 Oracle，优化 qubits 与 operations。 | 同一 Boolean benchmark 下的 qubit/ancilla、操作数、T/CNOT/深度、覆盖率和超时；是最重要的外部任务级基线之一。 | 本项目当前 mockturtle/CirKit probe 不含 ROS 的 SAT 垃圾管理和可逆线路发射，不能冒充 ROS 复现。若无法运行官方 ROS，只能列为文献参照。 | “ROS 与本项目解决同类资源受限 Oracle 综合问题；正式‘优于 ROS’结论必须来自可执行实现或作者结果可严格对齐的实例，而不是逻辑网络代理。” |
| `meuli2022xag` Meuli, Soeken & De Micheli, npj QI 2022；DOI 已核验；**D（强）** | 用 XAG 表示 Boolean 函数，使 XOR 与 AND 的不同量子成本显式化，研究 T-count/ancilla 的综合权衡。 | Boolean 输入、XOR/非线性结构、T-count、ancilla；mockturtle XAG 适合作为公开工具链逻辑网络基线。 | XAG 节点统计不是完整量子线路；缺失 garbage management、门调度或固定后端分解时，不能与 mapped CNOT/depth 混为一表。 | “XAG 是与 ANF/FPRM 因子搜索最接近的表示级参照；本项目的价值应定位为不同结构搜索与多资源目标，而非未经实验就宣称替代 XAG。” |
| `henderson2023minimal` Henderson et al., SPIE 2023；DOI/arXiv 已核验；**D（语义边界）** | 自动生成最小 qubit Oracle，并与保留函数 domain 的嵌入方式比较 qubit 与线路复杂度。 | Oracle 输入/输出寄存器约定、domain-preserving 语义、qubit/ancilla 与门复杂度权衡。 | 其嵌入函数与本项目固定的单输出 bit-flip 语义不完全相同；不能把“最小 qubit”迁移为同一 ancilla contract 下的门资源最优。 | “Oracle 的 qubit 数与是否保留 domain 是独立设计选择；本项目固定 domain-preserving bit-flip 语义，并显式验证辅助位回零。” |
| `yu2025backend` Yu et al., ASP-DAC 2025；DOI/作者论文已核验；**D + 后端边界** | 在 XAG Oracle 综合中纳入 fault-tolerant back-end 指标；作者报告其 benchmark 上 T-count、逻辑时间步和 helper qubit 的平均下降。 | 同一函数、同一 QEC/Clifford+T 后端时可比较 T、逻辑时步与 helper qubits；也说明前后端协同的重要性。 | 论文后端是容错/QEC 语境；本项目的 NISQ 合成拓扑映射不是同一层次，不能用 synthetic 2Q gate 数替代 logical time steps。 | “近年 Oracle 综合已开始把后端成本前置进逻辑优化。本项目现阶段只可称 topology-aware proxy；完成相同 back-end 模型前不得声称达到或超过该后端感知能力。” |
| `zheng2025sshr` Zheng et al., ICCAD 2025；DOI/arXiv/会议程序已核验；**D（最接近）** | SSHR 利用超立方体中的 parallelotope 空间结构综合 \(n\le 8\) Boolean 函数；SSHR-H 用启发式，SSHR-I 用 ILP，目标偏 CNOT/MCT。 | 与项目输入规模、Boolean 语义和 CNOT 导向高度一致；应在相同函数、SSHR 参数、MCT 分解、超时和硬件映射设置下直接对比。 | 原文摘要的 56%/81% 是其相对 ESOP/XAG 的作者结果，不能作为当前项目的基线数值；SSHR-I 还依赖不同求解器环境。当前 SSHR-Beam 是项目基于相同表示实现的 beam-search 扩展，不是 SSHR-I 的替代复现。 | “SSHR 是当前最强的同任务小规模比较点。冻结 primary20 只含 SSHR-H 与本地 SSHR-Beam；未运行 SSHR-I，因而不能声称超过论文完整方法。胜负按独立函数统计，并保留失败与超时。” |

### 逻辑层最低公平协议

| 必须冻结的因素 | 为什么会改变结论 | 交付中应保存 |
|---|---|---|
| 函数与输出语义 | 同一真值表也可能实现 phase oracle、bit-flip oracle 或一般置换 | truth table、函数 SHA256、输入/输出位顺序、oracle 类型 |
| ancilla 规则 | 脏 ancilla、干净 ancilla、uncompute 与峰值/总量定义不同 | 初态、末态清零验证、显式与峰值 ancilla |
| 门库与分解 | 一个高控制 MCT 的 CNOT/T 代价取决于分解、可用 ancilla 和相对相位门 | 高层门序列、分解器版本、basis、分解配置 |
| 搜索预算 | MCTS、ILP、SAT 与 beam search 的质量—时间曲线不同 | wall time、CPU/GPU 时间、simulation/node budget、timeout、seed |
| 正确性 | 资源更小但语义错误不是改进 | 符号验证、全输入态/算子验证、辅助位回零、相位检查 |

## 3. MCTS 与学习引导量子编译

| 文献（状态） | 原问题、学习/搜索机制与主要指标 | 可借鉴/可消融的维度 | 不可比边界 | 竞赛文档可用的谨慎表述 |
|---|---|---|---|---|
| `wang2023nestedmcts` Wang et al., IEEE TQE 2023；DOI/arXiv 已核验；**S** | Nested MCTS + combinatorial bandit 自动设计多类量子线路/ansatz，覆盖化学基态、图优化、线性方程和纠错编码等任务。 | 树策略、探索预算、搜索空间扩展、同预算随机/启发式消融、质量—时间 Pareto。 | 目标多为 task performance/ansatz，不是 Boolean 真值表到精确 Oracle；不能直接比较门数或“成功率”。 | “MCTS 已用于通用量子线路设计；本项目的区别应落在可验证 Boolean Oracle 语义、代数动作空间与资源约束，而非‘首次使用 MCTS’。” |
| `weiden2023qseed` Weiden et al., QCE 2023；DOI/arXiv 已核验；**S** | QSeed 用学习模型为 bottom-up unitary synthesis 提供高质量 seed；作者报告在指定 modular-exponentiation 案例上保持低门数并加速综合。 | learned vs random vs heuristic seed、泛化到未见函数、综合时间、最终门资源。 | 输入是 unitary/子线路分块，不是 ANF 因子计划；其 64-qubit 案例的“3.7×”不能迁移为本项目预期。 | “学习先验的合理价值是减少达到同等质量所需搜索，而不是默认改善最终最优值；因此项目应同时报告固定预算质量和达到阈值的时间。” |
| `rietsch2024rlsynthesis` Rietsch et al., QCE 2024；DOI/arXiv 已核验；**S** | Gumbel AlphaZero 综合可精确实现的 Clifford+T unitaries，报告最高约 5 qubits、随机线路最长约 60 gates 的实验。 | policy/value + tree search、精确验证、训练外规模测试、成功覆盖率与时间。 | 一般 unitary 的状态表示、动作和等价判定与 Boolean Oracle 完全不同；qubit/gate 规模不能横向排名。 | “该工作证明 AlphaZero 类树搜索可用于精确离散门综合；本项目需用 Boolean 特定的 factor action 和真值表验证来证明自己的任务专门化贡献。” |
| `tsaras2024shortcircuit` Tsaras et al., arXiv 2024 v2；**预印本，S** | AlphaZero 式搜索从 truth table 生成经典 AIG；作者在其 8-input 测试设置中报告生成覆盖与相对 ABC 的 AIG size 结果。 | truth-table 泛化、结构生成、AlphaZero 训练/搜索协议、数据分割与函数级统计。 | 这是经典 AIG 综合，不输出量子 Oracle，不含可逆化、ancilla、T/CNOT 或量子正确性；截至核验只按 arXiv 预印本引用。 | “ShortCircuit 使‘AlphaZero + Boolean truth table’本身不构成新颖性；本项目必须把贡献限定为量子 Oracle 资源模型、可逆语义和硬件映射。” |
| `fuerrutter2024diffusion` Fürrutter et al., Nature Machine Intelligence 2024；DOI/arXiv 已核验；**S** | 条件扩散模型生成/编辑量子线路，展示纠缠生成与 unitary compilation，并可通过 conditioning 纳入设备限制。 | 学习生成的训练成本、采样有效率、条件约束、训练分布外泛化及生成后验证。 | 生成模型与项目的可证明等价符号搜索不同；论文任务和指标不能成为 Oracle 资源的直接 baseline。 | “生成式模型拓宽了 AI 量子编译路线，但竞赛主张应突出每个候选均经 Oracle 语义验证；视觉上合理或模型高概率不等于线路正确。” |
| `ruiz2025alphatensor` Ruiz et al., Nature Machine Intelligence 2025；DOI/arXiv 已核验；**P + S** | AlphaTensor-Quantum 把 CNOT+T 线路的 T-count 优化映射为对称张量分解并用深度 RL 搜索，可嵌入 domain gadgets。 | T-count 单目标、learned search 与 domain knowledge 的消融、ancilla gadget 权衡。 | 它从已有线路的非 Clifford 部分开始，解决 fault-tolerant T 优化；项目目前没有等价 signature-tensor 后端，综合前端总分也不同。 | “AlphaTensor-Quantum 是强 T-count 后优化参照；只有把同一 Oracle 分解为其接受的同一门集并保持等价，才可进行端到端或阶段级比较。” |
| `riu2025rlzx` Riu et al., Quantum 2025；DOI/arXiv 已核验；**P + S** | PPO + GNN 在 ZX diagram 上选择保持等价的图重写，优化提取线路的门资源，并展示从小线路训练到较大线路的泛化。 | learned/heuristic rewrite 消融、2Q 门数、深度、运行时间、训练外规模与等价性。 | 输入已经是量子线路；ZX 重写可作为项目输出的后处理，却不是 Boolean-to-Oracle 前端的替代品。 | “RL-ZX 说明学习策略可控制等价重写序列；若接入项目，应单独报告前端收益、ZX 后处理收益及二者交互，不能把全部收益归因给 NMCTS。” |
| `zen2025rlft` Zen et al., Physical Review X 2025；DOI/arXiv 已核验；**S + H（任务边界）** | 用强化学习发现受连通性和门集约束的容错逻辑态制备线路，并报告门数/ancilla 改善。 | learned policy 在固定硬件约束下的搜索、连通性迁移、质量—时间与 ancilla 消融。 | 目标是 fault-tolerant state preparation，不是 Boolean bit-flip Oracle；不能把其硬件适配收益作为本项目 learned prior 的证据。 | “硬件约束可在学习搜索阶段直接进入动作/奖励；本项目当前 learned scorer 仍只参与逻辑候选排序，硬件收益来自后续确定性映射。” |

### AI 贡献必须做的因果拆分

| 组别 | 必须相同 | 能回答的问题 |
|---|---|---|
| `heuristic_only` vs `heuristic_plus_random` vs `heuristic_plus_learned` | 同一候选集合、PUCT/rollout 代码、simulation budget、函数、seed 和 timeout | 学习先验是否优于已有启发式及容量相当的随机控制 |
| `uniform` vs learned | 除 prior 外相同 | 搜索树先验是否真正提供信息，而非实现差异 |
| 完整 portfolio vs 最佳非学习组件 | 同一总预算和选择规则 | 系统整体是否改进；该差值不能自动归因于神经网络 |
| 训练/验证/测试 truth-table SHA256 隔离 | 生成器、同构去重与函数族分层 | 是否存在函数泄漏、重复真值表或只记忆小函数 |

## 4. Topology-aware mapping、routing 与 NISQ hardware-aware compilation

| 文献（状态） | 原问题与主要指标 | 与本项目可比的维度 | 不可比边界 | 竞赛文档可用的谨慎表述 |
|---|---|---|---|---|
| `li2019sabre` Li, Ding & Xie, ASPLOS 2019；DOI/arXiv 已核验；**H（强）** | SABRE 用启发式双向搜索处理初始布局与 SWAP 路由，在连通受限设备上优化新增门与深度。 | 冻结同一 basis-decomposed 逻辑线路后，对同一 coupling map、routing seed 和优化级别比较 2Q 门、2Q 深度、总深度、时间。 | SABRE 不是 Boolean 综合器；若前端线路不同，只能比较端到端系统，不能说路由算法本身更好。Qiskit 版本变化也会改变结果。 | “SABRE 是必须保留的路由基线。项目需要同时给 basis-only 参考与 mapped 结果，避免把门基分解成本误叫 routing overhead。” |
| `murali2019noiseadaptive` Murali et al., ASPLOS 2019；DOI/arXiv 已核验；**H** | 用设备校准和噪声信息选择映射，目标包括可靠性/成功率，并以真实 NISQ 设备实验支持。 | 只有取得带时间戳的真实 calibration/noise model 后，才能比较估计成功率、测量输出或硬件保真相关指标。 | 当前 line/grid/heavy-hex 是无校准 synthetic proxy；门数较少不等于真实硬件成功率较高。 | “现阶段工作是 topology-aware 而非 calibration-aware。若没有真实或可追溯噪声快照，只能报告结构成本，不使用‘硬件保真度提升’。” |
| `cowtan2019routing` Cowtan et al., TQC 2019；DOI/arXiv/Dagstuhl 已核验；**H** | 形式化 qubit routing，并围绕架构图、SWAP/桥接等策略分析及实现。 | 同一交互 DAG 和 coupling graph 下的额外 2Q 门、深度、可行性、运行时间；适合解释路由的图问题本质。 | 路由定义和允许原语必须一致；方向、bridge、动态重排或门交换规则不同会改变最优值。 | “路由指标需由明确的允许操作定义。项目应保存每条原生 2Q 门所用边和方向违规检查，而非只展示电路图。” |
| `nannicini2022ilp` Nannicini et al., ACM TQC，online 2022；DOI/arXiv 已核验；**H（强，小规模最优参照）** | 用 BIP 联合优化分配与路由，可编码误差、深度、crosstalk；论文在小规模实例求全局最优并与 SABRE/硬件执行比较。 | 小线路同一拓扑上的最优或有界 routing cost；可作为启发式映射的 optimality-gap 标尺。 | 方法规模呈指数困难；论文的 IBM 校准/硬件输出不能由当前 synthetic 数据复刻。不同 SWAP 合并规则也影响 CNOT 数。 | “ILP/BIP 适合在小规模给路由下界或最优证书，而不是替代所有规模的启发式。项目可在可承受子集报告 gap，超时必须保留。” |
| `hartnett2024learningtorank` Hartnett et al., Quantum 2024；DOI/arXiv 已核验；**H + S** | 学习排序多个等价候选线路，以选择真实硬件上表现更好的编译结果。 | 同一候选池、训练/测试设备隔离、排序质量、选择后实测表现和编译开销。 | 必须有真实执行标签或经验证的校准数据；synthetic topology 的门数标签不能称为 hardware-optimized performance。 | “学习模型可用于在等价候选中做硬件排序，但本项目当前神经策略只控制逻辑搜索。若以后增加硬件 ranker，应作为独立模块和独立消融。” |
| `li2025hopps` Li et al., arXiv 2025；**预印本，P + H** | HOPPS 对受拓扑约束的 \(\{\mathrm{CNOT},R_z\}\) phase-polynomial block 做 SAT 最优/分块优化，目标为 CNOT 数或深度。 | 同一 phase-polynomial block、同一 coupling graph 下的 CNOT 数/深度、最优性与运行时间。 | 本项目没有 \(R_z\)/phase-polynomial 综合后端，且主任务是 bit-flip Boolean Oracle；只能作为硬件感知综合边界，不进入 primary20 胜负表。 | “硬件感知可前置到 phase-polynomial 综合，但其任务和门集与本文不同；当前系统只在 bit-flip 前端之后执行 Target/SABRE 映射。” |

## 5. 强对比应如何进入最终竞赛文档

| 层级 | 核心直接基线 | 同表主指标 | 应单列而不能混入的指标 |
|---|---|---|---|
| Boolean 到逻辑 Oracle | Direct-ANF/ESOP、PPRM factor、SSHR-H；SSHR-I（取得 Gurobi 环境后）、本地 SSHR-Beam（须标为非论文扩展）、可执行的 XAG/ROS 类流程 | 正确率、T、CNOT、深度、峰值 ancilla、运行时间、coverage | 真实硬件 fidelity、QEC logical steps（除非已实现对应后端） |
| AI 搜索贡献 | heuristic、uniform、random-prior、learned-prior；同预算 MCTS | 固定预算资源差、达到目标时间、win/tie/loss、函数级 CI/效应量 | 不同任务论文中的单个 speedup 百分比 |
| 固定线路映射 | SABRE、项目 topology-aware mapper；小规模 ILP 最优参照 | native 2Q gates、2Q depth、routing delta、compile time、违规数 | 逻辑前端的 T/MCT 改进 |
| 校准/真机层 | noise-adaptive 或 learned ranking（仅在取得数据后） | calibration timestamp、shots、HOP/成功率/输出距离及置信区间 | 仅凭 synthetic coupling map 推断的“真实保真度” |

最终“显著优于”只应在以下条件同时满足时出现：严格配对；所有线路通过语义与映射验证；推断单位为独立 Boolean 函数而不是重复 seed；预先冻结超时和失败规则；Holm 校正后 \(p<0.05\)；95% 置信区间不跨 0；效应方向与指标范围写清。否则使用“在本地匹配实验的某指标上观察到降低/提高”，并保留失败、超时和负结果。

## 6. 核验结论与尚未补齐的证据

- 本矩阵共 23 篇：9 篇 Boolean/Oracle/可逆综合，8 篇 MCTS/RL/学习引导，6 篇 mapping/routing/hardware-aware；覆盖 2006--2025，其中 2022--2025 有 15 篇。
- 21 篇有正式期刊或会议出版 DOI；`tsaras2024shortcircuit` 与 `li2025hopps` 仅以 arXiv 预印本身份使用，其 DataCite arXiv DOI 不代表同行评审出版。
- DOI、arXiv、作者与年份均至少由 DOI 落地页、出版社/期刊页、会议页、arXiv 或作者机构论文页之一核验；细节见 manifest。
- 学术 MCP 未挂载，OpenAlex fallback 在本机出现 TLS ASN.1 错误；本轮改用 Crossref DOI API 与 arXiv Atom T1 元数据完成核对，最终审计为 23/23 verified、0 suspicious、0 mismatch、0 not-found。系统性撤稿/勘误检查仍未由 Crossmark API 全覆盖。
- 本文件不证明项目已超过任一论文。它提供的是对比对象、可比维度、边界和最小公平协议。
