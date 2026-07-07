# 中文 LaTeX 论文草稿

本目录存放中文论文草稿：

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

编译命令：

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment/paper_latex_zh
latexmk -xelatex -g main_zh.tex
```

主要证据来源：

- `../DELIVERABLE_zh.md`
- `../results/analysis_traditional_resource.md`
- `../results/analysis_esop_baseline.md`
- `../results/analysis_search_contribution.md`
- `../results/analysis_highdim_root_action_oracle.md`
- `../results/analysis_exact_fprm_dp.md`
- `../results/analysis_exact_xag_mc.md`
- `../results/analysis_mega_highdim_resource.md`
- `../literature_notes.md`

当前稿件只主张逻辑层资源优势，不包含硬件 mapping、连通性约束或真实设备噪声模型。
