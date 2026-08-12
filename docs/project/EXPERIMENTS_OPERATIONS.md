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
formal v4 provenance bundle，以及 E5 preflight/seal/v1.1/negative-audit 记录。
目录存在不等于实验验收：E4-v2 改善未获支持，E5 没有 accepted endpoint。
探索性阈值扫描、被替代的 pilot、E5 首次 release 失败记录和旧论文实验在
`../../misc/archive/experiments/`；这些归档只读，不得覆盖。下一核心方向为
E6-MSO 多输出共享 Oracle：机制 MVP、隔离 frozen-formal-v4 shared head、外部锁
final-measurement replay 合同、确定性单 arm head-only trainer 和 development
sealed-head schema/inference loader 均已实现并完成对抗测试；但尚无真实 replay 训练
run、真实 trained/sealed artifact、因果实验、formal runner/bundle/verifier/result 或
性能证据，598→581 不作正式证据。

`paper_latex`、`paper_latex_zh` 和 `submission_package` 是指向文档/归档的兼容
链接，目的是让旧的投稿工具仍能定位历史资源；新文稿从 `../../docs/papers/` 管理。
