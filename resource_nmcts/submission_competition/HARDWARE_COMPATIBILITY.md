# 硬件兼容性、限制与处置说明

本说明由 `scripts/capture_competition_environment.py` 的实测清单约束。正文和答辩
不得把下述合成拓扑、无噪声仿真或代理指标包装成真机实验。

## 当前机器与软件栈

- GPU：NVIDIA GeForce RTX 5090 Laptop GPU，24,463 MiB，compute capability 12.0。
- 驱动：610.62；PyTorch 2.9.1+cu128；CUDA runtime 12.8；cuDNN 9.1.0.2。
- CPU：24 个逻辑处理器；Windows 10.0.26200；Python 3.11.15。
- Qiskit 2.5.0；Qiskit Aer 0.17.2；DuckDB 1.5.4。
- GPU float32 `2048×2048` 矩阵乘冒烟测试通过。
- 当前 Aer `available_devices` 只有 `CPU`，没有可用 GPU simulator backend。

完整机器可读证据见 `environment_manifest.json` 和 `environment_packages.txt`。

## 已解决的兼容性问题

1. **Blackwell/compute 12.0 支持**：固定使用带 CUDA 12.8 的 PyTorch 2.9.1；旧 CUDA
   或旧 PyTorch wheel 不能作为复现实验的等价环境。
2. **逻辑线路与 Qiskit 隔离**：引擎继续输出 X/CNOT/MCT；公共 artifact API 保留
   真实门序，再由唯一映射层转换，避免图件、仿真和指标各自重建线路。
3. **真实拓扑约束**：新映射层使用 Qiskit `Target`、显式 coupling、布局与路由，
   并逐指令检查门集、耦合边和方向；旧 basis-only 数据明确降级为 legacy pilot。
4. **映射后语义**：按 initial/final layout 对全部 `x`、`y∈{0,1}` 验证输出、数据
   保持、辅助位归零、泄漏和输入相关相位。
5. **Windows 多进程**：runner 使用 spawn-safe 主入口和持久 worker；OpenMP 冲突
   环境需设置 `KMP_DUPLICATE_LIB_OK=TRUE`，并在 provenance 中记录。
6. **MCX clean-ancilla 语义修复**：早期直接设置
   `qubits_initially_zero=True` 会使 Qiskit HLS 把任意数据线误当作干净辅助位，造成
   映射后真值表错误。现实现只把显式新增的 `AncillaRegister` 交给 clean-ancilla
   分解，并在后续 pass manager 中固定 `qubits_initially_zero=False`；`maj5` 等回归
   用全部任意输入态验证通过。这说明“门集合法”不等于“Oracle 语义正确”。
7. **内存失控隔离**：JSONL v3 runner 每 250 ms 采样当前 worker 进程树 RSS 和系统
   内存，默认 70% 软上限；超限只终止当前 worker 树并记录 `resource_guard`，不会
   终止其他 Python 任务。worker 默认每 8 个 stage 回收，避免长期进程累积。

## 仍然存在的硬件不足

### 1. Aer 未使用 RTX 5090

当前 Aer 只提供 CPU 设备，状态向量和密度矩阵仿真不会因 5090 自动加速。GPU 只
用于神经网络训练和足够大的批评分；小批搜索推理默认 CPU，需用实测而非设备名称
判断更快的一侧。

处置：论文分别记录 `training_device`、`inference_device`、`simulator_device`；禁止
笼统写“全部实验由 GPU 加速”。若后续安装 GPU Aer，必须生成新 environment hash
和独立实验批次，不能与 CPU 批次混合。

### 2. 当前目标不是校准真机

`cx_full_19`、`cx_line_19_bidir`、`cz_grid_4x5` 和
`ecr_heavy_hex_d3_bidir` 是代码支持的无校准 synthetic proxy；当前资源安全正式
切片实际使用 `cx_full_12`，另有少量 `cx_line_12_bidir` pilot。它们能验证门集、
拓扑和路由兼容性，但没有门时长、读出误差、串扰、漂移或校准时间戳。未进入冻结
数据库分析的 grid/heavy-hex 只能称“实现支持”，不能称“已完成正式实验”。

处置：只报告原生门数、深度、2Q 深度、routing delta 和精确无噪声等价；不称
“真实保真度”“真实设备成功率”。后续真机/校准模拟必须保存 provider、backend、
Target、properties、calibration timestamp 和 noise-model SHA256。

### 3. 精确仿真指数扩展

状态向量成本随物理比特指数增长。正式协议对 `n≤8` 执行全部
`2^(n+1)` 个 `(x,y)` 状态；超过边界时当前实现明确拒绝，不会把抽样冒充 exact。

处置：若扩展到更大输入，分开报告 symbolic proof、抽样 basis states 和适用的
结构化验证；`verification_mode`、样本数和置信边界必须入库。

### 4. 高控制门的辅助位需求

MCX 高层综合可能需要 clean ancilla；稀疏目标的物理宽度不足会导致编译失败或采用
更昂贵的无辅助分解。辅助位预算也会改变不同方法的公平性。

处置：冻结 `hls_ancilla_budget`，报告 logical/work/physical width 与辅助位清零验证；
目标容量不足记录为 `target_capacity` 失败，不能静默更换目标。

### 5. 转译结果依赖版本与随机种子

Qiskit pass manager、HLS 插件和 SABRE 会随版本及 seed 改变门数和布局。

处置：固定 Qiskit 2.5.0、transpiler seeds、Target/config hash；保存 mapped QASM/门
JSON。跨版本只比较不变量与版本化快照，不使用未注明版本的门数 golden value。

### 6. 代理噪声不能代替器件噪声

均匀 depolarizing/readout 模型可做鲁棒性敏感性分析，但不能代表具体芯片，尤其
不能覆盖相关噪声、泄漏和串扰。

处置：如增加代理噪声，仅作为 secondary analysis，并对概率、参数范围和随机 seed
做敏感性曲线；主要正确性仍由无噪声精确验证承担。

### 7. 并行配置是资源合同的一部分

本机 24 个处理器、约 63.4 GB 内存。正式恢复批次使用有界配置：验证 batch size 16、
Aer `max_parallel_threads=16`、`max_parallel_experiments=16`、系统内存护栏 70%。在
AES Direct 单例上，有界实验并行把精确验证从 187.3 s 降至 103.4 s（1.81 倍），
而系统内存保持在约 27%；该数字只是运行器工程加速，不是量子线路质量提升。

处置：每行结果保存综合、映射和总峰值 RSS/系统内存，以及逐阶段峰值。任何调整
batch、线程、并行实验数或护栏阈值都会改变 compile/config hash，必须建立新批次；
不能仅凭一次瞬时任务管理器读数宣称完整资源上界。

## 竞赛交付措辞边界

允许：

> 在已进入冻结结果的 `cx_full_12`（以及单独标注的 line pilot）上完成门集、布局、
> 路由和映射后功能/相位验证；代码另支持 grid/heavy-hex 合成拓扑。

不允许：

> 已在 RTX 5090 上完成量子线路 GPU 仿真；已在 IBM/中科院真机上验证；显著提高
> 真实芯片保真度。

除非后续有对应设备日志、校准快照、噪声协议和统计证据，上述不允许表述不得进入
PDF、摘要、图题或答辩材料。
