# 中文 LaTeX 论文草稿

本目录存放中文论文草稿：

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

文件：

- `main_zh.tex` / `main_zh.pdf`：现有中文主稿。
- `resource_nmcts_zh_draft.tex` / `resource_nmcts_zh_draft.pdf`：独立中文技术论文草稿，包含更新后的 $n=16$ recursive linear-pair guard 结果。
- `resource_nmcts_zh_full.tex` / `resource_nmcts_zh_full.pdf`：当前更完整的中文论文草稿，整合 $n=16$ baseline-preserving AI guard、$n=18$ stress test、搜索贡献分解和 exact 小规模参照。
- `resource_nmcts_zh_report.tex` / `resource_nmcts_zh_report.pdf`：中文论文报告版，按“主张与边界、相关工作、方法、实验、结果、讨论”组织。
- `resource_nmcts_zh_robustness.tex` / `resource_nmcts_zh_robustness.pdf`：中文投稿论证稿，突出独立于 SSHR 的 Resource-NMCTS 主线、n=16 清洗后的 240 行结果和多资源权重鲁棒性分析。
- `resource_nmcts_zh_report.tex` / `resource_nmcts_zh_report.pdf`：中文论文报告版，更明确地区分研究主张、实验支撑和当前边界，适合继续讨论与修改。

编译命令：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment/paper_latex_zh
latexmk -xelatex -g main_zh.tex
latexmk -xelatex -g resource_nmcts_zh_draft.tex
latexmk -xelatex -g resource_nmcts_zh_full.tex
latexmk -xelatex -g resource_nmcts_zh_report.tex
latexmk -xelatex -g resource_nmcts_zh_robustness.tex
latexmk -xelatex -g resource_nmcts_zh_report.tex
```

主要证据来源：

- `../DELIVERABLE_zh.md`
- `../results/analysis_traditional_resource.md`
- `../results/analysis_esop_baseline.md`
- `../results/analysis_search_contribution.md`
- `../results/analysis_weight_robustness.md`
- `../results/analysis_highdim_root_action_oracle.md`
- `../results/analysis_exact_fprm_dp.md`
- `../results/analysis_exact_xag_mc.md`
- `../results/analysis_mega_highdim_resource.md`
- `../literature_notes.md`

当前稿件只主张逻辑层资源优势，不包含硬件 mapping、连通性约束或真实设备噪声模型。
