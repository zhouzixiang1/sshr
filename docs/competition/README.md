# XA-202609 competition delivery

该目录保存赛题、证据契约和提交说明。中文竞赛主稿只有一份，位于
`../papers/resource_nmcts/chinese/main.tex`，并持续同步到 Overleaf。

计划结构：

```text
docs/competition/
├── official/      # 赛题原始材料
├── evidence/      # 小型 verified summary 和 claim map
├── report/        # 学术论证契约；不另存主稿或 PDF
├── status/        # 当前验收状态与剩余缺口审计
└── submission/    # 白名单提交树说明

experiments/configs/xa202609/  # 冻结实验配置
experiments/demo/              # 演示脚本、样例和预期输出
```

大型 raw、训练缓存、私有报名表、联系信息和 API 凭据不得进入 Git。正式
`submission/` 必须由 manifest 驱动，并在干净目录通过独立 verifier。
