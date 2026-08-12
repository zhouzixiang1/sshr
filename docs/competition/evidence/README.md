# Verified evidence

只接收从 `experiments/results/xa202609/<run_id>/` 经 verifier 生成的小型证据：
summary、manifest、checksums、claim map 和必要的 figure source data。

不复制大型 raw、训练缓存、绝对路径日志或旧论文结果。每个报告数字必须指向一个
run_id 和可验证聚合规则。

## 当前受审计证据

| 证据 | 科学问题 | 当前结论 |
|---|---|---|
| `E2_QAOA_SCHEDULER_EVIDENCE.md` | QAOA 是否改善固定池的组合选择 | 局部 exact-hit/regret 改善；端到端资源 CI 跨 1 |
| `E3_NATIVE_FEEDBACK_EVIDENCE.md` | 执行标定是否改善 held-out 含噪端点 | 反馈机制生效，但主改善假设未通过 |
| `E4_AES_BIDIRECTIONAL_EVIDENCE.md` | 双向机制能否贯通 AES 坐标 Oracle | QAOA 8/8 命中冻结池最优，但逻辑、原生和含噪目标不一致 |
| `HARDWARE_ROUTES_EVIDENCE.md` | 超导、离子阱、光量子三路线的兼容证据边界是什么 | run `20260812-hardware-routes-v1-s202609` 的 27/27 项独立检查通过；超导为 synthetic executable/noisy，离子阱为 ideal unitary adapter，光量子仅 boundary-only，均非真机 |
| `CLEAN_INSTALL_EVIDENCE.md` | 当前树能否在全新环境复演 | 精确依赖、完整 demo 与 217 项测试通过；不含可选 SDK 或真机 |

五份证据共同约束主张：局部调度、逻辑综合、原生映射与含噪执行必须分层报告，
任何上游改善都不能自动外推为量子优势或硬件执行优势。
