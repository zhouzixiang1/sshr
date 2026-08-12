# Clean-install 复演证据

## 结论

XA-202609 当前树已在一个新建的 CPython 3.11 虚拟环境中完成依赖安装、软件自检、
竞赛 demo 复演和全套测试。该证据证明仓库相对路径下的离线软件合同可复演；它不
验证 Gurobi 许可证、Qiskit 可选栈、真实校准、量子硬件、量子加速或量子优势。

## 隔离环境

- 平台：Darwin 25.5.0 arm64；
- Python：3.11.15；
- 安装入口：`experiments/environment/requirements/dev.txt`；
- 核心精确版本：NumPy 2.4.6、SciPy 1.17.1、PuLP 3.3.1、PyTorch 2.12.0；
- `pip check`：`No broken requirements found.`；
- `core.txt` SHA-256：`427c7fa3ef35b1c20f87392f574fe885d25f7338750fda02116e5a48e16c0207`；
- `dev.txt` SHA-256：`54f9989bfaf208b0bbea9bac78472e0e21982d74c84a8f3c6d45ec044dce2c47`。

临时环境在复演后移入 macOS 废纸篓，可恢复但不属于提交资产。复演命令和验收器
均不依赖本机绝对路径；用户应按安装文档自行创建新的 `.venv`。

## 验收内容

默认验收器 `experiments/scripts/verify_clean_install.py` 返回 `ok=true`，并实际检查：

1. Python 主版本及四个核心包的精确版本；
2. SciPy MILP 求解和 PuLP 模型 API；
3. foundation checkpoint 的 60,450 个参数及 SHA-256
   `87904409966e6d9d18aae3711dff54d696608e6eefcf0e5cb5bb98ae96d4f57d`；
4. direct NumPy statevector QAOA mini-case，无 repair；
5. synthetic native mapping 与实际 zero-noise Pauli trajectory mini-case；
6. legacy smoke；
7. 临时目录中的完整 AES 竞赛 demo 和独立 verifier。

Demo 报告保持 `hardware_execution=false`、`performance_evidence=false`，并记录 direct
non-fallback QAOA。加入 E4-v2 execution-aware utility 核心测试后，同一隔离环境的
全套结果为 `217 passed in 62.50s`；legacy smoke 为 `smoke ok`。

## 复演命令

从 `experiments/` 执行：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r environment/requirements/dev.txt
.venv/bin/python -m pip check
.venv/bin/python scripts/verify_clean_install.py
.venv/bin/python -m pytest -q tests
```

`--quick` 只用于秒级诊断，不构成 clean-install 验收。SSHR-I/Gurobi 与 Qiskit 均为
独立可选分组，不得因为核心环境通过而标记为已安装或已验证。
