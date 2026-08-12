# E6：QAOA replay→共享策略头因果实验的负向证据

## 结论

E6 首次实际闭合了 `QAOA 最终测量 counts → replay 标签 → 共享 policy/value
head → 未见多输出 Boolean 函数的候选排序 → 精确共享动作调度`。它证明 Q4AI
信号确实进入 AI4Q 模型并改变了下游决策，但预设主假设被方向明确地否定：相对
复用同一 QAOA 分布、只置换动作标签关联的对照，保留原始标签关联的 QAOA replay
使 held-out 抽象资源比平均**增加 0.094978**，95% bootstrap CI 为
**[0.069638, 0.123767]**，双侧 sign-flip `p=9.9999e-6`；32 个函数簇中
胜/负/平为 **0/29/3**。两个输入宽度的效应均为正（`n=4`：`+0.154025`；
`n=5`：`+0.035931`），故 `claim_supported=false`。

这不是执行失败造成的假阴性。四臂共 128 个 held-out arm-case 的 fallback 和
degraded 均为 **0**，语义验证均通过。负结果定位到学习—排序机制：QAOA replay
head 在 31/32 个函数上把进入精确调度器的 top-k 排成空选择，平均选择动作数仅
0.0625，因而与 random replay 得到完全相同的主端点均值 `Y=0.999172`；置换标签
对照只有 3/32 个空选择，`Y=0.904194`，greedy replay 无空选择，
`Y=0.775639`。训练损失下降不能替代下游机制验收；当前 replay 目标与 head 排序
接口尚未形成有效 Q4AI→AI4Q 信号。

## 可证伪设计与双向关系

- **Q4AI 干预**：`qaoa_final_measurement_replay` 只使用 `p=1` QAOA 的最终
  bitstring counts，不读取优化轨迹；每个训练函数的 observation budget 为 512，
  QAOA 为 2 restarts × 6 steps，且 64/64 次均为 `direct_unrepaired`。
- **AI4Q 端点**：从同一 formal-v4 foundation checkpoint 初始化四个隔离的
  output/input/candidate-equivariant shared head；每臂使用相同 64 个训练函数、
  256 updates、batch size 4 和训练日程。head 只排序 held-out 共同候选池的
  top-10；下游统一用预算 2 的 exact conflict-aware scheduler 和 arm-neutral
  raw utility，输出经全部 `x`、全部初始 `y` 及 ancilla 回零验证。
- **唯一主因果对比**：QAOA replay 对 QAOA permuted-label control。两臂复用同一
  QAOA counts、最终参数与运行证明，只改变 bitstring count 与动作标签的关联，
  因而检验“保留量子测量分布中的动作关联是否改善 AI 排序”。random 与 greedy
  replay 只作描述性参照；配置明确 `compute_budget_equal=false`，不能据此作等算力
  或量子优势比较。
- **隔离评估**：训练集为 64 个合成结构化 VectorANF（`n=6/7` 各 32、6 输出）；
  held-out 为 SHA-ranked 且全局 orbit 去重的未见双射（`n=4/5` 各 16）。端点为
  `Y=共享程序 total_abstract_score / direct total_abstract_score`，越低越好；
  两个宽度各权重 1/2，以 whole-vector Boolean function 为配对簇。

## 完整结果

| 对比（QAOA final replay − 参照） | 配对数 | 平均效应 | 95% bootstrap CI | sign-flip p | 胜/负/平 |
|---|---:|---:|---:|---:|---:|
| permuted-label control（主比较） | 32 | +0.094978 | [0.069638, 0.123767] | 0.000010 | 0 / 29 / 3 |
| random-bitstring replay（描述性） | 32 | 0.000000 | [0.000000, 0.000000] | 1.000000 | 0 / 0 / 32 |
| greedy repeated-selection replay（描述性） | 32 | +0.223532 | [0.202845, 0.244426] | 0.000010 | 0 / 32 / 0 |

主比较使用 10,000 次按宽度分层的确定性 cluster bootstrap 和 100,000 次确定性
双侧 sign-flip。主比较无 fallback pair；门控还要求均值、CI 上界和两个宽度效应
都低于 0，本次三项方向均相反。全部 32 个 direct baseline 及 128 个四臂输出均
通过穷举语义检查；`n=4` 每臂每函数检查 256 个 `(x,y)` 状态，`n=5` 检查
1,024 个状态。

## 机制诊断

| 训练来源 | held-out 平均 Y | 空选择函数 | 平均选择动作数 | fallback / degraded |
|---|---:|---:|---:|---:|
| QAOA final-measurement replay | 0.999172 | 31/32 | 0.0625 | 0 / 0 |
| QAOA permuted-label control | 0.904194 | 3/32 | 1.5000 | 0 / 0 |
| random-bitstring replay | 0.999172 | 31/32 | 0.0625 | 0 / 0 |
| greedy repeated-selection replay | 0.775639 | 0/32 | 1.9063 | 0 / 0 |

四臂都从同一 head tensor SHA
`5d020fff1c3b706e455be08e7e7e699063a464f0d81d88dedcd67d08ff7bcfc2`
开始，且各自训练损失均下降；但只有 greedy 和置换标签对照把下降转化为非空共享
动作。当前证据更符合“QAOA counts 到 action-target 的映射、target 支持度或排序
校准存在错配”，而不是“QAOA 没有运行”或“综合器 fallback”。这只是由观测作出的
机制诊断，不能反向把对照臂的较好结果解释为正向量子效应。

## 五文件证据与复验

- Run ID：`20260812-e6-q4ai-causal-v1-full-s20260912`
- Bundle：
  `experiments/results/xa202609/20260812-e6-q4ai-causal-v1-full-s20260912/`
- Runner source commit：
  `e850c0ce91aa0ae9897f4ce0f5268171dbb22532`（运行时 clean，`source_dirty=false`）
- Runner wall time：140.32 s；独立 full verifier wall time：145.03 s。
- 五文件 snapshot SHA-256：
  `18b758ac3e432a5d4e9f0ba1f8be7e17bd1b848b6212234eea9d2e842d4cc76a`
  （对按文件名排序的 `{name,sha256,bytes}` 紧凑 JSON 加换行后取 SHA-256）。

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `config.json` | 4,361 | `735c78cdc6a4d0c1ebd5c808bafba0471082ccd7b8e2f3b3f8d17653ebc2b5aa` |
| `results.json` | 26,364 | `a4ab20dbf8892355d6dc96c14817504da5117428fe97af1c75bcb04ee3313d1f` |
| `raw.jsonl` | 1,477,206 | `d0f64a9140b8e42a4eb242155b0ec58555eccbf2ebe666bc622507939efc69c3` |
| `heldout_evaluation.json` | 1,067,546 | `f0684623495424515dd17391bff56cbfcfcaba21efe19771cf74b01e771c909b` |
| `checksums.sha256` | 323 | `b52bf90bb97c829de5285c1e407172411d46537c5b4757d63e4e81d64a6d2f8f` |

从 `experiments/` 复验：

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python \
  scripts/verify_e6_replay_training_bundle_v1.py \
  results/xa202609/20260812-e6-q4ai-causal-v1-full-s20260912
```

独立 verifier 的 **11/11** checks 全部为 `true`，包括五文件/checksum、canonical
payload、配置与源码绑定、训练 corpus 重建、四臂训练公平性、held-out 语义/统计
重算，以及从 replay 到训练再到 scheduler 的确定性全链重放；在记录的 source
commit 上复验时，当前源码树哈希也与配置绑定一致。`errors=[]`、`ok=true`。

## 结论边界与下一步 D1

本 bundle 严格是 single-researcher deterministic **development causal
experiment**：`heldout_development_evaluation=true`，但 `formal_evaluation=false`、
`performance_evidence=false`、`hardware_execution=false`、
`quantum_advantage=false`。资源仅为 abstract logical X/CNOT/MCT proxy；它不支持
等算力优势、密码泛化、真机、真实校准、量子加速、量子优势或已验收性能主张。
四个训练后 head 只用于本次单进程开发实验，没有发布为模型 artifact。

下一步只做预先声明的 **D1 机制诊断**，不围绕本次 held-out 结果事后调参：冻结
本 bundle 和主假设，另建不进入性能主张的诊断 split，逐层记录 QAOA count 质量、
count→action target 的支持度/熵、正效用动作的 top-k recall、logit–target 排序相关、
以及训练前后 selected-action cardinality。D1 先定位信号是在 replay 构造、监督目标
还是 head 排序校准处坍缩；修正方案和下一次因果实验的配置必须在新 held-out 运行
前固定，不能用当前 32 个函数筛选实例或追逐正结果。
