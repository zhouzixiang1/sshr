# XA-202609 三路线硬件兼容证据

## 证据对象

- run id：`20260812-hardware-routes-v1-s202609`
- bundle：
  `experiments/results/xa202609/20260812-hardware-routes-v1-s202609/`
- unified manifest SHA-256：
  `6c3b3758fdee68424c88d1bad0cf3814584001901ebeab86398cc34128bc2438`
- outer checksums 文件 SHA-256：
  `288e050365845a2020f2906f1ce48fd439c82b2804d0a3aa3c66e5278f7b0809`
- bundle 大小：7 个文件，121,663 bytes

全部 JSON 为 canonical、路径无关且确定性生成。manifest 对三条 route artifact 的内容
SHA 和字节数逐一绑定；artifact manifest 与外层 `checksums.sha256` 再绑定 verifier record
和全部载荷。

## 路线结论与证据等级

| 路线 | 状态 | evidence strength | 当前能证明什么 | 明确不能证明什么 |
|---|---|---|---|---|
| 超导 | `synthetic_executable_noisy` | synthetic full-basis + seeded noisy trajectory | `{rz,sx,x,cx}` 精确分解、synthetic topology、实际逐 shot Pauli trajectory | vendor device、真实 calibration、pulse/noise 完备性、真机性能 |
| 离子阱 | `ideal_resource_adapter` | ideal full-basis + unitary reference | fully connected `{rz,rx,rxx}`、无 SWAP/CX、逻辑酉等价 | 脉冲、时长、加热、串扰、真实离子阱噪声或执行 |
| 光量子 | `boundary_only` | interface boundary only | 编码/资源态/测量前馈/损耗/后选择的必需接口与 fail-closed 边界 | 任何门映射、成功率、loss-aware 执行或真机结果 |

三条路线均为 `hardware_execution=false`，均不构成量子加速或量子优势证据。

## 离子阱精确性

角度约定为

\[
R_{XX}(\theta)=\exp\!\left(-i\,\theta X\otimes X/2\right).
\]

独立测试使用与 adapter simulator 分离的矩阵实现，锁定 CNOT→RXX 的完整酉矩阵；随后对
四类小线路枚举所有输入基态，并比较完整 unitary up to one global phase：

| case | qubits / basis states | native gates | 1q / RXX | depth | max basis failure | max unitary error |
|---|---:|---:|---:|---:|---:|---:|
| X | 1 / 2 | 1 | 1 / 0 | 1 | 0 | `6.12e-17` |
| CNOT | 2 / 4 | 15 | 14 / 1 | 11 | `4.44e-16` | `3.51e-16` |
| Toffoli | 3 / 8 | 163 | 153 / 10 | 91 | `4.88e-15` | `2.78e-15` |
| 3-control MCT | 4 / 16 | 531 | 497 / 34 | 270 | `1.20e-14` | `1.10e-14` |

全部误差低于 `1e-9` 验收阈值；`inserted_swap_count=0`，最终 gate name 仅为
`rz/rx/rxx`。

## 超导小型执行证据

正式 bundle 的 3-qubit X+CNOT+Toffoli smoke 经 full-basis ideal verification：25 个
native gates（14 个单比特、11 个双比特），无插入 SWAP。seed `202609` 下实际执行
16-shot synthetic Pauli trajectory，理想输出 `011`，counts 为 `011:15, 111:1`；
`actual_noisy_simulation=true`、`noise_applied=true`、`hardware_execution=false`。

## 独立验证与篡改测试

执行：

```bash
cd experiments
python scripts/verify_hardware_routes_bundle.py \
  results/xa202609/20260812-hardware-routes-v1-s202609
```

正式 bundle 的独立 verifier 共 27 项检查全部通过，`errors=[]`、`ok=true`。检查包括：

- route set、claim boundary、artifact SHA/size、artifact manifest 和外层 checksums；
- 超导重新编译、全基态等价与 seeded noisy trajectory 精确重放；
- 离子阱 deterministic recompile、无 CX/SWAP、全基态及全酉矩阵重算；
- 光量子 boundary exact、non-executable、无伪造 native mapping；
- 本机路径隐私和三路线 `hardware_execution=false`。

`test_hardware_routes_bundle.py` 还会修改 CNOT 中的 `RXX(pi/2)` 角度，并重签 route
manifest、bundled verifier subject、artifact manifest 和外层 checksums。此时所有结构哈希
仍能通过，但独立 verifier 的 `ion_deterministic_recompile` 与
`ion_unitary_up_to_global_phase` 必须失败，证明验收不是只信任 checksum。

## 本轮测试

```text
60 passed in 1.59s
```

覆盖：既有 QASM/超导/含噪回归，离子阱 X/CNOT/Toffoli/3-control MCT、独立 CNOT
unitary、QASM gate-set/no-SWAP、光量子 fail-closed boundary、bundle byte determinism、
独立 verifier 和重签后语义篡改。
