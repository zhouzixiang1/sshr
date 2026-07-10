# 实验恢复指南

## 当前状态（2026-06-03 停止时）

| 实验 | 检查点文件 | 进度 | 说明 |
|---|---|---|---|
| n=5 CNOT（新代码） | `checkpoints/ilp_n5_cnot_fns2000_seed42.json` | 51/2000 | 可直接恢复 |
| n=6 CNOT（新代码） | `checkpoints/ilp_n6_cnot_fns200_seed42.json` | 0/200（文件损坏） | 需重新开始 |

旧代码结果（已备份，勿删）：
- `checkpoints/ilp_n5_cnot_fns2000_seed42_v1_oldcode.json` — 旧代码 n=5，2000/2000 完成，CNOT=75202
- `checkpoints/ilp_n6_cnot_fns100_seed42_v1_oldcode.json` — 旧代码 n=6，100/100 完成，CNOT=7064

---

## 恢复命令

必须在 `sshr/` 目录下运行，使用 `sshr` conda 环境（含 Gurobi）。

### 恢复 n=5（从第 51 个函数继续）

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/sshr

nohup /opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_checkpoint.py \
  --n 5 --objective cnot --fns 2000 \
  > results/n5_cnot_v2.log 2>&1 &

echo "PID=$!"
```

`--resume` 是默认选项，会自动从第 51 个函数继续。预计剩余时间：**~5.5h**。

### 重启 n=6（从头开始）

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/sshr

# 先删除损坏的检查点文件
rm experiments/checkpoints/ilp_n6_cnot_fns200_seed42.json

nohup /opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_checkpoint.py \
  --n 6 --objective cnot --fns 200 --timeout 600 --no-resume \
  > results/n6_cnot_v2.log 2>&1 &

echo "PID=$!"
```

`--timeout 600`：每函数 600s（旧代码用 120s，70% 超时；新代码 600s 预计降低超时率）。预计时间：**~8–12h**。

---

## 查看进度

```bash
# 实时进度（每函数完成后更新）
cat experiments/checkpoints/ilp_n5_cnot_fns2000_seed42.json
cat experiments/checkpoints/ilp_n6_cnot_fns200_seed42.json

# 日志末尾（每 10 个函数打印一次）
tail -20 results/n5_cnot_v2.log
tail -20 results/n6_cnot_v2.log

# 确认进程在运行
ps aux | grep run_ilp_checkpoint | grep -v grep
```

---

## 注意事项

1. **两个实验可同时运行**，Gurobi WLS 学术许可支持并行（但 CPU 竞争会让各自变慢）。
2. **进程被 macOS 杀死后**，直接重新运行上面的恢复命令即可（不要加 `--no-resume`），检查点会自动续传。
3. **n=6 检查点损坏原因**：macOS `com.apple.provenance` 安全属性导致新文件被锁定无法读取。删除旧文件后重新运行可以规避。
4. **结果对比基线**：
   - n=5 旧代码 CNOT=75202（2000 fns），新代码预计 ~73000–74000
   - n=6 旧代码 CNOT=7064（100 fns，70% 超时），新代码 200 fns 质量应大幅提升

---

## 其他待运行实验

| 实验 | 命令 | 预计时间 |
|---|---|---|
| n=5 T 目标 | `--n 5 --objective t --no-resume` | ~8–10h |
| n=6 更多函数 | `--n 6 --fns 500 --timeout 300` | 视机器情况 |
| n=4 T 目标验证 | `--n 4 --objective t` | <5min |
