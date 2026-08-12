# XA-202609 Quantum Oracle Synthesis

本仓库按工作性质只保留三个业务目录：

```text
tzb/
├── docs/          # 赛题、方案、论文、报告、PPT 与交付说明
├── experiments/   # 当前可运行的代码、模型、配置、测试和 XA 验证结果
└── misc/          # 历史实验、旧文稿、旧投稿包、缓存和本机配置
```

根目录的 `AGENTS.md`、`CLAUDE.md`、`.gitignore` 和 `.env.example` 是项目控制
文件；`.git/` 是版本库元数据。它们不是业务资料目录。

## 从哪里开始

1. 当前任务与风险边界：[`docs/project/PROJECT_STATUS_XA202609.md`](docs/project/PROJECT_STATUS_XA202609.md)
2. 实验路线与停止条件：[`docs/planning/EXPERIMENT_ROADMAP_XA202609.md`](docs/planning/EXPERIMENT_ROADMAP_XA202609.md)
3. 机器可读验收标准：[`docs/contracts/COMPETITION_ACCEPTANCE_MATRIX.json`](docs/contracts/COMPETITION_ACCEPTANCE_MATRIX.json)
4. 竞赛学术报告：[`docs/competition/report/`](docs/competition/report/)
5. 文稿与 Overleaf 同步：[`docs/papers/OVERLEAF_REPOSITORIES.md`](docs/papers/OVERLEAF_REPOSITORIES.md)

## 当前实验入口

```bash
cd experiments
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests -q
/opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py
```

公开综合入口为 `experiments/src/synthesizers.py::synthesize(...)`，仍只实现逻辑
X/CNOT/MCT 层的布尔 Oracle 综合。QAOA 固定预算调度、synthetic-profile 原生门/
路由/含噪执行和根动作反馈已作为独立扩展层实现并验证，但没有改变公开入口的逻辑
成本模型，也不是真机、量子加速或性能优势证据。

当前 XA 证据只保留在 `experiments/results/xa202609/`，覆盖 P0/E1、E2 QAOA、
E3 原生/含噪反馈、E4/E4-v2、formal v4、E5 负审计/可移植性链，以及 E6
replay→shared-head 的开发机制实验。早期 legacy QAOA replay 主比较显著反向；D2
将 teacher 改为正整程序 resource-gain credit 后，在 fresh structured 与 OOD 的同源
permuted-control 对比分别得到 `delta Y=-0.1688789442`（32/0/0）和
`-0.1535114735`（31/1/0）。QAOA 臂仍略弱于 greedy anchor，因此只构成
development mechanism repair，不是 formal/performance/advantage evidence。
参数扫描、被替代的 run 和旧论文实验均在 `misc/archive/`，只读且不应被重写。

## 文稿原则

中文主文稿位于 `docs/papers/resource_nmcts/chinese/`，其目标 Overleaf 仓库、同步
范围和安全命令均由 `docs/papers/resource_nmcts/overleaf/` 管理。任何准备交付的
文稿改动都先在本地编译，再通过同步脚本检查差异，最后才推送到 Overleaf。
