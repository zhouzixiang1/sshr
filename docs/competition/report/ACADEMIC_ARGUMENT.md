# XA-202609 学术论证契约

## 一句话论点

在严格保持密码 Boolean Oracle 语义的约束下，本项目检验三种可证伪的优化：
置换等变归纳偏置是否减少等价表示的重复学习，固定预算的 utility-diversity
调度是否减少相似分支对搜索预算的浪费，以及独立验证的原生映射与执行标定是否
缩小逻辑资源代理和目标硬件执行风险之间的偏差。

## 研究问题

| 编号 | 研究假设 | 最小充分证据 | 失败后的主张降级 |
|---|---|---|---|
| G0 | 所有进入比较的线路严格保持 Oracle 语义 | GF(2)、真值表和原生层独立等价正确率 100% | 整组性能比较作废 |
| H1 | 等变归纳偏置提高一致性、样本效率或 OOD 泛化 | 等变误差、匹配参数非等变基线、学习曲线和轨道隔离测试 | 只声称实现了等变接口 |
| H2 | policy、value、progressive widening 有可分离贡献 | C0–C7、固定预算、多 seed、配对统计 | 只保留通过证据的组件 |
| H3 | QAOA 能在冻结候选池上求解固定预算多样性调度 | QUBO 穷举审计、exact regret、direct non-fallback ideal/shot/noisy | 保留负结果，不声称量子优势 |
| H4 | 执行标定能改善 held-out 原生/含噪指标 | calibration/test 隔离、rerank/resynthesis 两阶段消融 | 只报告代理失配，不称反馈有效 |
| H5 | 上述作用能迁移到密码函数 | AES、SM4、PRESENT、ASCON 分族逐坐标结果 | 限定到通过的函数族 |

当前判定为：H2 中的 policy-only 信号成立但 learned value 未通过组件门；H3 在
随机 held-out 与 AES 冻结池上均支持“QAOA 改善局部组合选择”，但不支持稳定
端到端资源优势；H4 的反馈机制成立而 held-out 改善假设未通过；H5 目前只完成
AES forward S-box 的 8 个标量坐标，且只证明双向执行链贯通与目标错配，不能
外推到完整 SubBytes、其他密码族或密码攻击线路。

## 论证结构

正文必须遵循：

```text
问题与硬约束
→ 三类资源错配
→ 对应的数学机制
→ 可证伪假设
→ 公平实验与独立验证
→ 支持到哪一层
→ 失败模式与适用边界
```

不按“实现了 AI、实现了 QAOA、实现了硬件模块”的工程目录平铺。QAOA 是 H3
中的受审计求解器，不预设优于 greedy/exact；verifier、manifest 和 checksum 是
科学可信度基础，不包装成算法创新。

## 术语锁定

| 规范术语 | 使用边界 |
|---|---|
| 密码 Boolean Oracle | 以坐标 Boolean 函数为输入的 bit-flip Oracle；不等同完整密码攻击 |
| 置换等变 policy/value | 对单项式行置换不变、对变量重标号保持相应等变；不称通用基础模型 |
| Neural MCTS | 学习模型只引导搜索，确定性 verifier 决定语义正确性 |
| 量子辅助多样性调度 | 固定预算下选择彼此独立的 MCTS 子节点；不称同时动作 MWIS |
| 逻辑资源代理 | X/CNOT/MCT 层的 T、CNOT、depth、ancilla 等；不称硬件实测成本 |
| 原生映射与含噪仿真 | 给定 profile 和 simulator 的结果；无真机数据时不写真机效果 |
| 执行标定反馈 | calibration/test 隔离的 rerank 或 resynthesis；无 held-out 改善时不称闭环有效 |

## 写作门

- 每个 Results 小节以“为检验 Hx”开头，以“证据支持到哪一层、不能推出什么”结束。
- 每个定量主张必须绑定 run_id、raw、聚合规则、source/model/dataset SHA 和 verifier。
- 随机、结构化和密码函数分表；逻辑、原生和含噪指标分层。
- 负结果、超时、repair、fallback 和 not-invoked 不隐藏。
- 未过验收门的模块只能写入 Methods/Planned evaluation，不得出现在摘要结论中。
