# 中文 LaTeX 论文草稿

本目录存放中文论文草稿：

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

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
- `../results/analysis_screen_scale_depth_frontier_policy_terms.md`
- `../results/analysis_screen_scale_depth_frontier_policy_generalization_terms.md`
- `../results/analysis_truth_bridge_terms.md`
- `../results/analysis_schedule_metrics.md`
- `../results/analysis_giga_screen_gate_vs_resource.md`
- `../results/analysis_structure_gate.md`
- `../results/analysis_exact_fprm_dp.md`
- `../results/analysis_exact_xag_mc.md`
- `../results/analysis_mega_highdim_resource.md`
- `../literature_notes.md`

当前稿件只主张逻辑层资源优势，不包含硬件 mapping、连通性约束或真实设备噪声模型。
