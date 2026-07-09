# 最终投稿交接单

本文档面向作者本人使用，用来把当前已经完成的研究包推进到真实投稿。它不替代
`AUTHOR_INPUT_REQUIRED.md`，而是给出推荐执行顺序和检查点。

## 当前状态

研究、实验、LaTeX、匿名稿、payload 打包和自动审计已经准备好。当前仍不能直接
标记为投稿完成，原因是以下信息必须由作者或目标期刊确认，不能从代码和实验结果中
推断：

- 作者顺序、单位、ORCID、通讯作者和邮箱。
- CRediT 作者贡献。
- 基金、致谢、利益冲突。
- 目标期刊、稿件类型、参考文献格式、字数或页数限制、补充材料政策。
- 是否双盲审稿，以及是否需要匿名仓库或匿名归档链接。
- 最终数据和代码归档 DOI、仓库 URL、commit hash、license。
- AI assistance disclosure、预印本和既往投稿说明。

## 机器审计快照

以下 token 由 `analyze_public_handoff_freshness_audit.py` 检查，代表当前公开交接状态：

- PDF pages=39/39
- readiness=63 pass + 1 needs author input
- payload_files=1008
- artifact_registry=25 families / 147 raw CSV / 60306 raw rows
- source_privacy=0 strict leaks / 53 provenance files / 965 payload text files
- comparison_validity=8/8 pass
- novelty_scorecard=6/6 pass
- goal_gate=author/venue metadata remains open

## 推荐执行顺序

1. 先读 `target_venue_brief.md`，确定一个目标期刊和一个备选期刊。
2. 生成结构化元数据私有 starter。该命令会预填当前仓库 URL、commit hash 和环境说明，
   但仍保留作者/期刊字段为 `AUTHOR INPUT REQUIRED`：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_starter.py --write-private
```

   如果你想从完全空白的模板开始，也可以改用：

```bash
cp submission_package/submission_metadata_template.json submission_package/submission_metadata.json
```

3. 填写 `submission_package/submission_metadata.json` 中所有
   `AUTHOR INPUT REQUIRED` 字段。这个文件被 Git 忽略，适合存放私有作者信息。
4. 从 `resource_nmcts_experiment/` 目录运行：

```bash
./rebuild_submission_package.sh
./verify_submission_package.sh
```

5. 检查生成的私有预览文件：

- `submission_package/generated_author_declarations.md`
- `submission_package/generated_availability_statements.md`
- `submission_package/generated_cover_letter.md`
- `submission_package/generated_submission_text.md`

6. 如果目标期刊要求双盲审稿，使用匿名 PDF 和匿名源码作为投稿稿件，并把数据/代码
   链接替换成匿名审稿链接。不要把作者姓名、个人仓库、个人邮箱或可追溯致谢放进
   双盲材料。
7. 如果目标期刊不要求双盲审稿，使用作者版 PDF 和源码，并把最终 DOI/URL 写入投稿
   系统和 manuscript availability 文本中。
8. 上传前再次运行：

```bash
./verify_submission_package.sh
rg -n "needs author input|needs revision|closure_path_ready" results/analysis_submission_readiness_audit.md results/analysis_ros_reproduction_gap_audit.md results/analysis_editorial_screening_audit.md results/analysis_submission_support_packet_audit.md results/analysis_submission_metadata_audit.md results/analysis_submission_metadata_validator.md results/analysis_submission_metadata_closure_path.md
```

期望状态是：无 `needs revision`；最终投稿副本中不再保留未处理的
`AUTHOR INPUT REQUIRED`；terminal package verifier 全部通过。

## 上传材料

主要材料：

- 作者版论文：`paper_latex/resource_nmcts_submission_v1.pdf`
- 作者版源码：`paper_latex/resource_nmcts_submission_v1.tex`
- 匿名版论文：`paper_latex/resource_nmcts_submission_anonymous.pdf`
- 匿名版源码：`paper_latex/resource_nmcts_submission_anonymous.tex`
- 可上传 payload：`submission_package/dist/resource_nmcts_submission_payload.tar.gz`
- payload 校验：`submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256`

支撑材料：

- `submission_package/AUTHOR_INPUT_REQUIRED.md`
- `submission_package/submission_checklist.md`
- `submission_package/artifact_reproduction_guide.md`
- `submission_package/editor_screening_brief.md`
- `submission_package/reviewer_concern_brief.md`
- `results/analysis_ros_reproduction_gap_audit.md`
- `results/analysis_editorial_screening_audit.md`
- `results/analysis_submission_support_packet_audit.md`
- `results/analysis_submission_metadata_closure_path.md`
- `results/analysis_payload_verifier_smoke_audit.md`
- `results/analysis_submission_package_verifier.md`

## 不能改坏的论文边界

- Only claim logical-layer quantum Boolean oracle synthesis。
- Do not claim hardware mapping、routing、native-gate scheduling、noise-aware
  compilation。
- Do not claim universal dominance over SSHR、CirKit、RevKit，尤其不要把
  weighted-score 胜利写成 CNOT/depth/ancilla 全胜。
- Treat RevKit `oracle_synth` as a phase/Rz lower-bound or sensitivity probe,
  not a final Clifford+T comparison。
- Frame AI as search control、ranking、pruning、guard 和 Pareto selection 的组合，
  not as deep learning alone explaining the full resource reduction。

## 作者最终判断

如果目标期刊已经确定、作者元数据已经填完、最终归档链接已经生成，并且
`./verify_submission_package.sh` 通过，那么当前包可以进入真实投稿流程。否则，当前包
仍是研究和投稿材料已完成、但作者/期刊输入未完成的状态。
