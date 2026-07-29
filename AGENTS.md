See CLAUDE.md for project documentation.

## 速查（AI agent 用）

- **Git 根**：本目录（Windows 本机 `D:\University\code\sshr`，macOS 旧机曾为 `/Users/zhouzixiang/Desktop/tzb`）
- **工作目录**：所有命令在 `resource_nmcts/` 下执行
- **主入口**：`resource_nmcts/src/synthesizers.py` 的 `synthesize(method, bf, config, seed, model_path)`
- **主环境**：Windows 本机用 conda 环境 `mcts-qoracle`（`C:\Users\32143\.conda\envs\mcts-qoracle\python.exe`，torch + PuLP）。脚本里一律用 `python` 或 `sys.executable`，勿写死平台路径。SSHR-I 另需 Gurobi（仅 macOS `sshr` 环境，Windows 无）
- **冒烟测试**：`cd resource_nmcts && python tests/tests_smoke.py`（`python` 须指向 `mcts-qoracle` 环境）
- **逻辑层定位**：引擎只做逻辑 MCT 级综合（X/CNOT/MCT），不做硬件映射，没有 Rz 旋转门综合后端
- **两套布局**：工作树分层版（脚本在 `analysis/``scripts/``submission/`）vs payload 扁平版（`submission_package/dist/*.tar.gz`，审稿人用）；rebuild/verify 脚本为扁平布局设计
- **已修复的路径 bug**：`sshr_i.py:320` 裸 import、`synthesizers.py:28` STRUCTURE_GATE_MODEL 路径（`.parent` → `.parent.parent`）
- **Windows 兼容**：`.gitattributes` 强制 `*.sh`/`*.ps1`/`*.py` 用 LF；`.sh` 脚本 `PYTHON_BIN` 默认 `python`。详见 CLAUDE.md「Windows 平台兼容性」段
