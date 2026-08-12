# 三路线硬件兼容边界

本目录把同一 `logical-x-cnot-mct` IR 分成三条证据强度不同的路线。三条路线都明确
`hardware_execution=false`，不能由“兼容”推导出真机、器件校准、量子加速或量子优势。

## 1. 超导路线：synthetic executable/noisy

`superconducting.py` 将逻辑 IR 精确分解到 `{rz,sx,x,cx}`，并在声明的 synthetic
coupling graph 上做确定性最短路路由；`noise.py` 对明确的独立 Pauli-depolarizing 与
readout-bitflip 参数执行逐 shot statevector trajectory。这是实际运行的模拟器证据，
但不是 vendor device、pulse model 或真实 calibration。

## 2. 离子阱路线：ideal resource adapter

`ion_trap.py` 面向 fully connected `{rz,rx,rxx}`。角度约定固定为

\[
R_{XX}(\theta)=\exp\!\left(-i\,\theta X\otimes X/2\right).
\]

实现先复用现有 ancilla-free exact parity-phase MCT 分解，再执行：

- `x -> rx(pi)`（差一个全局相位）；
- `sx -> rx(pi/2)`（差一个全局相位）；
- 每个 CNOT 用 `rxx(pi/2)` 和局部 `rz/rx` 精确实现。

按时间顺序，CNOT 的中间表达为

```text
H(control)
RXX(control,target; pi/2)
H(control), H(target)
Rz(control; -pi/2), Rz(target; -pi/2)
H(target)
```

其中每个 `H` 再按 `Rz(pi/2), Rx(pi/2), Rz(pi/2)` 展开。该序列与 CNOT 的全酉矩阵
只差一个全局相位；测试并非只检查计算基 truth table。连接模型为全连接，因此不插入
SWAP，最终 native gate 中也不允许残留 `cx`。

当前证据覆盖 X、CNOT、Toffoli 和 3-control MCT。它只给出 ideal gate/resource
reference；没有脉冲时长、加热、串扰、离子链重排或真实器件噪声结论。

## 3. 光量子路线：boundary only

`photonic.py` 只声明接口前提并 fail closed，不把门模型线路伪装成光量子映射。进入可执行
适配前必须确定：

- 编码（如 dual-rail、single-rail 或 time-bin，当前均未选择）；
- resource-state 家族及生成/验证契约；
- 测量基、探测器和自适应 feed-forward 时序；
- 光源效率、传输损耗、干涉可见度、探测效率和暗计数；
- heralding 成功事件与 postselection 政策。

在这些输入缺失时，`compile_photonic(...)` 必须抛出
`PhotonicUnsupportedError`；当前不输出 native gates、成功概率或虚构的含噪结果。

## 统一 bundle

从 `experiments/` 执行：

```bash
python scripts/build_hardware_routes_bundle.py \
  --output-dir results/xa202609/20260812-hardware-routes-v1-s202609 \
  --run-id 20260812-hardware-routes-v1-s202609 \
  --seed 202609

python scripts/verify_hardware_routes_bundle.py \
  results/xa202609/20260812-hardware-routes-v1-s202609
```

builder 输出 canonical JSON、route artifact SHA、artifact manifest 和外层 checksum，并
通过子进程调用独立 verifier 的 semantic-only 模式。独立 verifier 不导入 builder；它会
重新编译超导/离子阱路线、重跑 seeded noisy trajectory，并用自带矩阵实现重算离子阱
全基态及全酉矩阵。测试还覆盖“修改 RXX 角度后重签所有结构哈希”的攻击，此时结构哈希
仍正确，但语义重算必须失败。

