# 中文竞赛主稿 → Overleaf 同步

本地规范源不是一个第二份 Overleaf 克隆，而是：

```text
docs/papers/resource_nmcts/chinese/main.tex
```

它复用本地 `../english/figures/submission_v36/` 和 `../english/tables/`。Overleaf
唯一对应的 Overleaf Git 仓库为：

```text
https://git@git.overleaf.com/6a748d57e970d09ad3c0dda4
```

项目采用扁平布局，因此同步时将：

- 当前中文主稿转换为 Overleaf 的 `main.tex`；
- 同步说明文件 `README_OVERLEAF.md`；
- 仅复制正文实际引用的算法、表格和图件；
- 把本地 `../english/...` 路径映射为 Overleaf 的 `algorithms/`、`tables/`、`figures/`；
- 不删除 Overleaf 中不在本地镜像内的文件；不触碰另一个统计建模项目。

先确保 Overleaf 克隆干净并更新，再执行：

```bash
target="$(pwd)/docs/papers/resource_nmcts/overleaf/worktree"
git -C "$target" pull --ff-only origin main

# 只比较，不写入
bash docs/papers/resource_nmcts/overleaf/sync_to_overleaf.sh --check

# 写入克隆并在临时目录编译，不推送
bash docs/papers/resource_nmcts/overleaf/sync_to_overleaf.sh --apply

# 通过编译后，创建一次明确提交并推送
bash docs/papers/resource_nmcts/overleaf/sync_to_overleaf.sh \
  --push \
  --message 'sync: update AI-Q Boolean Oracle manuscript'
```

上述命令需从项目根目录运行。脚本默认使用同级的 `worktree/`；只有在临时使用
另一个克隆时，才传入 `--overleaf-dir "$target"` 或设置 `OVERLEAF_WORKTREE`。

`--push` 会拒绝有未提交改动的克隆，且只暂存 `main.tex`、本次正文使用的
`README_OVERLEAF.md`、`algorithms/`、`tables/` 和 `figures/`。因此不能静默覆盖
Overleaf 端的独立改动。竞赛正文不再维护第二份 LaTeX 主文件；通过验证的新结果
先写入本地 `chinese/main.tex`，再由本脚本编译并推送到上述仓库。
