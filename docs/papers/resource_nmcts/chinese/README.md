# 中文主文稿

当前唯一中文规范源是 `main.tex`，当前构建产物为
`resource_nmcts_competition_current.pdf`。正文会持续吸收通过 verifier 的竞赛证据，
并同步到项目内的 Overleaf Git 工作树；它复用兄弟目录 `../english/` 中经审计的
表格与图件。原 v40 PDF 已移入历史归档，不代表终稿。

```bash
cd docs/papers/resource_nmcts/chinese
latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error \
  -jobname=resource_nmcts_competition_current main.tex
```

本地稿与 Overleaf 的路径形式不同：本地指向 `../english/`，Overleaf 使用项目根
的 `figures/`、`tables/`。不要手工复制文件；使用
[`../overleaf/sync_to_overleaf.sh`](../overleaf/sync_to_overleaf.sh) 进行检查和同步。

v1--v39、备用中文稿、构建日志和更早 PDF 已移到
`../../../../misc/archive/papers/resource_nmcts/chinese-manuscript-history/`。
