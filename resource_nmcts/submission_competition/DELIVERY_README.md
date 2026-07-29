# XA-202609 Resource-NMCTS 竞赛交付说明

本包交付可直接阅读的竞赛论文、LaTeX/图件源码、编译与实验代码、冻结 DuckDB、函数级统计、原始 JSONL 证据、模型权重、文献核验及环境快照。

## 核心结论与边界

- 冻结分析 ID：`xa202609-primary20-836553591061`。
- 主协议：20 个独立 Boolean 函数、6 个方法、3 个综合 seed，共 360 个计划单元；360 个全部通过逻辑与映射后精确验证（SSHR-Beam 在两个 AES 分量上的早期综合超时已通过 n=8 向量化补全）。
- 相对 Direct-ANF，Resource-NMCTS 在逻辑 T、逻辑 CNOT、native-2Q、mapped depth 上的函数级中位相对改善依次为 51.5%、16.6%、42.0%、45.2%；四项均通过预设双区间与分族 Holm 门槛。
- 五个基线 × 四个主指标共 20 个比较中，10 个满足严格“显著优于”门槛；其余均按中性或不占优报告。
- learned-prior clean pilot 主要为平局；60 个 Resource-NMCTS 单元中 54 个选择明确的确定性分支。因此组合收益不归因于神经网络。
- SSHR-Beam 是项目在 parallelotope 表示上的本地 beam-search 扩展，不是论文的 Gurobi/ILP 版 SSHR-I；本包不声称超过未运行的 SSHR-I。
- 当前硬件证据是无校准 synthetic Target 与无噪声精确验证；Qiskit Aer 仅检测到 CPU，RTX 5090 用于 PyTorch 训练/烟雾测试，不据此声称 GPU 加速了 Aer 或提升真实芯片保真度。

## 关键入口

- `paper/main.pdf`：20 页最终竞赛论文。
- `paper/main.tex`、`paper/references.bib`：论文与参考文献源码。
- `paper/figures/`：F0--F5 的 PDF/SVG/PNG、生成程序、source data、figure contract 与 manifest。
- `results/competition_primary20_final.duckdb`：冻结实验数据库。
- `results/final_stats/primary20_headline.{json,csv}`：20 个主比较的统一摘要。
- `evidence/final_analysis_manifest.json`：主统计输入、输出、coverage 与哈希链。
- `evidence/formal_coverage_audit.json`：360 个计划单元的完整 coverage 审计。
- `evidence/literature_verification_audit.{json,csv,md}`：23/23 条正文引用的 DOI/arXiv 核验。
- `evidence/environment_manifest.json`：Python/CUDA/GPU/Aer 能力和关键 artifact 哈希。
- `DELIVERY_MANIFEST.json`：包内每个文件的 SHA256、大小、来源与证据角色。
- `verify_delivery_manifest.py`：解压后逐文件验证大小与 SHA256。

## 环境与快速验证

推荐使用 `mcts-qoracle` conda 环境。在项目根目录执行：

```powershell
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
conda run -n mcts-qoracle python tests/tests_smoke.py
conda run -n mcts-qoracle python -m pytest `
  tests/test_final_primary20_report.py `
  tests/test_formal_coverage_audit.py `
  tests/test_hardware_validation_ingest.py `
  tests/test_hardware_runner.py `
  tests/test_competition_results_analysis.py `
  tests/test_experiment_db.py `
  tests/test_topology_mapping.py `
  tests/test_competition_benchmarks.py `
  tests/test_neural_training_split.py -q
```

最终交付前一次本地结果为 `60 passed, 15 subtests passed`，随后 `tests/tests_smoke.py` 输出 `smoke ok`。

解压后先做完整性检查：

```powershell
python verify_delivery_manifest.py
```

重建论文：

```powershell
Set-Location paper
xelatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

重新验证冻结摘要（脚本以只读方式打开 DuckDB）：

```powershell
conda run -n mcts-qoracle python analysis/build_final_primary20_report.py `
  --database results/competition_primary20_final.duckdb `
  --stats-dir results/final_stats `
  --coverage evidence/formal_coverage_audit.json `
  --consolidation-manifest evidence/formal_primary20_core3_final_manifest_v2.json
```

注意：该命令默认输出路径按开发树布局设计；在解压后的交付包内复核时，建议先复制包到原项目目录结构，或显式传入四个 `--output-*` 参数。不要覆盖包内冻结产物后再把它们视为原始证据。

## 完整性与提交前最后一步

最终 PDF SHA256 为 `b37d02768242ceb72bd1694faf2031544c14060a0c8a596c830e058b45f525f5`；冻结 DuckDB SHA256 为 `76f0369d09d74f6910126d84faa3162e9216edbea7ab23801c30a257b16774c3`。逐页视觉 QA 已渲染全部 20 页，自动裁切/空白页检查为 0 个 review pages，并人工检查 5 张联系表。

论文作者栏当前使用通用名称“XA-202609 参赛团队”。若赛事系统要求实名、单位或指导教师信息，请在提交前替换 `paper/main.tex` 中的 `\author{...}`，再按上述 XeLaTeX 链重编译；这会改变 PDF SHA256，应同步重建交付 manifest。

部分实验 provenance manifest 保留开发机绝对路径以证明原始执行位置；包内实际文件均由 `DELIVERY_MANIFEST.json` 以相对路径重新索引。过渡数据库、旧 schema 备份、失败的早期压力测试数据库和逐页 PNG 未纳入压缩包，以避免把历史中间态误当作冻结结果；原始成功、超时及 AI 消融 JSONL 已保留。
