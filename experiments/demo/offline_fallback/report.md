# XA-202609 离线确定性兜底（非 QAOA 成绩）

本资产只用于在 learned model 或 QAOA 路径不可用时维持可验证演示。它采用
`direct_anf`，不加载 learned policy/value，不调用 scheduler 或 QAOA。

- `fallback_only=true`
- `learned_policy_invoked=false`
- `qaoa_invoked=false`
- `performance_evidence=false`
- `hardware_execution=false`

## 逻辑语义

- AES S-box output bit 0，ANF 项数 `132`，逻辑门数
  `132`。
- Plan ANF、Circuit ANF、完整 256 输入 Oracle 与 `256 × 2` 可逆语义检查：
  `全部通过`。
- 逻辑 QASM SHA-256：`bf66f5313499d37644537e4cabef5ba6fe728c18108f2fb20bdc3b5749a60a18`。

## Synthetic native/noise 小例

- profile：`synthetic-heavy-hex-like-9q-v1`；原生总门 `140302`，双比特门
  `133394`，coupling 检查
  `通过`。
- 固定输入 `0x53`、seed `940000`、
  `0/1` sampled success。

## 边界

该 sampled endpoint 仅验证离线软件链可执行。它不是 AI for Quantum 或
Quantum for AI 成绩，不是真机或真实校准证据，也不支持性能、加速或量子优势主张。
