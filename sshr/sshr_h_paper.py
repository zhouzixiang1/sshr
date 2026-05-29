"""
论文原版 SSHR-H（Algorithm 2 严格实现）。

与 sshr_h.py 的关键区别：
  - 候选集 S 每步从**当前 onset A** 重新枚举（而非全超立方体）
  - 因为 S 的所有顶点都在 A 内，ratio 必然 = 1.0，R=3/4 阈值无实际过滤效果
  - 不引入 off-set 顶点，A 只减不增（严格单调缩减）

对应论文 Algorithm 2 第 3 行：
  "set S ← parallelotopes associated with A"
"""
from __future__ import annotations
from typing import List, Set
from bool_func import BooleanFunction, QuantumCircuit
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block


def sshr_h_paper(
    bf: BooleanFunction,
    R: float = 3 / 4,
) -> QuantumCircuit:
    """
    论文原版 SSHR-H：候选集 S 每步从当前 A 枚举。

    Parameters
    ----------
    bf : BooleanFunction
    R  : 选择阈值（论文取 3/4；因 S 从 A 枚举，所有候选 ratio=1.0，阈值实际不起过滤作用）

    Returns
    -------
    QuantumCircuit  (n+1 qubits)
    """
    n = bf.n
    circuit = QuantumCircuit(n + 1)

    A: Set[int] = set(bf.onset)
    if not A:
        return circuit

    while A:
        # 每步从当前 A 重新枚举候选集（论文 Algorithm 2 原意）
        S: List[Parallelotope] = enumerate_parallelotopes(list(A), n)

        # 因所有顶点均在 A 内，ratio 恒为 1.0，故 R 阈值不起过滤作用
        candidates = [
            P for P in S
            if len(P.vertices() & A) / len(P.vertices()) >= R
        ]

        if not candidates:
            break

        # 取第一个（枚举按维度降序，即优先选最高维）
        chosen = candidates[0]
        circuit.add_block(synth_block(chosen, n))
        A ^= chosen.vertices()   # A 严格缩减（无 off-set 污染）

    # 剩余点以 dim-0 单点（n-MCT）处理
    for minterm in list(A):
        p0 = Parallelotope(minterm, [])
        circuit.add_block(synth_block(p0, n))

    return circuit
