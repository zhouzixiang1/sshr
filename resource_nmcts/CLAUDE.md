# CLAUDE.md — Resource-NMCTS

Resource-Constrained Neural MCTS for Boolean Oracle synthesis. Git 根在上级目录 `/Users/zhouzixiang/Desktop/tzb`，工作目录是本目录 `resource_nmcts/`。完整项目文档见上级 `CLAUDE.md`。

## 数据流（一句话）

`BooleanFunction`（真值表）→ Möbius 变换得 ANF 项集 → 枚举候选因子动作（`factor_plan.py`）→ 神经/启发式打分排序 → greedy/beam/MCTS 构造 `Plan` 树 → `emit_plan_to_circuit` 发射成 X/CNOT/MCT 门序列 → `verify_oracle` 位并行符号验证 → `SynthesisResult`。

## 关键架构事实

- 引擎严格停留在**逻辑 MCT 级**（X/CNOT/MCT），不做硬件映射/路由/噪声
- `src/` 里**没有**独立的 Rz 旋转门综合后端；"phase" 仅指 FPRM 输入极性 + 相对相位 Toffoli 成本 + logical_and 门模式
- `src/sshr_lib/bool_func.py` 是事实上的布尔原语真源（`BooleanFunction`/`mct_cost`）；`src/bool_func.py` 是无人 import 的影子副本
- MCTS 求解器是 **minimize** 成本方向（与 AlphaZero 相反）
- `synthesize()`（synthesizers.py:1244）是唯一公开入口；portfolio 方法（`resource_nmcts`/`pareto_resource_nmcts`）递归调用叶子方法再用 Pareto 前沿选最优

## Quick Commands

```bash
# Working directory: resource_nmcts/

# Import check
/opt/anaconda3/envs/mcts-qoracle/bin/python -c "from src.synthesizers import synthesize; print('OK')"

# Smoke test
/opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py

# Run experiments
./scripts/run_experiments.py --preset smoke
```

## Package Paths

All imports use `from src.xxx import ...` from the project root.
SSHR vendored deps at `src/sshr_lib/`.
