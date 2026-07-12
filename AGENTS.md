See CLAUDE.md for project documentation.

## 速查（AI agent 用）

- **Git 根**：本目录 `/Users/zhouzixiang/Desktop/tzb`
- **工作目录**：所有命令在 `resource_nmcts/` 下执行
- **主入口**：`resource_nmcts/src/synthesizers.py` 的 `synthesize(method, bf, config, seed, model_path)`
- **主环境**：`/opt/anaconda3/envs/mcts-qoracle/bin/python`（torch + PuLP）；SSHR-I 另需 `sshr` 环境（Gurobi）
- **冒烟测试**：`cd resource_nmcts && /opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py`
- **逻辑层定位**：引擎只做逻辑 MCT 级综合（X/CNOT/MCT），不做硬件映射，没有 Rz 旋转门综合后端
- **两套布局**：工作树分层版（脚本在 `analysis/``scripts/``submission/`）vs payload 扁平版（`submission_package/dist/*.tar.gz`，审稿人用）；rebuild/verify 脚本为扁平布局设计
- **已修复的路径 bug**：`sshr_i.py:320` 裸 import、`synthesizers.py:28` STRUCTURE_GATE_MODEL 路径（`.parent` → `.parent.parent`）
