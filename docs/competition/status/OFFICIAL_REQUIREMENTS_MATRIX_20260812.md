# XA-202609 官方要求实时对照

本表以 `docs/competition/official/XA-202609-competition-brief.pdf` 第 9--12 页为
唯一赛题依据，并以当前工作树中的代码、实验 bundle、主稿和提交工具为证据。状态分为
“已证明”“部分证明”和“未完成”；设计文档或计划本身不算完成证据。

| 官方要求或评选维度 | 当前兑现与证据 | 状态 | 冻结前缺口 |
|---|---|---|---|
| 紧扣“量子+AI 双向赋能” | AI for Quantum 由置换等变 policy 与 Neural MCTS 优化 Oracle 综合；Quantum for AI 由 QAOA 在冻结候选池中分配搜索预算；E3/E4 追踪调度到原生执行端点 | 已证明到合成仿真机制层 | E4-v2 仍需证明执行感知反馈是否在 AES 留出集产生信息量和改善 |
| 场景锚定 | FIPS 197 AES S-box 八个坐标已贯通候选选择、逻辑 Oracle、原生映射和含噪轨迹；完整 256 输入与双目标初值语义通过 | 已证明 | 不等同完整 SubBytes、AES 轮或密码攻击；不得扩大表述 |
| 兼容主流及新兴硬件路线 | 正式 run `20260812-hardware-routes-v1-s202609` 统一超导 synthetic executable/noisy、离子阱 fully-connected `{rz,rx,rxx}` ideal adapter 与光量子 boundary-only；独立 verifier 27/27 通过 | 已证明到分级兼容证据 | 三路线均 `hardware_execution=false`；无真机/真实校准，离子阱仅 ideal，光量子仅能力边界 |
| 清晰说明量子路线与 AI 框架及选型依据 | 中文主稿已区分等变 policy/value、MCTS、QAOA 与三路线证据强度，并用统一逻辑契约解释选型 | 已证明 | 最终 PPT 和 Overleaf 主稿需随当前本地主稿及 E4-v2 同步 |
| 严谨推导和仿真数据 | QUBO 恒等式、严格 Oracle 语义检查、冻结 calibration/test、`RXX(theta)=exp(-i theta X⊗X/2)` 约定、全酉矩阵重算、SHA 绑定、语义篡改试验与 seeded noisy trajectories 均已有 bundle | 已证明 | 最终冻结 commit 后统一重跑并记录完整环境和日志 |
| 客观分析瓶颈、避免夸大量子 AI 效能 | 当前文本明确排除真机、量子加速、量子优势和跨硬件性能泛化；E3 负结果、E4 稀疏端点与三路线不对称证据均保留 | 已证明 | E4-v2 无论正负均按预注册门报告，不在留出集追逐结论 |
| 技术创新性 | 等变 policy、固定预算 QAOA 多样性调度、执行反馈效用和密码 Oracle 传播链形成统一研究问题 | 部分证明 | learned value 未通过；执行反馈改善尚未通过，创新主张必须按组件证据分层 |
| 方案可行性 | 精确依赖、clean-install verifier、主 demo、独立离线 fallback、白名单提交 builder/verifier 已存在 | 部分证明 | 最终 commit 的 fresh install、完整 SBOM、Git 冻结和可分发授权未完成 |
| 落地与价值 | 密码安全场景明确，已提供 AES 坐标级资源与执行诊断 | 部分证明 | 价值表述应聚焦编译审计与资源评估，不能把当前结果写成攻击能力或商业收益 |
| 验证严谨性 | E1--E4、E4-v2 tiny bundle 与硬件路线 bundle 已通过各自 verifier；后者 27/27 项并包含重签后语义篡改拒绝测试；主 demo 与 fallback 均可独立复核 | 已证明到当前快照 | E4-v2 正式 bundle、最终全量测试、干净解压包复验待完成 |
| 提交内容：设计说明、源码、返回结果、总结报告、创新点、使用与安装说明 | 中文 PDF、源码、evidence、demo、环境定义和提交工具已有白名单骨架 | 部分证明 | 最终 staging 需补齐 demo 自证文件、E4-v2 正式快照和顺序化复现说明 |
| 审核通过的报名表和规范压缩包名称 | 技术工具默认拒绝在缺授权时生成可分发 final 包 | 未完成 | 需由有权人提供报名审核材料、学校/提交人信息、许可/IP/来源声明及授权，不得由程序代签 |

## 当前最短技术路径

1. 用非 AES calibration 冻结非饱和执行端点和效用权重，再运行 AES 留出四臂实验；
2. 将已通过的三路线分级证据随中文主稿编译结果同步 Overleaf，并在 PPT 中保留同一证据强度表；
3. 把 E4-v2 通过门的结果写入唯一中文主稿和 PPT，并再次同步 Overleaf；
4. 冻结 Git，重跑 clean install、全套测试、两套 demo 和最终 staging verifier；
5. 外部授权材料齐备后才生成 `distributable=true` 的最终压缩包。
