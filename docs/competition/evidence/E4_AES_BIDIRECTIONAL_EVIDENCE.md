# E4 AES 双向编译证据：局部组合最优与执行目标错配

## 结论

E4 将 FIPS 197 前向 S-box 的 8 个标量 Boolean 坐标贯通到同池
置换等变 policy、固定预算分支调度、可验证逻辑 Oracle、合成
heavy-hex-like 原生门映射和逐 shot Pauli trajectory。QAOA-shot 在 8/8 个
冻结候选池上命中精确组合目标，而 classical greedy 仅命中 3/8；QAOA 使
5/8 个根分支集合发生变化，并使 4/8 个最终逻辑 QASM 发生变化。因此，
Quantum for AI 在本案例中并非名义模块，而是实际改变了 AI 搜索预算及其下游
线路。

这种局部优势没有一致转化为执行端优势。相对 classical greedy，QAOA 的平均
逻辑资源分数高 0.448%，平均原生总门数低 2.827%，平均原生双比特门数低
3.229%；原生资源的坐标级胜/负/平为 2/2/4。含噪端点仅观察到 5/4096 次成功，
其中 classical 为 2/2048、QAOA 为 3/2048。事件过稀且只有 8 个坐标，不能据此
声称 QAOA 改善含噪执行。本实验支持的最强结论是：QAOA 改善了冻结候选池中的
组合调度目标，但当前 utility、逻辑资源代理与真实执行代价仍未对齐。

## 可证伪问题

研究问题是：在完整 AES S-box 坐标、同一 learned-policy 候选池和固定搜索预算
下，shot-based QAOA 能否比经典 diversity greedy 更准确地求解根分支组合问题，
并将该局部选择改善传递到逻辑资源、原生资源和含噪 Oracle 端点？

该问题按三层分别判定，而不把上游成功自动外推到下游：

1. **调度层**：比较每个冻结池中返回子集与精确枚举最优子集；
2. **综合层**：比较最终逻辑 QASM、逻辑资源分数、原生总门与原生双比特门；
3. **执行层**：在声明的合成 topology/noise profile 上运行实际 seeded
   statevector trajectories，报告任务成功事件，不用门数公式替代执行。

## 冻结协议

- 数据：NIST FIPS 197-upd1 前向 S-box 的 8 个输出坐标，LSB 编号；每个坐标
  重新核验全部 256 个输入、固定锚点和真值表 SHA-256。
- 语义：每条 Plan、Circuit 和 Oracle 均通过验证；可逆 Oracle 对全部
  `256 × 2` 个输入/目标初值组合穷举验证。
- AI 条件：8 个根状态均实际调用 `boolean_oracle_fm_v3` 的置换等变 policy；
  learned value 明确关闭。
- 调度公平性：classical greedy 与 QAOA-shot 共用同一冻结候选池、效用、冗余
  矩阵、`K=6`、`B=3` 和 8 次独立根 action-edge simulation。
- QAOA：`p=1`，512 shots，4 次 optimizer restart，每次 12 steps；8/8 次调用
  均为 direct success，0 repair、0 fallback。
- 原生执行：`{rz,sx,x,cx}`，确定性最短路 SWAP，synthetic
  heavy-hex-like 10-qubit profile。
- 噪声：一比特门错误率 0.0002、双比特门错误率 0.003、readout flip 率
  0.01。每条 trial 使用输入 `0x00/0x53/0x7c/0xff`、两个 noise seed anchor
  `101/103` 和每端点 32 shots，即每 trial 256 shots、全矩阵 4096 shots。
- 范围：AES 尺度没有逐 trial 穷举原生 statevector 等价；原生等价范围明确标为
  `not-run-at-aes-scale`，含噪端点是多锚点 sampled diagnostic。

## 主要结果

| 指标 | Classical greedy | QAOA-shot | 配对解释 |
|---|---:|---:|---|
| 冻结池 exact objective 命中 | 3/8 | 8/8 | QAOA 局部组合目标占优 |
| QAOA attempted / direct / fallback | 0 / 0 / 0 | 8 / 8 / 0 | 无经典 fallback 冒充 QAOA |
| 相对另一调度器的根集合变化 | — | 5/8 | bits 0,2,3,4,7 |
| 最终逻辑 QASM 变化 | — | 4/8 | bits 0,2,4,7 |
| 平均逻辑资源分数 | 1799.036875 | 1807.096875 | QAOA 高 0.448%，W/L/T=1/3/4 |
| 平均原生总门数 | 26637.375 | 25884.250 | QAOA 低 2.827%，W/L/T=2/2/4 |
| 平均原生双比特门数 | 23587.875 | 22826.250 | QAOA 低 3.229%，W/L/T=2/2/4 |
| 含噪成功 | 2/2048 | 3/2048 | 事件过稀，不作改善主张 |

bit 3 提供了一个关键机制反例：QAOA 与 greedy 选择了不同根分支集合，但最终
逻辑 QASM 相同；bit 0 则由不同选择产生不同 QASM，并显著减少原生双比特门，
但其余坐标并不一致复制该方向。这说明“分支集合 → Plan/QASM → 原生线路 →
含噪端点”之间存在至少三次信息压缩，任何单层目标的最优都不能替代端到端检验。

## 验证与证据身份

- Run ID：`20260812-e4-aes-bidirectional-pilot-v1-s520000`
- Bundle：
  `experiments/results/xa202609/20260812-e4-aes-bidirectional-pilot-v1-s520000/`
- Trial：8 坐标 × 2 scheduler = 16；noisy endpoint 128；shots 4096。
- 独立 verifier：17/17 checks 为 `true`，覆盖冻结 AES 哈希、同池公平性、预算与
  edge 记账、逻辑语义重算、原生门/耦合、含噪执行契约、artifact 白名单和
  checksum。
- Dataset SHA-256：
  `5861a36ad5c40d91b096a9165825aa816d278ec6df1f0ac3a8ccc397468083c0`
- Raw SHA-256：
  `b2fb3ee7dc7493fd4b76fe5fe07649a55912c0ec3337bcccda638494ab7ae79a`
- Summary SHA-256：
  `1ecc0d5f3e6d5cb3ecbb44e89c4604862b3c8a507cec9d9474901808cc5ac145`
- Artifact manifest SHA-256：
  `d07ff2f35730d38ff6002b54469777291c69ea545c66ee72c7feabf4bc6d1e46`
- 正式运行 wall time：780.887 s；当前完整测试为 217 passed，legacy smoke 为
  `smoke ok`。

## 学术边界与下一步

E4 只覆盖 AES forward S-box 的 8 个标量坐标，不是多输出联合 SubBytes、完整
AES 轮函数或密码攻击线路。原生/噪声来自声明的 synthetic heavy-hex-like
profile；没有真机、真实设备校准、脉冲、退相干、泄漏、串扰、量子加速或量子
优势证据。5 个成功事件不足以比较两个 scheduler 的含噪性能。

下一步应预注册 execution-aware E4-v2，而不是围绕当前 5 个事件调参：在
calibration 内，用编译前可获得的预计原生双比特门、SWAP、depth 和执行风险
共同定义 QAOA utility，再在隔离的 AES/结构化坐标上检验其是否同时改善冻结池
目标、原生资源和 held-out 含噪端点。只有下游配对区间通过，才能把“Quantum
for AI 改善局部组合调度”升级为“改善可执行密码 Oracle 编译”。
