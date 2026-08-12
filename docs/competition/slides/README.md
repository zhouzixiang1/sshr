# XA-202609 答辩 PPT

本目录只保存当前可交付版本及其人工可读 QA；候选文件、inspect 输出和逐页渲染
统一放在 `misc/tmp/ppt/xa202609-deck/`，不作为交付物。

- `XA-202609_双向智能Boolean_Oracle答辩稿.pptx`：14 页当前答辩稿；每页讲稿均含
  `[Sources]`，结论指向 `../evidence/` 或
  `../../../experiments/results/xa202609/` 的可验证证据。
- `XA-202609_答辩稿_contact-sheet.png`：14 页视觉总览。
- `qa_report.md`：PPTX、builder 与联系表的固定 SHA，以及结构、溢出、模板保真和
  LibreOffice 渲染检查结果。

叙事主线为：密码 Boolean Oracle 场景与三类资源错配 → AI for Quantum 的置换等变
policy/value 与可验证 Neural MCTS → Quantum for AI 的固定预算 QAOA diversity
scheduler → 原生门、路由、含噪反馈 → E1--E4 正负证据 → 贡献和边界。当前 E4-v2
尚未写成正式结果。

当前本机唯一生成入口是
`misc/tmp/ppt/xa202609-deck/build-final-deck.mjs`；它与用户提供的“2025挑战”模板、
最终 PPTX 的 SHA 均记录在 `qa_report.md`。后续实质更新必须重新执行同一套结构、
模板保真和双渲染 QA，再替换当前 PPTX。
