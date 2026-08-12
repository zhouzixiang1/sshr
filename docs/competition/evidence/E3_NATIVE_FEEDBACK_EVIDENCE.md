# E3 原生执行反馈证据：冻结标定、同池干预与负向主结果

## 结论

E3 首次把逻辑 Oracle 经 `rz/sx/x/cx` 分解、局部耦合路由和实际门级
Pauli trajectory 得到的执行标签写回 MCTS 根节点调度效用。该闭环在机制上
成立，但预注册主假设未获支持：相对历史 QAOA-shot，执行反馈 QAOA-shot 的
held-out Oracle task NLL 平均变化为 **+0.001293**，函数簇 bootstrap 95% CI
为 **[-0.001170, 0.004719]**；几何成功率比为 **0.998708**，95% CI 为
**[0.995236, 1.001149]**。置信区间跨越零/一，因此不能声称执行反馈改善了
最终含噪表现。

这不是“反馈没有接入”的空结果。反馈在 QAOA 比较的 24 个配对搜索中改变了
6 次根分支集合（25%），其中 4 次进一步改变最终 Plan；在 greedy 比较中分别
改变 16/24 次分支集合和 10/24 次最终 Plan。结果表明，当前结构特征岭回归虽
能预测标定 NLL，却尚未把代理精度稳定转化为下游搜索收益。

## 可证伪问题与预注册判据

研究问题是：在 calibration/test Boolean 函数完全隔离的条件下，用原生映射
和实际门级含噪执行标签拟合的 profile-specific utility，能否在冻结 policy、
候选池、MCTS 预算和 QAOA 设置下，提高 held-out Oracle 的含噪任务成功率？

唯一主比较为 `feedback_qaoa_shot` 对 `historical_qaoa_shot`。先在每个函数内
聚合两个 search seed，再以函数为独立单位做 5,000 次配对 bootstrap。只有
NLL 差的 95% CI 上界小于 0、几何成功率比的 95% CI 下界大于 1，并且所有
语义、原生等价和证据 verifier 同时通过，才允许写“反馈改善”。本次未过该门。

## 冻结协议

- Calibration：12 个固定随机 `n=4` 函数，seed base 310000；56 个根动作的
  greedy rollout-completion 线路，无样本按资源或成功率删除。
- Test：12 个新的固定随机 `n=4` 函数，seed base 410000；与 calibration 的
  完整真值表 SHA-256 交集为空。
- 测试矩阵：12 函数 × 2 search seeds × 4 变体，共 96 条端到端 trial：
  历史/反馈 utility 与 greedy/QAOA-shot 的 2×2 组合。
- 原生执行：合成 heavy-hex-like 局部耦合图；原生门集
  `{rz,sx,x,cx}`；确定性最短路 SWAP；MCX 使用无辅助比特精确
  parity-phase 分解。
- 噪声：每个一比特门后独立 Pauli 错误率 0.0002，每个 CX 后独立双比特
  Pauli 错误率 0.003，逐物理位 readout flip 率 0.01。
- 每条线路穷举全部 `x` 和 `y∈{0,1}`，辅助位从 0 开始；每输入 16 shots、
  两个 noise seeds。Calibration 共执行 57,344 shots，test 共执行 98,304
  shots。
- 一次成功必须同时满足输入保持、输出为 `y xor f(x)`、辅助位回零，并按最终
  logical-to-physical layout 正确解码。

反馈模型只读取 calibration 标签。按函数留一交叉验证在
`alpha ∈ {0.01,0.1,1,10}` 中选择 `alpha=10`；完整 calibration 重拟合后立即
冻结，test 仅通过带 SHA 校验的 `from_metadata` 加载，不重新拟合。模型使用
置换不变的 StateKey/FactorAction 结构特征，标定内 MAE 为 0.04571、
`R²=0.8995`、Spearman 为 0.8472；这些是标定拟合指标，不是 held-out
因果效果。

## 主结果与机制结果

| 指标 | 结果 |
|---|---:|
| Test trial | 96 |
| QAOA attempted / direct / fallback | 每个 QAOA 变体 18 / 18 / 0 |
| QAOA not invoked | 每个 QAOA 变体 6 |
| Plan / Circuit / Oracle 验证 | 96 / 96 / 96 |
| 原生全基态等价 | 96 / 96 |
| NLL 差（反馈 − 历史） | +0.001293 |
| NLL 差 95% CI | [-0.001170, 0.004719] |
| 几何成功率比 | 0.998708 |
| 成功率比 95% CI | [0.995236, 1.001149] |
| 函数级 W/L/T | 1 / 3 / 8 |
| 主张门 | 未通过 |

反馈 penalty 在所有 40 条实际调用的反馈行中均非零；归一化 penalty span 的
均值为 0.06625。QAOA 路径中，6 次根选择变化只有 4 次改变最终 Plan、3 次
改变原生双比特门数，说明两层稀释同时存在：不同根动作可能收敛到同一 Plan，
而不同 Plan 也未必产生足以越过 shot 噪声的执行差异。

## 证据定位与哈希

- Calibration bundle：
  `experiments/results/xa202609/20260811-e3-cal-native-feedback-v1-s310000/`
- Test bundle：
  `experiments/results/xa202609/20260811-e3-test-native-feedback-v1-s410000/`
- 冻结反馈模型 SHA-256：
  `b9b0df42a0c6fd5d04bafaa29dd5a90a76182fc2d568d08381e0cd322ea6d187`
- Calibration summary SHA-256：
  `9945a2f38b5e0d126229cdf85b64a68ae0a746709df4737031888c4989c921a4`
- Test summary SHA-256：
  `328e12e2b0d306a41131dd004e4489ef3ad871c70b1b4a71c87fb3a1abcfb558`
- Native/noise profile SHA-256：
  `57b9a6517b122057226cb0ef011bae3c72c5eba9a543c012bbf7dfa12e27bcdf`

两个 bundle 均为独立九件套；`verify_hardware_feedback_bundle.py` 已重算
checksum/白名单、NLL、矩阵完整性、同池/同 rollout、公平性和 calibration
引用，均返回 `ok=true`。一次因 QAOA 事件分类错误而失败的旧 test bundle 已
原样移入本地 `misc/archive/experiments/failed-runs/`，未修改后冒充证据。

## 科学边界与下一步

本证据只支持“合成 profile 上的 simulator-calibrated root scheduling feedback
已经实现并接受了失败检验”。它不支持真机、真实校准、量子加速、QAOA 普遍
优于经典方法，也不构成 policy/value replay 更新。`n=4` 结果不能外推到 AES
或完整密码攻击。

下一步不应通过调 test penalty weight 或筛选函数来追逐正结果。应保持同一
隔离协议，预注册 E3-v2：用编译前可获得的原生 1q/2q/depth/SWAP/duration
特征替代当前纯结构代理；在 calibration 内联合选择正则与反馈尺度；提高 shots
并扩展到 `n=5`/结构化函数，检验“代理—动作—Plan—含噪端点”的哪一层造成
错配。只有新 held-out CI 过门，才能升级为正向双向闭环结论。
