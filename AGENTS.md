See CLAUDE.md for the July 18 Resource-NMCTS technical documentation.

## 工作区边界（改 v40 只在这里）

本目录是 **Resource-NMCTS 中文稿 v40 + 对应代码** 的独立工作区，不是 XA-202609 竞赛主线。

| 项 | 本仓库 |
|---|---|
| 本地路径 | `/Users/zhouzixiang/Desktop/resource_nmcts_v40` |
| Git 根 | **本目录**（不要写、不要打开 `/Users/zhouzixiang/Desktop/tzb`） |
| 远程 | `git@github.com:zhouzixiang1/sshr.git` |
| 分支 | `v40-20260718`（跟踪 `origin/v40-20260718`） |
| 冻结起点 | `2d264f2`（2026-07-18 23:37，AES S-box / 文献 / v40 正文最后一次定稿） |
| 工作目录 | 所有命令在 `resource_nmcts/` 下执行 |

后续改 v40 论文、代码、结果或投稿包：**只改本目录的 `resource_nmcts/` 等 v40 文件，在本文件夹提交并 `git push`**。推送只更新 `v40-20260718`，不会改竞赛 `main`。

`xa202609-oracle/` 交接快照已于 2026-08-13 移出至竞赛工作区 `/Users/zhouzixiang/Desktop/tzb/xa202609-oracle/`（它自己的私有远程 `zhouzixiang1/xa202609-oracle` 不变）。本目录不再保留该嵌套仓。**不要**把它提交进本分支（公开 `sshr`）；tzb 的 `.gitignore` 已加 `xa202609-oracle/` 防泄密。

### 目录关系

| 路径 | 是什么 | 怎么用 |
|---|---|---|
| 本目录 `resource_nmcts/` | v40 代码与论文 | **唯一允许改 v40 的位置** |
| `/Users/zhouzixiang/Desktop/tzb/xa202609-oracle/` | 2026-07-28 服务器交接快照（已移出本目录；嵌套 Git，远程 `zhouzixiang1/xa202609-oracle`） | 只读参考。Git 不同源；不要当 v40 编辑区；tzb 已 gitignore |
| `/Users/zhouzixiang/Desktop/tzb` | XA-202609 竞赛主工作区（`docs/` + `experiments/` + `misc/`，分支 `main`） | 同一 GitHub 仓库 `sshr` 的另一条分支；**禁止**把竞赛代码、E2–E6、身份材料合进本分支，也**禁止**为了改 v40 去编辑 `tzb` |

`CLAUDE.md` 里若仍写 Git 根为 `Desktop/tzb`，以**本文件**为准。

### Agent 操作规则

- 只修改本工作树中的 v40 文件（`resource_nmcts/`、`_archive/` 说明、本目录 `AGENTS.md`/`CLAUDE.md`）。
- 不要为了改 v40 去编辑 `tzb`，也不要改 `tzb/xa202609-oracle/` 来冒充 v40 更新。
- 保持布局为 `_archive/` + `resource_nmcts/`（2026-08-13 起重组为 `文本/代码/结果/模型` 四类），不要改成竞赛的 `docs/experiments/misc`。
- `xa202609-oracle/` 已移出至 tzb；本目录 `.gitignore` 的旧忽略行保留仅作历史记录。它是私有交接仓，推进公开 `sshr` 会泄密。
- 本目录对 v40 线是浅克隆，本地几乎没有 `2d264f2` 之前的提交；日常改文件、提交、推送即可。
- 远程 `sshr` 是公开仓库。不要提交竞赛未公开证据、私钥或已填写的身份元数据。

## 速查（AI agent 用）

- **Git 根**：本目录 `/Users/zhouzixiang/Desktop/resource_nmcts_v40`
- **工作目录**：所有命令在 `resource_nmcts/` 下执行
- **主入口**：`resource_nmcts/src/synthesizers.py` 的 `synthesize(method, bf, config, seed, model_path)`
- **主环境**：`/opt/anaconda3/envs/mcts-qoracle/bin/python`（torch + PuLP）；SSHR-I 另需 `sshr` 环境（Gurobi）
- **冒烟测试**：`cd resource_nmcts && /opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py`
- **逻辑层定位**：引擎只做逻辑 MCT 级综合（X/CNOT/MCT），不做硬件映射，没有 Rz 旋转门综合后端
- **两套布局**：工作树分层版（脚本在 `analysis/`、`scripts/`、`submission/`）vs payload 扁平版（`submission_package/dist/*.tar.gz`，审稿人用）；rebuild/verify 脚本为扁平布局设计
- **已修复的路径 bug**：`sshr_i.py:320` 裸 import、`synthesizers.py:28` STRUCTURE_GATE_MODEL 路径（`.parent` → `.parent.parent`）
- **交接快照已移出**：`xa202609-oracle/` 已于 2026-08-13 移至 `/Users/zhouzixiang/Desktop/tzb/xa202609-oracle/`（只读、独立 Git、tzb 已 gitignore）
