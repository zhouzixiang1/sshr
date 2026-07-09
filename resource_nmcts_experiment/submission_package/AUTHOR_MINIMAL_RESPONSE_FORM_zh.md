# 最小作者回复表

用途：把最终投稿前仍需作者确认的信息压缩成一张可回复清单。请不要把真实私人信息写进 tracked 文件；把答案填入被 Git 忽略的 `submission_package/submission_metadata_answers.json`，再由工具生成私有 `submission_metadata.json`。

如果只想看最终上传前的短路径，先读 `submission_package/LAST_MILE_ACTION_CARD_zh.md`。

推荐流程：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_from_answers.py --init-private-answers
$EDITOR submission_package/submission_metadata_answers.json
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_from_answers.py --write-private
./rebuild_submission_package.sh
./verify_submission_package.sh
```

## 1. 目标 venue 与审稿政策

- JSON path: `target_venue.*`
- 请回答：目标期刊/会议、稿件类型、是否双盲、是否已核对格式/参考文献/字数/补充材料/AI disclosure 政策。
- 先读：`TARGET_VENUE_POLICY_CHECKLIST_zh.md`，逐项确认 ACM TQC、Quantum 或最终目标 venue 的政策字段。
- 可接受简答：`ACM Transactions on Quantum Computing; regular article; anonymous review: no/yes; all policies checked: yes/no/not applicable`。

## 2. 作者与通讯作者

- JSON path: `authors[]`, `corresponding_author.*`
- 请回答：作者顺序、姓名、ORCID、单位、邮箱、通讯作者、通讯地址。
- ORCID 没有时请明确写 `no ORCID` 或 `not applicable`，不要留空。

## 3. CRediT 或等价贡献

- JSON path: `author_contributions.*`
- 请回答：conceptualization, methodology, software, validation, formal analysis, investigation, data curation, writing original draft, writing review/editing, visualization, supervision, funding acquisition 分别是谁。
- 目标 venue 不要求 CRediT 时，也请给出等价贡献说明。

## 4. 经费、致谢、利益冲突

- JSON path: `funding.*`, `acknowledgements.statement`, `competing_interests.statement`
- 请回答：基金声明和基金号；致谢或 no acknowledgements；利益冲突声明或 none-declared wording。

## 5. 数据与代码可用性

- JSON path: `data_availability.*`, `code_availability.*`
- 已可自动预填：`code_availability.repository_url`, `code_availability.commit_hash`, `code_availability.environment_notes`。
- 请回答：最终公开 archive DOI/URL，双盲匿名链接（如需），访问限制，代码 license，最终 Data/Code Availability 正文。
- 如果某项没有，请写 `none` 或 `not applicable`，不要留空。

## 6. AI assistance disclosure

- JSON path: `ai_assistance.statement`
- 请回答：目标 venue 是否要求 AI disclosure；若要求，给出最终文字；若不要求，写 `No disclosure required by the target venue` 或等价表述。

## 7. 预印本、既往投稿、相关稿件

- JSON path: `preprint_and_prior_submission.*`
- 请回答：是否有 preprint DOI/URL、是否有既往投稿历史、是否有相关在投/已投稿件，以及投稿系统要求的完整声明。

## 8. Cover letter 与审稿人建议

- JSON path: `cover_letter.*`
- 请回答：目标编辑/栏目、建议审稿人、回避审稿人、给编辑的 routing statement。
- 没有建议或回避审稿人时请写 `none`。

## 9. 权限确认

- JSON path: `permissions.*`
- 请确认：本文图表是否均来自本地脚本和实验 artifact；是否没有未授权第三方图表、表格、长引文或受版权限制材料。

## 10. 不要改的科学口径

- 写投稿系统文本或 cover letter 前，先读 `COMPARISON_HANDOFF_zh.md` 和 `COMPARISON_SIGNIFICANCE_MATRIX_zh.md`。
- 本文只主张 `logical-layer quantum Boolean oracle synthesis`。
- 不写成 hardware mapping、routing、native-gate scheduling、noise model、magic-state-factory resource estimate。
- 不把 ROS-style LUT proxy 写成 full official ROS SAT garbage-management reproduction。
- 不把 weighted-score 胜出写成对所有 T/CNOT/depth/ancilla 指标的全面支配。

## 填完后必须跑

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python validate_submission_metadata.py
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_text_preview.py
./rebuild_submission_package.sh
./verify_submission_package.sh
rg -n "needs author input|needs revision" results/analysis_submission_readiness_audit.md results/analysis_submission_metadata_audit.md results/analysis_submission_metadata_validator.md
```
