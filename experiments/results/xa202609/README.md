# XA-202609 experiment runs

该目录只保存当前 XA 证据。历史论文的平铺 `raw_*.csv`、`summary_*.csv`、
`manifest_*.json` 和 `analysis_*.md` 已移至
`../../../misc/archive/experiments/resource_nmcts-results/`，不得直接作为 XA
完成证据。

每次运行使用不可复用的目录名：

```text
YYYYMMDD-HHMMSS-<track>-<slug>-s<seed>/
├── run.json
├── raw.jsonl
├── summary.json
├── verifier.json
├── events.jsonl
├── stdout.log
├── stderr.log
├── artifacts.manifest.json
└── checksums.sha256
```

允许的主 track：

- `p0-freeze`：环境、SHA、smoke、回归和契约冻结；
- `e1-equivariant`：prior/value/C0–C7；
- `e2-qaoa`：经典与 QAOA diversity scheduler；
- `e3-native-noise`：原生分解、路由、理想等价、含噪与反馈；
- `e4-crypto`：AES/SM4/PRESENT/ASCON 案例；
- `hardware-routes`：三路线 capability、离子阱理想酉适配与光量子 fail-closed 边界；
- `e5-e2e`：端到端原型与演示。
- `e6-q4ai-causal`：QAOA final-measurement replay 到 shared policy/value head 的
  四臂单研究者确定性 development 因果实验。

`raw.jsonl`、事件流和日志默认留在本机/服务器 artifact storage；经 verifier
确认的小型 summary、manifest、校验和及 claim map 才复制到
`../../../docs/competition/evidence/`。不得在文件中写入凭据、私有报名信息或本机绝对路径。

执行顺序和验收门见：
`../../../docs/planning/EXPERIMENT_ROADMAP_XA202609.md`。

当前通过验收的 E2 主矩阵：

- `20260810-e2-qaoa-scheduler-v1-s120000/`：20 个 held-out 函数、3 个
  搜索种子、7 种同池同预算调度器，共 420 条端到端 trial；verifier 与 bundle
  checksum 均通过。冻结配置见
  `../../configs/xa202609/e2_qaoa_scheduler_v1.json`。

当前通过验收的三路线兼容 bundle：

- `20260812-hardware-routes-v1-s202609/`：7 个 canonical/SHA-bound 文件；
  独立 verifier 重算超导编译与 seeded noise、离子阱全基态/全酉矩阵和光量子
  unsupported boundary，全部检查通过；三条路线均为 `hardware_execution=false`。

当前 E6 Q4AI development 负证据：

- `20260812-e6-q4ai-causal-v1-full-s20260912/`：采用精简的五文件合同
  `config.json/results.json/raw.jsonl/heldout_evaluation.json/checksums.sha256`，绑定
  clean source `e850c0c` 和 snapshot
  `18b758ac3e432a5d4e9f0ba1f8be7e17bd1b848b6212234eea9d2e842d4cc76a`；64 个
  `n=6/7` train case、32 个 `n=4/5` held-out case，独立 verifier 11/11 通过。
  primary QAOA-control 差为 `+0.0949778`（越低越好），95% CI
  `[0.0696384,0.1237673]`，`p=9.9999e-6`，W/T/L=`0/3/29`；QAOA 与 random
  endpoint 32/32 相同且各有 31/32 空选择。greedy `Y=0.775639` 仅作非等计算
  描述。该目录是 development negative evidence，不是 formal/performance/
  generalization/hardware/advantage evidence。

复验命令：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_e6_replay_training_bundle_v1.py \
  results/xa202609/20260812-e6-q4ai-causal-v1-full-s20260912
```
