# Offline demo

单命令演示从 AES S-box Boolean 坐标进入置换等变 policy、固定预算 QAOA 调度、
逻辑语义验证、synthetic heavy-hex-like 原生映射和实际 seeded noisy trajectory：

```bash
cd /path/to/tzb
python \
  experiments/scripts/demo_competition.py \
  --case aes_sbox_bit0 \
  --synthesizer foundation_nmcts \
  --scheduler qaoa_diversity \
  --hardware superconducting_noise \
  --output experiments/demo/output

python \
  experiments/scripts/verify_demo_output.py experiments/demo/output
```

默认 demo 会执行缩小后的 8 坐标 × 2 scheduler contract smoke，并以 bit 0
作为可见 worked case。输出包含输入契约、人读报告、机器报告、执行日志、九件套
证据 bundle、外层 manifest/checksum 和独立 verification。它必须记录 direct
QAOA、repair、fallback 和 hardware flag；tiny 数字不是性能证据，不能替代正式
E2/E3/E4 bundle。

`experiments/demo/output/` 是生成目录，重新运行时请使用空目录。正式答辩性能数字
来自 `experiments/results/xa202609/`，而不是 demo smoke。

## 独立 deterministic fallback

`offline_fallback/` 是完全独立的可用性兜底，不加载 learned policy/value，也不
调用 QAOA。它使用 `direct_anf` 生成 AES S-box bit 0 逻辑 Oracle，完成完整逻辑
语义验证、synthetic profile 原生映射和一个固定 seed noisy trajectory 小例：

```bash
python experiments/scripts/demo_offline_fallback.py \
  --case aes_sbox_bit0 \
  --synthesizer direct_anf \
  --scheduler none \
  --hardware synthetic_superconducting_noise \
  --output experiments/demo/offline_fallback

python experiments/scripts/verify_offline_fallback.py \
  experiments/demo/offline_fallback
```

该资产必须保持 `fallback_only=true`、`qaoa_invoked=false`、
`performance_evidence=false` 和 `hardware_execution=false`。它不能作为
Quantum for AI、AI for Quantum、性能提升或量子优势证据。
