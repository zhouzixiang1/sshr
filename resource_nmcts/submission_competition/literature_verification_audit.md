# 文献核对与证据职责审计

- 工作流：citation-verification + multi-source-search gap check
- 实际引用：23；BibTeX 条目：23
- 状态：verified=23，suspicious=0，mismatch=0，not_found=0，manual_needed=0
- 缺失 citation key：无；未使用 BibTeX：无
- 核对源：Crossref DOI 元数据；10.48550/arXiv 使用 arXiv Atom fallback。验证状态不依赖抓取式数据库。

| key | 状态 | 年份 | 题名相似度 | 证据职责 | 禁止外推 | 来源 |
|---|---:|---:|---:|---|---|---|
| cowtan2019routing | verified | 2019/2019 | 1 | Formal qubit-routing problem framing | Routing theory is not oracle-synthesis quality evidence | [source](https://arxiv.org/abs/1902.08091) |
| fazel2007esop | verified | 2007/2007 | 1 | ESOP-to-Toffoli cascade baseline | Does not establish fault-tolerant T cost after decomposition | [source](https://doi.org/10.1109/PACRIM.2007.4313212) |
| fuerrutter2024diffusion | verified | 2024/2024 | 1 | Diffusion-based circuit generation/editing | Not a bit-flip Boolean-oracle baseline | [source](https://doi.org/10.1038/s42256-024-00831-9) |
| gupta2006pprm | verified | 2006/2006 | 1 | PPRM/Reed--Muller factoring | Does not establish mapped native-gate superiority | [source](https://doi.org/10.1109/TCAD.2006.871622) |
| hartnett2024learningtorank | verified | 2024/2024 | 1 | Hardware-data circuit ranking | Present learned scorer is not trained on hardware data | [source](https://doi.org/10.22331/q-2024-11-27-1542) |
| henderson2023minimal | verified | 2023/2023 | 1 | Oracle qubit/domain-preservation trade-off | Different embedding contract; no direct optimality transfer | [source](https://doi.org/10.1117/12.2663240) |
| li2019sabre | verified | 2019/2019 | 1 | SABRE layout/routing method | Does not provide hardware calibration evidence by itself | [source](https://doi.org/10.1145/3297858.3304023) |
| li2025hopps | verified | 2025/2025 | 1 | Hardware-aware CNOT+Rz phase-polynomial synthesis | No Rz backend here; preprint is boundary evidence only | [source](https://arxiv.org/abs/2511.18770) |
| meuli2019multiplicative | verified | 2019/2019 | 1 | Multiplicative-complexity/T-count oracle bound | Uses a different logic-network and ancilla contract | [source](https://doi.org/10.1109/ICCAD45719.2019.8942093) |
| meuli2020ros | verified | 2020/2020 | 1 | Resource-constrained LUT oracle synthesis | Not reproduced here as the official ROS SAT implementation | [source](https://doi.org/10.4204/EPTCS.318.8) |
| meuli2022xag | verified | 2022/2022 | 1 | XAG qubit/T-count/T-depth trade-off | Not a same-implementation mapping baseline in primary20 | [source](https://doi.org/10.1038/s41534-021-00514-y) |
| murali2019noiseadaptive | verified | 2019/2019 | 1 | Calibration-aware mapping | Present study uses uncalibrated synthetic targets | [source](https://doi.org/10.1145/3297858.3304075) |
| nannicini2022ilp | verified | 2023/2023 | 1 | Optimal assignment/routing counterpoint | Not run in primary20 and no optimality claim is transferred | [source](https://doi.org/10.1145/3544563) |
| rietsch2024rlsynthesis | verified | 2024/2024 | 1 | RL Clifford+T unitary synthesis | Different action space and objective | [source](https://doi.org/10.1109/QCE60285.2024.00102) |
| riu2025rlzx | verified | 2025/2025 | 1 | RL-guided ZX rewrite selection | Different representation and equivalence mechanism | [source](https://doi.org/10.22331/q-2025-05-28-1758) |
| ruiz2025alphatensor | verified | 2025/2025 | 1 | AlphaTensor T-count optimization | Starts from existing CNOT+T circuits; different causal target | [source](https://doi.org/10.1038/s42256-025-01001-1) |
| tsaras2024shortcircuit | verified | 2024/2024 | 1 | AlphaZero-driven classical circuit design | Classical circuit task, not mapped quantum-oracle evidence | [source](https://arxiv.org/abs/2408.09858) |
| wang2023nestedmcts | verified | 2023/2023 | 1 | MCTS for automated circuit design | Different parameterized-circuit task | [source](https://doi.org/10.1109/TQE.2023.3265709) |
| weiden2023qseed | verified | 2023/2023 | 1 | Learning-seeded unitary synthesis | Does not prove learned-prior gain in Boolean-oracle search | [source](https://doi.org/10.1109/QCE57702.2023.00093) |
| wille2009bdd | verified | 2009/2009 | 1 | BDD scalability route | Does not imply low mapped depth on the present target | [source](https://doi.org/10.1145/1629911.1629984) |
| yu2025backend | verified | 2025/2025 | 1 | Back-end-aware fault-tolerant oracle synthesis | Different backend cost model; no direct win claim | [source](https://doi.org/10.1145/3658617.3697776) |
| zen2025rlft | verified | 2025/2025 | 1 | Hardware-constrained RL circuit discovery | Fault-tolerant state preparation, not a Boolean-oracle baseline | [source](https://doi.org/10.1103/gqpr-dgz7) |
| zheng2025sshr | verified | 2025/2025 | 1 | Closest small-Boolean CNOT-oriented baseline | Only locally reimplemented SSHR-H/Beam variants are compared | [source](https://doi.org/10.1109/ICCAD66269.2025.11240690) |

## 定向补缺建议

- [Henderson et al., Automated Quantum Oracle Synthesis with a Minimal Number of Qubits (2023)](https://arxiv.org/abs/2304.03829)：direct oracle/qubit-domain-preservation trade-off; useful scope context；处理：added_to_review。
- [Li et al., HOPPS: Hardware-Aware Optimal Phase Polynomial Synthesis (2025 preprint)](https://arxiv.org/abs/2511.18770)：current hardware-aware CNOT+Rz phase-polynomial boundary；处理：added_as_boundary_only。
- [Zen et al., Quantum Circuit Discovery for Fault-Tolerant Logical State Preparation with Reinforcement Learning (2025)](https://arxiv.org/abs/2402.17761)：hardware-constrained RL circuit discovery, but different fault-tolerant state-preparation task；处理：added_as_boundary_only。

## 解释边界

现有综述已覆盖同任务 Boolean/Oracle 综合、学习/搜索和硬件映射三层。不同任务论文只用于定位方法空间，不得作为 primary20 的数值基线；未经同输入、同辅助位、同超时和同映射配置重跑的论文结果不得进入胜负统计。
