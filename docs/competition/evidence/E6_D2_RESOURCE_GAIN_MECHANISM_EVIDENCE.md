# E6-D2：resource-gain QAOA replay 的机制修复证据

## 结论

D2 只改动 replay policy teacher：将 QAOA 最终测量样本中每个可行 bitstring 的
正整程序资源收益分配给其所选动作，再按累计 credit 归一化；permuted control 使用
同一份 source credit 的固定标签置换。训练仍冻结 formal-v4 trunk，两个主比较臂均
使用 `value_loss_weight=0`、相同初始化、相同 64 个训练 group 和相同 1,024 次样本
呈现。该单一机制修复恢复了 QAOA 标签关联信号，但尚未达到性能验收：

- fresh structured validation 的 expanded-cap256 view 中，
  `gain_weighted_qaoa_vw0 - gain_weighted_permuted_vw0` 的资源比差为
  **-0.1688789442**（越低越好），W/T/L=`32/0/0`；
- 只在 structured diagnostics 完成后打开的 OOD endpoint 中，同一差为
  **-0.1535114735**，W/T/L=`31/1/0`；
- QAOA 臂在 structured/OOD 的平均 `Y` 分别为 `0.7470455`/`0.8116278`，仍略高于
  greedy anchor 的 `0.7410552`/`0.7928633`。greedy、legacy replay 和 frozen head
  只作诊断锚点，不属于主因果对比。

因此，证据支持的机制判断是：D1 的主要失败点在旧 action-marginal replay target，
而不是 QAOA 未执行或 scheduler fallback。resource-gain teacher 能把 source-label
关联转化为更好的模型排序和下游资源结果；但它仍未超过 strongest greedy，也不是
等算力、正式评估或性能结果。

## 设计与审计边界

- 数据 seed 为 train `20261011`、structured validation `20261012`、OOD
  `20261013`；三者在 vector、whole-vector cluster 和 orbit-cluster 三个层面均
  0 overlap。没有复用旧 E6 heldout。
- train 为 64 个 `n=6/7` case；structured validation 和 OOD 各 32 个 case。
  structured 同时包含 matched-6 teacher-aware view 与 expanded-cap256 teacher-free
  endpoint view；OOD 只有 expanded-cap256 teacher-free endpoint。
- train 64/64、structured 32/32 group 均有正 resource gain，训练报告中的
  `zero_gain_skipped_group_count=0`。若无正 gain，trainer 会跳过该 group；若全部为
  zero gain，则在构造模型前失败。
- endpoint 的 head 只负责 top-k 排序；所有臂随后使用相同的 budget-2 exact
  conflict-aware scheduler 和 arm-neutral raw analytic utility。所有 endpoint 行的
  semantic verification 均通过，fallback/degraded rate 均为 0。
- 本结果是 single-researcher deterministic development mechanism repair。
  `formal_evaluation=false`、`performance_evidence=false`、
  `quantum_advantage_claimed=false`；不支持硬件、密码泛化、加速或优势主张。

## 五文件证据

- Run ID：`20260813-e6-d2-resource-gain-teacher-v1-full-s20261011`
- Bundle：
  `experiments/results/xa202609/20260813-e6-d2-resource-gain-teacher-v1-full-s20261011/`
- Clean source commit：`51288b1e2aab3c420ee93a7afd85bbc9c22b2243`
- Development code commits：`46a370f`、`51288b1`；result commit：`5da75a4`
- 五文件 snapshot SHA-256：
  `b16715196ff1e456184eaae6654f73f28c12454c5190d288384739f8bc1576c1`

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `config.json` | 4,101 | `35e0a08f788c2770740313d01ba89568b5944e41aec225a79f463b7e1f384d57` |
| `results.json` | 22,970 | `4f5a40739c764efc01fcad5c5edb2b13ad5d9bf56cc0a7b1262ae7cd43364291` |
| `raw.jsonl` | 9,569,432 | `0e9c8d74eaf836e04cc77b1f317646ad636bb4508ee83a97372038c248963135` |
| `diagnostics.json` | 46,650 | `02bb269b8d38e711d2d1ff55fcda98c612b989c2bded89574797a66b5945fd44` |
| `checksums.sha256` | 316 | `cec28225b9edcc970bacf6c3989eac3661ffaf1d387aece5108bb914b81ebda3` |

snapshot 对按文件名排序的 `{name,sha256,bytes}` records 精确执行
`json.dumps(records, sort_keys=True, separators=(",", ":")) + "\n"`，再对 UTF-8
bytes 取 SHA-256。
`results.json` 绑定 config SHA、clean source、split overlap、训练报告和 800-row raw
计数；`diagnostics.json` 记录 matched teacher、structured expanded 与 OOD 三层结果。

在 clean source commit `51288b1e...` 的 checkout 中，从 `experiments/` 重跑同一开发协议：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python \
  scripts/run_e6_d2_resource_gain_teacher_v1.py \
  --config configs/xa202609/e6_d2_resource_gain_teacher_v1.json \
  --profile full \
  --run-id 20260813-e6-d2-resource-gain-teacher-v1-full-s20261011 \
  --output /tmp/e6-d2-resource-gain-rerun-full
```

请为每次复演选择一个新的空目录；runner 不覆盖或删除既有五文件 bundle。运行时间不进入确定性证据或
性能比较。
