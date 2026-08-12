# XA-202609 答辩 PPT

本目录保存当前可交付版本、最终 inspect、联系表及人工可读 QA；候选 inspect 和逐页渲染
统一放在 `misc/tmp/ppt/xa202609-deck/`，不作为交付物。

- `XA-202609_双向智能Boolean_Oracle答辩稿.pptx`：14 页当前答辩稿；每页讲稿均含
  `[Sources]`，结论指向 `../evidence/` 或
  `../../../experiments/results/xa202609/` 的可验证证据。
- `XA-202609_双向智能Boolean_Oracle答辩稿.pptx.inspect.ndjson`：最终结构化 inspect。
- `XA-202609_答辩稿_contact-sheet.png`：14 页视觉总览。
- `qa_report.md`：PPTX、builder 与联系表的固定 SHA，以及结构、溢出、模板保真和
  LibreOffice 渲染检查结果。

叙事主线为：密码 Boolean Oracle 场景与三类资源错配 → AI for Quantum 的置换等变
policy/value 与可验证 Neural MCTS → Quantum for AI 的固定预算 QAOA diversity
scheduler → 原生门、路由、含噪反馈 → E1--E5 正负证据 → E6-D1 标签错位诊断 →
E6-D2 resource-gain teacher 修复 replay 标签语义 → 全新种子、匹配预算下对
strongest greedy 的下一门实验。D2 只支持 development mechanism repair；E4-v2、
E5 与 E6 均未被写成 formal/performance/hardware/advantage 证据。

当前 D2 定点更新入口是
`misc/tmp/ppt/xa202609-deck/d2-candidate/build-d2-update.mjs`；它从当前 14 页 deck
复制 1:1 starter，只重写第 12--14 页的继承文本框与讲稿。builder、最终 PPTX 与 QA
产物的 SHA 均记录在 `qa_report.md`。后续实质更新必须重新执行同一套结构、模板
保真和双渲染 QA，再替换当前 PPTX。
