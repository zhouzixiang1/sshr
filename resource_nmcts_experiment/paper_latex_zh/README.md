# 中文 LaTeX 论文草稿

本目录存放中文论文草稿：

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

## 当前权威版本

- 当前中文同步精简稿：`resource_nmcts_zh_manuscript_v40.tex` / `resource_nmcts_zh_manuscript_v40.pdf`。
- 当前英文投稿权威稿：`../paper_latex/resource_nmcts_submission_v1.tex` / `../paper_latex/resource_nmcts_submission_v1.pdf`。
- v40 以当前英文投稿证据为权威源，补齐比较层级、baseline fairness、SSHR crosswalk、强化学习 Pareto 预算控制、最新 phase/scale 验证与声称边界；它是中文精简同步稿，不是英文 61 页审计型全文的逐段翻译。
- v39 及以前版本仅保留研究演进记录，不应再作为最新中文稿分发。

文件：

- `main_zh.tex` / `main_zh.pdf`：现有中文主稿。
- `resource_nmcts_zh_draft.tex` / `resource_nmcts_zh_draft.pdf`：独立中文技术论文草稿，包含更新后的 $n=16$ recursive linear-pair guard 结果。
- `resource_nmcts_zh_full.tex` / `resource_nmcts_zh_full.pdf`：当前更完整的中文论文草稿，整合 $n=16$ baseline-preserving AI guard、$n=18$ stress test、搜索贡献分解和 exact 小规模参照。
- `resource_nmcts_zh_report.tex` / `resource_nmcts_zh_report.pdf`：中文论文报告版，按“主张与边界、相关工作、方法、实验、结果、讨论”组织。
- `resource_nmcts_zh_robustness.tex` / `resource_nmcts_zh_robustness.pdf`：中文投稿论证稿，突出独立于 SSHR 的 Resource-NMCTS 主线、n=16 清洗后的 240 行结果和多资源权重鲁棒性分析。
- `resource_nmcts_zh_neural_plan.tex` / `resource_nmcts_zh_neural_plan.pdf`：中文方案与阶段性证据稿，聚焦神经 MCTS 论文主线、pairwise-wide root-action ranker、n=16 full synthesis 小幅正向结果、当前不足和下一步实验目标。
- `resource_nmcts_zh_manuscript_v2.tex` / `resource_nmcts_zh_manuscript_v2.pdf`：中文正式论文初稿 v2，按“引言、相关工作、问题定义、方法、实验、结果、讨论、结论”组织，弱化阶段汇报口吻。
- `resource_nmcts_zh_boolean_ring_v3.tex` / `resource_nmcts_zh_boolean_ring_v3.pdf`：中文短论文稿 v3，聚焦布尔环线性因子、n=16 matched improvement、n=20 边界测试和当前仍未完成的高维 AI 缺口。
- `resource_nmcts_zh_stage_delivery.tex` / `resource_nmcts_zh_stage_delivery.pdf`：中文阶段交付稿，面向导师/合作者快速阅读，压缩说明项目定位、方法主线、已达成提升、负面结果和下一步“明显提升”目标。
- `resource_nmcts_zh_adaptive_screen.tex` / `resource_nmcts_zh_adaptive_screen.pdf`：中文技术论文稿 v4，聚焦自适应 depth-2 布尔环筛选、n=18/n=20 最新 matched comparison，以及“筛选有效但高维神经先验仍弱”的边界。
- `resource_nmcts_zh_structure_policy_v5.tex` / `resource_nmcts_zh_structure_policy_v5.pdf`：中文技术论文稿 v5，聚焦结构级 depth policy、保守 depth-2 skip guard 与 screen-gate，把 AI 贡献从动作排序推进到结构选择，同时保留“guard 覆盖率仍小”的边界。
- `resource_nmcts_zh_manuscript_v6.tex` / `resource_nmcts_zh_manuscript_v6.pdf`：中文论文稿 v6，以“面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法”为主线，重新组织相关工作、方法、实验和局限，明确本文不从 SSHR 入手而是做 ANF/FPRM 项集合搜索。
- `resource_nmcts_zh_manuscript_v7.tex` / `resource_nmcts_zh_manuscript_v7.pdf`：中文论文稿 v7，在 v6 主线上进一步正式化讨论与局限，补充 direct depth-2 skip guard 相对 fixed depth-2 与 all-depth adaptive 的双时间口径。
- `resource_nmcts_zh_manuscript_v8.tex` / `resource_nmcts_zh_manuscript_v8.pdf`：中文论文稿 v8，补充 n=19/20 screen-gate holdout 和 n=20/22/24/28 项集级 screen-scale 证据，明确 n>20 为项集级逻辑资源评估而非完整 truth-table verification。
- `resource_nmcts_zh_manuscript_v9.tex` / `resource_nmcts_zh_manuscript_v9.pdf`：中文论文稿 v9，补充 n=20/22/24/28 screen-scale 的 ANF plan 符号展开验证，1344/1344 方法行通过，进一步区分 plan 级等价验证与完整 truth-table/emitted-circuit verification。
- `resource_nmcts_zh_manuscript_v10.tex` / `resource_nmcts_zh_manuscript_v10.pdf`：中文论文稿 v10，进一步补充 emitted X/CNOT/MCT circuit 的 ANF 符号模拟验证，1344/1344 方法行通过，边界收窄为“不是完整 truth-table simulation”。
- `resource_nmcts_zh_manuscript_v11.tex` / `resource_nmcts_zh_manuscript_v11.pdf`：中文论文稿 v11，主线收束版；在 v10 证据基础上补充 n=32/36/40 extended scale 和 n=20/28/40 depth-frontier，3000/3000 个项集级方法行通过 plan 与 emitted-circuit 两层 ANF 符号验证，并更明确地区分 Resource-NMCTS 主方法、Boolean-ring screen、结构级 AI、screen-gate 与尚未完成的高维 learned-prior 质量收益。
- `resource_nmcts_zh_manuscript_v12.tex` / `resource_nmcts_zh_manuscript_v12.pdf`：中文论文稿 v12，投稿框架与证据边界版；在 v11 的结果基础上重写摘要、引言和证据地图，把 depth-frontier 明确定位为新的质量前沿，同时把高维 learned-prior、完整 truth-table bridge 和外部工具链比较列为投稿前缺口。
- `resource_nmcts_zh_manuscript_v13.tex` / `resource_nmcts_zh_manuscript_v13.pdf`：中文论文稿 v13，frontier policy 与 truth-table bridge 版；补充 depth-frontier policy（scale n=20/28/40 相对 fixed depth-2 为 35/0/37、平均 score -2.19%；独立 seed n=24/28/32/40 为 40/0/56、平均 score -1.85%）和 n=21/22 完整 truth-table bridge（120/120 方法行通过完整 oracle 验证、plan 验证和 emitted-circuit 符号验证；bridge 中 frontier policy 相对 fixed depth-2 为 8/0/4、平均 score -3.50%）。
- `resource_nmcts_zh_manuscript_v14.tex` / `resource_nmcts_zh_manuscript_v14.pdf`：中文论文稿 v14，搜索主线与投稿文本版；重新压缩叙事为“ANF/FPRM 项集合搜索问题 -> Boolean-ring screen -> 神经动作先验/MCTS -> depth policy/frontier policy/guard -> 证据边界”，明确本文不从 SSHR 入手，SSHR 仅作为 CNOT-oriented baseline，并把独立 seed frontier-policy 泛化结果、4680/4680 项集级符号验证与 n=21/22 的 120/120 完整 truth-table bridge 作为当前正确性证据。
- `resource_nmcts_zh_manuscript_v15.tex` / `resource_nmcts_zh_manuscript_v15.pdf`：中文论文稿 v15，中文交付与想法梳理版；在 v14 投稿文本基础上新增“作者想法整理与当前论文定位”，直接写清“强化学习与 MCTS 的量子布尔函数综合搜索问题”主线、SSHR 的 baseline 定位、当前明显提升证据和投稿前最应补强的外部工具链/后端评估缺口。
- `resource_nmcts_zh_manuscript_v16.tex` / `resource_nmcts_zh_manuscript_v16.pdf`：中文论文稿 v16，逻辑层 schedule proxy 版；在 v15 基础上补充 emitted-circuit 并行逻辑深度、CNOT-depth proxy、T-depth proxy 和显式辅助线 lifetime area 证据，明确这些指标仍属于逻辑层，不是硬件 mapping 结果。
- `resource_nmcts_zh_manuscript_v17.tex` / `resource_nmcts_zh_manuscript_v17.pdf`：中文论文稿 v17，$n=23$ 完整 bridge 版；在 v16 基础上补充 6 个 $n=23$ 生成式 ANF 函数、60 个方法行的完整 truth-table oracle 验证，并把 n=21/22/23 bridge 合计更新为 180/180 完整验证通过。
- `resource_nmcts_zh_manuscript_v18.tex` / `resource_nmcts_zh_manuscript_v18.pdf`：中文论文稿 v18，ROS-style LUT proxy 版；在 v17 基础上补充 ABC `K=3,4,5` LUT sweep proxy，覆盖 309 个函数、927/927 truth-table 检查通过，并明确该 proxy 不是官方 ROS/RevKit/mockturtle 复现。
- `resource_nmcts_zh_manuscript_v19.tex` / `resource_nmcts_zh_manuscript_v19.pdf`：中文论文稿 v19，large frontier policy 版；在 v18 基础上补充扩大训练集后的 frontier policy、独立 seed `n=24,28,32,40` 泛化、large-policy `n=23` 完整 bridge rerun 和 `analysis_frontier_policy_upgrade.md` 汇总，当前项集级方法行验证更新为 5640/5640，完整 truth-table bridge 更新为 240/240。
- `resource_nmcts_zh_manuscript_v20.tex` / `resource_nmcts_zh_manuscript_v20.pdf`：中文论文稿 v20，cost-aware frontier policy 版；在 v19 基础上补充质量-时间折中标签 `score_delta + 0.003*time_delta`、cost-aware 独立泛化、cost-aware `n=23` 完整 bridge rerun 和升级后的 frontier policy 汇总，当前项集级方法行验证更新为 6600/6600，完整 truth-table bridge 更新为 300/300，并把 frontier policy 明确拆成偏质量的 large 模式和偏运行成本/辅助线生命周期的 cost-aware 模式。
- `resource_nmcts_zh_manuscript_v21.tex` / `resource_nmcts_zh_manuscript_v21.pdf`：中文论文稿 v21，RevKit API baseline 旧版；在 v20 基础上补充本机 RevKit Python `oracle_synth` baseline，177/177 个 `n<=6` 传统函数合成成功。该版本对 RevKit netlist 的 Clifford+T 口径表述过强，已由 v22 的 Rz 角度审计修正，后续引用应以 v22 为准。
- `resource_nmcts_zh_manuscript_v22.tex` / `resource_nmcts_zh_manuscript_v22.pdf`：中文论文稿 v22，RevKit Rz 角度审计版；修正 v21 的过强表述，确认 RevKit `oracle_synth` 返回的是 Rz-phase netlist lower-bound proxy，171/177 行含非 Clifford `Rz`、总数 9242、最大 angle/pi 分母 64，因此 `6/171/0`、score `+751.69%` 和 T-like count `+4060.08%` 不能写成精确 Clifford+T T-count 对比；新增 `score+1/Rz` 与 `score+2/Rz` 符号敏感性，Resource-NMCTS 分别为 140/37/0 和 177/0/0。
- `resource_nmcts_zh_manuscript_v23.tex` / `resource_nmcts_zh_manuscript_v23.pdf`：中文论文稿 v23，RevKit Rz portfolio 敏感性版；新增 `analyze_phase_rz_portfolio.py` 结果，把 Resource-NMCTS、Pareto-Resource-NMCTS 和 FPRM polarity archive 作为 score-reranked family portfolio。该 family 在 `lambda_Rz=1` 时相对 RevKit 为 157/20/0，在 `lambda_Rz=1.5` 时为 177/0/0；传统 baseline family 在 `lambda_Rz=1` 时只有 80/97/0。
- `resource_nmcts_zh_manuscript_v25.tex` / `resource_nmcts_zh_manuscript_v25.pdf`：中文论文稿 v25，近似 Rz 综合成本模型版；在 v23 基础上新增 `analyze_rz_synthesis_cost.py` 结果，把 RevKit 每个非 Clifford `Rz` 按 `ceil(a log2(1/epsilon)+b)` 计入近似 Clifford+T T-count proxy。Ross-Selinger-style `epsilon=1e-3` 时 `T/Rz=30`，Resource-NMCTS family 相对 RevKit 为 177/0/0、平均 score 降低 95.03%；更保守的 `4 log2(1/epsilon)+10` proxy 在 `epsilon=1e-6` 时仍为 177/0/0、平均 score 降低 97.01%。该版本明确声明 proxy 不输出实际 rotation sequence，也不是硬件 mapping。
- `resource_nmcts_zh_manuscript_v26.tex` / `resource_nmcts_zh_manuscript_v26.pdf`：中文论文稿 v26，RevKit 高维超时边界版；在 v25 基础上新增 `run_revkit_highdim_timeout_probe.py` 的可复现实验，对 `n=14` 前 8 个函数逐行用子进程运行 RevKit `oracle_synth` 并设置 30 s 硬超时。结果为 1/8 返回、7/8 超时；唯一返回行 `anf_n14_10` 含 32767 个非 Clifford `Rz`，RevKit lower-bound score 为 2948.79，`score+1/Rz` 为 35715.79。该版本明确高维 RevKit timeout 行不进入 paired resource 均值，只作为 adapter/scalability boundary。
- `resource_nmcts_zh_manuscript_v27.tex` / `resource_nmcts_zh_manuscript_v27.pdf`：中文论文稿 v27，投稿主线压缩版；在 v26 的完整项目报告基础上重写为更紧凑的论文文本，聚焦“ANF/FPRM 项集合资源约束搜索 -> Boolean-ring screen -> 神经 MCTS/depth-frontier/guard -> 外部 proxy 和 RevKit phase/Rz 边界 -> 正确性验证”的主线，保留关键定量证据并减少流水账式实验堆叠。
- `resource_nmcts_zh_manuscript_v28.tex` / `resource_nmcts_zh_manuscript_v28.pdf`：中文论文稿 v28，mockturtle 官方 probe 版；新增 `run_mockturtle_xag_probe.py` 和 `tools/mockturtle_blif_xag_stats.cpp`，把 ABC `K=4` BLIF 映射结果送入官方 mockturtle `blif_reader` 与 `xag_npn_resynthesis`。传统 `n<=6` 的 177 行全部正确，Pareto-Resource-NMCTS 相对 mockturtle XAG K4 为 166/11/0、平均 score -31.50%；高维 `n=14` 的 64 行全部正确，Pareto-Resource-NMCTS 为 64/0/0、平均 score -91.49%。该版本明确这仍是 KLUT-to-XAG probe，不是完整 ROS 或硬件 mapping。
- `resource_nmcts_zh_manuscript_v29.tex` / `resource_nmcts_zh_manuscript_v29.pdf`：中文论文稿 v29，投稿叙事重写版；在 v28 证据基础上重新组织为更接近论文正文的 11 页稿件，压缩版本流水账，突出“ANF/FPRM 项集合资源约束搜索 -> Boolean-ring screen -> 神经 MCTS/depth-frontier/guard -> 外部 LUT/mockturtle probe -> RevKit phase/Rz gate-set 边界 -> 高维验证桥接”的论证链，并保留 phase/Rz-aware emitter、官方 ROS/legacy RevKit-CirKit 和后端 mapping 作为投稿前明显提升目标。
- `resource_nmcts_zh_manuscript_v30.tex` / `resource_nmcts_zh_manuscript_v30.pdf`：中文论文稿 v30，phase-parity emitter 版；新增 `run_phase_parity_baseline.py` 的实际 phase-oracle baseline，把 ANF 单项式展开为 parity-phase Rz gadgets 并用 Fraction 精确验证 177/177 个 `n<=6` 传统函数 up to global phase。该 emitter 相对 RevKit lower-bound score 为 40/137/0、平均 +69.25%，但 `score+1/Rz` 为 177/0/0、平均 -48.16%，`T/Rz=30` proxy 为 177/0/0、平均 -64.98%，说明朴素 phase 展开不是最终方法，但已把 phase/Rz 边界推进为项目内部可验证 emitter 起点。
- `resource_nmcts_zh_manuscript_v31.tex` / `resource_nmcts_zh_manuscript_v31.pdf`：中文论文稿 v31，搜索主线交付版；在 v30 证据基础上重写为更聚焦的中文 LaTeX 论文文本，把标题、摘要、引言和讨论都收束到“基于强化学习与 MCTS 的资源约束量子布尔函数综合搜索方法”，明确 SSHR 只作为 CNOT-oriented baseline，并把“明显提升”的投稿前终点写成 phase/Rz-aware search、标准外部工具链复现和最小后端映射评估三项。
- `resource_nmcts_zh_manuscript_v32.tex` / `resource_nmcts_zh_manuscript_v32.pdf`：中文论文稿 v32，FPRM phase 搜索版；新增 `run_phase_parity_fprm_search.py`，对每个 `n<=6` 传统函数枚举 fixed-polarity Reed-Muller 极性并把 shifted parity phase 精确翻译回原变量，3 个 rank metric 共 531/531 行 up-to-global-phase 验证通过。`T/Rz=30` 目标相对 phase-parity ANF 为 59/0/118、平均 -0.47%，相对 RevKit 为 177/0/0、平均 -65.16%；该版本明确它是“真实但小幅”的 phase/Rz 搜索增量，不是最终 phase 方法。
- `resource_nmcts_zh_manuscript_v33.tex` / `resource_nmcts_zh_manuscript_v33.pdf`：中文论文稿 v33，n=24 完整验证桥接版；在 v32 phase 搜索主线基础上新增 `truth_bridge_n24`，使用位掩码 ANF truth-table evaluator 把完整 oracle 验证推进到 `n=24`。6 个生成式 ANF 函数、60 个方法行均通过完整 oracle 验证、ANF plan 验证和 emitted-circuit 符号验证，mismatch=0，平均 truth-table 构造时间 0.18 s/函数。该版本把完整 bridge 证据从 300/300 扩展为 360/360，同时明确 `n=25--40` 仍不是完整枚举。
- `resource_nmcts_zh_manuscript_v34.tex` / `resource_nmcts_zh_manuscript_v34.pdf`：中文论文稿 v34，n=25 完整验证桥接与 action-width probe 版；补充 `truth_bridge_n25` 和 width 6/12/24 probe，说明完整验证边界推进到 n=25，且盲目加宽候选集合不是当前主要收益来源。
- `resource_nmcts_zh_manuscript_v35.tex` / `resource_nmcts_zh_manuscript_v35.pdf`：中文论文稿 v35，Affine-FPRM phase search 版；补充有界可逆线性预条件与极性联合搜索，Affine-FPRM 在 `T/Rz=30` 目标下相对 fixed-polarity FPRM 为 81/0/96、平均 score 降低 2.51%，相对 RevKit proxy 为 177/0/0、平均降低 65.50%。
- `resource_nmcts_zh_manuscript_v36.tex` / `resource_nmcts_zh_manuscript_v36.pdf`：中文论文稿 v36，图表化投稿主稿；新增 `make_submission_figures.py` 生成 5 张主图和 source data，把正文重组为“问题-方法-外部基线-消融-验证-边界”的投稿结构，并按当前 source data 修正完整 truth-table bridge 为 400/400。
- `resource_nmcts_zh_manuscript_v37.tex` / `resource_nmcts_zh_manuscript_v37.pdf`：中文论文稿 v37，wide Affine-FPRM phase search 增量稿；新增 transform-budget 128 相对 budget 32 的配对分析，`T/Rz=30` 目标为 43/0/134、平均 synth-score 再降 0.60%，并保持 531/531 phase selected rows 验证通过。
- `resource_nmcts_zh_manuscript_v38.tex` / `resource_nmcts_zh_manuscript_v38.pdf`：中文论文稿 v38，learned phase candidate pruning 增量稿；新增 `train_phase_affine_policy.py`，在 `n<=5` 训练、held-out `n=6` 测试，policy top-512 相对 budget-32 为 17/0/21、`T/Rz=30` synth-score -2.47%，相对 wide-128 仅 +0.01%；但 same-budget random shortlist 也接近，因此写作上只作为可学习剪枝和候选空间密集性证据。
- `resource_nmcts_zh_manuscript_v39.tex` / `resource_nmcts_zh_manuscript_v39.pdf`：中文论文稿 v39，CirKit/RevKit CLI 外部 probe 增量稿；新增 legacy RevKit CLI exact-oracle reversible-synthesis portfolio，把每个函数嵌入为 `(x,y)->(x,y xor f(x))` 的 SPEC permutation，并运行 TBS/DBS/RMS 三个 flow。三流 531/531 行 usable，best-score portfolio 下 Pareto-Resource-NMCTS 相对 RevKit CLI 为 173/0/4、平均 score -67.28%，T-count -72.59%；但 peak ancilla 为 0/169/8、平均 +153.11%，因此写作上必须保留辅助线 trade-off。
- `resource_nmcts_zh_manuscript_v40.tex` / `resource_nmcts_zh_manuscript_v40.pdf`：当前中文同步精简稿。基于最新英文作者稿与 2026-07-10 证据更新，加入 9/9 baseline fairness、5/5 SSHR Table IV--VIII crosswalk、实验论据阶梯、反例型比较边界、`n=20--64` 符号验证、`n=21--30` 的 700/700 完整真值表 bridge，以及独立 320/160/160 train/validation/test 的 contextual-bandit fitted-Q Pareto 预算策略。该策略在 160 个测试函数上只运行 71 次 Pareto，保留 94.90% Pareto score gain，并降低 13.13% 保守搜索时间；相对 always-Pareto 的 +0.506% score regret 与相对 base 的 +4.48% peak-ancilla 代价同时保留。
- `resource_nmcts_zh_research_position.tex` / `resource_nmcts_zh_research_position.pdf`：中文研究定位稿，重新梳理“不从 SSHR 入手”的论文主线、AI 在搜索问题中的角色、当前证据边界和下一步明显提升目标。
- 最新 v4 稿已补充 `train_screen_depth_policy.py` 的结构级 depth policy 结果：n=14/16/18 训练、held-out n=20 测试，说明 AI 已能学习 screen 深度选择，但尚未超过固定 depth-2 的 score。
- 最新 v8 稿补充 `train_structure_gate.py` 的 screen-gated Resource-NMCTS 边界验证：原 n=20 切片资源持平且平均运行时间降低 75.58%，held-out n=19/20 合计 16/16 score 持平并平均节省 36.83%，但仍只作为运行时门控证据。

编译命令：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment/paper_latex_zh
latexmk -xelatex -g main_zh.tex
latexmk -xelatex -g resource_nmcts_zh_draft.tex
latexmk -xelatex -g resource_nmcts_zh_full.tex
latexmk -xelatex -g resource_nmcts_zh_report.tex
latexmk -xelatex -g resource_nmcts_zh_robustness.tex
latexmk -xelatex -g resource_nmcts_zh_neural_plan.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v2.tex
latexmk -xelatex -g resource_nmcts_zh_boolean_ring_v3.tex
latexmk -xelatex -g resource_nmcts_zh_stage_delivery.tex
latexmk -xelatex -g resource_nmcts_zh_adaptive_screen.tex
latexmk -xelatex -g resource_nmcts_zh_structure_policy_v5.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v6.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v7.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v8.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v9.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v10.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v11.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v12.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v13.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v14.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v15.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v16.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v17.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v18.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v19.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v20.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v21.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v22.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v23.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v25.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v26.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v27.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v28.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v29.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v30.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v31.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v32.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v33.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v34.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v35.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v36.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v37.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v38.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v39.tex
latexmk -xelatex -g resource_nmcts_zh_manuscript_v40.tex
latexmk -xelatex -g resource_nmcts_zh_research_position.tex
```

主要证据来源：

- `../DELIVERABLE_zh.md`
- `../results/analysis_traditional_resource.md`
- `../results/analysis_esop_baseline.md`
- `../results/analysis_search_contribution.md`
- `../results/analysis_weight_robustness.md`
- `../results/analysis_highdim_root_action_oracle.md`
- `../results/analysis_highdim_root_action_pairwise.md`
- `../results/analysis_neural_prior_highdim_pairwise_ablation.md`
- `../results/analysis_highdim_root_action_pairwise_widths.md`
- `../results/analysis_ultra_root_action_pairwise_widths.md`
- `../results/analysis_neural_prior_highdim_pairwise_wide_ablation.md`
- `../results/analysis_ultra_pairwise_wide_vs_recursive.md`
- `../results/analysis_ultra_pairwise_wide_vs_old_resource.md`
- `../results/analysis_ultra_boolean_linear_vs_deep.md`
- `../results/analysis_ultra_boolean_linear_vs_pairwise_resource.md`
- `../results/analysis_ultra_boolean_guard_vs_pairwise_wide.md`
- `../results/analysis_ultra_boolean_guard_vs_old_deep.md`
- `../results/analysis_boolean_neural_guard_vs_deterministic.md`
- `../results/analysis_mega_boolean_screen_vs_resource.md`
- `../results/analysis_giga_highdim_resource.md`
- `../results/analysis_mega_screen_deep_vs_screen.md`
- `../results/analysis_mega_screen_deep_vs_old_resource.md`
- `../results/analysis_giga_screen_deep_vs_screen.md`
- `../results/analysis_giga_screen_deeper_vs_deep.md`
- `../results/analysis_giga_screen_adaptive_vs_screen.md`
- `../results/analysis_giga_adaptive_resource_vs_and_direct.md`
- `../results/analysis_mega_screen_adaptive_vs_screen.md`
- `../results/analysis_mega_resource_vs_screen_adaptive.md`
- `../results/analysis_giga_resource_vs_boolean_screen.md`
- `../results/analysis_giga_resource_vs_and_direct.md`
- `../results/analysis_giga_resource_recursive_screen_vs_old.md`
- `../results/analysis_giga_resource_recursive_screen_vs_and_direct.md`
- `../results/analysis_giga_resource_deeper_vs_depth1_resource.md`
- `../results/analysis_giga_resource_deeper_vs_old_resource.md`
- `../results/analysis_giga_resource_deeper_vs_and_direct.md`
- `../results/analysis_boolean_screen_depth_policy.md`
- `../results/analysis_boolean_screen_depth_frontier_policy.md`
- `../results/analysis_boolean_screen_depth_frontier_policy_large.md`
- `../results/analysis_boolean_screen_depth_frontier_policy_cost_time003.md`
- `../results/analysis_screen_scale_depth_frontier_policy_terms.md`
- `../results/analysis_screen_scale_depth_frontier_policy_generalization_terms.md`
- `../results/analysis_screen_scale_depth_frontier_policy_large_generalization_terms.md`
- `../results/analysis_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.md`
- `../results/analysis_truth_bridge_terms.md`
- `../results/analysis_truth_bridge_n23_large_frontier_terms.md`
- `../results/analysis_truth_bridge_n23_cost_time003_frontier_terms.md`
- `../results/analysis_frontier_policy_upgrade.md`
- `../results/analysis_schedule_truth_bridge_n23_terms.md`
- `../results/analysis_schedule_metrics.md`
- `../results/analysis_ros_lut_proxy.md`
- `../results/analysis_toolchain_readiness.md`
- `../results/analysis_revkit_oracle_synth_traditional.md`
- `../results/analysis_revkit_highdim_timeout_probe.md`
- `../results/analysis_phase_rz_portfolio.md`
- `../results/analysis_rz_synthesis_cost.md`
- `../results/analysis_phase_parity_anf.md`
- `../results/analysis_phase_parity_fprm.md`
- `../results/analysis_phase_parity_affine_wide128.md`
- `../results/analysis_phase_affine_budget_wide128_vs_32.md`
- `../results/analysis_phase_affine_policy.md`
- `../results/analysis_revkit_cli_multiflow_traditional.md`
- `../results/analysis_revkit_cli_tbs_traditional.md`
- `../results/analysis_truth_bridge_n24_terms.md`
- `../results/toolchain_readiness.json`
- `../results/analysis_giga_screen_gate_vs_resource.md`
- `../results/analysis_structure_gate.md`
- `../results/analysis_exact_fprm_dp.md`
- `../results/analysis_exact_xag_mc.md`
- `../results/analysis_mega_highdim_resource.md`
- `../literature_notes.md`

当前稿件只主张逻辑层资源优势，不包含硬件 mapping、连通性约束或真实设备噪声模型。
