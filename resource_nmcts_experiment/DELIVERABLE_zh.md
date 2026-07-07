# Resource-NMCTS 中文交付文档

更新时间：2026-07-07  
当前提交：`e08e67f Add ESOP baseline evidence and finish mega run`  
代码位置：`/Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment`

## 1. 项目定位

本项目面向量子布尔函数 oracle 综合，目标是在逻辑层降低 T-count、CNOT、深度和辅助比特等资源。当前方法不依赖 SSHR 的 parallelotope 结构，而是把布尔 oracle 综合建模为 ANF/FPRM 项集合上的搜索问题：

- 用资源加权目标函数评价候选线路：
  `score = T + 0.04*CNOT + 0.015*depth + 0.01*gates + 2*ancilla`。
- 用神经先验、MCTS、FPRM 极性搜索、线性因子分解和 Pareto archive 生成候选。
- 用 direct ANF、AND-direct ANF、ESOP、ABC、BDD、SSHR-H/SSHR-I 等作为外部或内部 baseline。
- 所有结果均是逻辑层资源估计，不包含硬件映射和连通性约束。

论文主张应限定为：资源约束、低 T-count、低加权 score 的量子布尔函数 oracle 综合方法。不能写成 CNOT-only 最优，也不能写成硬件映射优势。

## 2. 当前已完成内容

### 2.1 ESOP baseline 对比

新增 `analyze_esop_baseline.py`，专门从同一 benchmark 的内部 ESOP-MILP 和外部 ABC-ESOP 结果中生成 ESOP 视角分析。

主要产物：

- `results/analysis_esop_baseline.md`
- `results/summary_esop_baseline.csv`
- `paper_latex/tables/esop_baseline_by_n.tex`

核心结果：

| Baseline | 函数数 | T-count 变化 | CNOT 变化 | ancilla 变化 | score 变化 | score 胜/负/平 |
|---|---:|---:|---:|---:|---:|---:|
| Internal ESOP-MILP | 177 | -51.23% | -37.13% | -15.09% | -48.49% | 167/3/7 |
| ABC-ESOP export | 177 | -25.18% | -4.38% | -14.04% | -23.00% | 170/1/6 |

按变量数分组：

- 对 internal ESOP-MILP：`n=3..6` 每组 T-count 和 CNOT 总量都更低；ancilla 在 `n=3` 持平，在 `n=4..6` 更低。
- 对 ABC-ESOP：`n=3..6` 每组 T-count 和 ancilla 总量都更低；CNOT 在 `n=3..5` 更低，在 `n=6` 高 `0.41%`。

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

## 3. 当前文件交付清单

### 3.1 核心代码

- `factor_plan.py`：FPRM/线性因子/beam/greedy 计划生成。
- `synthesizers.py`：方法组合、Resource/Profile/Pareto 候选选择。
- `run_experiments.py`：实验运行、隔离超时、resume/replace 逻辑。
- `analyze_results.py`：内部实验分析。
- `analyze_runtime.py`：运行时间和资源表生成。
- `analyze_external_baselines.py`：外部 baseline 对比分析。
- `analyze_esop_baseline.py`：新增 ESOP 专项分析。

### 3.2 结果文件

- `results/raw_traditional_resource.csv`
- `results/raw_external_traditional_resource_n6.csv`
- `results/analysis_esop_baseline.md`
- `results/summary_esop_baseline.csv`
- `results/raw_mega_highdim_resource.csv`
- `results/analysis_mega_highdim_resource.md`
- `results/runtime_mega_highdim_resource.md`
- `results/analysis_external_mega_highdim_resource.md`

### 3.3 论文文件

- `paper_latex/main.tex`
- `paper_latex/main.pdf`
- `paper_latex/tables/esop_baseline_by_n.tex`
- `paper_latex/tables/resource_mega_highdim_resource.tex`
- `paper_latex/tables/runtime_mega_highdim_resource.tex`

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
- `tests_smoke.py` 通过，输出 `smoke ok`。
- `py_compile` 通过。
- `git diff --check` 通过。
- `raw_mega_highdim_resource.csv` 审计：84 行、0 error、0 skipped、0 incorrect。

Git 状态：

- 最新提交：`e08e67f Add ESOP baseline evidence and finish mega run`
- 远端：`origin/main` 已同步。
- 注意：仓库根目录外层曾出现未跟踪压缩包 `resource_nmcts_experiment.zip`，不属于本次代码交付。

## 6. 论文当前可写主张

推荐主张：

1. 本文提出一种面向资源约束的量子布尔函数 oracle 综合方法，将问题表示为 ANF/FPRM 项集合上的搜索。
2. 方法不依赖 SSHR 的 parallelotope 结构，可以把 SSHR 作为外部 baseline。
3. 在 `n<=6` 传统 baseline 切片上，Pareto-Resource-NMCTS 对 ESOP cube beam、ESOP-MILP 和 ABC-ESOP 均有明显 score 优势。
4. 在 `n=18` 高维随机 ANF stress test 上，fast linear-pair guard 与 Resource/Profile/Pareto 可稳定改善 root-beam，说明高维 guard 不再只是保底策略。
5. 外部 ABC/BDD 结果支持低加权资源和低 ancilla 优势，但 depth 仍是 ABC-AIG/ABC-XAG 的优势指标。

不应写的主张：

1. 不应写“CNOT 全面优于 SSHR/ESOP/ABC”。
2. 不应写“硬件映射后仍然更优”，因为当前没有 mapping。
3. 不应写“Pareto 在 n=18 有额外独立收益”，因为 n=18 的 Pareto 当前故意收窄为稳定 guard。
4. 不应直接拿 SSHR 论文表格里的 ESOP 总量横比，除非函数集和成本模型一致。

## 7. 下一步建议

当前还需要一个更强的“AI/MCTS 贡献拆解”实验，否则审稿人可能认为主要提升来自 FPRM/linear-pair 工程启发，而不是强化学习或 MCTS。

建议下一步：

1. 做 `no-neural-prior`、`heuristic-only`、`beam-only`、`MCTS-without-profile` 的统一 ablation。
2. 选择 `n<=6` 和 `n=14/15/16/18` 两个尺度分别汇报。
3. 把结果写成“搜索策略贡献”而不是“单一启发式贡献”。
4. 如果时间允许，补一个小规模 exact/ILP 或 exhaustive oracle slice，强化公平性。

最有价值的下一个表格：

| 设置 | 函数集 | 方法 | 相对当前方法 score 差距 | 目的 |
|---|---|---|---:|---|
| no neural prior | n<=6 traditional | Resource/Pareto | 待测 | 证明 neural prior 贡献 |
| heuristic-only | n<=6 traditional | Resource/Pareto | 待测 | 证明 MCTS/搜索贡献 |
| beam-only | highdim | fast/root/linear | 待测 | 区分 beam 与 portfolio |
| profile disabled | resource sweep | Profile/Pareto | 待测 | 证明 profile/Pareto archive 贡献 |

## 8. 当前结论

当前版本已经具备一条比 SSHR 路线更适合投稿的主线：

“基于资源感知搜索、神经先验和 MCTS/Pareto 候选选择的量子布尔函数 oracle 综合方法，在同 benchmark 的 ESOP、ABC、BDD 和 direct ANF baseline 上展示显著低 T-count 与低加权资源优势。”

但是投稿前还需要继续补强“AI 搜索本身带来的贡献”这一点。否则文章容易被评价为一组 FPRM/ESOP 工程启发的组合，而不是强化学习与 MCTS 方法论文。
