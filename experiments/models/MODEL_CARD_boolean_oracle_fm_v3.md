# `boolean_oracle_fm_v3.pt` 模型卡

## 1. 状态

- **阶段**：开发候选（development candidate）
- **是否为 XA-202609 最终冻结模型**：否
- **推荐开发入口**：`synthesize("foundation_nmcts", ...)`
- **当前支持的逻辑门域**：`gate_mode="mct"`
- **记录日期**：2026-07-28

该 checkpoint 用于验证“置换等变共享主干 + 动作策略头 + 状态价值头”能否接入现有 Resource-NMCTS。它尚不能作为比赛最终模型交付：当前文件没有随附训练命令、随机种子、训练样本清单、数据切分、逐轮日志或独立评测 manifest。

## 2. 文件身份

| 字段 | 实测值 |
|---|---|
| 文件 | `models/boolean_oracle_fm_v3.pt` |
| SHA-256 | `87904409966e6d9d18aae3711dff54d696608e6eefcf0e5cb5bb98ae96d4f57d` |
| 大小 | 254,587 bytes |
| checkpoint 顶层字段 | `hidden`, `in_channels`, `layers`, `mlp_hidden`, `state_dict` |
| 参数量 | 60,450 |
| CPU 加载验证 | Python 3.11.15、PyTorch 2.12.0，`load=ok` |

以上值由当前工作树直接读取，不依赖文档中的人工转录。

## 3. 模型用途

模型接收 Boolean 函数 ANF 项集对应的 MCTS 搜索状态，并共享一次结构编码，用于两个任务：

1. **动作策略**：对候选因式分解动作排序，分数越高表示越应优先探索。
2. **状态价值**：预测
   `log(achievable_score / direct_score)`，经模型结构与部署端保护限制在不大于 0 的范围，用来近似替代部分经典 greedy rollout。

模型只负责逻辑层搜索控制；它不执行 QAOA、原生门分解、芯片映射、路由或噪声仿真。

## 4. 输入与输出

### 4.1 状态输入

ANF 项集编码为 `T × n × 12` 张量：

- 1 个单项式—变量成员关系通道；
- 8 个上下文通道：递归深度、活跃/剩余辅助比特容量，以及 T、CNOT、depth、gate、ancilla 权重；
- 3 个绝对规模通道：`log1p(T)`、ANF 密度、变量数。

行表示单项式集合，列表示输入变量。主干对单项式重排和变量重命名保持相应的等变/不变结构。

### 4.2 动作输入与输出

动作头额外读取：

- 动作覆盖的单项式子集；
- 被提取因子的变量子集；
- 全局状态表示；
- 4 个动作标量：相对即时收益、相对覆盖率、覆盖组绝对规模、状态绝对规模。

输出为每个候选动作的无归一化排序分数。

### 4.3 价值输出

价值头输出单个非正标量，表示可达资源分数相对于直接综合分数的对数比。部署端将其保护在 `[-3, 0]`，再乘以当前状态的 `direct_score` 得到估计值。

## 5. 架构

| 组件 | 配置 |
|---|---|
| 输入通道 | 12 |
| 等变主干宽度 | 32 |
| 残差等变块数 | 2 |
| 动作/价值 MLP 隐层宽度 | 128 |
| 总参数量 | 60,450 |

主干采用 `S_T × S_n` exchangeable 层：逐元素、行均值、列均值和全局均值四条线性路径相加，并配合 LayerNorm、GELU 和残差连接。动作头和价值头共享该主干。

## 6. 已知训练域与溯源缺口

当前源代码可确认：

- 训练程序为 `scripts/train_expert_iteration.py`，采用搜索访问计数监督策略头、可达/直接分数对数比监督价值头，并用 holdout accept/reject 决定是否保存；
- 训练程序固定构造 `gate_mode="mct"` 的逻辑层搜索配置；
- 训练程序中的资源权重为 `T=1.0`、`CNOT=0.04`、`depth=0.015`、`gates=0.01`、`ancilla=2.0`；
- 项目开发记录称 v3 的训练变量规模覆盖 `n=4..10`。

但现有 checkpoint **不能证明**它究竟使用了哪条命令。下列信息均未被写入 checkpoint，也没有找到配套训练 manifest：

- `--iterations`、`--functions`、`--holdout`、`--simulations`；
- `--epochs`、`--batch-size`、学习率和策略损失权重；
- 训练随机种子和每个 split 的函数/状态 ID；
- 每轮 accept/reject、损失与耗时日志；
- 训练代码 commit SHA；
- 是否存在中途人工续训或参数覆盖。

因此，训练脚本中的默认值不能反推为该文件的真实训练参数。最终模型必须重新训练或补齐可验证 provenance，并冻结 checkpoint、数据清单、配置和源码 SHA。

## 7. 当前验证

2026-07-28 在主开发环境执行：

- 完整现有测试：`36 passed`；
- 旧版冒烟测试：`smoke ok`；
- CPU checkpoint 加载：`load=ok`，参数量与 checkpoint 结构一致；
- 已有测试覆盖输入变换等变性、结构化 adapter、价值估计保护、`foundation_nmcts` 分发以及逻辑 OpenQASM 交换。

这些结果证明当前开发树能加载并调用模型，不等于完成比赛级效果复现。

## 8. 预备效果记录（不可作为最终申报结论）

`CLAUDE.md` 记录了以下 2026-07-28 开发期结果：

| n | 相对基线运行时间比 | 相对基线 score |
|---:|---:|---:|
| 8 | 2.70× | −2.49% |
| 9 | 4.33× | −1.58% |
| 10 | 4.26× | +2.69% |
| 11（分布外） | 5.28× | +0.37% |

其中运行时间比大于 1 表示更快，score 越低越好。上述数字目前没有同行的原始 CSV、样本数、种子、逐实例结果和 manifest，不能进入最终技术报告的主结论。尤其是 `n=11` 的分布外结果不能据此宣称稳定泛化。

## 9. 适用范围

当前可用于：

- 开发期 `foundation_nmcts` 逻辑 MCT 综合；
- 策略/value 接口、等变性与性能工程测试；
- 生成后续 C0–C7 因果实验的候选起点；
- CPU 推理原型。

当前不得用于支持以下表述：

- “通用量子基础模型”或跨任意 Boolean/密码任务的普适模型；
- `logical_and` 或其他未训练门代价域；
- 对任意硬件权重均已验证的硬件感知模型；
- QAOA 调度、量子加速或量子优势；
- 原生门、耦合图、路由、噪声或真实硬件效果；
- 完整 AES/SM4/PRESENT/ASCON 实现效果；
- 超出已记录训练域的可靠泛化。

## 10. 已知风险与限制

1. checkpoint provenance 不完整，无法从空目录复现该文件。
2. 资源权重虽然进入输入，但现有证据只支持固定 paper profile，不能据此推出跨权重泛化。
3. 开发期评测样本与种子没有固化，现有性能数字证据等级较低。
4. 价值估计是搜索启发式，不是可采纳最优下界；部署端仅用 direct-plan 范围保护限制明显失真。
5. 当前端到端路径停留在逻辑 MCT 层；逻辑 QASM 导出不是原生门映射。
6. 模型大小较小且训练域有限，“foundation”是架构方向名，不是模型规模或通用能力结论。

## 11. 最终冻结前必须补齐

- 机器可读训练配置、命令、环境、随机种子和源码 commit；
- 训练/验证/测试函数 ID 与哈希清单，证明 split 无泄漏；
- 每轮自博弈与训练日志、accept/reject 决策；
- C0–C7 独立种子评测的 raw/summary/manifest；
- 多随机种子均值、方差/置信区间和失败样本；
- 资源权重、变量规模、密码函数和分布外切片；
- checkpoint SHA、模型卡 JSON、CPU clean-load 与端到端复现实验；
- 明确选择最终 checkpoint，并将其他开发 checkpoint 排除出交付包。

## 12. 验证命令

在 `experiments/` 下执行：

```bash
shasum -a 256 models/boolean_oracle_fm_v3.pt
stat -f 'bytes=%z' models/boolean_oracle_fm_v3.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python -c 'from src.foundation.adapter import FoundationScorer; s=FoundationScorer.from_checkpoint("models/boolean_oracle_fm_v3.pt"); print(sum(p.numel() for p in s.model.parameters()), s.device)'
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests -q
/opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py
```
