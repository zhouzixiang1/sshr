# 本机历史归档索引

`misc/archive/` 是只读恢复区，不是当前 XA-202609 的工作输入，也不进入干净竞赛
提交。根 `.gitignore` 已排除它；不要执行 `git add -A`，否则旧 Git 跟踪文件会表现
为删除而不是重命名。

| 当前位置 | 内容 | 使用规则 |
|---|---|---|
| `misc/archive/experiments/resource_nmcts-results/` | 旧 Resource-NMCTS 的 891 个平铺实验结果与审计 | 只用于旧论文复现或追溯，不作为 XA 新证据 |
| `misc/archive/experiments/xa202609-development/` | 被替代的 XA pilot、预算/阈值/拓宽扫描 | 保留 provenance，不改写 manifest/checksum |
| `misc/archive/experiments/resource_nmcts-submission-package/` | 旧学术论文 submission payload | 不得作为 XA 提交包复用 |
| `misc/archive/papers/resource_nmcts/chinese-manuscript-history/` | 中文稿 v1--v39、备用稿和构建记录 | 当前唯一规范稿为 `docs/papers/resource_nmcts/chinese/main.tex`；v40 PDF 只是中间快照 |
| `misc/archive/external-tools/` | 第三方源码、编译树与大二进制 | 按 provenance 独立安装，不能直接随赛题包分发 |
| `misc/tmp/`、`misc/generated/` | 日志、预览、LaTeX 中间件和本机生成物 | 可删除/重建，不写入交付物 |

当前可提交和可运行的主线只有：

- `experiments/src/`、`experiments/scripts/`、`experiments/analysis/`、`experiments/tests/`；
- `experiments/models/`、`experiments/configs/` 和 `experiments/results/xa202609/`；
- `docs/` 中的项目文档、唯一中文竞赛主稿和最终 PPT。

如果旧论文打包脚本必须复现，请显式使用归档路径并在输出中声明其属于旧论文证据；
不要把归档内容复制回 `experiments/results/xa202609/`。
