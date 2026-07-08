# Resource-NMCTS 中文交付文档

更新时间：2026-07-09
当前代码版本：以 `origin/main` 最新提交为准
代码位置：`/Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment`

## 1. 项目定位

本项目面向量子布尔函数 oracle 综合，目标是在逻辑层降低 T-count、CNOT、深度和辅助比特等资源。当前方法不依赖 SSHR 的 parallelotope 结构，而是把布尔 oracle 综合建模为 ANF/FPRM 项集合上的搜索问题：

- 用资源加权目标函数评价候选线路：
  `score = T + 0.04*CNOT + 0.015*depth + 0.01*gates + 2*ancilla`。
- 用神经先验、MCTS、FPRM 极性搜索、线性因子分解和 Pareto archive 生成候选。
- 用 direct ANF、AND-direct ANF、ESOP、ABC、BDD、SSHR-H/SSHR-I、mockturtle、CirKit、RevKit API 和 legacy RevKit CLI 等作为外部或内部 baseline。
- 所有结果均是逻辑层资源估计，不包含硬件映射和连通性约束。

论文主张应限定为：资源约束、低 T-count、低加权 score 的量子布尔函数 oracle 综合方法。不能写成 CNOT-only 最优，也不能写成硬件映射优势。

### 1.1 对比对象与论文意义

当前方法的对比对象分三层，而不是只和 SSHR 比：

1. 传统 oracle 综合和布尔表示 baseline：direct ANF、AND-direct ANF、ESOP/ESOP-MILP、BDD、ABC-AIG/XAG/LUT/ESOP、XAG、ROS-style LUT。这一层证明方法不是只优化某个 SSHR 实现，而是在布尔函数表示和 oracle 资源层面降低 T-count、CNOT、深度、gate 和辅助比特等逻辑资源。
2. 可复现外部工具链 baseline：mockturtle official-header KLUT-to-XAG、CirKit 3 AIG/multiplicative-complexity probe、RevKit API 和 legacy RevKit CLI exact-oracle reversible-synthesis probe。这一层用于回应审稿人对“是否只和自写 baseline 比”的质疑，但必须保留边界：它们是逻辑层 probe 或复现，不能写成 full ROS/hardware mapping。
3. 搜索策略 baseline：greedy、direct、beam、fixed-coordinate MCTS、neural-prior ablation、Pareto archive、depth-frontier/stage-gated frontier、rank-diverse pruning 等。这一层证明创新点来自资源感知搜索和学习引导，而不是单纯换了一个 cost function。

因此论文意义应写成“面向资源约束量子布尔函数 oracle 综合的逻辑层 AI 搜索框架”，SSHR-H/SSHR-I 是小规模、CNOT-oriented 的重要结构化 baseline，但不是本文方法的定义边界。

本轮已把这层定位固化为两张可复现矩阵：先用 claim matrix 说明每类 baseline 的论证角色和不能支持的过度主张，再用 evidence matrix 汇总覆盖范围、verified rows 和 paired score 结果。

- `analyze_baseline_claim_matrix.py`
- `results/summary_baseline_claim_matrix.csv`
- `results/analysis_baseline_claim_matrix.md`
- `paper_latex/tables/baseline_claim_matrix.tex`

- `analyze_comparison_evidence_matrix.py`
- `results/summary_comparison_evidence_matrix.csv`
- `results/analysis_comparison_evidence_matrix.md`
- `paper_latex/tables/comparison_evidence_matrix.tex`

这两张矩阵已接入英文投稿稿 `resource_nmcts_submission_v1.tex`，用于直接回答“和什么比、为什么有意义、不能夸大到哪里”。

本轮进一步补充了 paired statistical evidence 层，避免论文只依赖均值叙述：

- `analyze_paired_statistical_evidence.py`
- `results/summary_paired_statistical_evidence.csv`
- `results/analysis_paired_statistical_evidence.md`
- `paper_latex/tables/paired_statistical_evidence.tex`

该分析直接从 correct、non-skipped 的 raw CSV 行按 item name 重算核心 score 对比，给出胜/负/平、平均相对变化、中位相对变化和 two-sided exact sign test。核心现象是：传统、外部工具链和高维 root-beam/fast-pair 对比的中位数变化也为负，说明主要优势不是少数 outlier 拉动；但 `n=16`、`n=18` 高维内部 guard 的幅度明显小于外部工具链 probe，应写成稳定小幅增益而不是大幅碾压。

本轮还补充了 raw multi-resource dominance 层，避免把 weighted score 优势误写成所有资源维度的全面支配：

- `analyze_multimetric_pareto_tradeoff.py`
- `results/summary_multimetric_pairwise_dominance.csv`
- `results/summary_multimetric_nondominated.csv`
- `results/analysis_multimetric_pareto_tradeoff.md`
- `paper_latex/tables/multimetric_pairwise_dominance.tex`
- `paper_latex/tables/multimetric_nondominated.tex`

该分析只用 T-count、CNOT、depth、peak ancilla 判断 Pareto 支配，不把 weighted score 放进支配谓词。核心结果是：Pareto-Resource-NMCTS 在 12-method `n<=6` 方法池中 170/177 个函数非支配；它对 ESOP beam 是 165/0/9/3（目标支配/基线支配/不可比/相同），对 ESOP-MILP 是 123/2/45/7。但对 SSHR-H、SSHR-I CNOT、mockturtle、CirKit、RevKit CLI 多数行是不可比，这反而更适合投稿：说明本文的优势是 T-count 和 weighted-score 方向的资源搜索优势，同时承认 SSHR 的 CNOT、CirKit 的 depth、RevKit 的 line-count 等真实 trade-off。

本轮新增 Boolean-ring structural evidence 层，把此前分散的高维结构搜索结果整理成一张可投稿表：

- `analyze_boolean_ring_structural_evidence.py`
- `results/summary_boolean_ring_structural_evidence.csv`
- `results/analysis_boolean_ring_structural_evidence.md`
- `paper_latex/tables/boolean_ring_structural_evidence.tex`

该表把 Boolean-ring/Boolean-screen 分成三类证据，而不是简单说“AI 更强”：质量型 guard 在 `n=14` 为 9/0/3、score -0.82%，在 `n=16` 为 14/0/10、score -0.34%；`n=16` boolean-linear deep 仍有 14/6/4、score -0.22%，同时 planning time -72.31%；`n=20` screen gate 与 full Resource 资源完全持平 0/0/6，但 time -75.58%；`n=20` recursive Boolean screen 相对 old Resource 为 5/0/1、score -7.47%，但 ancilla +13.06%。同时保留 `n=18` speed-only negative control：score +36.94%、time -97.90%，说明简单 screen 不能被宣传成普遍质量提升。

本轮进一步新增 sparse depth-frontier audit，把高维 frontier 从“depth-2/3/4 全部评估”压缩为“只评估 depth-2 和 depth-4”：

- `analyze_sparse_depth_frontier.py`
- `results/summary_sparse_depth_frontier.csv`
- `results/analysis_sparse_depth_frontier.md`
- `paper_latex/tables/sparse_depth_frontier.tex`

核心结果是：在 `scale-frontier` 72 对、`scale-generalization` 96 对、`n=23/24/25` truth-bridge 各 6 对上，sparse depth-2/4 frontier 相对完整 depth-2/3/4 frontier 分别为 0/0/72、0/0/96、0/0/6、0/0/6、0/0/6，score/T/CNOT/depth/ancilla 完全持平，同时平均 time 分别下降 27.57%、28.17%、24.94%、28.88%、27.06%。该结果比现有 stage-gated frontier 更干净：它不牺牲 score，不需要阈值，直接删除当前审计切片中没有最终入选的 depth-3 评估。但论文中仍应写成“当前生成切片上的经验 controller”，不能写成 depth-3 在所有函数上理论上被 depth-4 支配。

本轮新增 learned-control audit 层，用于校准题目中“neural/MCTS”的贡献强度：

- `analyze_learned_control_audit.py`
- `results/summary_learned_control_audit.csv`
- `results/analysis_learned_control_audit.md`
- `paper_latex/tables/learned_control_audit.tex`
- `paper_latex/figures/submission_v36/fig7_learned_control_summary.pdf`
- `paper_latex/figures/submission_v36/source_data/fig7_learned_control_summary.csv`

该表把 AI/学习控制组件分成两类：可作为论文证据的 depth-frontier policy、stage-gated frontier、sparse depth-4 gate、rank-diverse phase shortlist；以及只能作为限制或未来工作的 boolean neural guard、root-action neural ranker。关键数值：frontier policy 在 held-out `n=28,40` 上相对 oracle frontier 为 0/3/45、+0.04% score，但减少 51.30% all-depth frontier evaluation time；stage-gated frontier 在独立 `n=24,28,32,40` 上相对 all-depth 为 0/4/92、+0.04% score，减少 25.43% staged planning time；sparse depth-4 gate 在三组独立 seed 的 `n=24,28,32,40` 共 144 个 pair 上相对 deterministic sparse frontier 为 0/0/144、0 false skip，并减少 13.43% sparse-frontier evaluation time，阈值扫描显示 zero-false-skip plateau 可到 -14.92% time，允许 1 个 false skip 时为 -15.49% time 且 score gap 仅 +0.01%；rank-diverse phase shortlist 在 held-out `n=6` 上用 512/8192 exact forms/function 贴近 wide-128。另一方面，boolean neural guard 只有 -0.12% score 但 +94.49% runtime，root-action neural ranker质量未超过 beam4，因此不能作为主贡献夸大。

新增 summary figure 将上述边界可视化：promoted controls 同时满足 score 不显著变差/有改善与搜索开销下降，limited diagnostics 则落在“质量弱或运行时间反向”的区域，用于防止把所有 AI 组件都写成主贡献。

本轮继续补充 high-dimensional scaling/resource audit 层，避免“大规模结果”只以验证总数出现：

- `analyze_scaling_resource_audit.py`
- `results/summary_scaling_resource_audit.csv`
- `results/analysis_scaling_resource_audit.md`
- `paper_latex/tables/scaling_resource_audit.tex`

该审计把函数/设置数、方法行数、验证行数和代表性资源均值分开。核心覆盖为：`n=24,28,32,40` large term-set frontier 96 个函数、960/960 symbolic rows；stage-gated frontier 96/96 symbolic rows；`n=20,28,40` action-width probe 216 个 width/function settings、1512/1512 symbolic rows；`n=21--25` complete truth-table bridge 40 个 function/settings、400/400 truth+symbolic rows。对应代表性资源均值约为 score 1090--1130、T 985--1023、CNOT/depth 1593--1648、peak ancilla 5.2--5.3。论文中应把这写成“高维逻辑层验证与资源审计”，不是硬件映射，也不是全体 `n=26--40` 的完整真值表枚举。

本轮还补充 compute/reproducibility audit 层，用于回应“大规模实验是否可复现、是否利用多核/GPU环境”的问题：

- `analyze_reproducibility_audit.py`
- `results/summary_reproducibility_audit.csv`
- `results/analysis_reproducibility_audit.md`
- `results/manifest_reproducibility_audit.json`
- `paper_latex/tables/reproducibility_audit.tex`

该审计记录当前工作站为 Apple M4 Pro，14 CPU cores，24.0 GiB RAM，20-core Metal GPU；`mcts-qoracle` 环境中 Python 3.11.15、PyTorch 2.12.0、MPS=True、CUDA=False。manifest 层面有 54 个运行记录包含 worker count，最大 workers=10；代表性流程包括 traditional resource 10 workers/1770 rows、RevKit CLI 8 workers/708 rows、ROS-style LUT 8 workers/927 rows、CirKit 8 workers/177 rows、mockturtle 4 workers/177 rows。论文中应把 runtime/time 结果限定在这个工作站上下文；可移植主张仍是逻辑资源数量和验证通过率。

## 2. 当前已完成内容

### 2.0a mockturtle official-header XAG probe

本轮已把 mockturtle 从“源码可达但未适配”推进为“可编译、可运行、可产出统计的外部 probe”。当前流程不是官方 ROS：它先用 ABC 把导出 BLIF 映射为 `K=4` LUT 网络，再用官方 mockturtle `blif_reader` 读入 KLUT，并调用 `xag_npn_resynthesis` 生成 XAG 统计，最后把 XAG AND/XOR/depth 转换为本文的逻辑层 oracle resource proxy。

主要产物：

- `tools/mockturtle_blif_xag_stats.cpp`
- `run_mockturtle_xag_probe.py`
- `results/raw_mockturtle_xag_probe.csv`
- `results/summary_mockturtle_xag_probe.csv`
- `results/analysis_mockturtle_xag_probe.md`
- `results/manifest_mockturtle_xag_probe.json`
- `results/raw_mockturtle_xag_highdim_probe.csv`
- `results/summary_mockturtle_xag_highdim_probe.csv`
- `results/analysis_mockturtle_xag_highdim_probe.md`
- `results/manifest_mockturtle_xag_highdim_probe.json`
- `paper_latex/tables/mockturtle_xag_probe.tex`
- `paper_latex/tables/mockturtle_xag_highdim_probe.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v28.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v28.pdf`

核心结果：

| 对比 | 函数数 | 胜/负/平 | 平均 score 变化 |
|---|---:|---:|---:|
| Resource-NMCTS vs mockturtle XAG K4 | 177 | 165/12/0 | -28.97% |
| Pareto-Resource-NMCTS vs mockturtle XAG K4 | 177 | 166/11/0 | -31.50% |
| FPRM polarity archive vs mockturtle XAG K4 | 177 | 156/21/0 | -25.11% |
| Resource-NMCTS vs mockturtle XAG K4, `n=14` | 64 | 64/0/0 | -91.41% |
| Profile-Resource-NMCTS vs mockturtle XAG K4, `n=14` | 64 | 64/0/0 | -91.41% |
| Pareto-Resource-NMCTS vs mockturtle XAG K4, `n=14` | 64 | 64/0/0 | -91.49% |

解释边界：

- 传统函数 probe 177/177 行 correct，高维 `n=14` probe 64/64 行 correct，均无 error 或 timeout。
- 本结果调用了官方 mockturtle 头文件库和 `xag_npn_resynthesis`，比单纯 ABC-LUT proxy 更接近 mockturtle 生态。
- 这仍不是官方 ROS，不包含 SAT garbage management，不输出可逆线路或 Clifford+T gate sequence，也不包含硬件 mapping。
- 论文中应写成“official-header mockturtle KLUT-to-XAG resynthesis probe”，不能写成“复现完整 ROS”。

### 2.0a2 CirKit 3 shell AIG/MC probe

本轮把 CirKit 从“源码和 shell 可以构建”推进为“可复现、可验证、可计入论文外部 baseline 的 AIG/multiplicative-complexity probe”。流程如下：ABC 先把导出的 BLIF benchmark 转成 AIGER；CirKit 3 shell 读取 AIG，执行 `cut_rewrite -a; resub -a`，用 `mccost -a` 报告 AIG multiplicative complexity；随后 CirKit 输出 Verilog，ABC 再读回 Verilog 并写 BLIF，最终用现有 bit-parallel truth-table verifier 做逐行正确性验证。

主要产物：

- `run_cirkit_aig_probe.py`
- `results/raw_cirkit_aig_probe.csv`
- `results/summary_cirkit_aig_probe.csv`
- `results/analysis_cirkit_aig_probe.md`
- `results/manifest_cirkit_aig_probe.json`
- `results/raw_cirkit_aig_highdim_probe.csv`
- `results/summary_cirkit_aig_highdim_probe.csv`
- `results/analysis_cirkit_aig_highdim_probe.md`
- `results/manifest_cirkit_aig_highdim_probe.json`
- `paper_latex/tables/cirkit_aig_probe.tex`
- `paper_latex/tables/cirkit_aig_highdim_probe.tex`
- `results/analysis_toolchain_readiness.md`
- `results/toolchain_readiness.json`

核心结果：

| 对比 | 函数数 | score 胜/负/平 | 平均 score 变化 | T 胜/负/平 | CNOT 胜/负/平 | depth 胜/负/平 |
|---|---:|---:|---:|---:|---:|---:|
| Resource-NMCTS vs CirKit AIG/MC | 177 | 177/0/0 | -60.84% | 177/0/0 | 162/14/1 | 16/156/5 |
| Pareto-Resource-NMCTS vs CirKit AIG/MC | 177 | 177/0/0 | -62.34% | 177/0/0 | 167/9/1 | 16/156/5 |
| FPRM polarity archive vs CirKit AIG/MC | 177 | 177/0/0 | -58.96% | 176/0/1 | 163/13/1 | 11/165/1 |
| Pareto-Resource-NMCTS vs CirKit AIG/MC, `n=14` | 64 | 64/0/0 | -94.46% | 64/0/0 | 64/0/0 | 14/50/0 |
| Resource-NMCTS vs CirKit AIG/MC, `n=14` | 64 | 64/0/0 | -94.42% | 64/0/0 | 64/0/0 | 14/50/0 |

解释边界：

- 传统函数 probe 177/177 行 correct，高维 `n=14` probe 64/64 行 correct，均无 error 或 timeout。
- 这是真正调用官方 CirKit 3 shell 的外部工具实验，比仅仅说“CirKit 可构建”强很多。
- 资源数仍是逻辑层 AIG/MC proxy：`T=4*MC`，CNOT/depth/ancilla 用项目统一的 AND/XAG proxy 转换。
- 这个 probe 对 depth 很强，本文方法在 depth 上多数输给 CirKit，论文必须把它写成清晰 trade-off：本文主要赢 T-count、weighted score、CNOT 和 ancilla，而不是 depth-only。
- 这不是 legacy RevKit reversible synthesis，不是官方 ROS，也不输出 Clifford+T 可逆线路或硬件 mapping。

### 2.0a3 legacy RevKit CLI exact-oracle reversible-synthesis probe

本轮把 legacy RevKit/CirKit 命令行路径从“待复现”推进为“可构建、可运行、可产出 exact oracle permutation 可逆综合 baseline”。流程如下：每个布尔函数先嵌入为精确可逆 oracle 置换 `(x,y)->(x,y xor f(x))`；legacy RevKit CLI 用 `read_spec -p` 读入该 SPEC permutation，并分别运行 TBS、DBS、RMS 三个 reversible-synthesis flow；随后从 `ps -c` 读取 RevKit 的 T-count 和 logic-qubit 统计，并从 `gates` 的 Toffoli control distribution 派生 CNOT/depth proxy。

主要产物：

- `run_revkit_cli_probe.py`
- `results/raw_revkit_cli_tbs_traditional.csv`
- `results/summary_revkit_cli_tbs_traditional.csv`
- `results/analysis_revkit_cli_tbs_traditional.md`
- `results/manifest_revkit_cli_tbs_traditional.json`
- `results/raw_revkit_cli_multiflow_traditional.csv`
- `results/summary_revkit_cli_multiflow_traditional.csv`
- `results/analysis_revkit_cli_multiflow_traditional.md`
- `results/manifest_revkit_cli_multiflow_traditional.json`
- `paper_latex/tables/revkit_cli_tbs_traditional.tex`
- `paper_latex/tables/revkit_cli_multiflow_traditional.tex`
- `tmp/cirkit_legacy/build/programs/revkit`（构建产物，已在 `.gitignore` 中排除）

核心结果：

| 对比 | 函数数 | score 胜/负/平 | 平均 score 变化 | T 胜/负/平 | CNOT 胜/负/平 | depth 胜/负/平 | peak ancilla 胜/负/平 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Resource-NMCTS vs RevKit CLI best-score | 177 | 173/0/4 | -66.32% | 173/0/4 | 102/70/5 | 88/82/7 | 0/169/8 |
| Pareto-Resource-NMCTS vs RevKit CLI best-score | 177 | 173/0/4 | -67.28% | 173/0/4 | 107/63/7 | 90/79/8 | 0/169/8 |
| FPRM polarity archive vs RevKit CLI best-score | 177 | 173/0/4 | -64.24% | 173/0/4 | 91/78/8 | 76/94/7 | 0/171/6 |

解释边界：

- 三个直接 CLI flow 合计 531/531 行 usable，0 error，0 timeout；best-score portfolio 额外生成 177 行。
- 这是真实调用 legacy RevKit CLI 的 exact reversible oracle specification 实验，比 RevKit Python `oracle_synth` 的 phase-netlist boundary 更接近 bit-flip reversible synthesis。
- RevKit CLI 的 `T` 来自 `ps -c` 的 Maslov-style T-count；CNOT/depth 是从 Toffoli control distribution 和项目 MCT cost table 派生，因此仍是逻辑层 proxy。
- RevKit CLI portfolio 在辅助线数量上明显更强；本文方法的优势主要是 T-count 和 weighted score，CNOT/depth 仅为小幅或混合优势，不能写成全面支配。
- 该结果不是官方 ROS，不包含 SAT garbage management、硬件 mapping、routing 或 magic-state factory 调度。

### 2.0b phase-parity ANF emitter

本轮把 phase/Rz 方向从“只对 RevKit 的非 Clifford `Rz` 做成本敏感性分析”推进为“项目内部已有一个可验证的 phase-oracle emitter baseline”。新增 `run_phase_parity_baseline.py`，对每个非空 ANF 单项式使用 parity-phase 恒等式展开，合并相同 parity mask 的旋转角，并用 `Fraction` 精确验证每个函数的 phase oracle 语义（允许全局相位）。

主要产物：

- `run_phase_parity_baseline.py`
- `results/raw_phase_parity_anf.csv`
- `results/summary_phase_parity_anf.csv`
- `results/analysis_phase_parity_anf.md`
- `results/manifest_phase_parity_anf.json`
- `paper_latex/tables/phase_parity_anf.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v30.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v30.pdf`

核心结果：

| 项目 | 口径 | 结果 | 平均变化或均值 |
|---|---|---|---|
| phase-parity ANF 验证 | 177 functions | 177/177 verified | up to global phase |
| phase-parity ANF vs RevKit | lower-bound score | 40/137/0 | +69.25% |
| phase-parity ANF vs RevKit | score+1/Rz | 177/0/0 | -48.16% |
| phase-parity ANF vs RevKit | score+1.5/Rz | 177/0/0 | -53.26% |
| phase-parity ANF vs RevKit | Ross-Selinger-style `T/Rz=30` proxy | 177/0/0 | -64.98% |
| phase-parity ANF vs RevKit | non-Clifford Rz | 171/0/6 | -63.33% |
| phase-parity ANF vs RevKit | total Rz | 173/3/1 | -45.10% |
| phase-parity ANF 资源均值 | 177 | - | score 10.11 / CNOT 87.40 / depth 114.96 / total Rz 27.56 / non-Clifford Rz 21.75 |

解释边界：

- 这是 phase oracle emitter，不是现有 bit-flip Resource-NMCTS emitter 的替代品；两者语义口径不同。
- 常数项作为全局相位处理，因此正确性口径是 phase oracle up to global phase。
- lower-bound score 下 naive parity expansion 仍弱于 RevKit，说明“朴素 phase 展开”不足以作为最终投稿方法。
- 一旦给非 Clifford `Rz` 加入非常保守之前的 1/Rz 符号成本，phase-parity ANF 转为 177/0/0；这说明 RevKit lower-bound 优势高度依赖未计入旋转综合成本。
- 下一步明显提升目标应是 learned/optimized phase/Rz-aware search 和实际 rotation sequence 审计，而不是继续只做 `T/Rz` 常数 proxy。

### 2.0c fixed-polarity phase-parity search

本轮把 phase/Rz 方向从“单一 ANF emitter”推进为“有搜索变量的 phase-oracle emitter”。新增 `run_phase_parity_fprm_search.py`：对每个传统函数枚举全部 fixed-polarity Reed-Muller 极性 `p`，先综合 `g(z)=f(z xor p)` 的 phase polynomial，再把 shifted parity mask 翻译回原变量。如果极性与 parity mask 的交叠为奇数，旋转角取反并把原角度并入全局相位；验证时检查所有输入上的相位差是否为同一个有理数，而不是只检查整数常数项。

主要产物：

- `run_phase_parity_fprm_search.py`
- `results/raw_phase_parity_fprm.csv`
- `results/summary_phase_parity_fprm.csv`
- `results/analysis_phase_parity_fprm.md`
- `results/manifest_phase_parity_fprm.json`
- `paper_latex/tables/phase_parity_fprm.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v32.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v32.pdf`

核心结果：

| 项目 | 口径 | 结果 | 平均变化或均值 |
|---|---|---:|---:|
| FPRM phase search 验证 | 3 rank metrics × 177 functions | 531/531 verified | up to global phase |
| FPRM-score vs phase-parity ANF | lower-bound score | 59/0/118 | -3.98% |
| FPRM-Rz1 vs phase-parity ANF | score+1/Rz | 59/0/118 | -1.65% |
| FPRM-`T/Rz=30` vs phase-parity ANF | synthesis proxy | 59/0/118 | -0.47% |
| FPRM-`T/Rz=30` vs RevKit | synthesis proxy | 177/0/0 | -65.16% |
| FPRM non-Clifford Rz vs RevKit | count | 171/0/6 | -63.48% |
| FPRM CNOT vs RevKit | count | 34/140/3 | +34.18% |
| FPRM-`T/Rz=30` 资源均值 | 177 | - | score 9.57 / CNOT 87.22 / depth 114.42 / total Rz 27.20 / non-Clifford Rz 21.60 |

解释边界：

- 这是真正的 phase/Rz 搜索增量：极性会改变 ANF 单项式集合、parity mask 合并结果和全局相位，而不是只改变计分口径。
- 结果是正向但幅度小。相对 phase-parity ANF，`T/Rz=30` 目标虽然 59/0/118 不退化，但平均只降低 0.47%。这不足以作为最终论文的主要创新结果。
- 该结果应写成“phase/Rz-aware search 的第一个可验证极性维度”，并把下一步目标设为 learned/optimized phase search，例如选择极性、线性变量变换、parity gadget 合并和旋转谱代价的联合搜索。

### 2.0d Affine-FPRM phase-parity search

本轮把 phase/Rz 搜索从“只枚举 FPRM 输入极性”推进为“有界可逆线性预条件 + FPRM 极性”的联合代数搜索。新增 `run_phase_parity_affine_search.py`：对每个候选可逆 GF(2) 线性变换 `B`，先构造 `h(y)=f(B^{-1}y)`，再枚举极性 `p` 得到 `g(z)=h(z xor p)` 的 phase polynomial；选中的 parity mask 通过 `m_x=B^T m_z` 翻译回原变量，如果 `m_z dot p=1` 则旋转角取反并把原角度并入全局相位。该变换不作为硬件 mapping 或 CNOT wrap 计入，而是逻辑层 phase-polynomial 代数重写。

主要产物：

- `run_phase_parity_affine_search.py`
- `results/raw_phase_parity_affine.csv`
- `results/summary_phase_parity_affine.csv`
- `results/analysis_phase_parity_affine.md`
- `results/manifest_phase_parity_affine.json`
- `paper_latex/tables/phase_parity_affine.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v35.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v35.pdf`

核心结果：

| 项目 | 口径 | 结果 | 平均变化或均值 |
|---|---|---:|---:|
| Affine-FPRM phase search 验证 | 3 rank metrics × 177 functions | 531/531 verified | up to global phase |
| Affine-FPRM-`T/Rz=30` vs fixed-polarity FPRM | synthesis proxy | 81/0/96 | -2.51% |
| Affine-FPRM-`T/Rz=30` vs phase-parity ANF | synthesis proxy | 85/0/92 | -2.98% |
| Affine-FPRM-`T/Rz=30` vs RevKit | synthesis proxy | 177/0/0 | -65.50% |
| Affine-FPRM-score vs fixed-polarity FPRM | lower-bound score | 80/0/97 | -5.77% |
| Affine-FPRM non-Clifford Rz vs fixed-polarity FPRM | count | 20/0/157 | -0.73% |
| Affine-FPRM-`T/Rz=30` 资源均值 | 177 | - | score 8.92 / CNOT 85.32 / depth 111.46 / total Rz 26.14 / non-Clifford Rz 21.45 |

解释边界：

- identity transform 被纳入搜索，因此在同一 rank metric 下 Affine-FPRM 相对 fixed-polarity FPRM 不退化。
- `T/Rz=30` 目标有 81/177 个函数选择非 identity 线性变换，说明收益来自 parity gadget 合并结构改变，而不是单纯 tie-breaking。
- 该结果比 fixed-polarity phase search 明显强，但仍是逻辑层 phase-oracle emitter：没有输出近似旋转序列，没有进行硬件 mapping，也没有声明 phase/Rz 全局最优。
- 论文中应把它写成当前 phase/Rz 分支最强证据：phase 搜索空间已经从 polarity 扩展到 affine algebraic preconditioning，下一步才是 learned/optimized phase policy 和 rotation-sequence audit。

### 2.0e n=24 完整 truth-table bridge

本轮把高维完整验证边界从 `n=23` 推进到 `n=24`。新增结果复用 `run_truth_bridge_terms.py`，并依赖当前 `anf_utils.truth_table_from_anf` 的位掩码 truth-table evaluator：对每个变量预先构造赋值位集，单项式用大整数 AND 计算，完整 ANF 用 XOR 合并。该实现已与原 zeta 实现做小规模随机等价测试；在 `n=24` bridge 首样本上，truth-table 构造从中断前 10 min 未完成降到约 0.10 s。

主要产物：

- `results/raw_truth_bridge_n24_terms.csv`
- `results/summary_truth_bridge_n24_terms.csv`
- `results/analysis_truth_bridge_n24_terms.md`
- `paper_latex/tables/truth_bridge_n24_terms.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v33.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v33.pdf`

核心结果：

| 项目 | 结果 |
|---|---:|
| n=24 生成式 ANF 函数 | 6 |
| 完整 truth-table oracle 验证 | 60/60 |
| ANF plan 验证 | 60/60 |
| emitted-circuit 符号验证 | 60/60，mismatch=0 |
| 平均 truth-table 构造时间 | 0.18 s/函数 |
| adaptive all-depth vs single screen | 6/0/0，score -9.42% |
| adaptive all-depth vs fixed depth-2 | 4/0/2，score -2.21% |
| depth-frontier policy vs fixed depth-2 | 3/0/3，score -2.05% |
| depth-frontier policy vs depth-4 | 0/1/5，score +0.16%，plan time -27.08% |

解释边界：

- 这是完整 oracle 验证边界的实质推进：按当前 v36 主图源数据口径，`n=21,22,23` 基础 bridge 与两组 `n=23` policy rerun 合计 280/280 方法行，现在加上 `n=24` 后为 340/340。
- 该结果提升的是验证 harness 和高维语义可信度，不改变 Resource-NMCTS 搜索算法本身。
- 该轮结束时仍不能写成 `n=25--40` 已完整枚举；当前状态见下一节 `n=25` bridge。

### 2.0f n=25 完整 truth-table bridge 与 action-width 消融

本轮在 `n=24` 的基础上继续推进完整 oracle 验证边界。`run_truth_bridge_terms.py` 直接扩展到 `n=25`，仍采用位掩码 truth-table evaluator；同时补充 action-width 6/12/24 的 screen-scale probe，用来判断“继续加宽候选集合”是否是高维收益来源。

主要产物：

- `results/raw_truth_bridge_n25_terms.csv`
- `results/summary_truth_bridge_n25_terms.csv`
- `results/analysis_truth_bridge_n25_terms.md`
- `paper_latex/tables/truth_bridge_n25_terms.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v34.tex`
- `results/raw_screen_scale_width6_probe_terms.csv`
- `results/raw_screen_scale_width12_probe_terms.csv`
- `results/raw_screen_scale_width24_probe_terms.csv`
- `results/analysis_screen_scale_width6_probe_terms.md`
- `results/analysis_screen_scale_width12_probe_terms.md`
- `results/analysis_screen_scale_width24_probe_terms.md`
- `paper_latex/tables/screen_scale_width6_probe_terms.tex`
- `paper_latex/tables/screen_scale_width12_probe_terms.tex`
- `paper_latex/tables/screen_scale_width24_probe_terms.tex`

核心结果：

| 项目 | 结果 |
|---|---:|
| n=25 生成式 ANF 函数 | 6 |
| 完整 truth-table oracle 验证 | 60/60 |
| ANF plan 验证 | 60/60 |
| emitted-circuit 符号验证 | 60/60，mismatch=0 |
| 平均 truth-table 构造时间 | 0.45 s/函数 |
| adaptive all-depth vs single screen | 6/0/0，score -7.31% |
| adaptive all-depth vs fixed depth-2 | 4/0/2，score -2.14% |
| depth-frontier policy vs fixed depth-2 | 4/0/2，score -2.14% |
| depth-frontier policy vs depth-4 | 0/0/6，score +0.00%，plan time -8.87% |
| depth-frontier policy vs adaptive all-depth | 0/0/6，score +0.00%，plan time -46.09% |
| width 6/12/24 probe 验证 | 每组 504/504 plan 与 emitted-circuit 符号验证通过 |
| width probe 结论 | 单纯加宽 root candidates 没有改善 fixed depth-2/adaptive 的 score 结论，时间成本显著上升 |

解释边界：

- 完整 bridge 从 `n=21,22,23,24` 的 340/340 扩展到 `n=21,22,23,24,25` 的 400/400 方法行。
- `n=25` 是验证边界和 frontier policy 证据的实质推进：frontier policy 在该切片上与 depth-4/all-depth score 持平，同时降低 plan time。
- width probe 是一个有用的负向消融：当前高维收益来自递归深度与 frontier 选择，而不是盲目增加 action width；因此论文中继续使用 width 6 作为默认设置是有证据的。
- 仍不能写成 `n=26--40` 已完整枚举；这些维度目前仍主要依赖项集级 plan 验证和 emitted-circuit GF(2) 符号验证。

### 2.0 RevKit API baseline 与工具链边界

本轮已把外部工具链审计从“是否存在命令”升级为“能否真实运行一个可复现 baseline”。当前 `mcts-qoracle` 环境中已安装 `cmake`、`pybind11` 和 RevKit Python API，并新增 `run_revkit_baseline.py` 调用 RevKit 的 `oracle_synth` 对完整 truth-table 函数合成。

主要产物：

- `analyze_toolchain_readiness.py`
- `run_revkit_baseline.py`
- `run_revkit_highdim_timeout_probe.py`
- `analyze_phase_rz_portfolio.py`
- `analyze_rz_synthesis_cost.py`
- `results/analysis_toolchain_readiness.md`
- `results/toolchain_readiness.json`
- `results/raw_revkit_oracle_synth_traditional.csv`
- `results/summary_revkit_oracle_synth_traditional.csv`
- `results/analysis_revkit_oracle_synth_traditional.md`
- `results/manifest_revkit_oracle_synth_traditional.json`
- `results/raw_revkit_highdim_timeout_probe.csv`
- `results/summary_revkit_highdim_timeout_probe.csv`
- `results/analysis_revkit_highdim_timeout_probe.md`
- `results/manifest_revkit_highdim_timeout_probe.json`
- `results/raw_phase_rz_portfolio.csv`
- `results/summary_phase_rz_portfolio.csv`
- `results/analysis_phase_rz_portfolio.md`
- `results/manifest_phase_rz_portfolio.json`
- `results/raw_rz_synthesis_cost.csv`
- `results/summary_rz_synthesis_cost.csv`
- `results/analysis_rz_synthesis_cost.md`
- `results/manifest_rz_synthesis_cost.json`
- `paper_latex/tables/revkit_oracle_synth_traditional.tex`
- `paper_latex/tables/revkit_highdim_timeout_probe.tex`
- `paper_latex/tables/phase_rz_portfolio.tex`
- `paper_latex/tables/rz_synthesis_cost.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v21.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v21.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v22.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v22.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v23.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v23.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v25.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v25.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v26.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v26.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v27.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v27.pdf`

本轮新增 `resource_nmcts_zh_manuscript_v27.tex/pdf`，定位为“投稿主线压缩版”：相比 v26 的完整项目报告口径，v27 更集中呈现 ANF/FPRM 项集合搜索、Boolean-ring screen、神经 MCTS/depth-frontier/guard、外部 proxy 和 RevKit phase/Rz 边界、正确性验证与投稿限制，适合先交给导师或合作者阅读主线。

核心结果：

| 对比 | 指标 | 函数数 | 胜/负/平 | 平均变化 |
|---|---|---:|---:|---:|
| Resource-NMCTS vs RevKit `oracle_synth` | lower-bound score | 177 | 6/171/0 | +751.69% |
| Resource-NMCTS vs RevKit `oracle_synth` | score+1/Rz | 177 | 140/37/0 | -14.52% |
| Resource-NMCTS vs RevKit `oracle_synth` | score+2/Rz | 177 | 177/0/0 | -53.48% |
| Pareto-Resource-NMCTS vs RevKit `oracle_synth` | score+1/Rz | 177 | 157/20/0 | -17.89% |
| Pareto-Resource-NMCTS vs RevKit `oracle_synth` | score+2/Rz | 177 | 177/0/0 | -55.24% |
| Resource-NMCTS vs RevKit `oracle_synth` | T+Rz | 177 | 148/18/11 | -23.88% |
| Resource-NMCTS family portfolio vs RevKit `oracle_synth` | score+1/Rz | 177 | 157/20/0 | -17.89% |
| Resource-NMCTS family portfolio vs RevKit `oracle_synth` | score+1.5/Rz | 177 | 177/0/0 | -42.26% |
| Traditional baseline family portfolio vs RevKit `oracle_synth` | score+1/Rz | 177 | 80/97/0 | +7.58% |
| Resource-NMCTS family portfolio vs RevKit `oracle_synth` | Ross-Selinger-style `T/Rz=30` proxy | 177 | 177/0/0 | -95.03% |
| Resource-NMCTS family portfolio vs RevKit `oracle_synth` | conservative `T/Rz=90` proxy | 177 | 177/0/0 | -97.01% |
| RevKit `oracle_synth` high-dimensional timeout probe | `n=14`, 30 s subprocess cutoff | 8 | 1 usable / 7 timeout / 0 error | median 30.00 s |

解释边界：

- 这是一个真实 RevKit Python API baseline，不是 ABC-only 的 ROS-style LUT proxy。
- RevKit 返回的是 Rz-phase netlist，不是可以直接按 T/Tdg 完整计数的 Clifford+T netlist；171/177 行包含非 Clifford `Rz`，总数 9242，角度除以 pi 的最大分母为 64。
- 当前 `score` 是 RevKit lower-bound proxy，没有包含非 Clifford rotation synthesis 成本；因此不能写成精确 Clifford+T T-count 对比。
- `score+1/Rz`、`score+2/Rz`、`T+Rz` 只是符号敏感性分析，不是硬件 mapping 或精确 rotation synthesis；但它们说明 RevKit 差距高度依赖非 Clifford phase cost 口径。
- `analyze_phase_rz_portfolio.py` 进一步说明 Resource-NMCTS family 的中位 break-even 为 0.80/Rz；`lambda_Rz=1.5` 时 family portfolio 已覆盖 177/177 行，而传统 baseline family 在 `lambda_Rz=1` 时仍只有 80/177 行获胜。
- `analyze_rz_synthesis_cost.py` 进一步把每个非 Clifford `Rz` 按 `ceil(a log2(1/epsilon)+b)` 计入近似 Clifford+T T-count proxy。Ross-Selinger-style `epsilon=1e-3` 时 `T/Rz=30`，Resource-NMCTS family 相对 RevKit 为 177/0/0、平均 score 降低 95.03%；更保守的 `4 log2(1/epsilon)+10` proxy 在 `epsilon=1e-6` 时 `T/Rz=90`，同样为 177/0/0、平均 score 降低 97.01%。
- 近似 Rz synthesis 结果仍是逻辑层成本模型，不输出实际 Clifford+T rotation sequence，不测量 synthesis runtime，也不包含硬件 mapping；它用于界定 RevKit phase lower-bound 口径，而不能替代最终 gate-sequence 级实验。
- `run_revkit_highdim_timeout_probe.py` 用一次一子进程的硬超时方式审计高维 RevKit API 边界。当前 `n=14` 前 8 个函数中 1 行返回、7 行触发 30 s timeout；唯一返回行 `anf_n14_10` 含 32767 个非 Clifford `Rz`，RevKit lower-bound score 为 2948.79，`score+1/Rz` 为 35715.79，说明高维 RevKit API 结果既受可扩展性限制，也受 phase/Rz 口径支配。
- 高维 timeout 行没有线路资源，不能参与 paired resource 均值；该结果支持把正式 RevKit API paired benchmark 限定在已经验证的 `n <= 6`，把高维 RevKit 写成 adapter/scalability boundary。
- 该结果不是坏消息，而是新的强基线：投稿前要么新增 phase/Rz-aware emitter 并处理 rotation synthesis 成本，要么把论文主张严格限定为 bit-flip oracle 的逻辑层资源综合。
- 当前已打通 mockturtle official-header probe、CirKit 3 shell AIG/MC probe 和 legacy RevKit CLI exact-oracle reversible-synthesis probe；官方 ROS 全流程仍未完整复现。

### 2.1 ESOP baseline 对比

新增 `analyze_esop_baseline.py`，专门从同一 benchmark 的内部 ESOP-MILP 和外部 ABC-ESOP 结果中生成 ESOP 视角分析。

主要产物：

- `results/analysis_esop_baseline.md`
- `results/summary_esop_baseline.csv`
- `paper_latex/tables/esop_baseline_by_n.tex`

核心结果：

| Baseline | 函数数 | T-count 变化 | CNOT 变化 | ancilla 变化 | score 变化 | score 胜/负/平 |
|---|---:|---:|---:|---:|---:|---:|
| Internal ESOP-MILP | 177 | -51.64% | -37.80% | -12.65% | -48.77% | 167/3/7 |
| ABC-ESOP export | 177 | -25.80% | -5.40% | -11.58% | -23.42% | 170/1/6 |

按变量数分组：

- 对 internal ESOP-MILP：`n=3..6` 每组 T-count 和 CNOT 总量都更低；ancilla 在 `n=3` 持平，在 `n=4..6` 更低。
- 对 ABC-ESOP：`n=3..6` 每组 T-count、CNOT 和 ancilla 总量都更低。

因此，论文中应写成“相同 benchmark 下显著优于 ESOP 的低 T / 加权资源结果”，而不是写成“所有 CNOT 指标都优于 ESOP”。

### 2.2 n=18 mega stress 收束

当前 `mega_highdim_resource` 已完成 12 个随机 `n=18` ANF 函数、7 个方法、84 行结果：

- `direct_anf`
- `and_direct_anf`
- `and_fprm_root_beam`
- `and_fprm_linear_pair_fast`
- `and_resource_nmcts`
- `and_profile_resource_nmcts`
- `and_pareto_resource_nmcts`

数据审计结果：

- 总行数：84
- error：0
- skipped：0
- incorrect：0
- 每个方法 12 行

核心结果：

| 对比 | T-count 胜/负/平 | score 胜/负/平 | 平均 T-count 变化 | 平均 score 变化 |
|---|---:|---:|---:|---:|
| fast linear-pair vs root-beam | 6/0/6 | 6/0/6 | -2.72% | -1.91% |
| Resource/Profile/Pareto vs fast linear-pair | 12/0/0 | 12/0/0 | -3.75% | -3.55% |
| Resource/Profile/Pareto vs root-beam | 12/0/0 | 12/0/0 | -6.19% | -5.29% |
| Resource/Profile/Pareto vs direct ANF | 12/0/0 | 12/0/0 | -60.05% | -56.99% |
| Resource/Profile/Pareto vs AND-direct ANF | 12/0/0 | 12/0/0 | -33.39% | -32.01% |

代价：

- 相对 direct ANF，CNOT、depth 和 peak ancilla 增加。
- 相对 AND-direct ANF，T、CNOT、depth 和 score 都改善，但 peak ancilla 增加。
- n=18 的 Pareto-Resource-NMCTS 当前故意收窄到与 Resource/Profile 相同的稳定高维 guard，因此它不是新的 Pareto 分离证据，而是规模和验证边界证据。

### 2.2.1 n=20 giga stress 边界测试

本轮新增 `giga_highdim_resource` 压力边界切片，覆盖 6 个随机 `n=20` ANF 函数、8 个方法、48 行结果；随后又补了 recursive Boolean-ring screen 的 targeted rerun，并继续把递归深度从 1 扩到 2：

- `direct_anf`
- `and_direct_anf`
- `and_boolean_linear_pair_screen`
- `and_boolean_linear_pair_screen_deep`（targeted rerun）
- `and_boolean_linear_pair_screen_deeper`（targeted rerun，recursive depth=2）
- `and_fprm_root_beam`
- `and_fprm_linear_pair_fast`
- `and_resource_nmcts`
- `and_profile_resource_nmcts`
- `and_pareto_resource_nmcts`

主要产物：

- `results/raw_giga_highdim_resource.csv`
- `results/summary_giga_highdim_resource.csv`
- `results/manifest_giga_highdim_resource.json`
- `results/analysis_giga_highdim_resource.md`
- `results/runtime_giga_highdim_resource.md`
- `paper_latex/tables/resource_giga_highdim_resource.tex`
- `paper_latex/tables/runtime_giga_highdim_resource.tex`
- `results/raw_giga_boolean_screen_deep.csv`
- `results/analysis_giga_screen_deep_vs_screen.md`
- `results/analysis_giga_resource_recursive_screen_vs_old.md`
- `results/raw_giga_boolean_screen_deeper.csv`
- `results/analysis_giga_screen_deeper_vs_deep.md`
- `results/analysis_giga_resource_deeper_vs_depth1_resource.md`
- `results/analysis_giga_resource_deeper_vs_old_resource.md`
- `paper_latex/tables/giga_screen_deep_vs_screen.tex`
- `paper_latex/tables/giga_resource_recursive_screen_vs_old.tex`
- `paper_latex/tables/giga_screen_deeper_vs_deep.tex`
- `paper_latex/tables/giga_resource_deeper_vs_old_resource.tex`

核心结果：

| 对比 | T-count 胜/负/平 | score 胜/负/平 | 平均 T-count 变化 | 平均 score 变化 |
|---|---:|---:|---:|---:|
| Resource/Profile/Pareto vs direct ANF | 5/0/1 | 5/1/0 | -36.80% | -34.00% |
| Resource/Profile/Pareto vs AND-direct ANF | 5/0/1 | 5/0/1 | -5.24% | -4.89% |
| ANF Boolean linear screen vs AND-direct ANF | 5/0/1 | 5/0/1 | -5.24% | -4.89% |
| Recursive Boolean screen vs single Boolean screen | 5/0/1 | 5/0/1 | -4.62% | -4.52% |
| Recursive-screen Resource-NMCTS vs old Resource-NMCTS | 5/0/1 | 5/0/1 | -4.62% | -4.52% |
| Deeper recursive Boolean screen vs depth-1 screen | 5/0/1 | 5/0/1 | -3.22% | -3.13% |
| Deeper-screen Resource-NMCTS vs old Resource-NMCTS | 5/0/1 | 5/0/1 | -7.64% | -7.47% |
| Deeper-screen Resource-NMCTS vs AND-direct ANF | 5/0/1 | 5/0/1 | -12.24% | -11.80% |

运行边界：

- `and_fprm_root_beam` 和 `and_fprm_linear_pair_fast` 在 6 个函数上全部触发 300 s task timeout。
- `and_boolean_linear_pair_screen` 是新增的可扩展修复分支：它不做 FPRM 极性筛选，只在原始 ANF 上用 Boolean-ring 规则筛选单层 linear factor，因此 6/6 完成，median runtime 为 10.659 s。
- `and_boolean_linear_pair_screen_deep` 在单层 screen 的 quotient/rest 子问题上再做一层同类 Boolean-ring screen，仍不做 FPRM 极性筛选。它 6/6 完成，相对单层 screen 为 5/0/1、平均 score -4.52%，standalone mean runtime 12.73 s，仅比单层 screen 慢约 16.92%。
- `and_boolean_linear_pair_screen_deeper` 把同类 screen 深度扩到 2，仍不做 FPRM 极性筛选。它 6/6 完成，相对 depth-1 screen 为 5/0/1、平均 score -3.13%，standalone mean runtime 20.15 s；代价是 peak ancilla 平均从 2.833 增至 3.000。
- 集成后的 `and_resource_nmcts` 也完成 6/6，相对上一版 depth-1 Resource 为 5/0/1、平均 score -3.13%；相对旧 Resource-NMCTS 为 5/0/1、平均 score -7.47%；相对 AND-direct ANF 为 5/0/1、平均 score -11.80%；相对 direct ANF 为 5/1/0、平均 score -38.86%。
- 因此，n=20 可以写成“边界改善进一步扩大”：当前实现仍无法让 FPRM root-beam/fast linear-pair 在 300 s 内完成，但 ANF-only depth-2 recursive Boolean-ring screen 能在超高维上提供可验证的 baseline-preserving 增益。不能把它写成深层神经/FPRM 搜索已经解决 n=20；也要注明运行时间和辅助比特有上升。

### 2.3 外部 ABC/BDD 高维对比

当前高维外部 baseline 覆盖：

- 64 个 `n=14` 函数
- 32 个 `n=15` 函数
- 24 个 `n=16` 函数
- 12 个 `n=18` 函数

每个函数都有 ABC-AIG、ABC-XAG、ABC-LUT、BDD 行，总计 528 个外部比较行，均通过 truth-table 验证。

`n=18` 上 Resource/Profile/Pareto 的平均 score 降幅：

- ABC-AIG：-98.85%
- ABC-XAG：-99.05%
- ABC-LUT：-99.69%
- BDD：-98.30%

边界条件：

- ABC-AIG 和 ABC-XAG 在多数高维函数上保持更低的 level/depth 估计。
- 因此，高维外部结果支持“低 ancilla / 低加权资源 / 低 T-count”，但不支持“depth-only 支配”。

### 2.4 搜索贡献分解

新增 `analyze_search_contribution.py`，把分散在多个实验文件中的消融结果统一成一张 contribution decomposition 表，避免论文只给出“大结果”而无法回答“提升到底来自哪里”。

主要产物：

- `results/analysis_search_contribution.md`
- `results/summary_search_contribution.csv`
- `results/analysis_weight_robustness.md`
- `results/summary_weight_robustness.csv`
- `results/raw_search_ablation_traditional.csv`
- `results/analysis_search_ablation_traditional.md`
- `results/raw_search_ablation_highdim.csv`
- `results/analysis_search_ablation_highdim.md`
- `results/raw_neural_prior_ablation.csv`
- `results/analysis_neural_prior_ablation.md`
- `paper_latex/tables/search_contribution_decomposition.tex`

关键结论：

| 贡献环节 | 函数集 | score 胜/负/平 | 平均 score 变化 | 解释 |
|---|---|---:|---:|---|
| affine greedy vs fixed-coordinate MCTS | `ablation_affine` | 165/88/68 | -12.12% | 仿射坐标搜索是最大前置收益，但不是单调 guard |
| neural refine over affine greedy | `ablation_affine` | 65/0/257 | -1.08% | 神经 refine 有小幅、无 score loss 的增益 |
| guarded Affine-NMCTS over no-guard | `ablation_affine` | 88/0/234 | -1.74% | final guard 有无损增益 |
| learned prior for Resource-NMCTS | `traditional_resource` | 39/0/138 | -1.10% | 学习先验是质量信号，但不是最快模式 |
| Pareto archive over Resource-NMCTS | `traditional_resource` | 68/0/109 | -3.26% | 小规模 profile/Pareto archive 贡献明确 |
| Resource-NMCTS over no-MCTS portfolio | `search_ablation_traditional` | 54/0/123 | -1.44% | dedicated rerun 证明 MCTS/神经候选在强化 no-MCTS baseline 后仍有增益 |
| Pareto Resource-NMCTS over no-MCTS portfolio | `search_ablation_traditional` | 106/0/71 | -4.69% | Pareto archive 对 no-MCTS portfolio 的增益更明确 |
| highdim no-MCTS portfolio over root beam | `search_ablation_highdim` | 14/0/2 | -6.25% | n=14 同 preset 高维 guard/no-MCTS 机制证据 |
| highdim no-MCTS portfolio over linear-pair | `search_ablation_highdim` | 14/0/2 | -3.08% | 说明 no-MCTS portfolio 在高维下仍能改善单一 linear-pair child |
| linear-pair guard vs root beam, n=14 | `highdim_resource` | 60/0/4 | -3.00% | 高维主要增益来自 bounded linear-pair guard |
| recursive linear-pair guard vs root beam, n=15 | `highdim_scale_resource` | 30/0/2 | -5.28% | 递归 pair guard 是 n=15 的主要规模贡献 |
| shallow linear-pair guard vs root beam, n=16 | `ultra_highdim_resource` | 22/0/2 | -1.88% | 旧浅层 guard 仍有可测增益 |
| recursive linear-pair guard vs shallow linear-pair, n=16 | `ultra_highdim_resource` | 23/0/1 | -2.54% | 新增递归 guard 明确优于浅层 guard |
| recursive linear-pair guard vs root beam, n=16 | `ultra_highdim_resource` | 23/0/1 | -4.31% | n=16 的主要规模贡献已更新为 recursive linear-pair guard |
| root-neural recursive guard vs deterministic recursive guard, n=16 | `ultra_highdim_resource` | 6/7/11 | +0.08% | 单独神经排序不稳定，不能作为正向主张 |
| baseline-preserving AI guard vs deterministic recursive guard, n=16 | `ultra_highdim_resource` | 6/0/18 | -0.05% | 用 deterministic guard 兜底后获得无 score-loss 小增益 |
| pairwise-wide Resource-NMCTS vs deterministic recursive guard, n=16 | `ultra_pairwise_wide_vs_recursive` | 10/0/14 | -0.18% | root-action pairwise ranker + heuristic/neural union 把高维 AI 增益放大到 full synthesis 层面 |
| pairwise-wide Resource-NMCTS vs old Resource-NMCTS, n=16 | `ultra_pairwise_wide_vs_old_resource` | 10/0/14 | -0.12% | 新 pairwise-wide 分支优于旧 root-teacher Resource 结果 |
| Boolean-ring linear-deep vs deterministic recursive guard, n=16 | `ultra_boolean_linear_vs_deep` | 17/3/4 | -0.39% | 允许 quotient 与 linear factor 共享变量后，结构性收益强于 pairwise-wide neural guard |
| Boolean-guard Resource-NMCTS vs pairwise-wide Resource-NMCTS, n=16 | `ultra_boolean_guard_vs_pairwise_wide` | 14/0/10 | -0.34% | full synthesis 主方法获得无 score-loss 的新高维改进 |
| fast linear-pair guard vs root beam, n=18 | `mega_highdim_resource` | 6/0/6 | -1.91% | n=18 是可验证的压力边界证据 |
| Resource-NMCTS vs fast linear-pair, n=18 | `mega_highdim_resource` | 12/0/0 | -3.55% | n=18 Resource guard 对 fast child 仍有进一步选择收益 |

这个结果把论文主张进一步收窄为：仿射坐标搜索、神经 refine、guard/Pareto archive、高维 linear-pair guard 和 Boolean-ring linear factor 共同构成方法贡献；其中高维大规模证据不能夸大为完整 Pareto archive 的强独立优势，因为部分高维设置中 Resource/Profile/Pareto 会退化或收窄到稳定 guard。最新 `n=16` Boolean-ring rerun 后，`Resource-NMCTS` 在 full synthesis 层面相对上一轮 pairwise-wide Resource 获得 14/0/10、平均 score 降低 0.34%；相对 deterministic recursive guard 获得 18/0/6、平均 score 降低 0.52%。因此该切片现在应写成“recursive guard + Boolean-ring linear factor + baseline-preserving portfolio”的结构性正向证据；pairwise-wide neural guard 仍是 AI 模块的小幅正向消融，但不再是高维主质量增益的唯一来源。

### 2.5 高维 learned-prior 诊断

本轮补了 `highdim_neural_prior` 小切片，目标是回答“学习先验在高维 Resource-NMCTS 中是否仍有贡献”。直接使用全递归 neural linear-pair child 会在 n=14 上产生明显长尾，因此代码改成了 root-only neural screening：神经模型只影响高维 linear-pair 的根层候选排序，后续子问题仍使用确定性 greedy/beam。

新增训练产物：

- `models/linear_action_scorer_highdim.pt`

新增结果产物：

- `results/raw_highdim_neural_prior_learned_prior.csv`
- `results/raw_highdim_neural_prior_no_prior.csv`
- `results/raw_neural_prior_highdim_ablation.csv`
- `results/analysis_neural_prior_highdim_ablation.md`
- `paper_latex/tables/neural_prior_highdim_ablation.tex`

核心结果：

| 对比 | 函数集 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---|---:|---:|---:|
| learned Resource-NMCTS vs no-prior Resource-NMCTS | 12 个 n=14 random ANF | 1/0/11 | -0.01% | +104.07% |

结论：高维 learned-prior 小切片已经完成，但它不是强正向证据。专用 linear-action 模型只带来 1 个轻微 score 胜例，且运行时间约翻倍。因此论文主贡献仍应放在 n<=6 learned-prior 正向证据、低维 neural refine、MCTS/Pareto archive、以及高维 bounded linear-pair guard；高维 neural guidance 目前只能写成边界诊断或 future work。

### 2.5.1 结构级 Boolean screen depth policy

本轮新增 `train_screen_depth_policy.py`，把 AI 从 root action 排序推进到结构级选择：给定高维 ANF 项集合的统计特征，预测应该使用 single、depth-1 还是 depth-2 Boolean-ring screen。标签不是人工规则，而是实际运行三种 screen 后按统一资源 score 选择 oracle depth。

主要产物：

- `train_screen_depth_policy.py`
- `models/boolean_screen_depth_policy.pt`
- `results/raw_boolean_screen_depth_policy.csv`
- `results/summary_boolean_screen_depth_policy.csv`
- `results/analysis_boolean_screen_depth_policy.md`
- `paper_latex/tables/boolean_screen_depth_policy.tex`

实验设置：

- 训练集：240 个生成式高维 ANF 项集合，变量数 `n=14,16,18`。
- 验证集：72 个同分布项集合。
- 测试集：48 个 held-out `n=20` 项集合。
- 特征：项数、次数分布、变量/二元共现密度、root Boolean-ring action 数量与 top action 覆盖率/收益等结构统计。

核心结果：

| 对比 | 函数数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---:|---:|---:|---:|
| policy vs single screen | 48 | 42/0/6 | -6.57% | +2224.00% |
| policy vs depth-1 screen | 48 | 34/0/14 | -2.57% | +257.27% |
| policy vs depth-2 screen | 48 | 0/5/43 | +0.28% | -10.85% |
| policy vs all-depth adaptive | 48 | 0/5/43 | +0.28% | -34.71% |

结论：这是比 action-level prior 更明确的结构级 AI 证据，说明模型可以学习何时需要更深 Boolean-ring screen；但它仍不能写成最终质量突破，因为固定 depth-2 screen 在 score 上略优。论文里应表述为“结构级 AI 已经能减少全 depth adaptive 评估开销，并优于浅层固定策略；下一步需要加 baseline-preserving guard，让 policy 在不劣于 depth-2 的前提下降低运行时间或选择更强分支”。

### 2.5.2 保守 depth-2 skip guard

本轮新增并更新 `train_screen_depth_guard.py`，专门修补上一节的质量缺口。它不再直接预测 single/depth-1/depth-2 三分类，而是学习一个更保守的问题：何时可以跳过 depth-2，使 depth-1 screen 与固定 depth-2 screen 的 score 持平。当前实现区分两种执行模式：`static-direct` 只用静态 ANF/action 特征，在综合前直接派发到 depth-1 或 depth-2；`shallow-staged` 先运行 single/depth-1 screen，再用浅层观测特征决定是否跳过 depth-2。阈值在 train+validation 上按 zero-false-skip 约束选择；shallow-staged 额外使用 0.95 高置信阈值下限。

主要产物：

- `train_screen_depth_guard.py`
- `models/boolean_screen_depth_guard.pt`
- `models/boolean_screen_depth_guard.json`
- `models/boolean_screen_depth_guard_shallow_staged.pt`
- `models/boolean_screen_depth_guard_shallow_staged.json`
- `results/raw_boolean_screen_depth_guard.csv`
- `results/summary_boolean_screen_depth_guard.csv`
- `results/analysis_boolean_screen_depth_guard.md`
- `results/boolean_screen_depth_guard_shallow_staged/`
- `results/analysis_boolean_screen_depth_guard_modes.md`
- `results/summary_boolean_screen_depth_guard_modes.csv`
- `paper_latex/tables/boolean_screen_depth_guard.tex`
- `paper_latex/tables/boolean_screen_depth_guard_modes.tex`

核心结果：

| split | 函数数 | skip depth-2 | false skip | vs fixed depth-2 score | vs fixed depth-2 time | vs all-depth time |
|---|---:|---:|---:|---:|---:|---:|
| static-direct train | 480 | 12 | 0 | 0/0/480 持平 | -0.16% | -23.62% |
| static-direct valid | 144 | 3 | 0 | 0/0/144 持平 | -0.28% | -23.45% |
| static-direct test, n=20 | 96 | 4 | 0 | 0/0/96 持平 | -0.54% | -24.74% |
| shallow-staged test, n=20 | 48 | 8 | 0 | 0/0/48 持平 | +29.10% | -7.81% |

解释：这个 guard 第一次把结构级策略的 score 缺口降为 0，并把运行时证据拆成两条清晰路线。`static-direct` 是可部署默认模式：不先跑 shallow screen，在 96 个 held-out `n=20` 样本上相对固定 depth-2 小幅节省 0.54%，相对 all-depth adaptive 节省 24.74%。`shallow-staged` 用浅层观测把安全跳过覆盖提高到 8/48，仍保持 0 false skip 和 0 score loss，但因为先运行 single/depth-1 screen，相对固定 depth-2 screen 仍慢 29.10%。这已经比上一版“3/48 skip、-2.87% all-depth time”的证据更清楚，但仍不能写成最终高维质量突破。下一步应把 shallow 观测蒸馏回 direct guard，或让 guard 同时选择 Resource tail / FPRM / screen 分支。

### 2.5.3 Resource screen-gate 运行时门控

本轮还出现了一个工程性改进：`train_structure_gate.py` 用 adaptive Boolean-ring screen 与完整 Resource-NMCTS 的配对结果训练一个可解释 decision stump，判断何时可以跳过昂贵的 Resource-NMCTS tail。当前模型很小，经过 safety-first 阈值选择后学到的规则是 `n >= 20` 时优先跳过 Resource tail；`synthesizers.py` 也同步改为 direct branch gate：当模型只依赖 `n` 且判定不跳过时，直接运行 Resource-NMCTS，不再预先支付 screen 开销；当判定跳过时，只运行 adaptive screen 作为输出候选。它应被视为运行时门控证据，而不是新的资源质量模型。

主要产物：

- `train_structure_gate.py`
- `models/resource_structure_gate.json`
- `results/analysis_structure_gate.md`
- `results/raw_giga_screen_gate_resource.csv`
- `results/summary_giga_screen_gate_resource.csv`
- `results/analysis_giga_screen_gate_vs_resource.md`
- `results/analysis_giga_screen_gate_vs_adaptive_screen.md`
- `results/raw_gate_holdout_resource.csv`
- `results/analysis_gate_holdout_by_n.md`
- `results/analysis_gate_holdout_screen_gate_vs_resource.md`
- `results/analysis_gate_holdout_adaptive_vs_resource.md`
- `paper_latex/tables/giga_screen_gate_vs_resource.tex`
- `paper_latex/tables/giga_screen_gate_vs_adaptive_screen.tex`
- `paper_latex/tables/gate_holdout_by_n.tex`

核心结果：

| 对比 | 函数数 | T/CNOT/depth/score | 平均运行时间变化 |
|---|---:|---:|---:|
| screen-gated Resource vs full Resource, n=20 | 6 | 全部 0/0/6 持平 | -75.58% |
| screen-gated Resource vs adaptive screen, n=20 | 6 | 全部 0/0/6 持平 | -0.04% |
| held-out gate vs full Resource, n=19+20 | 16 | score 全部 0/0/16 持平 | -36.83% |
| held-out adaptive screen vs full Resource, n=19 | 8 | score 0/4/4，平均 +14.14% | -94.42% |
| held-out gate vs full Resource, n=20 | 8 | score 全部 0/0/8 持平 | -73.66% |

结论：screen-gate 说明当前 n=20 上完整 Resource tail 没有带来额外资源收益，可以被结构门控跳过以减少运行时间；新增 held-out n=19/20 切片更关键：n=19 上 adaptive screen 仍会输给 full Resource，因此 gate 不跳过且通过 direct branch 避免额外 screen 开销；n=20 上 adaptive screen 与 full Resource 全部持平，因此 gate 跳过并节省时间。这使门控证据比单一 n=20 切片更可信，但因为训练样本仍只有 18 个，论文中仍只能写成“高维运行时尾部控制”，不能写成普适替代 Resource-NMCTS。

### 2.5.4 n=20--28 项集级大规模 screen-scale

完整 truth table 在 n>20 后构造和验证成本迅速上升，因此本轮继续升级 `run_screen_scale_terms.py`：它直接在 ANF 项集合这一搜索状态上评估 direct logical-AND、single/depth-1/depth-2 Boolean-ring screen、all-depth adaptive、已训练 depth policy 和保守 depth-2 guard。同时，脚本先对每个返回的 factor plan 做 ANF 符号展开验证：direct 节点返回自身项集，普通 factor 将 quotient 项乘回 monomial factor，Boolean-ring linear factor 在 GF(2) 上展开线性因子，再与 rest 项集合异或合并；随后把 `emit_plan_to_circuit` 产生的 X/CNOT/MCT oracle 线路也作为 GF(2) 多项式系统符号模拟，检查输入线恢复、输出项集合等价和辅助线清零。该实验不替代完整 truth-table simulation，但已经从“只看资源估计”提升到“项集级资源评估 + plan 级符号等价验证 + emitted-circuit 级符号验证”。

主要产物：

- `run_screen_scale_terms.py`
- `results/raw_screen_scale_terms.csv`
- `results/summary_screen_scale_terms.csv`
- `results/analysis_screen_scale_terms.md`
- `paper_latex/tables/screen_scale_terms.tex`

核心结果：

| 对比 | 项集数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---:|---:|---:|---:|
| adaptive all-depth vs single screen, n=20/22/24/28 | 192 | 169/0/23 | -6.63% | +3077.71% |
| adaptive all-depth vs fixed depth-2, n=20/22/24/28 | 192 | 0/0/192 | +0.00% | +47.92% |
| depth policy vs single screen, n=20/22/24/28 | 192 | 169/0/23 | -6.56% | +2328.66% |
| depth policy vs all-depth adaptive, n=20/22/24/28 | 192 | 0/6/186 | +0.08% | -31.01% |
| depth policy vs all-depth adaptive, n=28 | 48 | 0/0/48 | +0.00% | -32.15% |
| direct depth-2 guard vs fixed depth-2, n=20/22/24/28 | 192 | 0/0/192 | +0.00% | -0.14% |
| ANF plan 符号验证 | 1344 方法行 | 1344/0 通过/失败 | 0 mismatch | - |
| emitted-circuit ANF 符号验证 | 1344 方法行 | 1344/0 通过/失败 | 0 mismatch | max wire terms 272 |

结论：这是目前最清楚的大规模结构级 AI 证据。All-depth adaptive 说明 depth-2 screen 是强质量基线；depth policy 在 n=20--28 上几乎复制 all-depth 的质量收益，并节省约三成 all-depth 评估时间，尤其 n=28 上全部持平。新增 emitted-circuit ANF 符号验证后，n>20 结果不再只是资源估算表，也不只停留在 plan 级等价；每个候选分解生成的 X/CNOT/MCT 线路都能在符号多项式层面验证输出等价和辅助线复原。它仍不是完整 truth-table simulation，也不能替代 n<=20 的 truth-table correctness 结果，但可以更有力地支撑“结构级策略可扩展到更高维项集合”的论文主张。

### 2.5.5 n=32--40 项集级 extended scale

为进一步回应“大规模是否只是 n=20--28 的偶然切片”这一风险，本轮把同一项集级 screen-scale 协议扩展到 `n=32,36,40`，每个维度 48 个生成式高维 ANF 项集，共 144 个样本。该实验使用 `run_screen_scale_terms.py --tag extended` 写入独立结果文件，不覆盖 2.5.4 的主表。验证协议与 n=20--28 完全一致：每个 factor plan 先做 ANF 符号展开验证，再把生成的 X/CNOT/MCT oracle 线路作为 GF(2) 多项式系统符号模拟，检查输入线恢复、输出项集合等价和辅助线清零。

主要产物：

- `results/raw_screen_scale_extended_terms.csv`
- `results/summary_screen_scale_extended_terms.csv`
- `results/analysis_screen_scale_extended_terms.md`
- `paper_latex/tables/screen_scale_extended_terms.tex`

核心结果：

| 对比 | 项集数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---:|---:|---:|---:|
| adaptive all-depth vs single screen, n=32/36/40 | 144 | 110/0/34 | -5.55% | +2680.60% |
| adaptive all-depth vs fixed depth-2, n=32/36/40 | 144 | 0/0/144 | +0.00% | +64.37% |
| depth policy vs single screen, n=32/36/40 | 144 | 110/0/34 | -5.55% | +2061.11% |
| depth policy vs all-depth adaptive, n=32/36/40 | 144 | 0/0/144 | +0.00% | -33.14% |
| depth2 guard vs fixed depth-2, n=32/36/40 | 144 | 0/0/144 | +0.00% | -0.00% |
| ANF plan 符号验证 | 1008 方法行 | 1008/0 通过/失败 | 0 mismatch | - |
| emitted-circuit ANF 符号验证 | 1008 方法行 | 1008/0 通过/失败 | 0 mismatch | max wire terms 288 |

结论：extended scale 的价值在于验证结构策略的高维泛化边界。Depth policy 的训练维度仍是 n=14/16/18，但在 n=32/36/40 上与 all-depth adaptive 全部 score 持平，并节省约三分之一 all-depth 评估时间；相对 single screen 仍保持 110/0/34、平均 score -5.55% 的质量优势。这比 n=20--28 结果更能支撑“大规模项集合上结构级策略可扩展”的主张。边界也必须保留：该实验仍是项集级 symbolic verification，不是完整 truth-table simulation，也没有证明 policy 超过 fixed depth-2 质量基线。

### 2.5.6 depth-3/4 Boolean-ring screen 质量-时间前沿

前两组 scale 结果说明 fixed depth-2 是很强的默认质量基线，但这也带来一个审稿风险：结构级 AI 只是学习何时复制 depth-2，并没有继续提升质量。本轮新增 `--max-screen-depth` 参数，把同一项集级协议扩展到 depth-3 和 depth-4 Boolean-ring screen。该实验定位为高预算质量前沿，不替代默认快速策略。

主要产物：

- `results/raw_screen_scale_depth_frontier_terms.csv`
- `results/summary_screen_scale_depth_frontier_terms.csv`
- `results/analysis_screen_scale_depth_frontier_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_terms.tex`

核心结果：

| 对比 | 项集数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---:|---:|---:|---:|
| screen depth-3 vs fixed depth-2, n=20/28/40 | 72 | 49/0/23 | -1.93% | +193.71% |
| screen depth-4 vs fixed depth-2, n=20/28/40 | 72 | 49/0/23 | -3.10% | +682.97% |
| screen depth-4 vs depth-3, n=20/28/40 | 72 | 44/0/28 | -1.21% | +127.55% |
| all-depth adaptive depth<=4 vs fixed depth-2 | 72 | 49/0/23 | -3.10% | +1129.85% |
| ANF plan 符号验证 | 648 方法行 | 648/0 通过/失败 | 0 mismatch | - |
| emitted-circuit ANF 符号验证 | 648 方法行 | 648/0 通过/失败 | 0 mismatch | max wire terms 244 |

结论：这是本轮最重要的质量增益证据。Depth-3/4 不再只是省时门控，而是稳定打破 fixed depth-2 的 score 上限：在 n=20/28/40 上均无 score loss，depth-4 平均 score 进一步降低 3.10%。代价也很明确，depth-4 平均运行时间比 depth-2 增加约 6.8 倍，all-depth<=4 因需要同时跑多种深度，时间开销更高。因此论文中应把它写成“可调预算的质量-时间前沿”：快速默认模式仍是 depth policy/guard，投稿级质量模式可以加入 depth-3/4 作为高预算候选。

### 2.5.7 depth-frontier policy：把高预算质量前沿学习化

v12 中把 depth-frontier 写成下一步缺口：需要训练一个策略，在 depth-2/3/4 之间选择，使其接近 depth-4 的质量但低于 all-depth<=4 的运行成本。本轮新增 `train_screen_depth_frontier_policy.py`，训练结构级 depth-frontier policy，并把该策略接入 `run_screen_scale_terms.py`。

主要产物：

- `train_screen_depth_frontier_policy.py`
- `models/boolean_screen_depth_frontier_policy.pt`
- `results/raw_boolean_screen_depth_frontier_policy.csv`
- `results/summary_boolean_screen_depth_frontier_policy.csv`
- `results/analysis_boolean_screen_depth_frontier_policy.md`
- `paper_latex/tables/boolean_screen_depth_frontier_policy.tex`
- `results/raw_screen_scale_depth_frontier_policy_terms.csv`
- `results/summary_screen_scale_depth_frontier_policy_terms.csv`
- `results/analysis_screen_scale_depth_frontier_policy_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_policy_terms.tex`
- `results/raw_screen_scale_depth_frontier_policy_generalization_terms.csv`
- `results/summary_screen_scale_depth_frontier_policy_generalization_terms.csv`
- `results/analysis_screen_scale_depth_frontier_policy_generalization_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_policy_generalization_terms.tex`

核心结果：

| 设置 | 对比 | 项集数 | score 胜/负/平 | 平均 score 变化 | 平均运行时间变化 |
|---|---|---:|---:|---:|---:|
| held-out n=28/40 | frontier policy vs depth-2 | 32 | 13/0/19 | -1.95% | +455.93% |
| held-out n=28/40 | frontier policy vs depth-4 | 32 | 0/9/23 | +0.80% | -25.99% |
| held-out n=28/40 | frontier policy vs oracle depth-2/3/4 frontier | 32 | 0/9/23 | +0.80% | -58.76% |
| scale n=20/28/40 | depth_frontier_policy vs depth-2 | 72 | 35/0/37 | -2.19% | +503.20% |
| scale n=20/28/40 | depth_frontier_policy vs depth-4 | 72 | 0/16/56 | +0.97% | -22.17% |
| scale n=20/28/40 | depth_frontier_policy vs all-depth depth<=4 | 72 | 0/16/56 | +0.97% | -58.69% |
| independent seed n=24/28/32/40 | depth_frontier_policy vs depth-2 | 96 | 40/0/56 | -1.85% | +456.43% |
| independent seed n=24/28/32/40 | depth_frontier_policy vs depth-4 | 96 | 0/19/77 | +0.61% | -23.40% |
| independent seed n=24/28/32/40 | depth_frontier_policy vs all-depth depth<=4 | 96 | 0/19/77 | +0.61% | -61.25% |
| ANF plan 符号验证 | 720 方法行 | 720/0 通过/失败 | 0 mismatch | - |
| emitted-circuit ANF 符号验证 | 720 方法行 | 720/0 通过/失败 | 0 mismatch | max wire terms 244 |
| independent seed ANF plan 符号验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | - |
| independent seed emitted-circuit ANF 符号验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | max wire terms 270 |

结论：这是本轮相对 v12 的主要 AI 进展。Depth-frontier policy 不能完全达到 depth-4/oracle frontier，但已经把 depth-4 的质量收益学习化为可选择策略：正式 scale 中相对 fixed depth-2 平均 score 降低 2.19%，独立 seed 泛化集中仍降低 1.85%，两组均无 score loss；同时相对完整 all-depth<=4 评估节省 58.69%--61.25% 时间。论文中应写成“结构级 AI 的质量-时间折中证据”，而不是写成全局最优策略。

### 2.5.7.1 large frontier policy：压缩质量 gap 的增强版

为回应“frontier policy 相对 all-depth 仍有约 0.61%--0.80% score gap”的问题，本轮把 teacher 数据和模型容量继续放大：训练样本从 96 增至 192，验证样本从 36 增至 72，held-out 测试样本从 32 增至 48，隐藏层宽度从 96 增至 160，并保留 depth-2/3/4 frontier 作为监督目标。

主要产物：

- `models/boolean_screen_depth_frontier_policy_large.pt`
- `results/raw_boolean_screen_depth_frontier_policy_large.csv`
- `results/summary_boolean_screen_depth_frontier_policy_large.csv`
- `results/analysis_boolean_screen_depth_frontier_policy_large.md`
- `paper_latex/tables/boolean_screen_depth_frontier_policy_large.tex`
- `results/raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv`
- `results/summary_screen_scale_depth_frontier_policy_large_generalization_terms.csv`
- `results/analysis_screen_scale_depth_frontier_policy_large_generalization_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_policy_large_generalization_terms.tex`
- `results/raw_truth_bridge_n23_large_frontier_terms.csv`
- `results/summary_truth_bridge_n23_large_frontier_terms.csv`
- `results/analysis_truth_bridge_n23_large_frontier_terms.md`
- `paper_latex/tables/truth_bridge_n23_large_frontier_terms.tex`
- `results/analysis_frontier_policy_upgrade.md`
- `paper_latex/tables/frontier_policy_upgrade.tex`

核心结果：

| 设置 | 对比 | 项集/函数数 | score 胜/负/平 | 平均 score 变化 | 平均时间变化 |
|---|---|---:|---:|---:|---:|
| held-out n=28/40 | large frontier vs oracle depth-2/3/4 frontier | 48 | 0/3/45 | +0.04% | -51.30% |
| independent seed n=24/28/32/40 | large frontier vs fixed depth-2 | 96 | 56/0/40 | -2.34% | +563.80% |
| independent seed n=24/28/32/40 | large frontier vs old frontier | 96 | 17/0/79 | -0.49% | +119.26% |
| independent seed n=24/28/32/40 | large frontier vs all-depth depth<=4 | 96 | 0/6/90 | +0.10% | -53.50% |
| n=23 bridge | large frontier vs fixed depth-2 | 6 | 5/0/1 | -2.36% | +790.62% |
| n=23 bridge | large frontier vs old frontier | 6 | 1/0/5 | -0.48% | +46.16% |
| n=23 bridge | large frontier vs all-depth | 6 | 0/1/5 | +0.12% | -45.99% |
| large scale ANF plan 验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | - |
| large scale emitted-circuit ANF 验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | - |
| large n=23 完整 truth-table / plan / emitted-circuit 验证 | 60 方法行 | 60/0 通过/失败 | 0 mismatch | - |

结论：large frontier policy 是本轮更明确的“明显提升”证据。它把 held-out 相对 oracle frontier 的 score gap 从旧模型的 +0.80% 压到 +0.04%，把独立泛化集相对 all-depth 的 gap 从 +0.61% 压到 +0.10%，并在同一泛化集上相对旧 policy 取得 17/0/79、平均 score -0.49%。但它更频繁选择 depth-3/4，因而比旧 policy 慢、辅助线 lifetime area 也可能增加。论文中应写成“质量增强型结构策略”，不能写成“同时更快更优”的策略。

### 2.5.7.2 cost-aware frontier policy：质量-时间-辅助线折中版

large frontier policy 解决了质量 gap，但时间和辅助线生命周期代价偏高。为把策略从单一质量目标推进到质量-时间-辅助线折中，本轮扩展 `train_screen_depth_frontier_policy.py`，新增 `--label-time-weight` 和 `--label-ancilla-weight`。当前 cost-aware 版本使用标签目标 `score_delta + 0.003*time_delta`（相对 fixed depth-2），保持同样的 192/72/48 train/validation/test 规模和 hidden=160。

主要产物：

- `models/boolean_screen_depth_frontier_policy_cost_time003.pt`
- `results/raw_boolean_screen_depth_frontier_policy_cost_time003.csv`
- `results/summary_boolean_screen_depth_frontier_policy_cost_time003.csv`
- `results/analysis_boolean_screen_depth_frontier_policy_cost_time003.md`
- `paper_latex/tables/boolean_screen_depth_frontier_policy_cost_time003.tex`
- `results/raw_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv`
- `results/summary_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv`
- `results/analysis_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.md`
- `paper_latex/tables/screen_scale_depth_frontier_policy_cost_time003_generalization_terms.tex`
- `results/raw_truth_bridge_n23_cost_time003_frontier_terms.csv`
- `results/summary_truth_bridge_n23_cost_time003_frontier_terms.csv`
- `results/analysis_truth_bridge_n23_cost_time003_frontier_terms.md`
- `paper_latex/tables/truth_bridge_n23_cost_time003_frontier_terms.tex`

核心结果：

| 设置 | 对比 | 项集/函数数 | score 胜/负/平 | 平均 score 变化 | 平均时间变化 | T-depth / lifetime area |
|---|---|---:|---:|---:|---:|---:|
| held-out n=28/40 | cost policy vs cost-aware frontier | 48 | 0/6/40 | +0.38% | -71.54% | - |
| independent seed n=24/28/32/40 | cost policy vs fixed depth-2 | 96 | 56/0/40 | -1.39% | +170.03% | T-depth -1.36%，lifetime +14.63% |
| independent seed n=24/28/32/40 | cost policy vs all-depth | 96 | 0/53/43 | +1.10% | -76.54% | T-depth +1.06%，lifetime -8.86% |
| independent seed n=24/28/32/40 | cost policy vs large policy | 96 | 1/48/47 | +0.99% | -33.02% | T-depth +0.97%，lifetime -7.61% |
| n=23 bridge | cost policy vs fixed depth-2 | 6 | 4/0/2 | -1.46% | +196.09% | T-depth -1.43%，lifetime +15.95% |
| n=23 bridge | cost policy vs large policy | 6 | 0/5/1 | +0.92% | -56.29% | T-depth +0.73%，lifetime -12.62% |
| cost scale ANF plan / emitted-circuit 验证 | 960 方法行 | 960/0 通过/失败 | 0 mismatch | - | - |
| cost n=23 完整 truth-table / plan / emitted-circuit 验证 | 60 方法行 | 60/0 通过/失败 | 0 mismatch | - | - |

结论：cost-aware frontier policy 不是新的最高质量策略，而是一个可写进论文的“运行模式”贡献：large policy 是质量模式，cost-aware policy 是快速质量折中模式。它在独立泛化集上保持与 large policy 相同的 56/0/40 胜/负/平结构，但把相对 depth-2 的平均 plan time 增幅从 +563.80% 压到 +170.03%，把 lifetime area 增幅从 +26.13% 压到 +14.63%。在 n=23 完整 bridge 上，相对 large policy 节省 56.29% plan time 和 12.62% lifetime area，代价是 score 高 0.92%。这比单纯继续追求最低 score 更接近“资源约束综合”的论文主题。

### 2.5.7.3 stage-gated frontier：接近 all-depth 的高质量 teacher/guard

为进一步把 depth-frontier 从“单次神经选择”扩展成更可解释的搜索预算控制，本轮新增 `analyze_stage_gated_frontier.py`。该脚本不重新生成候选，而是复用 large frontier 实验中已经测量并验证过的 depth-2/3/4 行，构造一个 progressive controller：

1. 先评估 depth-2 和 depth-3 Boolean-ring screen；
2. 只有当 depth-3 相对 depth-2 的 score 改进达到阈值时才评估昂贵的 depth-4；
3. 在已评估深度中选择 score 最低的候选。

阈值不在独立 scale/test 上调参，而是在 large frontier 的 validation split 上选择：约束 validation 相对 all-depth 的 score gap 不超过 0.05%，再选 staged time 最低的阈值。最终阈值为 `1.25%`。

主要产物：

- `analyze_stage_gated_frontier.py`
- `results/raw_stage_gated_frontier.csv`
- `results/summary_stage_gated_frontier.csv`
- `results/analysis_stage_gated_frontier.md`
- `results/manifest_stage_gated_frontier.json`
- `paper_latex/tables/stage_gated_frontier.tex`

核心结果：

| 设置 | 对比 | 项集/函数数 | score 胜/负/平 | 平均 score 变化 | 平均 staged time 变化 | depth-4 触发 |
|---|---|---:|---:|---:|---:|---:|
| validation | staged frontier vs all-depth | 72 | 0/2/70 | +0.03% | -11.71% | 52/72 |
| independent seed n=24/28/32/40 | staged frontier vs all-depth | 96 | 0/4/92 | +0.04% | -25.43% | 52/96 |
| independent seed n=24/28/32/40 | staged frontier vs fixed depth-2 | 96 | 58/0/38 | -2.40% | +893.25% | 52/96 |
| independent seed n=24/28/32/40 | staged frontier vs large policy | 96 | 5/3/88 | -0.06% | +101.10% | 52/96 |
| n=23 bridge | staged frontier vs all-depth | 6 | 0/0/6 | +0.00% | -11.51% | 5/6 |
| n=23 bridge | staged frontier vs fixed depth-2 | 6 | 5/0/1 | -2.47% | +1322.09% | 5/6 |
| n=23 bridge | staged frontier vs large policy | 6 | 1/0/5 | -0.12% | +94.20% | 5/6 |

验证边界：

- independent scale 的 staged 选择行全部来自已通过 plan 与 emitted-circuit ANF 符号验证的 960 行；`raw_stage_gated_frontier.csv` 中 96/96 selected scale rows verified。
- n=23 bridge 的 staged 选择行全部来自已通过完整 truth-table oracle、ANF plan 和 emitted-circuit 符号验证的 60 行；6/6 selected rows verified。
- staged time 是基于已测得的 depth-2/3/4 单深度规划时间求和得到的可部署模拟时间；当前脚本是离线重组分析，不是单独重跑一个会提前停止的 planner。

结论：stage-gated frontier 不是替代 large/cost neural policy 的新 SOTA 点，而是一个接近 all-depth oracle 的高质量 teacher/guard。它在独立 scale 上把 all-depth 的 score gap 控制在 +0.04%，同时少 25.43% staged time；在 n=23 完整验证桥上与 all-depth score 持平。这可以增强论文中“搜索预算可控、质量-时间前沿可校准”的论点，也可以作为后续训练神经 policy 的 teacher，但不能写成比 large policy 同时更快更优。

### 2.5.8 n=21/22 完整 truth-table bridge

为回应“n>20 只有项集级符号验证”的审稿风险，本轮新增 `run_truth_bridge_terms.py`，在 n=21/22 上构造完整 truth table，并对 emitted X/CNOT/MCT oracle circuit 做 bit-parallel truth-table verification。该实验规模故意小于 n=20--40 scale，因为 truth-table 构造是主成本，但它把完整验证边界向 n>20 后移。

主要产物：

- `run_truth_bridge_terms.py`
- `results/raw_truth_bridge_terms.csv`
- `results/summary_truth_bridge_terms.csv`
- `results/analysis_truth_bridge_terms.md`
- `paper_latex/tables/truth_bridge_terms.tex`

核心结果：

| 验证项或比较 | 结果 | 说明 |
|---|---:|---|
| 完整 truth-table oracle 验证 | 120/120 | 所有 emitted circuit 逐点验证通过 |
| ANF plan 符号验证 | 120/120 | 0 plan mismatch |
| emitted-circuit ANF 符号验证 | 120/120 | 0 circuit mismatch，max wire terms 215 |
| 平均 truth-table 构造时间 | 30.34 s/function | n=21/22 合计 12 个函数 |
| screen depth-4 vs fixed depth-2 | 10/0/2 | 平均 score -3.81%，plan time +734.91% |
| depth-frontier policy vs fixed depth-2 | 8/0/4 | 平均 score -3.50%，plan time +634.71% |
| depth-frontier policy vs depth-4 | 0/2/10 | 平均 score +0.32%，plan time -15.54% |
| depth-frontier policy vs all-depth | 0/2/10 | 平均 score +0.32%，plan time -50.87% |
| adaptive all-depth vs single screen | 11/0/1 | 平均 score -10.19% |

结论：这是验证边界上的实质推进。n=21/22 bridge 不能替代 n=24--40 的完整 truth-table simulation，但它证明本项目的 emitted-circuit 生成与符号验证不是孤立的资源估算；同一类方法在 n>20 的完整枚举切片上也通过了逐点 oracle 验证。

### 2.5.9 逻辑层 schedule proxy：补充 T-depth 与辅助线生命周期证据

为回应“只报告 T-count/CNOT/peak ancilla 仍偏逻辑资源静态统计”的审稿风险，本轮新增 emitted-circuit schedule proxy。它不做硬件 mapping，不引入连通性、routing 或噪声模型；只在生成的 X/CNOT/MCT oracle circuit 上计算并行逻辑深度、CNOT-depth proxy、T-depth proxy、显式辅助线 live peak 和显式辅助线 lifetime area。这使论文能讨论后端相关的逻辑层时序/生命周期 trade-off，而不越界声称真实设备优势。

主要产物：

- `analyze_schedule_metrics.py`
- `results/raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv`
- `results/summary_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv`
- `results/analysis_screen_scale_schedule_depth_frontier_policy_generalization_terms.md`
- `results/raw_schedule_truth_bridge_terms.csv`
- `results/summary_schedule_truth_bridge_terms.csv`
- `results/analysis_schedule_truth_bridge_terms.md`
- `results/raw_schedule_truth_bridge_n23_terms.csv`
- `results/summary_schedule_truth_bridge_n23_terms.csv`
- `results/analysis_schedule_truth_bridge_n23_terms.md`
- `results/summary_schedule_metrics.csv`
- `results/analysis_schedule_metrics.md`
- `paper_latex/tables/schedule_truth_bridge_n23_terms.tex`
- `paper_latex/tables/schedule_metrics.tex`

核心结果：

| 设置 | 对比 | 项数/方法行 | score 胜/负/平 | T-depth proxy 胜/负/平 | lifetime area 变化 |
|---|---|---:|---:|---:|---:|
| schedule generalization n=24/28/32/40 | frontier policy vs fixed depth-2 | 96 | 40/0/56，-1.85% | 40/0/56，-1.85% | +20.09% |
| schedule generalization n=24/28/32/40 | frontier policy vs depth-4 | 96 | 0/19/77，+0.61% | 0/19/77，+0.55% | -5.42% |
| schedule generalization n=24/28/32/40 | frontier policy vs all-depth | 96 | 0/19/77，+0.61% | 0/19/77，+0.55% | -5.42% |
| schedule truth bridge n=21/22 | frontier policy vs fixed depth-2 | 12 函数/120 方法行 | 8/0/4，-3.50% | 8/0/4，-3.32% | +32.93% |
| schedule truth bridge n=21/22 | frontier policy vs depth-4 | 12 函数/120 方法行 | 0/2/10，+0.32% | 0/2/10，+0.32% | -4.01% |
| schedule truth bridge n=21/22 | 完整 truth-table 验证 | 120 方法行 | 120/120 通过 | 120/120 plan/circuit 验证通过 | 0 mismatch |
| schedule truth bridge n=23 | frontier policy vs fixed depth-2 | 6 函数/60 方法行 | 4/0/2，-1.88% | 4/0/2，-1.69% | +29.49% |
| schedule truth bridge n=23 | frontier policy vs depth-4 | 6 函数/60 方法行 | 0/1/5，+0.61% | 0/1/5，+0.52% | -5.09% |
| schedule truth bridge n=23 | 完整 truth-table 验证 | 60 方法行 | 60/60 通过 | 60/60 plan/circuit 验证通过 | 0 mismatch |

解释：这个结果让 frontier policy 的定位更清楚。相对 fixed depth-2，它不仅降低 score，也同步降低 T-depth proxy；代价是显式辅助线生命周期面积增加，说明更深结构会延长部分辅助线占用。相对 depth-4/all-depth，它牺牲约 0.32%--0.55% 的 T-depth proxy，在 n=23 上牺牲 0.52%，却减少约 4%--5% 的显式辅助线 lifetime area，并显著节省搜索时间。论文中应把它写成“逻辑层后端相关 proxy 下的质量-生命周期 trade-off”，而不是写成硬件后端映射结论。

### 2.5.10 n=23 完整 truth-table bridge

本轮把完整 truth-table bridge 从 n=21/22 继续推进到 n=23。该实验仍只覆盖小样本，因为完整 truth-table 构造是主成本；但它把“项集级符号验证是否可信”的验证边界向更高维推进了一步。

运行命令：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_truth_bridge_terms.py --seed 20260713 --ns 23 --per-n 6 --workers 2 --max-screen-depth 4 --tag schedule_truth_bridge_n23
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_schedule_metrics.py --input schedule_generalization=results/raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv --input schedule_truth_bridge=results/raw_schedule_truth_bridge_terms.csv --input schedule_truth_bridge_n23=results/raw_schedule_truth_bridge_n23_terms.csv --summary results/summary_schedule_metrics.csv --out results/analysis_schedule_metrics.md --latex-out paper_latex/tables/schedule_metrics.tex
```

主要产物：

- `results/raw_schedule_truth_bridge_n23_terms.csv`
- `results/summary_schedule_truth_bridge_n23_terms.csv`
- `results/analysis_schedule_truth_bridge_n23_terms.md`
- `paper_latex/tables/schedule_truth_bridge_n23_terms.tex`

核心审计：

| 验证项或比较 | 结果 | 说明 |
|---|---:|---|
| n=23 完整 truth-table oracle 验证 | 60/60 | 6 个函数、10 个方法，所有 emitted circuit 逐点验证通过 |
| n=23 ANF plan 符号验证 | 60/60 | 0 plan mismatch |
| n=23 emitted-circuit ANF 符号验证 | 60/60 | 0 circuit mismatch |
| 平均 truth-table 构造时间 | 209.54 s/function | 总运行时间 665.54 s，2 workers |
| depth-frontier policy vs fixed depth-2 | 4/0/2 | score -1.88%，T-depth proxy -1.69%，lifetime area +29.49% |
| depth-frontier policy vs depth-4 | 0/1/5 | score +0.61%，T-depth proxy +0.52%，lifetime area -5.09% |
| depth-frontier policy vs all-depth | 0/1/5 | score +0.61%，plan time -48.77% |

结论：n=21/22/23 bridge 合计达到 18 个函数、180 个方法行的完整 truth-table oracle 验证、plan 验证和 emitted-circuit 符号验证。它仍不能替代 n=24--40 的完整枚举，但比 v16 更有力地证明了项集级符号验证与最终 oracle circuit 逐点语义之间的一致性。

### 2.6 高维 root-action teacher 诊断

新增 `analyze_highdim_root_action_oracle.py`，用于回答一个更具体的问题：高维 CNOT-only linear-pair 根层动作排序是否还有可学习空间。该脚本不追求全局最优，而是在 `highdim_neural_prior` 的 12 个 `n=14` random ANF 函数上，用真实 greedy child plan 对更宽的 root-action 集合做 one-step teacher 评分。

主要产物：

- `results/raw_highdim_root_action_oracle.csv`
- `results/summary_highdim_root_action_oracle.csv`
- `results/analysis_highdim_root_action_oracle.md`
- `paper_latex/tables/highdim_root_action_oracle.tex`

核心结果：

| 对比 | score 胜/负/平 | 平均 score 变化 | 解释 |
|---|---:|---:|---|
| oracle top-12 vs heuristic top-4 | 3/0/7 | -0.18% | 更宽动作集合有小幅 headroom |
| oracle top-24 vs heuristic top-4 | 3/0/7 | -0.18% | top-12 已覆盖该切片的额外收益 |
| oracle top-24 vs heuristic top-1 | 7/0/3 | -0.43% | 单一启发式 top-1 会丢失多个更好 root action |
| neural top-4 vs heuristic top-4 | 1/1/8 | +0.06% | 现有 immediate-label 高维模型没有利用 teacher signal |

解释：

- 这个结果不是新的最终综合最优结果，而是给高维 neural guidance 提供监督目标。
- 它说明高维 root-action 排序有真实但幅度较小的可学习空间；当前 immediate-gain 训练的 `linear_action_scorer_highdim.pt` 还没有学到这个 one-step teacher。
- 后续如果继续补强 AI 贡献，应优先训练 root-action ranker 去逼近 oracle top-12/top-24，而不是继续简单叠加现有 neural prior。

### 2.6.1 Pairwise-wide root-action ranker 与 n=16 full synthesis

本轮在 pairwise root-action ranker 基础上继续补了一层保守候选扩展：不再让神经排序替换启发式 top-4，而是保留 heuristic top-4，并额外加入 neural top-8 的 root action。这个策略对应代码中的 `fprm_linear_pair_deep_root_neural_wide` 和 `fprm_linear_pair_deep_ai_guard_wide`。它的意义是把神经模型写成“候选扩展器”，而不是高维递归搜索的单点决策器。

新增/更新产物：

- `analyze_paired_method_comparison.py`
- `results/raw_highdim_root_action_pairwise_widths.csv`
- `results/analysis_highdim_root_action_pairwise_widths.md`
- `results/raw_ultra_root_action_pairwise_widths.csv`
- `results/analysis_ultra_root_action_pairwise_widths.md`
- `results/raw_highdim_neural_prior_pairwise_wide.csv`
- `results/analysis_neural_prior_highdim_pairwise_wide_ablation.md`
- `results/raw_ultra_highdim_resource_pairwise_wide_resource.csv`
- `results/analysis_ultra_pairwise_wide_vs_recursive.md`
- `results/analysis_ultra_pairwise_wide_vs_old_resource.md`

关键结果：

| 对比 | 函数集 | score 胜/负/平 | 平均 score 变化 | 解释 |
|---|---|---:|---:|---|
| heuristic top-4 + neural top-8 vs heuristic top-4 | 10 个有 linear action 的 n=14 random ANF | 2/0/8 | -0.14% | 接近 oracle top-24 的 3/0/7、-0.18% headroom |
| highdim pairwise-wide learned prior vs no-prior | 12 个 n=14 random ANF | 2/0/10 | -0.05% | 比原 pairwise top-4 的 -0.04% 略好，但运行时间 +179.59% |
| heuristic top-4 + neural top-8 vs heuristic top-4 | 23 个有 linear action 的 n=16 random ANF | 5/0/18 | -0.06% | 修复旧 neural top-4 的负迁移；旧 neural top-4 为 4/2/17、+0.05% |
| pairwise-wide Resource-NMCTS vs deterministic recursive guard | 24 个 n=16 random ANF | 10/0/14 | -0.18% | full synthesis 层面的无 score-loss AI 增益 |
| pairwise-wide Resource-NMCTS vs old Resource-NMCTS root-teacher | 24 个 n=16 random ANF | 10/0/14 | -0.12% | 新 ranker 与 wide union 明确优于旧 root-teacher 结果 |

解释：这是当前高维 AI 贡献中最可信的一组正向证据。它仍不是“大幅提升”：n=16 平均 score 降幅为 0.18%，且运行时间相对 deterministic recursive guard 增加约 274.75%。但它已经把之前“高维 neural top-4 会负迁移”的问题改成了 full synthesis 层面的无 score-loss 正向结果，适合作为下一版论文中 AI 模块的核心消融之一。

### 2.6.2 Boolean-ring linear factor 与 n=16 结构性提升

pairwise-wide 主要改善“根动作排序”，但 headroom 只有 0.1%--0.2%。本轮把高维结构分支从普通 square-free ANF 乘法推广到 Boolean 环规则：允许 quotient monomial 与 linear factor 共享变量，并在展开时使用 `x_i^2=x_i` 和 GF(2) 偶数项消去。这样可以捕获形如 `(x_i xor x_j) * x_i m = x_i m xor x_i x_j m` 的重叠变量因子；旧 `linear_pair` 要求 quotient 与 factor 变量不相交，会漏掉这类结构。

新增/更新产物：

- `results/raw_highdim_neural_prior_boolean_guard.csv`
- `results/analysis_highdim_boolean_guard_vs_pairwise_wide.md`
- `results/analysis_highdim_boolean_guard_vs_no_prior.md`
- `results/raw_ultra_boolean_linear_pair_deep.csv`
- `results/analysis_ultra_boolean_linear_vs_deep.md`
- `results/analysis_ultra_boolean_linear_vs_pairwise_resource.md`
- `results/raw_ultra_highdim_resource_boolean_guard.csv`
- `results/analysis_ultra_boolean_guard_vs_pairwise_wide.md`
- `results/analysis_ultra_boolean_guard_vs_old_deep.md`
- `results/raw_mega_boolean_linear_screen.csv`
- `results/analysis_mega_boolean_screen_vs_resource.md`
- `models/boolean_linear_action_scorer_root_teacher.pt`
- `results/raw_boolean_neural_highdim.csv`
- `results/analysis_boolean_neural_guard_vs_deterministic.md`
- `results/raw_giga_boolean_neural_resource.csv`
- `results/analysis_giga_resource_vs_boolean_screen.md`
- `results/analysis_giga_resource_vs_and_direct.md`
- `results/raw_mega_boolean_screen_deep.csv`
- `results/analysis_mega_screen_deep_vs_screen.md`
- `results/raw_giga_boolean_screen_deep.csv`
- `results/analysis_giga_screen_deep_vs_screen.md`
- `results/raw_giga_recursive_screen_resource.csv`
- `results/analysis_giga_resource_recursive_screen_vs_old.md`
- `results/raw_giga_boolean_screen_deeper.csv`
- `results/analysis_giga_screen_deeper_vs_deep.md`
- `results/raw_giga_deeper_screen_resource.csv`
- `results/analysis_giga_resource_deeper_vs_old_resource.md`

关键结果：

| 对比 | 函数集 | score 胜/负/平 | 平均 score 变化 | 解释 |
|---|---|---:|---:|---|
| Boolean-guard Resource-NMCTS vs pairwise-wide Resource-NMCTS | 12 个 n=14 random ANF | 9/0/3 | -0.82% | 高维 learned-prior 切片从 0.05% 量级提升到接近 1% |
| Boolean-guard Resource-NMCTS vs no-prior Resource-NMCTS | 12 个 n=14 random ANF | 9/0/3 | -0.86% | 同时降低 T、CNOT 和 depth；时间代价约 +247.75% |
| Boolean-linear-deep vs deterministic recursive guard | 24 个 n=16 random ANF | 17/3/4 | -0.39% | 单独结构分支已经优于旧 recursive linear-pair guard |
| Boolean-linear-deep vs pairwise-wide Resource-NMCTS | 24 个 n=16 random ANF | 14/6/4 | -0.22% | 单分支质量优于上一轮完整 Resource，且平均时间低 72.31% |
| Boolean-guard Resource-NMCTS vs pairwise-wide Resource-NMCTS | 24 个 n=16 random ANF | 14/0/10 | -0.34% | 组合主方法无 score-loss 改善，T/CNOT/depth 同时下降 |
| Boolean-guard Resource-NMCTS vs deterministic recursive guard | 24 个 n=16 random ANF | 18/0/6 | -0.52% | 当前最强 n=16 full synthesis 证据 |
| Boolean-linear neural guard vs deterministic Boolean-linear | 24 个 n=16 random ANF | 4/0/20 | -0.12% | 新 boolean-linear root-teacher 模型只有小幅无 loss 收益，平均时间 +94.49%，仍不是主提升来源 |
| Boolean-linear screen vs old Resource-NMCTS | 12 个 n=18 random ANF | 0/12/0 | +42.45% | ANF-only screen 很快但质量差，只能作为 n=18/n=20 边界诊断 |
| Adaptive depth-2 Boolean screen vs single Boolean screen | 12 个 n=18 random ANF | 11/0/1 | -6.47% | adaptive screen 改善单层 screen，但完整 Resource 仍进一步降低 23.85% |
| Recursive-screen Resource-NMCTS vs old Resource-NMCTS | 6 个 n=20 random ANF | 5/0/1 | -4.52% | root-beam/fast pair timeout 时的超高维有效修复 |
| Deeper-screen Resource-NMCTS vs old Resource-NMCTS | 6 个 n=20 random ANF | 5/0/1 | -7.47% | depth-2 screen 在同一 timeout 边界上进一步降低 T/CNOT/depth/score |

解释：Boolean-ring linear-deep 是 n=16 上最重要的实际提升。它不是单纯扩大 beam 或神经 top-k，而是扩大了可表示的代数因子类型；因此相对 pairwise-wide neural guard 更像“方法创新”。本轮新训练的 Boolean-linear action scorer 能在 guard 下避免 score loss，但 4/0/20、-0.12% 的幅度仍不足以作为显著 AI 贡献。必须区分 deep 版本和 screen 版本：deep 版本在 n=14/n=16 有稳定质量收益；recursive screen 在 n=20 这种 FPRM 分支全部 timeout 的边界上有效，depth-2 screen 还能把旧 Resource 的 score 降幅扩大到 -7.47%，但在 n=18 仍远差于旧 Resource，不应泛化为中高维主质量方法。

### 2.7 小规模 exact FPRM-DP 精确切片

本轮新增 `analyze_exact_fprm_dp.py`，用于补上一个小规模、同模型内部精确证据链。它对 bounded fixed-polarity FPRM factor model 做动态规划，枚举所有单项式 factor action 和 CNOT-only linear-pair factor action，并对所有 FPRM polarity 求最优。这个 exact 只限定在该受限 FPRM 因子模型内，不是全局 reversible circuit optimum。

主要产物：

- `results/raw_exact_fprm_dp.csv`
- `results/summary_exact_fprm_dp.csv`
- `results/analysis_exact_fprm_dp.md`
- `paper_latex/tables/exact_fprm_dp.tex`

数据范围与审计：

- 覆盖 `traditional_resource` 中全部 `n<=4` 的 72 个函数。
- error：0
- skipped：0
- incorrect：0
- 每条 exact DP 线路均通过 oracle truth-table 验证。

核心结果：

| 对比 | 配对数 | score 胜/负/平 | 平均 score 变化 |
|---|---:|---:|---:|
| Resource-NMCTS vs Exact FPRM-DP | 72 | 51/3/18 | -12.18% |
| Pareto-Resource-NMCTS vs Exact FPRM-DP | 72 | 51/0/21 | -12.20% |
| Exact FPRM-DP vs ESOP-MILP | 72 | 57/12/3 | -13.30% |
| Exact FPRM-DP vs SSHR-I CNOT | 72 | 60/12/0 | -13.73% |
| Exact FPRM-DP vs SSHR-I T | 72 | 59/12/1 | -13.38% |

解释：

- 如果 Resource/Pareto 能击败 Exact FPRM-DP，说明 portfolio 找到了这个受限 FPRM-DP 模型之外的候选线路，而不是 exact solver 失败。
- Exact FPRM-DP 自身比 ESOP-MILP 和 exact SSHR-I 的加权 score 更好，但相对 SSHR-I 的 CNOT 通常更高；因此它进一步支持低 T / 低加权资源主张，不支持 CNOT-only 最优主张。
- 这一切片把“公平性”从 time-limited external baseline 往前推进了一步：至少在 `n<=4` 的 bounded FPRM factor family 内，可以给出 exact optimum 参照。

### 2.8 小规模 exact XAG 乘法复杂度下界

本轮新增 `analyze_exact_xag_mc.py`，用于补上比 bounded FPRM-DP 更硬的 T-count 参照。该脚本在 XOR-AND graph 模型中对 `n<=4` 的目标布尔函数做 exact breadth-first search，求最少 AND 节点数。由于 logical-AND 资源模型中每个 AND 至少需要 4 个 T gate，因此 `4 * min AND` 是全局逻辑层 T-count 下界。它不是 CNOT、depth 或完整可逆线路最优。

主要产物：

- `results/raw_exact_xag_mc.csv`
- `results/summary_exact_xag_mc.csv`
- `results/analysis_exact_xag_mc.md`
- `paper_latex/tables/exact_xag_mc.tex`

数据范围与审计：

- 覆盖 `traditional_resource` 中全部 `n<=4` 的 72 个函数。
- solved：72/72
- unknown/error：0
- 最重函数访问 66541 个 exact BFS 状态，说明该切片当前是可复现的全局小规模下界，而不是采样估计。

核心结果：

| 方法 | 配对数 | 达到 T 下界 | 高于下界 | 平均 T gap |
|---|---:|---:|---:|---:|
| Resource-NMCTS | 72 | 12 | 60 | +53.01% |
| Pareto-Resource-NMCTS | 72 | 12 | 60 | +53.01% |
| ESOP-MILP | 72 | 3 | 69 | +120.14% |
| SSHR-I-T | 72 | 5 | 67 | +143.06% |

解释：

- 没有任何方法低于 exact XAG T 下界，说明当前 T-count 口径与下界一致。
- Resource/Pareto 在 12/72 个函数上达到全局 XAG 乘法复杂度 T 下界，且平均 T gap 明显低于 ESOP-MILP 和 T-optimized SSHR-I。
- 这个证据只能支撑低 T-count 接近全局乘法复杂度下界，不能支撑 CNOT/depth 全局最优。

### 2.9 高维 root teacher 与 wide guard 负向诊断

本轮进一步把 2.6 的 teacher signal 实际用于训练 `models/linear_action_scorer_root_teacher.pt`，并新增 `highdim_guard_upgrade` preset 测试宽根层 deterministic guard。

主要产物：

- `models/linear_action_scorer_root_teacher.pt`
- `results/raw_highdim_root_action_teacher.csv`
- `results/summary_highdim_root_action_teacher.csv`
- `results/analysis_highdim_root_action_teacher.md`
- `results/raw_highdim_guard_upgrade.csv`
- `results/summary_highdim_guard_upgrade.csv`
- `results/analysis_highdim_guard_upgrade.md`

核心结论：

- root-teacher 模型训练 2287 个样本，valid loss 为 0.2778；但在同一 root-action 诊断上，`root_neural_top4` 相对 heuristic top-4 为 2/3/5，平均 score 变化 +0.16%，没有形成可用提升。
- `and_resource_nmcts_wide` 在 12 个 `n=14` random ANF 函数上相对 `and_resource_nmcts` 为 0/0/12，资源完全持平，但平均运行时间增加 59.80%。
- 因此，本轮不能把高维 root-teacher 或 wide-fast 写成主贡献；它们应作为负向诊断，说明当前高维 AI 排序仍未突破，后续需要更强的策略梯度、pairwise ranking 或更丰富特征。

### 2.10 多资源权重鲁棒性与中文 PDF 交付

本轮新增 `analyze_weight_robustness.py`，用于回答一个直接的审稿风险：当前 score 结论是否只是某一组权重系数制造出来的。该脚本不重新综合线路，而是对已经通过验证的 raw CSV 行做 post-hoc rescoring，比较 Paper score、T-only、T-heavy、CNOT-depth 和 Ancilla-tight 五种逻辑资源权重。

主要产物：

- `results/summary_weight_robustness.csv`
- `results/analysis_weight_robustness.md`
- `paper_latex/tables/weight_robustness_compact.tex`
- `paper_latex_zh/resource_nmcts_zh_robustness.tex`
- `paper_latex_zh/resource_nmcts_zh_robustness.pdf`
- `paper_latex_zh/resource_nmcts_zh_stage_delivery.tex`
- `paper_latex_zh/resource_nmcts_zh_stage_delivery.pdf`

核心结果：

| 对比 | Paper score | T-only | CNOT-depth | Ancilla-tight |
|---|---:|---:|---:|---:|
| Pareto vs ESOP cube beam, n<=6 | 174/0/3，-36.09% | 174/0/3，-38.95% | 174/0/3，-32.08% | 174/0/3，-32.75% |
| Pareto vs ESOP-MILP, n<=6 | 167/3/7，-29.84% | 166/0/11，-32.77% | 165/4/8，-25.44% | 167/3/7，-26.68% |
| Pareto vs SSHR-H, n<=6 | 173/4/0，-41.06% | 173/0/4，-47.93% | 168/9/0，-27.87% | 172/5/0，-31.95% |
| Resource vs root beam, n=16 | 23/0/1，-4.36% | 23/0/1，-4.70% | 23/0/1，-4.28% | 23/0/1，-3.43% |
| Resource vs root beam, n=18 | 12/0/0，-5.29% | 12/0/0，-6.19% | 12/0/0，-4.54% | 11/1/0，-3.33% |
| Resource vs fast linear-pair, n=18 | 12/0/0，-3.55% | 12/0/0，-3.75% | 12/0/0，-3.23% | 12/0/0，-3.33% |

解释：

- 主要结论在 T-only、CNOT-depth 和 Ancilla-tight 等替代权重下仍成立，说明当前结果不是单一 score 权重偶然造成的。
- CNOT-depth profile 下相对 SSHR-H 的优势收窄到 -27.87%，这反而强化了论文边界：SSHR 的 CNOT-oriented 优势必须如实承认，本文只主张低 T 和低加权资源。
- 新中文 PDF `resource_nmcts_zh_robustness.pdf` 是独立投稿论证稿，重点写清楚“方法不依赖 SSHR、AI/MCTS 贡献如何被消融支持、权重鲁棒性如何降低审稿风险”。

### 2.11 外部工具链 readiness 与文献边界审计

本轮新增 `analyze_toolchain_readiness.py`，把“还缺 ROS/mockturtle/RevKit 复现实验”从文字判断变成可复现环境审计。

主要产物：

- `results/analysis_toolchain_readiness.md`
- `results/raw_screen_scale_extended_terms.csv`
- `results/summary_screen_scale_extended_terms.csv`
- `results/analysis_screen_scale_extended_terms.md`
- `results/raw_screen_scale_depth_frontier_terms.csv`
- `results/summary_screen_scale_depth_frontier_terms.csv`
- `results/analysis_screen_scale_depth_frontier_terms.md`
- `literature_notes.md` 中新增 back-end-aware oracle synthesis、mockturtle、RevKit 定位说明。

当前环境审计结果：

| 工具 | 当前状态 | 作用 |
|---|---|---|
| ABC | 可用，位于 `tmp/abc/abc` | 已支撑 AIG/XAG/LUT/ESOP 外部估算 baseline |
| mockturtle | 源码与项目 KLUT-to-XAG adapter 可用 | 已支撑 official-header mockturtle XAG probe |
| CirKit 3 shell | 可用，位于 `tmp/cirkit/build/cli/cirkit` | 已支撑 AIG/MC 外部 probe |
| RevKit Python API | 可用 | 已支撑 `oracle_synth` phase-netlist baseline |
| legacy RevKit CLI | 可用，位于 `tmp/cirkit_legacy/build/programs/revkit` | 已支撑 exact-oracle TBS/DBS/RMS reversible-synthesis portfolio |

解释：

- 这不是新的资源提升结果，但它降低了投稿准备中的不确定性：当前能诚实声称的是 ABC/BDD/ESOP/SSHR、mockturtle KLUT-to-XAG、CirKit AIG/MC、RevKit Python API 和 legacy RevKit CLI exact-oracle probe；仍不能声称已经完成官方 ROS 或硬件 mapping。
- 文献上，back-end-aware fault-tolerant oracle synthesis 已经把 XAG oracle synthesis 扩展到后端感知指标；本文目前只做逻辑层，因此不能借用其 mapping/back-end 结论。
- 本轮还临时探测了两个潜在算法升级方向：高维 affine-linear factor 和局部 polarity 下降。前者在前几个 `n=14` 函数上更慢且 score 更差，后者在高项数函数上选回 polarity 0 且 fast linear-pair 结果更差；因此暂不纳入方法贡献。

### 2.12 ROS-style LUT proxy：资源约束 LUT 路线压力测试

本轮新增 `run_ros_lut_proxy.py`，用于弥补“只有固定 K=4 ABC-LUT baseline，不足以代表 LUT 路线”的缺口。它不是官方 ROS、RevKit 或 mockturtle 复现，而是一个明确标注的外部 proxy：从同一导出 BLIF benchmark 出发，调用 ABC `if -K` 对 `K=3,4,5` 做 sweep；每个映射后 BLIF 都经过 truth-table 检查，再把 LUT 网络估算成 local-ANF compute/action/uncompute 资源，并按当前 score 选择 best-K。

主要产物：

- `run_ros_lut_proxy.py`
- `results/raw_ros_lut_proxy_sweep.csv`
- `results/raw_ros_lut_proxy_best.csv`
- `results/summary_ros_lut_proxy.csv`
- `results/analysis_ros_lut_proxy.md`
- `results/manifest_ros_lut_proxy.json`
- `paper_latex/tables/ros_lut_proxy.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v18.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v18.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v19.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v19.pdf`

覆盖范围与正确性：

- 函数集：`n=3..6` 传统函数 177 个，加上 `n=14,15,16,18` 高维导出函数 132 个，共 309 个函数。
- K-sweep 行：927 行。
- Best-K 行：309 行。
- truth-table 检查：927/927 通过；无 timeout、error、skipped 或 incorrect 行。

关键结果：

| 对比 | 指标 | 函数数 | 胜/负/平 | 平均相对变化 |
|---|---|---:|---:|---:|
| Resource-NMCTS vs ROS-style LUT proxy | score | 309 | 309/0/0 | -83.77% |
| Profile-Resource-NMCTS vs ROS-style LUT proxy | score | 132 | 132/0/0 | -97.38% |
| Pareto-Resource-NMCTS vs ROS-style LUT proxy | score | 309 | 309/0/0 | -84.27% |
| AND-direct ANF vs ROS-style LUT proxy | score | 309 | 307/2/0 | -67.45% |
| ROS-style LUT proxy vs fixed K=4 LUT | score | 309 | 219/0/90 | -18.12% |

解释：

- Best-K proxy 相比固定 K=4 ABC-LUT 自身有明显提升，因此它是更强的 LUT 压力测试，而不是重复已有 fixed-K 结果。
- Resource/Pareto/Profile 仍然全胜该 proxy，说明当前低加权资源优势不只依赖于一个较弱的固定 LUT 参数。
- 这仍不能写成“已复现 ROS”。官方 ROS 的 LUT decomposition、垃圾管理和 reversible-toolchain 细节没有被实现；本文只能把它写成“ROS-style LUT proxy 外部对比”。

### 2.12.1 ROS-style LUT line-sensitivity：辅助线压力下的稳健性

本轮新增 `analyze_ros_lut_line_sensitivity.py`，复用已经 truth-table 验证通过的 ABC LUT sweep，不重新运行 ABC，而是在同一批 `K=3,4,5` 行上按更严格的辅助线压力重新选择 LUT 结果。它仍然不是官方 ROS：没有 SAT garbage management，也没有 reversible-toolchain 或硬件 mapping；作用是检查“Resource-NMCTS 胜过 LUT proxy”是否依赖 best-score 的 K 选择。

主要产物：

- `analyze_ros_lut_line_sensitivity.py`
- `results/raw_ros_lut_line_sensitivity.csv`
- `results/summary_ros_lut_line_sensitivity.csv`
- `results/analysis_ros_lut_line_sensitivity.md`
- `results/manifest_ros_lut_line_sensitivity.json`
- `paper_latex/tables/ros_lut_line_sensitivity.tex`

关键结果：

| 对比 | 指标 | 函数数 | 胜/负/平 | 平均相对变化 |
|---|---|---:|---:|---:|
| Pareto-Resource-NMCTS vs min-ancilla LUT selector | score | 309 | 309/0/0 | -85.83% |
| Pareto-Resource-NMCTS vs min-ancilla LUT selector | peak ancilla | 309 | 301/0/8 | -68.21% |
| Pareto-Resource-NMCTS vs line-weighted LUT selector, w=10 | score | 309 | 309/0/0 | -84.45% |
| Pareto-Resource-NMCTS vs K4 line-cap LUT selector | score | 309 | 309/0/0 | -85.02% |
| min-ancilla LUT selector vs best-score LUT proxy | peak ancilla | 309 | 197/0/112 | -32.47% |
| min-ancilla LUT selector vs best-score LUT proxy | score | 309 | 0/197/112 | +40.67% |

解释：

- min-ancilla 选择器确实把 LUT proxy 的平均 peak ancilla 从 best-score 选择进一步压低，但代价是自身 score 明显变差。
- Resource/Pareto 对 line-aware 和 min-ancilla 选择仍保持 309/0/0 score 胜出，因此 LUT proxy 的结论对 K 选择和辅助线压力是稳健的。
- 该结果应写成“ROS-style LUT proxy sensitivity”，不能写成“官方 ROS 已被复现”。

## 3. 当前文件交付清单

### 3.1 核心代码

- `factor_plan.py`：FPRM/线性因子/beam/greedy 计划生成。
- `synthesizers.py`：方法组合、Resource/Profile/Pareto 候选选择。
- `run_experiments.py`：实验运行、隔离超时、resume/replace 逻辑。
- `train_neural_policy.py`：普通 factor-action 与高维 linear-action 神经先验训练。
- `analyze_results.py`：内部实验分析。
- `analyze_runtime.py`：运行时间和资源表生成。
- `analyze_external_baselines.py`：外部 baseline 对比分析。
- `analyze_esop_baseline.py`：新增 ESOP 专项分析。
- `analyze_search_contribution.py`：新增搜索贡献分解分析。
- `analyze_weight_robustness.py`：新增多资源 score 权重鲁棒性分析。
- `analyze_exact_fprm_dp.py`：新增小规模 bounded FPRM-DP 精确切片。
- `analyze_exact_xag_mc.py`：新增小规模 exact XAG 乘法复杂度 T 下界。
- `analyze_highdim_root_action_oracle.py`：新增高维 root-action teacher 诊断。
- `analyze_toolchain_readiness.py`：新增外部工具链 readiness 审计。
- `run_ros_lut_proxy.py`：新增 ROS-style LUT proxy 外部基线。
- `analyze_ros_lut_line_sensitivity.py`：新增 ROS-style LUT proxy 辅助线压力敏感性分析。

### 3.2 结果文件

- `results/raw_traditional_resource.csv`
- `results/raw_external_traditional_resource_n6.csv`
- `results/analysis_esop_baseline.md`
- `results/summary_esop_baseline.csv`
- `results/raw_mega_highdim_resource.csv`
- `results/analysis_mega_highdim_resource.md`
- `results/runtime_mega_highdim_resource.md`
- `results/raw_giga_highdim_resource.csv`
- `results/summary_giga_highdim_resource.csv`
- `results/analysis_giga_highdim_resource.md`
- `results/runtime_giga_highdim_resource.md`
- `results/analysis_external_mega_highdim_resource.md`
- `results/analysis_search_contribution.md`
- `results/summary_search_contribution.csv`
- `results/analysis_neural_prior_highdim_ablation.md`
- `results/raw_neural_prior_highdim_ablation.csv`
- `results/raw_exact_fprm_dp.csv`
- `results/summary_exact_fprm_dp.csv`
- `results/analysis_exact_fprm_dp.md`
- `results/raw_exact_xag_mc.csv`
- `results/summary_exact_xag_mc.csv`
- `results/analysis_exact_xag_mc.md`
- `results/raw_highdim_root_action_oracle.csv`
- `results/summary_highdim_root_action_oracle.csv`
- `results/analysis_highdim_root_action_oracle.md`
- `results/analysis_highdim_root_action_teacher.md`
- `results/analysis_highdim_guard_upgrade.md`
- `results/analysis_toolchain_readiness.md`
- `results/raw_ros_lut_proxy_sweep.csv`
- `results/raw_ros_lut_proxy_best.csv`
- `results/summary_ros_lut_proxy.csv`
- `results/analysis_ros_lut_proxy.md`
- `results/manifest_ros_lut_proxy.json`

### 3.3 论文文件

- `paper_latex/main.tex`
- `paper_latex/main.pdf`
- `paper_latex/tables/esop_baseline_by_n.tex`
- `paper_latex/tables/neural_prior_ablation.tex`
- `paper_latex/tables/search_contribution_decomposition.tex`
- `paper_latex/tables/weight_robustness_compact.tex`
- `paper_latex/tables/neural_prior_highdim_ablation.tex`
- `paper_latex/tables/exact_fprm_dp.tex`
- `paper_latex/tables/exact_xag_mc.tex`
- `paper_latex/tables/highdim_root_action_oracle.tex`
- `paper_latex/tables/resource_search_ablation_highdim.tex`
- `paper_latex/tables/runtime_search_ablation_highdim.tex`
- `paper_latex/tables/external_traditional_resource_n6.tex`
- `paper_latex/tables/resource_mega_highdim_resource.tex`
- `paper_latex/tables/runtime_mega_highdim_resource.tex`
- `paper_latex/tables/resource_giga_highdim_resource.tex`
- `paper_latex/tables/runtime_giga_highdim_resource.tex`
- `paper_latex/tables/ros_lut_proxy.tex`
- `paper_latex_zh/resource_nmcts_zh_report.tex`
- `paper_latex_zh/resource_nmcts_zh_report.pdf`
- `paper_latex_zh/resource_nmcts_zh_robustness.tex`
- `paper_latex_zh/resource_nmcts_zh_robustness.pdf`
- `paper_latex_zh/resource_nmcts_zh_boolean_ring_v3.tex`
- `paper_latex_zh/resource_nmcts_zh_boolean_ring_v3.pdf`
- `paper_latex_zh/resource_nmcts_zh_stage_delivery.tex`
- `paper_latex_zh/resource_nmcts_zh_stage_delivery.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v18.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v18.pdf`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v19.tex`
- `paper_latex_zh/resource_nmcts_zh_manuscript_v19.pdf`

## 4. 复现命令

环境使用：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python <script>.py
```

基础验证：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python tests_smoke.py
```

重新生成 ESOP 分析：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src
/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/analyze_esop_baseline.py
```

重新生成 exact FPRM-DP 精确切片：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_exact_fprm_dp.py --max-n 4
```

重新生成 exact XAG 乘法复杂度下界：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_exact_xag_mc.py --max-n 4
```

重新生成多资源权重鲁棒性分析和中文 PDF：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_weight_robustness.py
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment/paper_latex_zh
latexmk -xelatex -g resource_nmcts_zh_robustness.tex
```

重新生成外部工具链 readiness 审计：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_toolchain_readiness.py
```

重新生成 ROS-style LUT proxy：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_ros_lut_proxy.py --manifest traditional=benchmark_exports/traditional_resource_external_seed42/manifest.json --manifest n14=benchmark_exports/highdim_resource_external_seed42/manifest.json --manifest n15=benchmark_exports/highdim_scale_resource_external_seed42/manifest.json --manifest n16=benchmark_exports/ultra_highdim_resource_external_seed42/manifest.json --manifest n18=benchmark_exports/mega_highdim_resource_external_seed42/manifest.json --internal traditional=results/raw_traditional_resource.csv --internal n14=results/raw_highdim_resource.csv --internal n15=results/raw_highdim_scale_resource.csv --internal n16=results/raw_ultra_highdim_resource.csv --internal n18=results/raw_mega_highdim_resource.csv --ks 3,4,5 --workers 8 --timeout 45 --raw-out results/raw_ros_lut_proxy_sweep.csv --best-out results/raw_ros_lut_proxy_best.csv --summary results/summary_ros_lut_proxy.csv --analysis results/analysis_ros_lut_proxy.md --latex-out paper_latex/tables/ros_lut_proxy.tex --run-manifest results/manifest_ros_lut_proxy.json
```

重新生成 ROS-style LUT line-sensitivity：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src
/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/analyze_ros_lut_line_sensitivity.py --internal resource_nmcts_experiment/results/raw_traditional_resource.csv --internal resource_nmcts_experiment/results/raw_highdim_resource.csv --internal resource_nmcts_experiment/results/raw_highdim_scale_resource.csv --internal resource_nmcts_experiment/results/raw_ultra_highdim_resource.csv --internal resource_nmcts_experiment/results/raw_mega_highdim_resource.csv --ancilla-weights 10,25
```

重新生成搜索贡献分解：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset search_ablation_traditional --model models/action_scorer_rollout_logical_and.pt --workers 10 --checkpoint-every 100 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset search_ablation_traditional
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset search_ablation_highdim --model models/action_scorer_rollout_logical_and.pt --workers 6 --checkpoint-every 16 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset search_ablation_highdim
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_search_contribution.py
```

重新生成 n=32/36/40 extended screen-scale：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --ns 32,36,40 --per-n 48 --workers 6 --tag extended
```

重新生成 depth-3/4 quality-frontier screen-scale：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --ns 20,28,40 --per-n 24 --workers 6 --max-screen-depth 4 --tag depth_frontier
```

重新生成高维 learned-prior 诊断：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset linear_highdim --gate-mode logical_and --label-mode immediate --action-family linear --max-depth 1 --child-branch 1 --out models/linear_action_scorer_highdim.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_neural_prior --model models/linear_action_scorer_highdim.pt --out-dir /tmp/resource_nmcts_highdim_learned_prior --workers 6 --checkpoint-every 6 --isolate-timeouts
cp /tmp/resource_nmcts_highdim_learned_prior/raw_highdim_neural_prior.csv results/raw_highdim_neural_prior_learned_prior.csv
cp /tmp/resource_nmcts_highdim_learned_prior/summary_highdim_neural_prior.csv results/summary_highdim_neural_prior_learned_prior.csv
cp /tmp/resource_nmcts_highdim_learned_prior/manifest_highdim_neural_prior.json results/manifest_highdim_neural_prior_learned_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_neural_prior --model /tmp/nonexistent_model.pt --out-dir /tmp/resource_nmcts_highdim_no_prior --workers 6 --checkpoint-every 6 --isolate-timeouts
cp /tmp/resource_nmcts_highdim_no_prior/raw_highdim_neural_prior.csv results/raw_highdim_neural_prior_no_prior.csv
cp /tmp/resource_nmcts_highdim_no_prior/summary_highdim_neural_prior.csv results/summary_highdim_neural_prior_no_prior.csv
cp /tmp/resource_nmcts_highdim_no_prior/manifest_highdim_neural_prior.json results/manifest_highdim_neural_prior_no_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_neural_prior_ablation.py --learned-csv results/raw_highdim_neural_prior_learned_prior.csv --no-prior-csv results/raw_highdim_neural_prior_no_prior.csv --methods and_resource_nmcts --out-raw results/raw_neural_prior_highdim_ablation.csv --summary results/summary_neural_prior_highdim_ablation.csv --out results/analysis_neural_prior_highdim_ablation.md --latex-out paper_latex/tables/neural_prior_highdim_ablation.tex --dataset-label highdim_neural_prior --model-label models/linear_action_scorer_highdim.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_highdim_root_action_oracle.py
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset linear_root_teacher --seed 31415 --gate-mode logical_and --label-mode root_teacher --action-family linear --max-depth 0 --child-branch 1 --root-teacher-width 24 --rest-direct-limit 450 --hidden 128 --out models/linear_action_scorer_root_teacher.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_highdim_root_action_oracle.py --model models/linear_action_scorer_root_teacher.pt --raw results/raw_highdim_root_action_teacher.csv --summary results/summary_highdim_root_action_teacher.csv --analysis results/analysis_highdim_root_action_teacher.md --latex-out paper_latex/tables/highdim_root_action_teacher.tex
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_guard_upgrade --model /tmp/nonexistent_model.pt --workers 6 --checkpoint-every 6 --isolate-timeouts
```

重新生成 n=18 内部分析：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset mega_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset mega_highdim_resource
```

重新生成 n=18 外部分析：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py \
  --external-csv results/raw_external_mega_highdim_resource.csv \
  --internal-csv results/raw_mega_highdim_resource.csv \
  --targets and_resource_nmcts,and_profile_resource_nmcts,and_pareto_resource_nmcts,and_fprm_linear_pair_fast,and_fprm_root_beam,direct_anf,and_direct_anf \
  --out results/analysis_external_mega_highdim_resource.md
```

编译论文：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment/paper_latex
latexmk -pdf -g main.tex
```

## 5. 当前验证状态

已完成验证：

- `latexmk -pdf -g main.tex` 通过。
- `latexmk -xelatex -g resource_nmcts_zh_manuscript_v19.tex` 通过；生成 13 页中文 PDF。
- `tests_smoke.py` 通过，输出 `smoke ok`。
- `py_compile` 通过。
- `git diff --check` 通过。
- `raw_mega_highdim_resource.csv` 审计：84 行、0 error、0 skipped、0 incorrect。
- `raw_giga_highdim_resource.csv` 审计：48 行、36 usable、12 timeout error、0 skipped；timeout 均来自 `and_fprm_root_beam` 和 `and_fprm_linear_pair_fast`。
- `analysis_search_contribution.md` 审计：无 NaN/空配对。
- `raw_search_ablation_highdim.csv` 审计：128 行、0 error、0 skipped、0 incorrect。
- `raw_neural_prior_highdim_ablation.csv` 审计：24 行、0 error、0 skipped、0 incorrect。
- `raw_exact_fprm_dp.csv` 审计：72 行、0 error、0 skipped、0 incorrect。
- `raw_exact_xag_mc.csv` 审计：72 行、72 solved、0 unknown/error。
- `raw_highdim_root_action_oracle.csv` 审计：62 行、0 error、0 incorrect。
- `raw_highdim_root_action_teacher.csv` 审计：62 行、0 error、0 incorrect。
- `raw_highdim_guard_upgrade.csv` 审计：24 行、0 error、0 skipped、0 incorrect。
- `analysis_toolchain_readiness.md` 审计：ABC 可用；mockturtle 源码与项目 KLUT-to-XAG adapter 可用；CirKit 3 shell AIG/MC probe 可用；RevKit Python API 可用；legacy RevKit/CirKit CLI 可用并已生成 exact-oracle portfolio。
- `raw_cirkit_aig_probe.csv` 审计：177 行、177/177 correct、0 error、0 timeout。
- `raw_cirkit_aig_highdim_probe.csv` 审计：64 行、64/64 correct、0 error、0 timeout。
- `raw_screen_scale_extended_terms.csv` 审计：1008 行、1008/1008 plan 符号验证通过、1008/1008 emitted-circuit 符号验证通过、0 mismatch。
- `raw_screen_scale_depth_frontier_terms.csv` 审计：648 行、648/648 plan 符号验证通过、648/648 emitted-circuit 符号验证通过、0 mismatch。
- `raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv` 审计：960 行、960/960 plan 符号验证通过、960/960 emitted-circuit 符号验证通过、0 mismatch。
- `raw_truth_bridge_n23_large_frontier_terms.csv` 审计：60 行、60/60 完整 truth-table oracle 验证通过、60/60 plan 符号验证通过、60/60 emitted-circuit 符号验证通过、0 mismatch。
- `raw_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv` 审计：960 行、960/960 plan 符号验证通过、960/960 emitted-circuit 符号验证通过、0 mismatch。
- `raw_truth_bridge_n23_cost_time003_frontier_terms.csv` 审计：60 行、60/60 完整 truth-table oracle 验证通过、60/60 plan 符号验证通过、60/60 emitted-circuit 符号验证通过、0 mismatch。

Git 状态：

- 最新提交：以本轮最终回复中的 Git commit 为准。
- 远端：`origin/main` 已同步。
- 注意：仓库根目录外层曾出现未跟踪压缩包 `resource_nmcts_experiment.zip`，不属于本次代码交付。

## 6. 论文当前可写主张

推荐主张：

1. 本文提出一种面向资源约束的量子布尔函数 oracle 综合方法，将问题表示为 ANF/FPRM 项集合上的搜索。
2. 方法不依赖 SSHR 的 parallelotope 结构，可以把 SSHR 作为外部 baseline。
3. 在 `n<=6` 传统 baseline 切片上，Pareto-Resource-NMCTS 对 ESOP cube beam、ESOP-MILP 和 ABC-ESOP 均有明显 score 优势。
4. 在 `n=18` 高维随机 ANF stress test 上，fast linear-pair guard 与 Resource/Profile/Pareto 可稳定改善 root-beam，说明高维 guard 不再只是保底策略。
5. 外部 ABC/BDD 结果支持低加权资源和低 ancilla 优势，但 depth 仍是 ABC-AIG/ABC-XAG 的优势指标。
6. 贡献分解显示：仿射坐标搜索是最大前置收益，神经 refine 和 final guard 提供无 score loss 的小幅增益，Pareto archive 在小规模传统切片上贡献明确，高维主要由 bounded linear-pair guard 支撑。
7. `n<=4` exact FPRM-DP 精确切片显示：Resource/Pareto portfolio 可以在受限 FPRM exact 模型之外继续降低 score；Exact FPRM-DP 本身也优于 ESOP-MILP 和 exact SSHR-I 的加权 score。
8. `n<=4` exact XAG 乘法复杂度切片显示：Resource/Pareto 在 12/72 个函数上达到全局 T 下界，平均 T gap 为 +53.01%，明显低于 ESOP-MILP 的 +120.14% 和 SSHR-I-T 的 +143.06%。
9. 高维 root-action teacher 诊断显示：oracle top-24 相对启发式 top-4 有 3/0/7、-0.18% 的小幅 headroom；pairwise-wide root-action ranker 进一步在 n=16 full synthesis 中相对 deterministic recursive guard 获得 10/0/14、-0.18%，因此高维 AI 贡献已从负向诊断推进到小幅正向证据。
10. Boolean-ring linear factor 将 quotient 与 linear factor 的变量不相交限制放宽到 Boolean 环 `x_i^2=x_i` 展开；在 n=16 上，Boolean-guard Resource-NMCTS 相对 pairwise-wide Resource-NMCTS 获得 14/0/10、平均 score 降低 0.34%，相对 deterministic recursive guard 获得 18/0/6、平均 score 降低 0.52%。这是当前高维结构搜索中比 pairwise-wide 更明显的正向提升。
11. 外部工具链 readiness 审计显示：ABC 已可用并支撑当前 AIG/XAG/LUT/ESOP baseline；mockturtle 已推进到 official-header KLUT-to-XAG probe；CirKit 3 shell 已推进到 AIG/multiplicative-complexity probe；RevKit Python API 已形成 `oracle_synth` phase-netlist baseline；legacy RevKit CLI 已形成 exact-oracle reversible-synthesis portfolio；官方 ROS 全流程仍未完整复现。
12. ROS-style LUT proxy 显示：在 309 个 `n=3..6,14,15,16,18` 函数上，ABC `K=3,4,5` LUT sweep 的 927/927 行均通过 truth-table 检查；best-K proxy 相对固定 K=4 为 219/0/90、平均 score -18.12%，而 Resource-NMCTS 相对该更强 proxy 仍为 309/0/0、平均 score -83.77%。进一步的 line-sensitivity 显示，min-ancilla LUT selector 相对 best-score proxy 可降低 peak ancilla 32.47% 但 score 变差 40.67%；Pareto-Resource-NMCTS 相对 min-ancilla、line-weighted 和 K4 line-cap selectors 仍保持 309/0/0 score 胜出，平均 score 降低 84.45%--85.83%。
13. `n=20` giga stress 已从纯边界失败推进为边界改善：root-beam 与 fast linear-pair 仍全部 timeout，但 depth-2 recursive Boolean screen 让 Resource-NMCTS 相对旧 Resource-NMCTS 获得 5/0/1、平均 score -7.47%；相对 AND-direct ANF 获得 5/0/1、平均 score -11.80%；相对 direct ANF 获得 5/1/0、平均 score -38.86%。
14. `n=32,36,40` extended screen-scale 显示：depth policy 相对 single screen 获得 110/0/34、平均 score -5.55%；相对 all-depth adaptive 在 144 个项集上全部 score 持平，并节省 33.14% 平均运行时间；1008/1008 个方法行通过 plan 和 emitted-circuit 两层 ANF 符号验证。
15. `n=20,28,40` depth-frontier 显示：depth-3 Boolean-ring screen 相对 fixed depth-2 为 49/0/23、平均 score -1.93%；depth-4 相对 fixed depth-2 为 49/0/23、平均 score -3.10%；648/648 个方法行通过 plan 和 emitted-circuit 两层 ANF 符号验证。这是新的高预算质量前沿证据，但运行时间显著增加。
16. Depth-frontier policy 已把高预算质量前沿学习化：在 `n=20,28,40` scale harness 中，相对 fixed depth-2 获得 35/0/37、平均 score -2.19%；相对 all-depth depth<=4 平均 score +0.97%，但节省 58.69% 时间；720/720 个方法行通过 plan 和 emitted-circuit 两层 ANF 符号验证。
17. Large frontier policy 进一步压缩质量 gap：held-out 相对 oracle frontier 从旧模型 +0.80% 降到 +0.04%；独立 seed `n=24,28,32,40` 相对旧 policy 为 17/0/79、平均 score -0.49%，相对 all-depth 仅 +0.10% 且节省 53.50% 时间；代价是比旧 policy 更慢。
18. Cost-aware frontier policy 给出更符合“资源约束”的快速质量模式：独立 seed `n=24,28,32,40` 相对 fixed depth-2 仍为 56/0/40、平均 score -1.39%，但相对 depth-2 的 plan time 增幅为 +170.03%，显著低于 large policy 的 +563.80%；在 n=23 bridge 上相对 large policy 节省 56.29% plan time 和 12.62% lifetime area，代价是 score +0.92%。
19. Stage-gated frontier 把 depth-frontier 进一步变成 validation-calibrated 搜索预算控制：在 large frontier validation 上选出 `1.25%` depth-4 触发阈值后，独立 seed `n=24,28,32,40` 相对 all-depth 为 0/4/92、平均 score +0.04%、staged time -25.43%；n=23 bridge 与 all-depth score 持平且 staged time -11.51%。该证据是接近 all-depth 的 teacher/guard，不应写成比 large policy 同时更快更优。
20. Learned sparse depth-4 gate 把 sparse frontier 继续学习化：在 `n=16,20,24` 训练、`n=28,40` held-out 测试，保守阈值下 48 个测试 pair 中只运行 32 个 depth-4，false skip 为 0，相对 deterministic sparse depth-2/4 frontier score 为 0/0/48、平均 +0.00%，同时 sparse-frontier evaluation time -17.39%；进一步在三组独立 seed 的 `n=24,28,32,40` 共 144 个 pair 上不重训审计，运行 106 个 depth-4，false skip 仍为 0，相对 sparse frontier 为 0/0/144、平均 +0.00%，time -13.43%。阈值敏感性分析显示 selected threshold 位于 zero-false-skip plateau 内：最优 0-false-skip operating point 为 -14.92% time；允许 1 个 false skip 时为 -15.49% time、score gap +0.01%；纯 depth-2-only 则有 94 false skips、score gap +2.84%。该证据应写成可校准搜索预算控制器，而不是比 deterministic sparse frontier 更强的质量前沿。
21. `n=21,22,23` 完整 truth-table bridge 加 large-policy 与 cost-aware `n=23` rerun 显示：按当前 v36 主图源数据口径，280/280 个方法行同时通过完整 truth-table oracle 验证、ANF plan 符号验证和 emitted-circuit ANF 符号验证；该结果把完整验证边界从 n<=20 主实验推进到 n>20 的桥接切片。
22. phase/Rz 分支已经从 RevKit 成本敏感性推进到可验证内部 emitter 和 Affine-FPRM 搜索：phase-parity ANF、fixed-polarity FPRM 与 Affine-FPRM 三组 selected rows 均为 531/531 或 177/177 up-to-global-phase 验证通过；Affine-FPRM 在 `T/Rz=30` 口径下相对 fixed-polarity FPRM 为 81/0/96、平均 score -2.51%，相对 phase-parity ANF 为 85/0/92、平均 score -2.98%，相对 RevKit 为 177/0/0、平均 score -65.50%。
23. wide Affine-FPRM phase search 显示 phase/Rz 分支仍受可逆线性预条件搜索预算限制：将 transform budget 从 32 扩展到 128 后，531/531 selected rows 继续 up-to-global-phase 验证通过；相对 budget 32，`T/Rz=30` 目标为 43/0/134、平均 synth-score -0.60%，total Rz -2.39%，CNOT -1.74%，depth -1.93%。该结果为后续 learned phase/Rz-aware policy 提供了明确搜索空间，而不是只做固定极性枚举。
24. learned phase candidate pruning 已把 phase/Rz 分支从“宽预算穷举”推进到“可学习剪枝”诊断，并进一步加入 rank-label 训练、diversity rerank 与 8 组 same-budget random repeat 控制：`train_phase_affine_policy.py` 在 `n<=5` 训练、held-out `n=6` 的 38 个函数测试；diverse policy top-512 只 exact-score 512/8192 个候选，相对 budget-32 的 2048 个候选为 17/0/21、`T/Rz=30` synth-score -2.48%，相对 wide-128 均值 gap 约 +0.00%，且 7611/7611 selected rows up-to-global-phase 验证通过。新增 `analyze_phase_policy_random_control.py` 将随机重复按函数求均值后做 paired sign test：diverse top-512 相对 per-function random-repeat mean 为 17/0/21、p=1.53e-05，且均值低于全部 8 个 random seed mean。绝对幅度仍只有约 0.01%--0.03%，所以该证据可写成 learned pruned-search feasibility 与显著优于 random-repeat mean，不能写成 phase/Rz 全局最优。
25. CirKit 3 shell AIG/MC probe 把外部工具链对比从 mockturtle/ABC 继续补强：传统 177 行与高维 `n=14` 64 行均逐行 Verilog readback truth-table 验证通过。Pareto-Resource-NMCTS 相对 CirKit AIG/MC 在传统集为 177/0/0、平均 score -62.34%，在 `n=14` 为 64/0/0、平均 score -94.46%；但 depth 分别为 16/156/5 和 14/50/0，说明本文不能宣称 depth-only 支配 CirKit。
26. Legacy RevKit CLI exact-oracle reversible-synthesis probe 进一步补齐可逆工具链对比：TBS/DBS/RMS 三流合计 531/531 行 usable，best-score portfolio 覆盖传统 177 个函数。Pareto-Resource-NMCTS 相对 RevKit CLI best-score portfolio 在 score 上为 173/0/4、平均 -67.28%，T-count 为 173/0/4、平均 -72.59%；但 peak ancilla 为 0/169/8、平均 +153.11%，说明本文方法用更多辅助线换取低 T 和低 weighted score。

不应写的主张：

1. 不应写“CNOT 全面优于 SSHR/ESOP/ABC”。
2. 不应写“硬件映射后仍然更优”，因为当前没有 mapping。
3. 不应写“Pareto 在 n=18 有额外独立收益”，因为 n=18 的 Pareto 当前故意收窄为稳定 guard。
4. 不应直接拿 SSHR 论文表格里的 ESOP 总量横比，除非函数集和成本模型一致。
5. 不应把 Exact FPRM-DP 写成全局可逆线路最优；它只是在 bounded fixed-polarity FPRM factor model 内 exact。
6. 不应把 Exact XAG 乘法复杂度写成 CNOT/depth/ancilla 最优；它只给出 logical-AND T-count 的全局下界。
7. 不应把 n=20 giga stress 写成深层神经/FPRM 搜索的新突破；当前正向增益来自 ANF-only recursive Boolean-ring screen，root-beam/fast linear-pair 仍在 300 s 预算下失效。
8. 不应把 Boolean-linear screen 泛化成所有高维上的高质量方法；recursive screen 在 n=20 是有效的可扩展修复，在 n=18 也优于单层 screen，但 n=18 结果仍显示 deep Resource 分支明显更强，因此 screen 应写成超高维边界候选。

## 7. 下一步建议

当前已经完成第一版“搜索贡献分解”，并新增了 `search_ablation_traditional`、`search_ablation_highdim`、`highdim_neural_prior`、`highdim_root_action_oracle`、`exact_fprm_dp`、`exact_xag_mc`、`highdim_root_action_teacher` 和 `highdim_guard_upgrade` 等 dedicated ablation/diagnostic。投稿前仍建议继续补强：

1. 高维 neural guidance 仍需继续改进；当前 pairwise-wide 版本已经把 n=16 full synthesis 推进到 10/0/14、-0.18%，但真正更明显的新收益来自 Boolean-ring linear factor。下一步应把 neural ranker 从“排序旧 pair action”升级为“选择 Boolean-ring factor / recursive depth / polarity 的策略网络”，否则 AI 贡献仍弱于手工结构扩展。
2. phase/Rz 分支已经有 learned candidate-pruning 诊断，但 same-budget random shortlist 接近，说明当前 policy objective 仍弱；下一步需要从候选剪枝推进到 learned/optimized phase policy、旋转谱优化和 rotation-sequence audit，不能声明 phase/Rz 全局最优。
3. 小规模 exact/exhaustive oracle slice 已完成 bounded FPRM-DP 和 exact XAG 乘法复杂度版本；如果继续加强，可以再补一个更接近全局 reversible circuit 的 exact/SMT/SAT 小规模证书。
4. 继续补官方 ROS 全流程和更强 reversible-toolchain 对比，减少“proxy 式 ABC/BDD/LUT baseline”的审稿风险；当前已有 ROS-style LUT proxy、official-header mockturtle probe、CirKit 3 shell AIG/MC probe、RevKit Python API baseline 和 legacy RevKit CLI exact-oracle portfolio，但官方 ROS 仍未完整复现，RevKit CLI 也尚未覆盖 ROS/SAT garbage-management 或硬件 mapping。

已完成/待补强状态：

| 设置 | 函数集 | 当前证据 | 状态 |
|---|---|---|---|
| no neural prior | n<=6 traditional | Resource-NMCTS score 39/0/138，-1.10% | 已有 |
| affine/neural/guard 分解 | 322-function ablation | neural refine 65/0/257，guard 88/0/234 | 已有 |
| heuristic-only / no-MCTS | n<=6 traditional | Resource vs no-MCTS 54/0/123，-1.44%；Pareto vs no-MCTS 106/0/71，-4.69% | 已有 |
| highdim no-MCTS guard | n=14 random ANF | no-MCTS vs root-beam 14/0/2，-6.25%；no-MCTS vs linear-pair 14/0/2，-3.08% | 已有 |
| Pareto archive | n<=6 traditional | Pareto vs Resource 68/0/109，-3.26% | 已有 |
| highdim guard | n=14/15/16/18 | linear-pair guard 相对 root-beam 均无 score loss | 已有 |
| highdim no-neural-prior | 12 个 n=14 random ANF | pairwise-wide learned prior 2/0/10，-0.05%，运行时间 +179.59% | 已有但仍弱 |
| highdim root-action teacher | n=14/n=16 random ANF | n=14 heuristic top-4 + neural top-8 为 2/0/8，-0.14%；n=16 为 5/0/18，-0.06% | 已有小幅正向诊断 |
| n=16 pairwise-wide full synthesis | 24 个 n=16 random ANF | vs deterministic recursive guard 为 10/0/14，-0.18%；vs old Resource 为 10/0/14，-0.12% | 新增正向 AI 证据，但运行时间更高 |
| n=16 Boolean-ring full synthesis | 24 个 n=16 random ANF | Boolean-guard vs pairwise-wide Resource 为 14/0/10，-0.34%；vs deterministic recursive guard 为 18/0/6，-0.52% | 当前最强高维结构改进 |
| n=18 Boolean-linear screen | 12 个 n=18 random ANF | vs old Resource 为 0/12/0，+42.45%，但运行时间 -98.48% | 负向质量诊断，只能说明快速边界可跑 |
| n=18 adaptive depth-2 Boolean screen | 12 个 n=18 random ANF | vs single screen 为 11/0/1，-6.47%；Resource vs adaptive screen 为 11/0/1，-23.85% | 改善 screen 但不能替代深搜索 |
| n=20 depth-2 recursive Boolean screen | 6 个 n=20 random ANF | Resource vs old Resource 为 5/0/1，-7.47%；vs AND-direct 为 5/0/1，-11.80%；vs depth-1 Resource 为 5/0/1，-3.13% | 当前最明确的超高维边界改善 |
| n=32/36/40 extended screen-scale | 144 个高维 ANF 项集 | depth policy vs single 为 110/0/34，-5.55%；vs all-depth adaptive 为 0/0/144，省时 -33.14%；1008/1008 emitted-circuit 符号验证通过 | 新增大规模泛化证据 |
| n=20/28/40 depth-frontier | 72 个高维 ANF 项集 | depth-3 vs depth-2 为 49/0/23，-1.93%；depth-4 vs depth-2 为 49/0/23，-3.10%；648/648 emitted-circuit 符号验证通过 | 新增高预算质量前沿 |
| depth-frontier policy | 32 个 held-out + 72 个 scale 项集 | held-out vs oracle frontier 为 +0.80% score、-58.76% time；scale vs depth-2 为 35/0/37、-2.19%；720/720 emitted-circuit 符号验证通过 | 新增结构级 AI 质量-时间折中 |
| large frontier policy | 48 个 held-out + 96 个独立泛化项集 + 6 个 n=23 bridge 函数 | held-out vs oracle frontier 为 +0.04% score、-51.30% time；独立泛化 vs 旧 policy 为 17/0/79、-0.49%；n=23 bridge vs 旧 policy 为 1/0/5、-0.48% score、-0.45% T-depth proxy | 新增质量增强型结构 AI 证据 |
| cost-aware frontier policy | 48 个 held-out + 96 个独立泛化项集 + 6 个 n=23 bridge 函数 | scale vs depth-2 为 56/0/40、score -1.39%、time +170.03%；n=23 vs large 为 score +0.92%、time -56.29%、lifetime -12.62% | 新增快速质量折中模式 |
| stage-gated frontier | 72 个 validation 项集 + 96 个独立泛化项集 + 6 个 n=23 bridge 函数 | validation 选阈值 1.25%；scale vs all-depth 为 +0.04% score、staged time -25.43%；n=23 vs all-depth 为 +0.00% score、staged time -11.51% | 新增接近 all-depth 的 teacher/guard |
| learned sparse depth-4 gate | train `n=16,20,24`；三组独立 seed 审计 `n=24,28,32,40`，144 个 pair | vs sparse frontier 为 0/0/144、score +0.00%、false skip 0；只运行 106/144 个 depth-4，time -13.43%；阈值扫描 zero-false-skip 最优为 -14.92% time | 新增 sparse frontier 内部学习预算控制 |
| n=21/22/23 truth-table bridge | 16 个基础生成式 ANF 函数 + 12 个 n=23 rerun 函数 | 按当前 v36 主图源数据口径，280/280 完整 truth-table oracle 验证通过，280/280 plan 与 emitted-circuit 符号验证通过，0 mismatch；large/cost 两种 n=23 rerun 均完整验证 | 新增 n>20 完整验证桥接 |
| n=24/25 truth-table bridge | 12 个生成式 ANF 函数 | 新增 120/120 完整 truth-table oracle 验证通过，120/120 plan 与 emitted-circuit 符号验证通过，0 mismatch；累计 bridge 为 400/400 | 新增 n=24 与 n=25 完整验证边界 |
| action-width probe | n=20/28/40，每个宽度 72 个项集 | width 6/12/24 各 504/504 plan 与 emitted-circuit 符号验证通过；单纯加宽不改善默认 score 结论，时间显著上升 | 新增负向消融，支持默认 width 6 |
| schedule proxy | 96 个 n=24/28/32/40 项集 + 30 个 n=21/22/23 bridge/rerun 函数 | frontier policy vs depth-2：项集 T-depth proxy 40/0/56、-1.85%，large n=23 vs old policy 为 1/0/5、-0.45% T-depth proxy；cost n=23 vs large 为 time -56.29%、lifetime -12.62% | 新增逻辑层后端相关指标，非硬件 mapping |
| ROS-style LUT proxy | 309 个 n=3..6/14/15/16/18 函数 | 927/927 K-sweep truth-table 检查通过；best-K vs fixed K=4 为 219/0/90、-18.12%；Resource vs proxy 为 309/0/0、-83.77% | 新增更强 LUT proxy，但不是官方 ROS 复现 |
| ROS-style LUT line-sensitivity | 同上 309 个函数 | min-ancilla selector vs best-score proxy：peak ancilla -32.47% 但 score +40.67%；Pareto vs min-ancilla/line-weighted/K4-line-cap selectors score 均为 309/0/0，-84.45% 到 -85.83% | 新增辅助线压力稳健性证据，仍不是官方 ROS |
| CirKit 3 shell AIG/MC probe | n<=6 traditional 177 个函数 + n=14 highdim 64 个函数 | 传统 177/177、n=14 64/64 Verilog readback truth-table 验证通过；Pareto vs CirKit score 分别为 177/0/0、-62.34% 和 64/0/0、-94.46%；depth 多数输给 CirKit | 新增官方 CirKit shell probe，但不是 legacy RevKit/ROS |
| RevKit CLI exact-oracle portfolio | n<=6 traditional 177 个函数 | TBS/DBS/RMS 三流 531/531 usable；best-score portfolio 下 Pareto vs RevKit score 为 173/0/4、-67.28%，T 为 173/0/4、-72.59%，peak ancilla 为 0/169/8、+153.11% | 新增 legacy reversible-synthesis CLI probe，但不是 ROS 或硬件 mapping |
| Affine-FPRM phase search | n<=6 traditional, 177 个函数 | 531/531 selected rows up-to-global-phase 验证通过；`T/Rz=30` vs fixed-polarity FPRM 为 81/0/96、-2.51%；vs phase-parity ANF 为 85/0/92、-2.98%；vs RevKit 为 177/0/0、-65.50% | 当前最强 phase/Rz 搜索证据，仍非旋转序列级综合 |
| Wide Affine-FPRM phase search | n<=6 traditional, 177 个函数；transform budget 128 | 531/531 selected rows up-to-global-phase 验证通过；相对 budget 32，`T/Rz=30` 目标为 43/0/134、synth-score -0.60%，total Rz -2.39%，CNOT -1.74%，depth -1.93% | 新增 phase/Rz 搜索预算扩展证据 |
| Rank-diverse learned phase candidate pruning | train n<=5, held-out n=6 38 个函数；transform budget 128 | 7611/7611 selected rows up-to-global-phase 验证通过；diverse policy top-512 vs budget-32 为 17/0/21、`T/Rz=30` synth-score -2.48%；vs wide-128 均值约 +0.00%；vs per-function random-repeat mean 为 17/0/21、p=1.53e-05，低于 8/8 random seed means | 新增更强可学习剪枝证据，但仍不能声称 phase/Rz 全局最优 |
| highdim wide-fast guard | 12 个 n=14 random ANF | wide vs Resource 为 0/0/12，运行时间 +59.80% | 已有但属负向诊断 |
| exact FPRM-DP | n<=4 traditional | Resource vs exact FPRM-DP 51/3/18，-12.18%；Pareto vs exact FPRM-DP 51/0/21，-12.20% | 已有但模型受限 |
| exact XAG MC | n<=4 traditional | Resource/Pareto 达到 T 下界 12/72，平均 T gap +53.01%；ESOP 为 +120.14%，SSHR-I-T 为 +143.06% | 已有全局 T 下界 |
| toolchain readiness | 当前工作站 | ABC 可用；mockturtle probe、CirKit 3 shell probe、RevKit Python API 与 legacy RevKit CLI 可用 | 已有环境审计，仍需完整 ROS 复现和更强 reversible-toolchain 对比 |

## 8. 当前结论

当前版本已经具备一条比 SSHR 路线更适合投稿的主线：

“基于资源感知搜索、神经先验和 MCTS/Pareto 候选选择的量子布尔函数 oracle 综合方法，在同 benchmark 的 ESOP、ABC、BDD 和 direct ANF baseline 上展示显著低 T-count 与低加权资源优势。”

但是投稿前还需要继续补强“AI 搜索本身带来的贡献”这一点。learned sparse depth-4 gate 已经把 frontier 内部预算控制补上了一块，但文章仍需要避免被评价为一组 FPRM/ESOP 工程启发的组合，而不是强化学习与 MCTS 方法论文。

本轮新增贡献分解、`search_ablation_traditional`、`search_ablation_highdim`、`highdim_neural_prior`、`highdim_root_action_oracle`、`exact_fprm_dp`、`exact_xag_mc`、pairwise-wide n=16 full synthesis、Boolean-ring linear factor、schedule proxy、n=23/24/25 完整 truth-table bridge、ROS-style LUT proxy、CirKit 3 shell AIG/MC probe、legacy RevKit CLI exact-oracle portfolio、large frontier policy、cost-aware frontier policy、learned sparse depth-4 gate、Affine-FPRM phase search、wide Affine-FPRM budget 扩展和 learned phase candidate pruning 后，这个风险已经下降：现在能证明 neural refine、learned prior、final guard、no-MCTS portfolio、Resource-NMCTS、Pareto archive、高维 guard/no-MCTS 组合、小规模 exact bounded FPRM 对照、全局 XAG T 下界对照、高维 pairwise-wide root-action ranker、Boolean-ring factor 扩展、emitted-circuit 层 T-depth/辅助生命周期 trade-off、n=21/22/23/24/25 共 400/400 方法行的完整 oracle 验证、large frontier policy 相对旧 policy 的质量提升、cost-aware frontier policy 的快速质量折中、sparse depth-4 gate 在 144 个独立 seed 审计 pair 上 0 false skip 且省 13.43% sparse-frontier 时间，并且阈值扫描显示 zero-false-skip 省时可到 14.92%、相对更强 LUT proxy 的 309/0/0 score 优势、相对 CirKit AIG/MC 的传统 177/0/0 与 n=14 64/0/0 score 优势、相对 RevKit CLI best-score portfolio 的 173/0/4 score 优势、Affine-FPRM 相对 fixed-polarity FPRM 的 81/0/96 phase-search 增益、wide128 相对 budget32 的 43/0/134 `T/Rz=30` 增益，以及 policy top-512 相对 budget32 的 17/0/21 剪枝增益和相对 random-repeat mean 的 17/0/21、p=1.53e-05 稳健性。不过官方 ROS 完整复现、从 phase/Rz 候选剪枝升级到真正的 learned rotation/phase policy、以及目标期刊格式英文稿仍需继续推进，所以目标还不能判定完成。
