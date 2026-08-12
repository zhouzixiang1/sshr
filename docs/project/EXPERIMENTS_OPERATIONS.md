# Current experiment operations

工作目录：`../../experiments/`。其源码布局保持 `src/`、`scripts/`、`analysis/`、
`submission/`、`tests/`、`models/`、`results/`，使现有 Python 相对路径继续有效。

## 核心数据流

`BooleanFunction`（真值表）→ Möbius 变换生成 ANF 项集 → 枚举
`FactorAction` → policy/heuristic 排序 → greedy/beam/NMCTS 生成 `Plan` →
发射为 X/CNOT/MCT 逻辑线路 → GF(2) 符号验证。

- `src/synthesizers.py`：统一入口；`synthesize_detailed()` 输出 `PlanTrace`、逻辑 IR/QASM 与验证记录。
- `src/nmcts_solver.py`：最小化成本的 PUCT/MCTS；policy scorer 和 rollout scorer 已分离。
- `src/foundation/`、`src/search/value_net.py`：置换等变 policy/value 的开发路径。
- `scripts/run_p0_freeze.py`：从空目录创建 checksum-verified P0 bundle。
- `scripts/run_c0c7_pilot.py`：C0--C7 因果验证；当前 evidence 显示 value 不应部署。

## 运行命令

```bash
cd experiments
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests -q
/opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/run_p0_freeze.py
```

论文权重必须显式设置为 `T=1.0, CNOT=0.04, depth=0.015, gates=0.01,
ancilla=2.0`；裸 `SearchConfig()` 的默认权重不同。

## 结果与历史

`results/xa202609/` 保留当前 P0/E1--E4 证据、E4-v2 两阶段 frozen replication、
formal v4 provenance bundle、E5 preflight/v1.1/negative-audit 记录，以及 E6
Q4AI 四臂 development 因果实验。
目录存在不等于实验验收：E4-v2 改善未获支持，E5 没有 accepted endpoint。
探索性阈值扫描、被替代的 pilot、E5 首次 release 失败记录和旧论文实验在
`../../misc/archive/experiments/`；这些归档只读，不得覆盖。下一核心方向为
E6-MSO 的 D1 机制诊断：机制 MVP、frozen-formal-v4 shared head、final-measurement
replay 与确定性单 arm trainer 已经进入真实四臂 run；结果 bundle 为
`results/xa202609/20260812-e6-q4ai-causal-v1-full-s20260912/`。它包含 64 个训练
case 和 32 个 held-out case，独立 verifier 11/11 通过，但 primary QAOA-control
差为 `+0.0949778`（越低越好），95% CI `[0.0696384,0.1237673]`，显著反向于改善。
下一步先诊断 QAOA/random 32/32 endpoint 相同、31/32 空选择的作用链，不在本次
held-out 上事后调参。greedy `Y=0.775639` 只作非等计算描述。

E6 复验从 `experiments/` 执行：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python scripts/verify_e6_replay_training_bundle_v1.py \
  results/xa202609/20260812-e6-q4ai-causal-v1-full-s20260912
```

该五文件 bundle 绑定代码提交 `e850c0c`、证据提交 `8cc5f3c` 与 snapshot
`18b758ac3e432a5d4e9f0ba1f8be7e17bd1b848b6212234eea9d2e842d4cc76a`。原始 full
runner 用时 140.32 秒，独立 full verifier 用时 145.03 秒；这些时间只用于操作
预估，不是速度性能证据。formal/performance/generalization/hardware/advantage 均为
false。

`paper_latex`、`paper_latex_zh` 和 `submission_package` 是指向文档/归档的兼容
链接，目的是让旧的投稿工具仍能定位历史资源；新文稿从 `../../docs/papers/` 管理。
