# 作者与投稿元数据填写问卷

这份问卷用于一次性收集最终投稿前必须由作者确认的信息。请不要把真实私人信息直接写进本文件；推荐把答案填入被 Git 忽略的私有文件：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_from_answers.py --init-private-answers
$EDITOR submission_package/submission_metadata_answers.json
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_from_answers.py --write-private
./rebuild_submission_package.sh
./verify_submission_package.sh
```

私有短答案文件 `submission_package/submission_metadata_answers.json` 和生成后的 `submission_package/submission_metadata.json` 都被 Git 忽略。生成后的元数据会由 `validate_submission_metadata.py` 校验，并生成同样被 Git 忽略的 `generated_author_declarations.md`、`generated_availability_statements.md`、`generated_cover_letter.md`、`generated_submission_text.md` 和 `generated_upload_plan.md` 供投稿系统复制粘贴与最终上传路由核对。

## 0. 不要改动的论文边界

- 本文只主张 logical-layer quantum Boolean oracle synthesis。
- 不主张 hardware mapping、routing、native-gate scheduling、noise model 或 magic-state-factory 资源。
- 不把 ROS-style LUT proxy 写成 full official ROS SAT garbage-management reproduction。
- 不把 weighted-score 胜出写成对 SSHR、RevKit、CirKit 或所有 CNOT/depth/ancilla 指标的全面支配。

## 1. 目标期刊与审稿政策

请在 `target_venue.*` 填写或确认：

- `target_venue.name`：最终目标期刊或会议名称。
- `target_venue.manuscript_type`：article、regular paper、short paper、technical note 等。
- `target_venue.formatting_policy_checked`：是否已核对模板、页数、双栏/单栏要求。
- `target_venue.reference_style_checked`：是否已核对参考文献格式。
- `target_venue.word_limit_checked`：是否已核对摘要、正文、图表和补充材料限制。
- `target_venue.supplementary_material_policy_checked`：是否允许上传代码、数据、artifact payload。
- `target_venue.ai_disclosure_policy_checked`：是否需要 AI assistance disclosure。
- `target_venue.anonymous_review_required`：是否双盲；若是，必须准备 anonymous review link。

建议先看 `submission_package/target_venue_brief.md` 和 `TARGET_VENUE_POLICY_CHECKLIST_zh.md`，再把最终选择填入私有短答案 JSON。

## 2. 作者身份与通讯作者

请在 `authors[]` 和 `corresponding_author.*` 填写：

- `authors[].order`：作者顺序，从 1 开始连续编号。
- `authors[].name`：作者姓名。
- `authors[].orcid`：ORCID；没有则填明确的 no ORCID / not applicable。
- `authors[].affiliations`：每位作者的单位。
- `authors[].email`：邮箱。
- `authors[].corresponding`：是否通讯作者。
- `corresponding_author.name`
- `corresponding_author.email`
- `corresponding_author.affiliation`
- `corresponding_author.postal_address`

校验器会检查邮箱、ORCID 格式、作者顺序和通讯作者一致性，但不会把真实值写入 tracked 输出。

## 3. CRediT 作者贡献

请在 `author_contributions.*` 填写每个角色对应作者：

- `author_contributions.conceptualization`
- `author_contributions.methodology`
- `author_contributions.software`
- `author_contributions.validation`
- `author_contributions.formal_analysis`
- `author_contributions.investigation`
- `author_contributions.data_curation`
- `author_contributions.writing_original_draft`
- `author_contributions.writing_review_editing`
- `author_contributions.visualization`
- `author_contributions.supervision`
- `author_contributions.funding_acquisition`

如果目标期刊不用 CRediT，也请填入等价的作者贡献说明或明确 not required。

## 4. 经费、致谢与利益冲突

请填写：

- `funding.statement`：基金或无基金声明。
- `funding.grant_numbers`：基金号；没有则填 not applicable。
- `acknowledgements.statement`：致谢或 no acknowledgements。
- `competing_interests.statement`：利益冲突声明；没有则填目标期刊要求的 none-declared wording。

这些内容不能从代码或实验推断，必须由作者确认。

## 5. 数据、代码和匿名审稿链接

请填写：

- `data_availability.archive_link_or_doi`：最终数据/附件归档 DOI 或 URL。
- `data_availability.anonymous_review_link`：双盲审稿用匿名数据链接；不需要则填 not applicable。
- `data_availability.access_restrictions`：访问限制；没有则填 none。
- `data_availability.statement`：投稿系统或论文里的 Data Availability 文字。
- `code_availability.repository_url`：公开代码仓库或归档链接。
- `code_availability.commit_hash`：最终投稿 commit hash。
- `code_availability.license`：代码许可证。
- `code_availability.environment_notes`：环境说明；当前模板已预填 mcts-qoracle 和 Python 路径。
- `code_availability.anonymous_review_link`：双盲审稿用匿名代码链接；不需要则填 not applicable。
- `code_availability.statement`：Code Availability 文字。

如果选择双盲 venue，不要在匿名稿或匿名 artifact 链接中暴露作者身份。

## 6. AI 辅助、预印本和既往投稿

请填写：

- `ai_assistance.statement`：目标期刊要求的 AI assistance disclosure 或明确 no disclosure required。
- `preprint_and_prior_submission.preprint_url_or_doi`：预印本 DOI/URL；没有则填 none。
- `preprint_and_prior_submission.prior_submission_history`：既往投稿历史；没有则填 none。
- `preprint_and_prior_submission.related_manuscripts`：相关在投或已投论文；没有则填 none。
- `preprint_and_prior_submission.statement`：投稿系统需要的完整声明。

## 7. Cover Letter 和编辑路由

请填写：

- `cover_letter.target_editor`：目标编辑或栏目；不知道则填 not specified。
- `cover_letter.suggested_reviewers`：建议审稿人；没有则填 none。
- `cover_letter.excluded_reviewers`：回避审稿人；没有则填 none。
- `cover_letter.editorial_routing_statement`：给编辑的路由说明。

写 cover letter 前请先读 `submission_package/COMPARISON_HANDOFF_zh.md`，避免把 SSHR、ROS、RevKit 或 AI/MCTS 口径写过头。

## 8. 第三方材料与权限

请填写：

- `permissions.third_party_material_confirmed`：确认没有未授权第三方图表、长引用或受版权限制材料。
- `permissions.statement`：权限声明；当前模板已说明图表来自本地脚本和实验 artifact，但仍需作者最终确认。

## 9. 填完后的闭环检查

填完私有短答案 JSON 并生成私有元数据后运行：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python validate_submission_metadata.py
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_text_preview.py
./rebuild_submission_package.sh
./verify_submission_package.sh
rg -n "needs author input|needs revision" results/analysis_submission_readiness_audit.md results/analysis_submission_metadata_audit.md results/analysis_submission_metadata_validator.md
```

目标状态：没有 `needs revision`，最终上传副本中没有未处理的 `AUTHOR INPUT REQUIRED`，并且 `results/analysis_submission_package_verifier.md` 显示全部 pass。
