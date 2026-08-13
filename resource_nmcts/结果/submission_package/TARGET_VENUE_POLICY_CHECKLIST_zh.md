# 目标期刊政策核对表

核对日期：2026-07-09

用途：在最终上传前，把首选 ACM TQC 与备选 Quantum 的公开政策入口映射到私有 `submission_metadata.json` 字段。不要在本 tracked 文件中填写真实作者信息。

推荐用法：先选定目标期刊，再按本表把答案写入被 Git 忽略的 `submission_package/submission_metadata.json`，随后运行 `./rebuild_submission_package.sh` 和 `./verify_submission_package.sh`。

## 必须先确认的总原则

- 本文当前只主张 logical-layer quantum Boolean oracle synthesis。
- 若选择 ACM TQC，当前已有 `paper_latex/resource_nmcts_submission_acm_tqc.tex`、review-stage CCS/keywords 和已通过的 ACM/TQC format smoke，但正式 ACM metadata、rights、ORCID、conflict、AI disclosure 与最终 archive 链接仍需作者确认。
- 若选择 Quantum，通常需要 arXiv/quant-ph 路线、贡献声明和 AI/LLM 使用范围说明。
- Data/code archive DOI、匿名审稿链接、license、funding、acknowledgements、conflict、prior submission 都不能从代码自动推断。

## 核对矩阵

| venue | policy item | fill in private JSON | author action | source | boundary |
|---|---|---|---|---|---|
| ACM Transactions on Quantum Computing | Submission route and manuscript type | `target_venue.name; target_venue.manuscript_type` | Confirm ACM TQC as the final target and choose the manuscript type expected by the submission system. | https://dl.acm.org/journal/tqc/author-guidelines | This records the upload route only; it does not select the journal on behalf of the author. |
| ACM Transactions on Quantum Computing | ACM template and TAPS-compatible LaTeX discipline | `target_venue.formatting_policy_checked; target_venue.reference_style_checked; target_venue.supplementary_material_policy_checked` | Confirm the ACM primary-article template version, reference style, package restrictions, and supplementary-material handling before upload. | https://www.acm.org/publications/authors/submissions | The current ACM/TQC smoke draft proves a review-format path compiles; final ACM metadata, rights, CCS, and keywords still require author review. |
| ACM Transactions on Quantum Computing | Authorship, ORCID, corresponding author, and conflicts | `authors[]; corresponding_author.*; author_contributions.*; competing_interests.statement` | Fill author order, affiliations, ORCIDs, corresponding author, contributions, and competing-interest wording in the private metadata JSON. | https://www.acm.org/publications/policies/new-acm-policy-on-authorship | These are private author decisions and cannot be inferred from the repository. |
| ACM Transactions on Quantum Computing | AI assistance disclosure | `target_venue.ai_disclosure_policy_checked; ai_assistance.statement` | Choose the exact disclosure wording for any AI-assisted writing, code, bibliographic, figure, or calculation use, or record that no disclosure is required for the actual use case. | https://www.acm.org/publications/policies/frequently-asked-questions | The checklist does not decide whether the author's actual tool use crosses ACM's disclosure threshold. |
| ACM Transactions on Quantum Computing | Prior publication and preprint status | `preprint_and_prior_submission.*` | Record any arXiv/preprint URL and certify that the manuscript is not under review elsewhere unless the selected venue explicitly permits it. | https://www.acm.org/publications/policies/new-acm-policy-on-authorship | Prior-submission history is author-specific and must not be guessed. |
| Quantum | ArXiv or quant-ph route | `target_venue.name; target_venue.manuscript_type; preprint_and_prior_submission.preprint_url_or_doi` | If Quantum is selected, post or cross-list the manuscript to quant-ph and record the arXiv identifier before journal submission. | https://quantum-journal.org/instructions/authors/ | This is only needed if Quantum becomes the selected venue. |
| Quantum | Author contribution and AI statement | `author_contributions.*; ai_assistance.statement` | Prepare the contribution statement and include any AI/LLM use scope, including grammar checking, reformatting, text, image, bibliography, code, or calculation assistance. | https://quantum-journal.org/instructions/authors/ | The contribution statement must reflect the actual author roles. |
| Quantum | Cover letter, editor, referee, and exclusivity checks | `cover_letter.target_editor; cover_letter.suggested_reviewers; cover_letter.excluded_reviewers; preprint_and_prior_submission.prior_submission_history` | If Quantum is selected, prepare suggested editors/referees or avoidance lists and confirm no concurrent journal submission. | https://quantum-journal.org/instructions/authors/ | Editor/referee choices and prior-submission status are author decisions. |
| Any selected venue | Data, code, archive, license, and anonymous-review links | `data_availability.*; code_availability.*; target_venue.anonymous_review_required` | Create final public archive links or anonymous review links as required, choose the code license wording, and paste final availability text into private metadata. | submission_package/dist/resource_nmcts_submission_payload.tar.gz | The repo can generate the package, but final DOI/URL/license choices remain outside the tracked source. |

## 填完后必须验证

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python validate_submission_metadata.py
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_text_preview.py
./rebuild_submission_package.sh
./verify_submission_package.sh
```
