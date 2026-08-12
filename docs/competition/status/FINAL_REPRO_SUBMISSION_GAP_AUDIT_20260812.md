# XA-202609 最终复现与提交包验收缺口审计

审计日期：2026-08-12（Asia/Shanghai）

审计范围仅覆盖当前工作树中的环境定义、clean-install verifier、两套 demo、提交包
builder/verifier 与相关证据文档。本次未联网、未创建新环境，也未修改 E4-v2 runner、
PPT 或中文主稿。

## 一页结论

当前项目已经具备可执行的**技术验收骨架**：精确版本环境、模型哈希检查、完整 demo、
离线确定性 fallback、实验 bundle verifier、白名单式提交包 builder，以及与 builder
独立的 fail-closed verifier。2026-08-12 对当前工作树做的定向复核为：

- `test_competition_submission.py`、`test_offline_fallback.py`、
  `test_competition_demo.py` 合计 `10 passed`；
- QAOA 竞赛 demo verifier 为 `13/13`；
- 离线 fallback verifier 为 `14/14`；
- `experiments/results/xa202609/` 下现有 11 个 `verifier.json` 均为
  `ok=true`，包括 E1--E4 和当前 E4-v2 tiny calibration/test bundle。

但当前状态仍不是“最终可提交包”：工作树尚未绑定到冻结提交，fresh-install 证据早于
最近的 fallback、提交包和 E4-v2 变更，最终人工授权目录不存在，E4-v2 snapshot 也尚未
纳入提交范围。最终 builder 对这些条件保持拒绝放行是正确行为。

2026-08-12 后续收口已将主 demo 的 manifest/checksum/log 与 fallback 的
manifest/checksum/log/QASM 全部加入 staging 白名单和独立 verifier 必需集合；同时从
demo 生成源头移除了本机 checkout 绝对路径。定向测试为 `10 passed`，另一次独立
internal-audit build 生成 178 文件，staging 与 tar.gz verifier 均为 `ok=true`，两套
包内局部 checksum 也全部通过。E4-v2 tiny 依约暂不纳入。

## 已被当前证据证明的部分

| 项目 | 当前证据与边界 | 结论 |
|---|---|---|
| 核心环境定义 | `environment.yml` 固定 CPython 3.11.15；`core.txt` 精确固定 NumPy、SciPy、PuLP、PyTorch；`dev.txt` 精确固定 pytest | 已定义，可用于最终重建 |
| clean-install 验收程序 | `verify_clean_install.py` 检查 Python/依赖版本、SciPy MILP、PuLP、模型 SHA-256 与参数量、QAOA mini、native/noise mini，并在默认模式运行 smoke 和完整竞赛 demo | 程序已闭环；`--quick` 明确不是 clean-install 证据 |
| 历史 fresh-install | `CLEAN_INSTALL_EVIDENCE.md` 记录 Darwin arm64 新建 CPython 3.11 venv、`pip check`、默认 verifier、`217 passed` 和 `smoke ok` | 证明当时快照可安装；尚未证明最终冻结快照 |
| QAOA 竞赛 demo | 持久化输出由独立 verifier 复核，当前 `13/13` 通过；明确 synthetic profile、非真机、非性能证据、无量子优势主张 | 已通过当前工作树复核 |
| 离线 fallback | 不加载 learned policy/value、不调用 QAOA；逻辑语义、QASM、native 映射、含噪轨迹、manifest/checksum 均重算，当前 `14/14` 通过 | 已完成可用性兜底，且与主 demo 主张严格分离 |
| 实验 bundle | 现有 E1--E4、E4-v2 calibration/test 的 11 个 verifier 均报告 `ok=true` | bundle 内部完整性已证明；不能自动提升为性能或真机证据 |
| 提交包技术门 | 定向测试实际构建 internal-audit staging 与 tar.gz，验证目录/归档、篡改检测和路径穿越拒绝 | 内部演练链已证明 |
| 最终授权门 | 缺授权时 builder 拒绝生成 final；占位符、错误声明、误导性文件名均失败 | fail-closed 行为已证明，最终授权本身未完成 |

## 优先级缺口与最小安全动作

### P0：最终提交的硬门

| 缺口 | 当前状态 | 最小安全动作 | 预计耗时 |
|---|---|---|---|
| 冻结 Git/source 身份 | 当前 `HEAD=2d264f2`，本地缓存显示 `main` 落后 `origin/main` 1 个提交；工作树有 3 个 tracked 修改、2776 个 tracked 删除和 5 个 untracked 顶层入口。该形态主要来自目录重构，但还不是可追溯的发布提交 | 合并并审阅正在进行的工作；确认三目录重构的删除/迁移映射；吸收或处理远端 1 个提交；只提交最终白名单内容；记录最终 commit SHA | 2--4 小时 |
| 对最终 commit 重做 fresh-install | 现有 fresh-install 文档停留在 `217 passed`，早于最近新增/变更；本次只做了 10 个定向测试，没有创建新环境 | 冻结后从 `dev.txt` 新建空 venv，执行 `pip check`、默认 `verify_clean_install.py`、全套 pytest 与 legacy smoke；保存命令、平台、commit、依赖清单、日志 SHA | 1--2 小时，取决于下载/缓存 |
| 最终人工授权 bundle | `LICENSE`、`IP_STATEMENT.md`、`CODE_PROVENANCE.json`、`THIRD_PARTY_NOTICES.md`、`REGISTRATION_APPROVAL.pdf`、`SUBMISSION_AUTHORIZATION.json`、`SBOM.cdx.json` 尚未提供；builder 因此正确拒绝 final | 由有权人确认竞赛报名、学校、提交人、许可证、知识产权、模型/数据/第三方再分发；在独立授权目录提供 7 个真实文件并完成 11 项声明 | 技术整理 1--3 小时；人工/校方确认通常 0.5--2 个工作日，无法由代码代签 |
| `sshr_lib` 来源和再分发 | final gate 专门要求 `sshr_lib_prehistory_confirmed`；当前脚本不会、也不应自行推断权利归属 | 形成逐目录/关键文件 provenance，确认 `experiments/src/sshr_lib/` 初始来源、作者和可再分发依据，再由有权人签署 | 1--3 小时技术盘点，外加人工确认 |
| 完整传递依赖 SBOM | builder 生成的 `SBOM-LITE.json` 只覆盖声明的直接依赖；final gate 要求经审阅的 CycloneDX `SBOM.cdx.json` | 在最终冻结环境导出直接/传递依赖，生成 CycloneDX，核对许可证与 third-party notices 后放入授权目录 | 1--3 小时，外加许可证复核 |
| 最终 staging/archive 验收 | 当前只证明 internal-audit draft；不存在 `distributable=true` 的终包证据 | 授权与 commit 冻结后只构建一次新目录；分别验证 staging 和 tar.gz；在干净临时目录解压再验；记录 archive SHA-256 与 verifier JSON | 30--60 分钟 |

### P1：应在冻结前补齐的证据闭环

| 缺口 | 当前状态 | 最小安全动作 | 预计耗时 |
|---|---|---|---|
| demo 在提交包内不完全自证 | **已收口。** 主 demo 的 7 个顶层文件和 fallback 的 9 个顶层文件均进入唯一白名单与独立 verifier 必需集合；包内局部 checksum 全通过；主 demo 日志使用 `${PROJECT_ROOT}`，不再泄露本机 checkout 路径 | 冻结 commit 后随两套 demo 最终重跑再验证一次即可 | 已完成；冻结后复核约 10--15 分钟 |
| E4-v2 未进入提交快照 | 当前 E4-v2 calibration/test bundle 均通过 verifier，但 staging spec 只打包到 E4 v1 | 仅当最终主稿/PPT采用 E4-v2 时，将 CAL/TEST 两个 bundle 加入 evidence spec、独立 verifier 的 ID 集和证据说明；继续标记 tiny、synthetic、`performance_evidence=false`。若不采用则明确排除 | 30--60 分钟 |
| 持久化 demo 与最终源码重新绑定 | 当前输出能通过 verifier，但它们生成于最近代码收尾之前；最终 commit 尚不存在 | 冻结源码后在空输出目录重跑两套 demo，再跑各自 verifier；核对无绝对路径和旧 run identity 后才替换持久化副本 | 15--30 分钟 |
| 证据文档数字漂移 | `CLEAN_INSTALL_EVIDENCE.md` 与 `E4_AES_BIDIRECTIONAL_EVIDENCE.md` 仍写 `217 passed` | 不猜测新总数；以最终 commit 的一次全量测试结果统一更新两处，并记录测试时间与 commit | 15--30 分钟 |
| 最终操作说明 | 自动生成的 `README_PACKAGE.md` 只给出包验证命令；运行 demo、fallback、最小输入输出 schema 和常见失败处理主要散在 repo 文档 | 给最终包增加一页顺序化复现说明：安装、验证、主 demo、fallback、证据边界、预期输出；命令必须在干净解压目录实跑 | 30--60 分钟 |

### P2：不应阻塞当前交付的扩展项

- 真机运行、真实 calibration、量子优势结论目前都不具备证据，且现有文档已明确排除；
  不应为了“看起来完整”而把它们写成已完成。
- Qiskit 与 SSHR-I/Gurobi 是可选路线，不属于当前核心 clean-install 门；除非最终赛题清单明确
  强制，不建议在收口阶段扩大核心依赖面。
- Linux/CUDA/第二操作系统复现可增强可信度，但不应先于 commit 冻结、完整包自证和授权材料。

## 时间判断

- **仅技术收口，不等待外部签署：约 4--7 个专注小时。** 其中 Git 冻结/迁移审阅
  2--4 小时，白名单与文档收口 1--2 小时，最终 clean-install、全量测试、建包与双重
  verifier 1--2 小时；部分步骤可并行。
- **达到真正 `distributable=true` 的关键路径：技术收口时间 + 人工授权时间。** 若许可证、
  报名/学校/提交人确认和 `sshr_lib` 来源材料当天齐备，可同日完成；若尚未确认，通常还需
  0.5--2 个工作日，且该等待不能用自动生成的占位文件替代。
- **不需要等待更多大规模实验才能完成软件验收。** E4-v2 当前是 tiny、零差异的集成证据；
  若继续扩展统计实验，应与最终提交包的工程收口并行，而不应阻塞冻结与复现链。

## 最短执行顺序

1. 合并当前并行改动，决定 E4-v2 是否进入最终主张和提交 evidence。
2. 补齐 demo 完整 artifact 白名单，更新独立 verifier 与定向测试。
3. 审阅目录重构和远端差异，形成唯一冻结 commit。
4. 对冻结 commit 重跑两套 demo、fresh-install、全量测试和 smoke。
5. 同步更新证据数字、最终中文稿、PPT 和 Overleaf 后再记录对应 commit/hash。
6. 收齐 7 个授权文件与 11 项真实声明，生成并审阅 CycloneDX SBOM。
7. 构建 final staging/tar.gz；验证 staging、archive 和干净解压副本；交付 archive SHA-256。
