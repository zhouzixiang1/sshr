# Frozen configs

只保存通过验证门的竞赛实验与演示配置。每个配置必须包含 schema/version、资源
权重、数据 split、seed、预算、checkpoint SHA 和适用 track；调参草稿留在实验
run 目录，不在此处滚动覆盖。

已冻结配置：

- `e2_qaoa_scheduler_v1.json`：QAOA 固定预算多样性调度主矩阵；对应 run
  `20260810-e2-qaoa-scheduler-v1-s120000` 已通过 24 项 verifier checks。
- `e4_v2_execution_aware_v1.json`：E4-v2 权威两阶段合同。先用预声明的非 AES
  n=8 函数及 compile-time native features 按单一预注册规则冻结非负惩罚权重，
  再在 E4 已观察过的八个 FIPS 197 坐标上做四臂 post-E4 frozen replication；
  `historically_seen_in_E4=true`、`generalization_claim=false`，noisy success 仅为诊断。
  `--tiny` 只用于契约与 artifact 冒烟，不构成性能证据。早期含 noisy/risk
  调参入口的冲突草稿已可恢复地归档到
  `misc/archive/experiments/xa202609-development/config-drafts/`，不得用于正式结论。
- `e6_q4ai_causal_v1.json`：单研究者确定性 E6 四臂 development 实验。固定同一
  初始化与 `n=6/7` 训练语料，依次训练 random、greedy、QAOA final-measurement
  replay、permuted-label control，并在 SHA-ranked `n=4/5` whole-vector 数据上评估。
  `full` 已由 clean source `e850c0c` 执行；结果明确为负，不得调参后覆盖原 run，
  也不得写成 formal/performance/generalization/hardware/quantum-advantage evidence。

唯一权威 E4-v2 配置是上述 `e4_v2_execution_aware_v1.json` 及同名 protocol lock。
旧 `e4_execution_aware_v2` noisy-primary 草案不是生产配置；其精确 payload 只在
`tests/fixtures/e4_execution_aware_v2.superseded-test-only.json` 中用于旧 runner
回归测试，不能用于正式运行、held-out 或 generalization 表述。
