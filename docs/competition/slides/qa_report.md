# XA-202609 答辩稿最终 QA 报告

日期：2026-08-12  
状态：**PASS**

## 交付物与唯一构建入口

- 最终答辩稿：`docs/competition/slides/XA-202609_双向智能Boolean_Oracle答辩稿.pptx`
- Canonical builder：`misc/tmp/ppt/xa202609-deck/build-final-deck.mjs`
- Artifact 联系表：`docs/competition/slides/XA-202609_答辩稿_contact-sheet.png`
- LibreOffice 联系表：`misc/tmp/ppt/xa202609-deck/qa/libreoffice-contact-sheet-407-final.png`
- 历史 builder 仅为非规范追溯物；本次未运行 `legacy/` 下任何脚本。

SHA-256：

- builder：`18bf17e082319a6cdcd30f80c14b9b57c2989769a073f0b7cb0797436e078830`
- PPTX：`cdb66ca733a6783cd020fd7b9ab8c568e7a80ef876d1109330cb62b3084680ae`
- Artifact contact sheet：`c22d5224d1a1d74e74d995c075b88ffcab49bc7e7029a4cea9dcc3db71168611`
- LibreOffice contact sheet：`82573fbee8a7f8634dc001d8dc435647e73eda1e113f98fabad5a1f1ea506117`

## 内容与主张边界

- 14 页方法论叙事；每页为结论式标题，14/14 页讲稿均含 `[Sources]`。
- 第 11 页保留 E4 局部机制证据：exact frozen-pool hit 由 3/8 提升到 8/8，selection changed 5/8，logical QASM 4/8；不把局部目标升级为端点改善。
- E4-v2 为 post-E4 frozen replication，不是 held-out。primary native-2q 差为 `−513.9375`，95% CI `[−2059.0625, 589.9375]` 跨 0，`generalization_claim=false`，不支持改善主张。
- E5：ASCON 可调度 group 为 0、PRESENT 为 6；negative audit 重建 90/90 行。V3 current/fresh 20/20 与 fresh-v2 19/19 进一步闭合软件可移植验证，但 `protocol_acceptance=false`、`experiment_completed=false`，没有 accepted endpoint；这些检查数不是性能指标。
- 第 12 页仅显示当前集成树 `407 tests + smoke ok`；讲稿记录完整回归为 `407 passed in 334.05s`，legacy smoke 为 `smoke ok`。E4-v2 external checks 为 calibration 26/26、replication 32/32，E5 为 V3 current/fresh 20/20、fresh-v2 19/19 且 `protocol=false`。
- 锚定 fresh-validation V2 的 `383 passed in 295.779s` 仅保留在讲稿中作为历史冻结锚定，明确不代表当前集成树，也未被改写为 407。
- 35 页中文主稿已同步 Overleaf `origin/main`：`c5c6993d1589469a61dfe18000a313d798b1c02f`；当前 PDF SHA-256：`f6a19cf8a7d2e245505777838a934f30219b378a063703784bf6cf535f908d8f`。
- 第 13 页把 E6-MSO 标记为已实现并独立验证的 mechanism MVP；资源表述限定为显式 `workspace peak≤2`，且明确 MCT 分解未计。讲稿进一步限定该计数仅是 abstract logical X/CNOT/MCT proxy，并非分解后或硬件精确门数。仍无 shared head、QAOA replay、formal blind result 或性能证据，`598→581` 仅为开发观察。
- 所有执行证据仍为 synthetic profile，`hardware=false`；不声称真机结果、量子加速或量子优势。

## QA 结果

- `slides_test.py --width 1600 --height 900`：PASS，无文本溢出。
- PPTX XML/结构检查：PASS；14 个 slide XML、14 个 notes XML、14/14 `[Sources]`；无空 slide-level placeholder、无默认提示词、无旧测试计数。
- OOXML 与 artifact inspect 均确认第 12 页可见区域只包含当前 `407 tests` 断言；speaker notes 已确认 `383 passed in 295.779s` 仅为历史 fresh-validation V2 锚点，并确认最新 Overleaf HEAD、PDF SHA 与 E5 检查数并非性能成功率。
- Layout 检查：PASS；无实质越界对象；仅保留模板原有的 ≤3 px 背景出血。
- Template fidelity：PASS，0 issues；最终版从 `template-starter.pptx` 导入并用 `@oai/artifact-tool` 导出，未使用 python-pptx。
- Artifact-tool 与 LibreOffice 已分别渲染全 14 页；两套联系表及第 12、13 页全尺寸图均完成逐页视觉复核。第 12 页两行证据完整可读，第 13 页 workspace 边界保持完整且未裁切或重叠。
- Artifact-tool 对两个模板继承连接符启用 fallback route；最终双渲染、结构、模板与溢出检查均通过，定为低严重度、不阻塞交付。

结构化 QA 记录：`misc/tmp/ppt/xa202609-deck/qa/structural-qa.json`。
