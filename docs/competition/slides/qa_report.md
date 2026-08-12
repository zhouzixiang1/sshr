# XA-202609 答辩稿最终 QA 报告

日期：2026-08-13  
状态：**PASS**

## 交付物与唯一构建入口

- 最终答辩稿：`docs/competition/slides/XA-202609_双向智能Boolean_Oracle答辩稿.pptx`
- Canonical builder：`misc/tmp/ppt/xa202609-deck/d2-candidate/build-d2-update.mjs`
- Artifact 联系表：`docs/competition/slides/XA-202609_答辩稿_contact-sheet.png`
- 最终 inspect：`docs/competition/slides/XA-202609_双向智能Boolean_Oracle答辩稿.pptx.inspect.ndjson`

SHA-256：

- PPTX：`fa7b319fa620a37a62302be24c04ed70fb432be91d7d0fafbd8cf2e08377412f`
- builder：`90c0d842b754f949625328bb58ae5543ffb8f3dccf7d2ac46d2b4715baa12cbf`
- Artifact contact sheet：`72558f6634c5f4717d7305db5e45845fa62c2ae6a73fea8b2e2dcbb4f390536f`
- inspect：`46ab7fefe816a955a91754c777f501e16153b3b99668bf6e9d3bf1e10fac343e`
- structural QA：`4215613ea2b8098f77aa7fb51c0111615d8c01866d7c882d87a250ccec0c84fe`
- template fidelity QA：`3969de614b38e94e9fac0ae814b474313b88c8cfe7340e6f5c97f6aafd61648e`
- LibreOffice contact sheet：`1ae793432ea7cc645d741f4a77da76afd7b634a3f9b61cae7456bb756409af41`

## 内容与主张边界

- 14 页方法论叙事；14/14 页讲稿均含 `[Sources]`。
- 第 12 页唯一可见测试计数为 `631 tests + smoke ok`；讲稿记录当前完整回归 `631 passed in 411.04s`，并保留历史 fresh-v2 锚点 `383 passed in 295.779s`。
- D2 共 800 rows（96 audit + 384 matched + 320 endpoint）；讲稿将其中语义检查准确标为 `704/704 program diagnostic rows`，未误写成 endpoint rows。
- 39 页中文主稿已同步：PDF SHA-256 `f6826f61595e5a7de9b311a13e6027b061c99323fbbdc626196986a7c3cbda95`；Overleaf HEAD `cb6962eab16974ce7a5734ae43094a15abf99138`。
- 第 13 页记录 D2 resource-gain teacher 的单一干预：structured development 上 `gain−permuted ΔY=-0.1688789442`、W/T/L=`32/0/0`；OOD 上 `ΔY=-0.1535114735`、W/T/L=`31/1/0`。
- D2 修复了 D1 的标签语义错位，但仍未超过 strongest greedy：structured `ΔY=+0.005990`，OOD `ΔY=+0.018765`。结论仅为 development mechanism repair，不是性能或量子优势。
- 下一步冻结 D2，不再改 teacher；用全新 seeds、matched compute 直接做 gain-QAOA vs strongest-greedy paired evaluation。
- AI4Q/Q4AI 链条已闭合，但 `formal/performance/hardware/generalization/advantage=false`；保留 `abstract logical X/CNOT/MCT proxy`、`workspace peak≤2` 且 MCT 分解未计的资源边界。

## QA 结果

- `slides_test.py`：PASS，无文本溢出。
- 结构检查：PASS；14 个 slide、14 个 notes、14/14 `[Sources]`；无空 slide placeholder、默认提示词、旧测试计数或实质越界对象。
- Template fidelity：PASS，0 issues；第 1--11 页 preserve-only，第 12--14 页只改继承文本框与 notes；master/layout、字体、图像和对象几何保持不变。
- Artifact-tool 已逐页全尺寸渲染并复核 14/14 页；第 12--14 页内容、几何、裁切与重叠均通过。
- LibreOffice 已完成第二套 14 页渲染；第 12--14 页全文、数值、换行与几何均与 Artifact 渲染一致，LO 兼容性通过。
- 最终路径再次通过 `slides_test.py`、结构检查、模板保真与 `unzip -t`；PPTX 仅在候选全部 PASS 后原子替换。

结构化记录：

- `misc/tmp/ppt/xa202609-deck/qa/structural-qa.json`
- `misc/tmp/ppt/xa202609-deck/d2-candidate/qa/template-fidelity-check.json`
