# 英文学术稿与共享图表

本目录保留英文投稿源（v1、anonymous、ACM/TQC）以及中文主稿复用的
`figures/submission_v36/` 和 `tables/`。这些内容对应旧论文证据链，而不是
XA-202609 的新竞赛主张。

```bash
cd docs/papers/resource_nmcts/english
latexmk -pdf resource_nmcts_submission_v1.tex
```

旧实验数据、旧 submission payload 和可再生构建中间件均已归档到
`../../../../misc/archive/experiments/` 或 `../../../../misc/generated/`。当前竞赛
文稿应从 `../chinese/` 和 `../../../competition/report/` 管理。
