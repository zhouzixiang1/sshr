# XA-202609 答辩稿最终 QA 报告

日期：2026-08-13  
状态：**PASS**

## 交付物与唯一构建入口

- 最终答辩稿：`docs/competition/slides/XA-202609_双向智能Boolean_Oracle答辩稿.pptx`
- Canonical builder：`misc/tmp/ppt/xa202609-deck/build-final-deck.mjs`
- Artifact 联系表：`docs/competition/slides/XA-202609_答辩稿_contact-sheet.png`
- 最终 inspect：`docs/competition/slides/XA-202609_双向智能Boolean_Oracle答辩稿.pptx.inspect.ndjson`

SHA-256：

- PPTX：`bf830dee8dd9adf5e9110cbf8b73f0ebbfbb3fe453c3aad03c057b031581d4e3`
- builder：`2a07643d0072b2cc8e7657273eccc5c11b738a7fd9859e927b3741be628d0975`
- Artifact contact sheet：`3a333413142beb87973341ea3d652bd936c2f5f1f79d7c87627ebad3902547e6`
- inspect：`8242a57e896aa0214cbb321fb0f3a277b62ab51a5e552fb69181bfbd9f69bcca`
- structural QA：`95698a8706f29fff2e9bb67175064135e7771376dbf9d74ce926f4b2c38546d3`
- template fidelity QA：`5b398a97c367e671a26429c0533a23c5172e0328acdc0e13bc5b827da7602db5`

## 内容与主张边界

- 14 页方法论叙事；14/14 页讲稿均含 `[Sources]`。
- 第 12 页唯一可见测试计数为 `588 tests + smoke ok`；讲稿记录当前完整回归 `588 passed in 363.66s`，并保留历史 fresh-v2 锚点 `383 passed in 295.779s`。
- 38 页中文主稿已同步：PDF SHA-256 `fadd6965e39a390589086e1784e6e68984ce2121339dbace802775858d3fcfe3`；Overleaf HEAD `739b6c921e5c574871b12172024e2302aed8bb9c`。
- 第 13–14 页记录 Q4AI 四臂 development 机制消融已运行：QAOA-permuted 的下优 score-ratio 差 `+0.094978`，95% CI `[0.069638, 0.123767]`，`p=9.9999e-6`，W/T/L=`0/3/29`；`claim=false`。
- QAOA/random 的 32/32 endpoint 相同，且 31/32 为空选择。结论限定为当前 teacher 标签关联有害或错位，不是量子优势；下一步仅做 D1 机制诊断，不进行事后调参。
- AI4Q/Q4AI 链条已闭合，但 `formal/performance/hardware/generalization/advantage=false`；保留 `workspace peak≤2` 且 MCT 分解未计的资源边界。

## QA 结果

- `slides_test.py`：PASS，无文本溢出。
- 结构检查：PASS；14 个 slide、14 个 notes、14/14 `[Sources]`；无空 slide placeholder、默认提示词、旧测试计数或实质越界对象。
- Template fidelity：PASS，0 issues；使用现有 PPTX 视觉模板、canonical builder 与 `@oai/artifact-tool`，未使用 python-pptx 或直接 OOXML 修改。
- Artifact-tool 已逐页渲染并复核 14/14 页；第 12–14 页内容、几何、裁切与重叠均通过。
- LibreOffice 已完成第二套 14 页渲染。该运行时对“微软雅黑/黑体”缺少字体替换，中文缺字与旧 final 的同运行时结果一致；拉丁字符、数值和几何未见新增异常，因此此项记录为既有运行时字体限制，Artifact 渲染作为视觉验收依据。

结构化记录：

- `misc/tmp/ppt/xa202609-deck/e6-candidate/structural-qa.json`
- `misc/tmp/ppt/xa202609-deck/e6-candidate/qa/template-fidelity-check.json`
