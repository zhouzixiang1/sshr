# E2：QAOA 固定预算分支调度证据

## 证据身份

- Run ID：`20260810-e2-qaoa-scheduler-v1-s120000`
- 冻结配置：`experiments/configs/xa202609/e2_qaoa_scheduler_v1.json`
- 结果目录：`experiments/results/xa202609/20260810-e2-qaoa-scheduler-v1-s120000/`
- 数据：独立 held-out 随机 Boolean 函数，(n=8,9) 各 10 个；每个函数 3 个搜索种子。
- 公平性：七种调度器共享同一根候选池、效用向量、冗余矩阵、(K=10)、
  (B=4) 和 24 次 MCTS simulation；learned value 关闭。
- AI 条件：根节点 ANF 项数均超过 96，置换等变 policy 实际参与候选排序；
  QAOA 只决定哪些独立 action edge 获得搜索预算，不改变 `Plan` 语义。

Artifact manifest SHA-256：
`63f522f36bb66a00167bc839a1d92b2948797b953d0e33ccfa61dcec0e1619c4`。

## 主要结果

资源分数越低越好，调度目标越高越好。比值和置信区间均先在每个 Boolean
函数内平均 3 个搜索种子，再以 20 个函数簇进行 5000 次 bootstrap。

| 调度器 | exact objective 命中率 | objective regret | 资源分数 / greedy | 函数簇 95% CI | 相对 greedy 胜/负/平 |
|---|---:|---:|---:|---:|---:|
| random | 0.0% | 0.135873 | 1.007852 | [1.001311, 1.015243] | 5 / 15 / 0 |
| top-B | 0.0% | 0.101250 | 1.000954 | [0.998814, 1.002967] | 5 / 9 / 6 |
| greedy | 65.0% | 0.007694 | 1.000000 | [1.000000, 1.000000] | 0 / 0 / 20 |
| exact | 100.0% | 0.000000 | 0.999124 | [0.997985, 0.999985] | 4 / 1 / 15 |
| QAOA ideal | 26.7% | 0.067263 | 1.000355 | [0.997170, 1.003417] | 7 / 6 / 7 |
| QAOA shot | 81.7% | 0.002288 | 0.999734 | [0.998476, 1.000921] | 4 / 3 / 13 |
| QAOA noisy | 76.7% | 0.003564 | 0.999734 | [0.998532, 1.000907] | 4 / 3 / 13 |

QAOA-shot 将局部 exact-hit 从 greedy 的 65.0% 提高到 81.7%，平均 objective
regret 从 0.007694 降到 0.002288；但其端到端资源分数比值的函数簇置信区间
跨过 1。因此，本实验支持“QAOA 改善固定池中的组合选择质量”，不支持“QAOA
已经稳定改善最终 Oracle 资源”或“量子加速”。局部调度目标与非局部搜索回报的
错配，是下一轮反馈目标校准需要解决的科学问题。

## QAOA 执行分账

| 模式 | attempted | direct non-fallback | repair | fallback |
|---|---:|---:|---:|---:|
| ideal | 60 | 25 | 35 | 0 |
| shot | 60 | 60 | 0 | 0 |
| noisy | 60 | 60 | 0 | 0 |

`ideal` 返回 statevector 的模态 bitstring，而 `shot/noisy` 从实际采样 counts 中
选择最优可行样本；前者不是后者的“无限 shots 极限”。35 条 ideal repair 均保留
原始 bitstring，并未伪装为量子直接输出。2% 独立测量比特翻转使 4/60 个 noisy
子集相对 shot 改变，但本矩阵中最终资源分数未改变。

## 验证门

- 420/420 条 trial 的 Plan ANF、Circuit ANF 和全真值表 Oracle 验证通过；
- 20/20 个候选池的 QUBO 能量恒等式、可行集排序和罚项充分性通过；
- `K=0`、`K<B`、`K=B`、`K>B` 四类边界通过；
- 每次 simulation 只评估一个根 action edge，排除 edge 的访问数始终为 0；
- 三种 QAOA 模式共 180 次调用，180 次成功，0 fallback；
- 24/24 verifier checks 与 artifact checksum 验证通过。

## 结论边界

该证据来自固定 (p=1) 的 NumPy statevector 小规模模拟；noisy 只实现独立测量
比特翻转。它没有原生门、拓扑路由、门级噪声或真机证据，也没有证明量子优势。
下一阶段应把执行校准后的回报写回 utility，并在 AES 坐标函数与超导原生门链上
重新检验“调度目标改善是否转化为最终资源与含噪执行收益”。
