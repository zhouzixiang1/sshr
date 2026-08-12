# XA-202609 合规与提交就绪审计

> 审计日期：2026-07-28
> 状态：**NOT READY / 不得直接打包提交**
> 范围：当前 Git 工作树、开发模型、旧论文提交包及 XA-202609 计划交付物
> 性质：技术合规与打包审计，不替代学校、团队或法律人员的知识产权意见

本审计不读取、复制或展示个人字段值，也没有修改任何个人元数据、Git 历史、
许可证或提交包。

## 1. 结论

当前仓库不能直接制作 XA-202609 最终提交包。必须先关闭以下 P0 问题：

1. 项目没有 `LICENSE`，但已跟踪元数据声称采用 MIT；
2. 一个已跟踪 JSON 含非占位作者/机构/联系方式字段；
3. `src/sshr_lib/` 的仓库内部迁移已查清，但初始来源、权利归属和再分发授权未确认；
4. 最终模型和训练数据 provenance 不可复现；
5. 旧论文 tar 含本机路径和大量无关投稿材料，且没有 XA-202609 产物或许可证；
6. 没有 `pyproject.toml`、requirements 或 environment 文件；
7. 目标源码、测试、模型和规划文档仍有大量未跟踪改动；
8. 用户已确认报名审核通过和竞赛共同 IP 条款；私有报名表、学校/团队字段、
   最终提交责任人及既有代码权利材料尚未在本技术审计中归档。

最终必须新建独立、白名单式 `competition/` staging。不得复制整个仓库、整个
`results/`、旧论文包或 `misc/archive/`。

## 2. 当前快照

| 项目 | 2026-07-28 实测 |
|---|---:|
| Git 已跟踪文件 | 2,779 |
| 工作树状态条目 | 34（含当前 XA 治理与状态文档） |
| 项目级 LICENSE / NOTICE / THIRD_PARTY | 0 |
| Python/Conda 安装声明文件 | 0 |
| Boolean Oracle 开发 checkpoint | 6，均未跟踪 |
| 旧论文 tar 成员 | 1,130 |
| 旧论文 tar 中 LICENSE/NOTICE/THIRD_PARTY | 0 |
| 旧论文 tar 中 XA-202609/foundation/QAOA/hardware/noise 目标命中 | 0 |
| Git 已跟踪 `_archive` 文件 | 466 |
| 作用域内常见 API token / 私钥形状命中 | 0 |
| `.env`、PEM、P12/PFX、credentials 文件命中 | 0 |

“没有发现常见密钥形状”只是当前作用域的静态扫描结果，不等于最终 secret
scan 已完成。最终 ZIP 仍须在生成后重新扫描。

## 3. P0 阻断项

### C1. 项目许可证缺失且声明矛盾

证据：

- 仓库根和 `experiments/` 均无项目 `LICENSE`；
- `misc/archive/experiments/resource_nmcts-submission-package/submission_metadata_answers.json:66,68`
  声明 `MIT`；
- 同一旧论文元数据还确认“第三方材料检查完成”，并对其论文图表范围声明没有
  第三方版权材料；该旧投稿自述不能证明 XA-202609 新增源码、模型或数据已完成
  来源和许可审查；
- 当前没有权利人批准、版权归属、竞赛新增 IP 或第三方代码清单。

风险：一句元数据声明不能构成授权。竞赛共同知识产权条款已经由用户确认，
但这不能替代既有代码权利人、初始来源和再分发许可确认；继续写“MIT”仍可能
造成错误授权。

关闭条件：

- 确认背景 IP、竞赛新增 IP、模型权重、数据、论文与第三方代码的权利人；
- 由有权主体批准项目许可证；
- 增加项目 `LICENSE`；
- 元数据、README、报告和模型卡中的许可声明完全一致。

项目许可证只能覆盖已确认由项目权利人拥有或有权再许可的内容。在 C3 闭环前，
不得以新增项目 `LICENSE` 推定 `src/sshr_lib` 已获得再分发权。

### C2. 已跟踪个人元数据

证据：

- 历史 `submission_metadata_answers.json` 曾被 Git 跟踪，现已移入本机归档；
- 文件含非空作者、ORCID、机构、邮箱、通讯作者和邮寄地址等字段；
- 最新可定位提交为 `f589bf2c8fa8af748639228e42268c3432bbf494`；
- 该文件当前没有被 `.gitignore` 排除。

风险：公开仓库、Git 历史或错误的递归打包可能泄漏个人信息。

关闭条件：

- 只保留不含真实信息的模板；
- 真实报名/竞赛元数据移入私有、受控位置；
- 停止跟踪真实答案文件并加入忽略规则；
- 确认远端可见性；若历史已经公开，由负责人决定是否进行历史清理；
- 最终 ZIP 的源码区不含作者邮箱、邮寄地址或手机号；必要信息只进入批准表单和
  外层归档名。

本审计不执行停止跟踪或历史重写，因为这属于需要负责人明确批准的隐私操作。

### C3. `src/sshr_lib` 内部代码谱系已确认，但初始来源与再分发权未闭合

证据：

- 当前 8 个活动文件均于提交 `85c4d01` 从本仓库既有 `sshr/` 或
  `gnn-sshr/src/sshr_core/` 路径迁入；
- 仓库内部历史可追溯至初始提交 `497dc2c`，其中 `sshr_i.py` 另有后续重构和
  路径修复记录；
- `src/factor_plan.py` 和公开综合入口直接依赖 `src/sshr_lib`；
- 现有历史未提供 `497dc2c` 之前的作者与来源证据，也未发现对应的上游源码地址、
  软件许可证、授权书或 NOTICE；
- 论文引用只能证明算法文献来源，不能替代软件再分发许可；
- 文件级内部迁移证据见 `DEPENDENCY_PROVENANCE_DRAFT_XA202609.md`。

风险：当前证据不能确认初始版本是否由团队独立实现，也不能排除曾使用外部源码、
补充材料或私有代码，因此尚不能证明随赛题源码再分发的完整授权基础；这不等于
已经证明其为外部复制或存在侵权。

关闭条件：

- 逐文件记录已确认的仓库内部来源路径、首次提交、后续修改和当前维护者；
- 由初始作者或负责人书面确认 `497dc2c` 之前的形成方式、是否使用外部源码、
  AI 辅助范围及权利归属；
- 若使用外部源码，补齐上游 URL、版本、许可证和必要授权；
- 若无法确认授权，实施洁净室重写并保留需求隔离、实现人员、语义测试和回归证据；
- 形成经负责人批准的 `CODE_PROVENANCE.md/json`。

当前统一状态：

> 仓库内部复制／修改已确认；外部来源未证实；初始作者身份与再分发权待人工确认。

### C4. 模型与数据 provenance 不完整

候选 checkpoint：

| 文件 | SHA-256 | 大小（bytes） |
|---|---|---:|
| `boolean_oracle_fm.pt` | `329e1a07aee1465baf8c2b12ea6d43e94c8fbb02943041d1cb86adbd49f74e14` | 251,910 |
| `boolean_oracle_fm_big.pt` | `269fefd502dbe1e92a9ba85d37e179a457102e73c43d32b1ef7dd011ca9703c4` | 959,292 |
| `boolean_oracle_fm_sized.pt` | `407308cd16d88ead897533932f655b07142e88ca66cd4d40636b63d5777be288` | 493,835 |
| `boolean_oracle_fm_small.pt` | `bb8c7b34e6dbb8282ef7eb009c01e2a22897e4b2313f4529880659006dd82af8` | 253,744 |
| `boolean_oracle_fm_v2.pt` | `40d20954a856b1b64ae3afb2bcef0ca4673cff152033acd4b758a0fd65d753f0` | 254,587 |
| `boolean_oracle_fm_v3.pt` | `87904409966e6d9d18aae3711dff54d696608e6eefcf0e5cb5bb98ae96d4f57d` | 254,587 |

当前六个文件均未跟踪。v3 模型卡已经明确：checkpoint 内没有训练命令、seed、
split、逐轮日志或源码 commit。

关闭条件：

- 重新训练或补齐可信 provenance；
- 冻结唯一 checkpoint，排除其他开发权重；
- 保存完整命令、配置、环境、源码 commit、训练/验证/测试 ID+hash、seed 和日志；
- 增加机器可读 model card、data card 与 checkpoint checksum；
- 明确生成数据、标准密码向量和模型权重的权利人及再分发许可；
- 在干净 CPU 环境验证加载和端到端推理。

### C5. 旧论文提交包不可复用

`misc/archive/experiments/resource_nmcts-submission-package/dist/resource_nmcts_submission_payload.tar.gz`
是旧学术论文 payload：

- 1,130 个成员；
- 没有 LICENSE/NOTICE/THIRD_PARTY；
- 没有 XA-202609、v3 foundation、QAOA、原生门或噪声目标产物；
- 脱敏扫描发现 57 个文件、6,210 行含用户目录路径，26 个文件、270 行含
  本机环境绝对路径；
- 包含大量旧论文、审稿和 venue 专用材料。

关闭条件：

- 使用独立的 `docs/competition/` 与 `experiments/` 交付树；
- 只从明确白名单复制批准文件；
- 最终用 ZIP，而不是复用旧 tar；
- 从干净临时目录解压并运行独立 verifier；
- archive manifest、SHA 和 verifier 必须针对同一个最终 ZIP。

### C6. 安装与第三方依赖声明缺失

当前没有 `pyproject.toml`、`requirements*.txt`、`environment*.yml`、lockfile
或 Dockerfile。foundation 算法语义层直接依赖 PyTorch，但公开综合入口因顶层
导入旧基线还会加载 NumPy 和 SciPy；后续 QAOA/含噪路径还需要明确的量子 SDK。
旧文档依赖本机 Conda 环境，不能作为交付安装方式。

当前直接依赖初步审计已确认：

- 运行入口：PyTorch 2.12.0、NumPy 2.4.6、SciPy 1.17.1；
- 测试：pytest 9.0.3；
- 逻辑 OpenQASM 子路径没有第三方 Python 依赖；
- Qiskit、Qiskit Aer 尚未安装或选型，只能列为计划依赖；
- PuLP、scikit-learn 虽存在于当前环境，但目标范围源码未直接导入；
- Gurobi 仅属于旧 SSHR-I 可选路径，不得把本机许可证或许可标识打入提交包。

详细证据和许可证边界见 `DEPENDENCY_PROVENANCE_DRAFT_XA202609.md`。该文件是
开发快照，不是最终 SBOM 或许可证通知。

关闭条件：

- 选择一套权威安装方式并固定 Python/核心依赖版本；
- 从冻结环境生成直接与传递依赖 SBOM；
- 用 `THIRD_PARTY_NOTICES.md` 记录已确认第三方包的版本、来源、许可证和必要通知；
- 不打包 Gurobi 许可证、第三方工具源码树或系统环境；
- 在空环境中按用户文档逐条执行 import、smoke、模型加载、QAOA/noise mini
  example 和完整 demo。

### C7. 目标源码与结果尚未冻结

当前 foundation、search、hardware、训练脚本、测试、六个 checkpoint 和本轮
治理文档仍未全部纳入版本控制。旧论文结果不能证明 XA-202609 新闭环。

关闭条件：

- 明确最终源码白名单；
- Git 中只保留一个推荐 checkpoint；
- 新实验使用独立 `competition/results/`；
- 每项实验有 raw、summary、manifest、analysis 和 figure source data；
- 最终 commit 工作树干净，报告和模型卡记录同一 commit。

### C8. G0 已确认，私有人工材料仍待最终归档

官方报名系统开放期为 2026-05-30 至 2026-06-30，当前日期已经晚于该窗口；
用户已于 2026-07-28 确认报名完成并审核通过，也确认了“获奖团队与发榜单位
共同拥有知识产权”的竞赛条款。出于隐私和最小披露原则，本审计没有读取或
复制报名表、学校、团队或联系方式。

最终提交前仍需在私有受控位置准备并核对：

- 审核通过的报名表或赛事方等效确认；
- 学校法定全称；
- 团队成员和指导教师；
- 联系手机号；
- 原创声明、贡献确认和既有代码权利边界；
- 符合赛事格式的最终 ZIP 名称。

关闭条件：最终提交责任人从私有位置附入审核通过的报名表，并核对表单、学校、
团队和归档名一致；手机号只进入必要表单和归档名。竞赛 IP 条款的确认不能
替代 C1/C3 的许可证、初始来源和再分发权关闭条件。

## 4. 路径、隐私和打包白名单

当前非结果开发树仍有多处用户主目录、本机 Conda 环境和工作目录的绝对路径。
开发文档可以保留明确标注的本机命令，但最终用户文档、manifest 和 ZIP 不得
依赖这些路径。

最终 staging 必须排除：

- `.git/`、`.claude/`、`.DS_Store`；
- `misc/archive/`；
- `misc/tmp/`；
- `misc/archive/experiments/resource_nmcts-submission-package/` 旧论文包；
- `docs/papers/resource_nmcts/` 中未被当前交付白名单选中的旧论文源，以及 `misc/generated/`；
- `__pycache__/`、`.pytest_cache/` 和 LaTeX 构建垃圾；
- 私有 metadata、云平台凭证、本地许可证和个人通讯信息；
- 未选择的 checkpoint、旧模型和与竞赛无关的完整 `results/`。

建议最终白名单只包含：

- `docs/competition/README.md`、`experiments/environment/requirements/` 与环境文件；
- 最小必要 `src/`、`scripts/` 和 `tests/`；
- 唯一冻结模型及 model/data card；
- XA-202609 raw/summary/manifest/analysis；
- 技术报告 PDF 与必要源文件；
- 演示材料和批准样例；
- LICENSE、THIRD_PARTY_NOTICES、IP/原创声明；
- archive manifest、checksums 和 verifier。

## 5. 关闭顺序

1. **G0 已确认；接下来确认既有代码权利人和许可证策略，并私下保管报名材料。**
2. 隔离并处理已跟踪个人元数据，不做递归整仓打包。
3. 完成 `src/sshr_lib` 初始作者、外部来源和权利归属确认，形成
   `CODE_PROVENANCE`；如确认含第三方代码，再补对应许可证、NOTICE 或书面授权。
4. 选择环境格式并固定直接/间接依赖。
5. 重新训练或正式冻结一个可复现模型和数据 manifest。
6. 所有目标源码、测试、结果和报告进入独立 competition 命名空间。
7. 生成白名单 ZIP，在干净目录执行安装、E2E、PDF、secret/privacy 和清单校验。
8. 最后补批准表单与归档名，复算 SHA，禁止再修改包内内容。

## 6. 最终合规验收门

最终 verifier 至少必须证明：

1. 项目许可证只覆盖已确认有权授权的内容，并与所有公开声明一致；
2. `CODE_PROVENANCE` 覆盖内部迁移、初始来源、AI 辅助和权利批准；
3. `THIRD_PARTY_NOTICES` 覆盖所有已确认的随包第三方内容；
4. 私有身份元数据不在公开源码区；
5. 最终模型和数据有完整 provenance、SHA 与再分发授权；
6. ZIP 中无 `_archive`、旧论文包、构建垃圾和本机绝对路径；
7. ZIP 脱敏 secret scan 零高风险命中；
8. ZIP 文件名严格符合赛事格式；
9. 报名、团队、IP 和原创声明经过人工批准；
10. 干净解压后许可证、清单、源码、模型、PDF、文档和演示全部存在；
11. 干净环境单命令端到端验收通过。

在上述十一项全部有证据前，合规提交包状态保持 `missing` / `incomplete`。
