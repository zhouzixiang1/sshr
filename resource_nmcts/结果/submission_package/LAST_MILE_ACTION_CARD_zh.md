# 最后一步行动卡

用途：真实投稿前只看这一页，确认还缺什么、先填什么、填完跑什么命令。本卡不包含真实作者信息；所有私人答案只写入被 Git 忽略的 `submission_package/submission_metadata_answers.json` 和 `submission_package/submission_metadata.json`。

## 当前只剩的人工作业

- 选定最终 target venue、稿件类型和是否双盲。
- 填作者顺序、单位、ORCID、通讯作者和邮箱。
- 填 CRediT 或等价作者贡献、基金、致谢、利益冲突。
- 填 Data Availability、Code Availability、license、最终公开 DOI/URL 或匿名审稿链接。
- 填 AI assistance disclosure、预印本/既往投稿/相关稿件说明。
- 填 cover letter 的目标编辑、建议审稿人、回避审稿人和编辑路由说明。

## 建议顺序

1. 读 `target_venue_brief.md` 和 `TARGET_VENUE_POLICY_CHECKLIST_zh.md`，先决定目标 venue。
2. 读 `COMPARISON_HANDOFF_zh.md` 和 `COMPARISON_SIGNIFICANCE_MATRIX_zh.md`，确认投稿系统或 cover letter 里的比较口径。
3. 用短表收集答案：`AUTHOR_MINIMAL_RESPONSE_FORM_zh.md`。
4. 生成并填写私有答案文件：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_from_answers.py --init-private-answers
$EDITOR submission_package/submission_metadata_answers.json
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_from_answers.py --write-private
```

5. 生成私有投稿文本预览并重建包：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python validate_submission_metadata.py
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_text_preview.py
/opt/anaconda3/envs/mcts-qoracle/bin/python make_final_upload_plan.py
./rebuild_submission_package.sh
./verify_submission_package.sh
```

6. 检查私有预览文件后，再复制到投稿系统：

- `submission_package/generated_author_declarations.md`
- `submission_package/generated_availability_statements.md`
- `submission_package/generated_cover_letter.md`
- `submission_package/generated_submission_text.md`
- `submission_package/generated_upload_plan.md`

7. 上传前看一次 `submission_package/generated_upload_plan.md` 和
   `results/analysis_upload_bundle_matrix_audit.md`，按目标 venue 选择作者版、
   匿名版、ACM/TQC review 版和 payload/source-data bundle。

## 填完后的通过标准

- `./verify_submission_package.sh` 通过。
- `results/analysis_submission_package_verifier.md` 显示 terminal package verifier 全部 pass。
- `results/analysis_upload_bundle_matrix_audit.md` 中所有 upload bundle 均为 pass。
- `results/analysis_final_upload_plan_tool_audit.md` 中三条 synthetic route 均为 pass。
- `results/analysis_submission_readiness_audit.md` 中没有 `needs revision`。
- 最终上传副本不再保留未处理的 `AUTHOR INPUT REQUIRED`。
- 如果双盲，匿名稿和匿名 artifact 链接中没有作者姓名、个人仓库、个人邮箱或可追溯致谢。

## 不能写过头的口径

- The paper claims logical-layer quantum Boolean oracle synthesis only.
- It does not claim hardware mapping, routing, native-gate scheduling, noise modeling, or magic-state-factory accounting.
- It does not claim universal dominance over SSHR, RevKit, CirKit, Caterpillar, or all CNOT/depth/ancilla metrics.
- ROS-style LUT rows are not full ROS reproduction and not official SAT garbage-management reproduction.
- RevKit `oracle_synth` is a phase/Rz sensitivity or proxy branch, not a final Clifford+T comparison.
- AI/MCTS should be framed as search control, ranking, pruning, guard, and Pareto selection, not as deep reinforcement learning alone explaining the full result.

## 最小上传选择

- 非双盲 venue：上传 `paper_latex/resource_nmcts_submission_v1.pdf`、对应 TeX/source，以及 `submission_package/dist/resource_nmcts_submission_payload.tar.gz`。
- 双盲 venue：上传 `paper_latex/resource_nmcts_submission_anonymous.pdf` 或 ACM/TQC anonymous review-format PDF/source，并把可用性链接替换成匿名 review link。
- 任何 venue：保留 payload SHA256，上传前最后一次运行 `./verify_submission_package.sh`。
