# XA-202609 双向智能编译演示

## AI for Quantum

- AES S-box output bit 0 由置换等变 learned policy 实际参与根候选排序；
  learned value 明确关闭。
- Plan ANF、Circuit ANF、完整 Oracle 与 `256 × 2` 可逆语义验证：
  `全部通过`。
- 逻辑资源分数：`1839.845000`；逻辑 QASM SHA-256：
  `0e02e3b67f95473525add5dc49b622b03678c7e94b6464d0f76fbfaab761ed04`。

## Quantum for AI

- 直接 QAOA、无 repair/fallback：
  `是`。
- 冻结候选池 `K=6`、预算 `B=3`；
  greedy 选择 `[1, 2, 4]`，QAOA 选择
  `[0, 3, 4]`。
- 本次 tiny smoke 的 QAOA objective / exact objective：
  `0.724487 / 0.783856`；regret：
  `0.059369`。

## 原生映射与含噪执行

- profile：`synthetic-heavy-hex-like-10q-v1`；原生门集：
  `rz, sx, x, cx`。
- 原生总门：`29136`；双比特门：
  `26044`；coupling 检查：
  `通过`。
- classical / QAOA noisy success：`0/1`
  与 `0/1`。

## 结论边界

本缩小演示只证明执行与验证契约，不把 tiny 数字作为性能证据。原生/含噪路径
使用 synthetic heavy-hex-like profile 与 seeded simulation，不是真机校准；
不主张量子加速或量子优势。
