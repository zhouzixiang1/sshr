# XA-202609 安全提交 staging

竞赛提交树由仓库根相对的显式白名单生成，不手工拖拽文件。当前实现位于：

- `experiments/submission/competition_staging_spec.json`：唯一输入白名单和精简 evidence 规则；
- `experiments/submission/build_competition_staging.py`：确定性 staging/archive builder；
- `experiments/submission/verify_competition_package.py`：不导入 builder、也不信任包内白名单的独立 verifier。

白名单纳入 SHA 锁定的 39 页中文主稿 PDF 与可编译 LaTeX 依赖、经单独 SHA 锁定的最终
PPT、核心源码与测试、formal v4 训练 provenance bundle、精确 requirements、竞赛 demo
脚本和样例报告，以及 E2/E3/E4、canonical E4-v2 与 E5 v1/v1.1 的
`run/summary/verifier/manifest/checksum` 精简快照。另完整纳入由外部 anchor 锁定的 E5
portable V3、fresh-v2 及原生 19-check verifier 所需的六个 predecessor/source/link 九件套（包括各自
`raw/events/log`），以便独立重算跨 Torch 二进制 build 的可移植性边界；predecessor 只作
provenance 输入，不进入性能主张或推荐结果，outer manifest 逐文件绑定 anchor、snapshot
与 SHA。原始 90-row v1.1 source 的角色固定为
`scientific_source_predecessor_only_unaccepted_endpoint`，其 preflight/seal 仅作 source-link
输入。E6 除 mechanism MVP 源码、配置与测试外，还完整纳入两个五文件 development
bundle：legacy conditional negative bundle 使用 `heldout_evaluation.json`，D2
resource-gain mechanism-repair bundle 使用 `diagnostics.json`，其余均为
`config.json/results.json/raw.jsonl/checksums.sha256`。D2 在 fresh structured/OOD 上
相对同源 permuted control 分别得到 `delta Y=-0.1688789442`（32/0/0）和
`-0.1535114735`（31/1/0），但仍略弱于 greedy；两份 bundle 的 formal/performance/
hardware/generalization/advantage 均为 `false`。它们都是普通单研究者确定性开发实验。
除上述八个精确九件套与两个 E6 五文件 bundle 外，大型
`raw.jsonl`、事件/日志、`misc/archive/`、旧论文 submission package、缓存和构建产物一律
不复制；精简 evidence 会记录完整源 bundle 的文件名、字节数和 SHA-256，同时明确哪些
大文件未复制。精简快照中含本机绝对路径的 JSON 会规范化为 `${REPO_ROOT}`，原始 SHA 与
打包后 SHA 分别保存在 provenance 中；两个 locked raw 例外保持原始字节并由下述窄门处理。

## 默认 fail-closed

以下人工/外部授权材料全部存在且通过声明门之前，builder 不会生成 final staging：

1. `LICENSE`：权利人批准、且范围与实际可分发内容一致的项目许可证；
2. `IP_STATEMENT.md`：学校、团队、雇主和竞赛共同知识产权条款的批准说明；
3. `CODE_PROVENANCE.json`：尤其覆盖 `experiments/src/sshr_lib/` 初始来源；
4. `THIRD_PARTY_NOTICES.md`：经核实的第三方内容和许可证/许可记录；
5. `REGISTRATION_APPROVAL.pdf`：已批准报名表或组织方等价确认；
6. `SUBMISSION_AUTHORIZATION.json`：授权提交人签署的机器可读声明；
7. `SBOM.cdx.json`：冻结环境的完整 CycloneDX 直接/传递依赖 SBOM。

这些文件必须来自人工确认的外部授权目录；脚本绝不生成许可证、IP 结论或授权声明。
`SUBMISSION_AUTHORIZATION.json` 的最低结构如下，其中所有声明都必须严格为 `true`，
字符串不得是占位符：

```json
{
  "schema_version": "xa.submission-authorization.v1",
  "competition_id": "XA-202609",
  "status": "approved",
  "archive_name": "XA-202609_<approved-name>.tar.gz",
  "attested_by": "<human name>",
  "attested_role": "<authorized role>",
  "attested_at_utc": "<ISO-8601 timestamp>",
  "submitting_university": "<confirmed university>",
  "authorized_submitter": "<confirmed submitter>",
  "declarations": {
    "registration_approved": true,
    "submitting_university_confirmed": true,
    "authorized_submitter_confirmed": true,
    "project_license_approved": true,
    "ip_statement_approved": true,
    "code_provenance_approved": true,
    "sshr_lib_prehistory_confirmed": true,
    "redistribution_authorized": true,
    "third_party_notices_approved": true,
    "model_data_redistribution_authorized": true,
    "transitive_sbom_reviewed": true
  }
}
```

上面的尖括号仅用于说明 schema，不能原样写入真实授权文件；placeholder 检查会拒绝它们。

## 独立的最终模型与主张技术门

人工签字不能覆盖技术证据或科学验收缺失。当前状态刻意区分：

- foundation v3 是 demo 使用的 `development candidate`；
- formal v4 的 command、config、split、seed、training log/hash、checkpoint 与 source SHA
  已闭合，checkpoint SHA-256 为
  `5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7`；
- formal v4 仍只是 `provenance_closed_development_candidate`，训练 holdout 不是外部性能证据；
- E4-v2 是已见 AES 坐标上的 post-E4 frozen replication，95% CI
  `[-2059.0625, 589.9375]` 跨 0，不能写成 held-out、generalization 或改善；
- E5 v1.1 虽有 90 行矩阵，但 ASCON 可调度 group 为 0，negative audit 保持
  `protocol_acceptance=false`，当前没有 accepted E5 endpoint；
- portable negative-audit V3 snapshot 为
  `4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea`，fresh-v2 snapshot
  为 `dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23`，二者由 SHA
  `036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686` 的外部 anchor
  闭合；fresh-v2 记录 9/9 命令和 383 passed，但只构成软件/可移植性证据，不能提升为
  protocol、performance、hardware 或 quantum-advantage evidence；
- fresh-v1/fresh-v2 的 locked `raw.jsonl` 各含一条历史 verifier stdout 中的本机路径。两条
  原始字节均不可在不破坏 snapshot 的前提下清洗，因此 verifier 只对这两个精确文件、
  `command_id=portable_v3_verifier`、`stdout.text` 和同一 V3 目标各放行一次；全包总数必须
  恰为 2，其余文件仍对本机绝对路径 fail-closed。该字符串不是运行依赖；
- E6 legacy 五文件 bundle 已闭合 64 个 `n=6/7` training case、32 个 `n=4/5` whole-vector
  heldout development case 与真实四臂训练，独立 verifier 为 11/11；主比较显著反向于
  改善，只构成 development conditional negative evidence。该 run 的 formal/performance/
  hardware/generalization/advantage 均为 `false`，不能作为性能结果；
- E6-D2 五文件 bundle 使用新的 `20261011/12/13` train/structured/OOD seed，三层
  orbit overlap 均为 0，语义 100%、0 fallback/degraded。它只支持 resource-gain
  teacher 的 source-label mechanism repair；因为 gain-QAOA 仍略弱于 greedy，
  `formal_evaluation=false`、`performance_evidence=false`。

因此当前 final 模式仍必须因“模型卡不是 final frozen、缺少 accepted external performance
evidence”和人工授权材料缺失而拒绝；仅当仓库 dirty 时再增加
`repository_not_clean_frozen_commit`。机器可读最终模型卡
必须使用 `xa.final-model-card.v1`，且至少满足：

```json
{
  "schema_version": "xa.final-model-card.v1",
  "status": "final_frozen",
  "development_candidate": false,
  "checkpoint": {
    "path": "<explicitly whitelisted final checkpoint>",
    "sha256": "<64 lowercase hex>"
  },
  "training": {
    "command": "<repository-relative reproducible command>",
    "config": {"path": "<explicitly whitelisted path>", "sha256": "<64 lowercase hex>"},
    "split_manifest": {"path": "<explicitly whitelisted path>", "sha256": "<64 lowercase hex>"},
    "seeds": [0],
    "logs": [{"path": "<optional explicitly whitelisted path>", "sha256": "<64 lowercase hex>"}],
    "source": {
      "commit_sha": "<frozen git commit>",
      "source_tree_algorithm": "xa-python-source-tree.v1",
      "source_tree_sha256": "<64 lowercase hex>"
    }
  }
}
```

配置、split 和带路径的日志必须同时加入显式白名单；机器模型卡不能动态扩大白名单。模型卡
还必须引用被独立 verifier 接受的外部性能 evidence；human authorization 不能把 provenance
candidate 或失败端点提升为 final。

## 内部审计草稿

技术链可在授权未闭合时用 `--allow-incomplete` 演练，但输出目录必须含
`internal-audit-draft`，归档固定命名为 `XA-202609_INTERNAL_AUDIT_DRAFT.tar.gz`，
包内同时包含醒目的 `INCOMPLETE_INTERNAL_AUDIT_DRAFT.md`。它不能被命名或解释为 final：

PPT 尚未完成原子锁定时，必须加 `--omit-presentation`；该选项不会 stat/read/copy PPT，且
只能用于 internal pre-lock audit。PPT 锁定后应去掉该选项并传入真实 SHA。

```bash
cd /path/to/tzb
python experiments/submission/build_competition_staging.py \
  --allow-incomplete \
  --omit-presentation \
  --output-dir /tmp/XA-202609-internal-audit-draft \
  --archive /tmp/XA-202609_INTERNAL_AUDIT_DRAFT.tar.gz

python experiments/submission/verify_competition_package.py \
  --allow-incomplete /tmp/XA-202609_INTERNAL_AUDIT_DRAFT.tar.gz
```

即使草稿的 checksum、路径和白名单全部通过，verifier 仍报告
`distributable=false`；去掉 `--allow-incomplete` 后必须因授权门失败。

## Final 构建与独立复验

人工授权材料闭合后：

```bash
python experiments/submission/build_competition_staging.py \
  --authorization-dir /secure/path/to/approved-authorization \
  --expected-presentation-sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef \
  --output-dir /tmp/XA-202609-submission

python experiments/submission/verify_competition_package.py \
  /tmp/XA-202609-submission
```

verifier 检查单根安全解包、路径穿越/符号链接、独立白名单、MANIFEST 与 checksum 完整
覆盖、本机路径/高可信密钥模式、文件大小、SBOM、provenance、evidence 子校验和，并以
硬编码 anchor SHA 调用 fresh-v2 的 19-check 独立 verifier；同时检查 PPT
存在性和全部人工授权状态。任何文件改动、额外文件、漏项或占位授权都会失败。
上面的 64 位值只是命令格式示例，执行时必须替换为完成 PPT QA 后锁定的真实 SHA-256；
final 模式不接受省略该参数，builder 只读取一次 PPT 并把观察值与锁定值比较后复制。
