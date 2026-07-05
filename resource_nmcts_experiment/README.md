# Resource-Constrained Neural MCTS Oracle Synthesis

This directory implements a new logic-level line of work for:

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

The method does not use SSHR parallelotope candidates.  It treats Boolean
oracle synthesis as a symbolic factorization search over ANF/XAG-style
compute/uncompute plans, then verifies the generated oracle circuits by
classical simulation.

Initial commands:

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python tests_smoke.py
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset smoke
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset smoke
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset pilot
```

Current presets:

- `smoke`: fast correctness/regression run.
- `pilot`: medium structured-oracle run with ANF, factor-MCTS, FPRM-MCTS,
  neural-MCTS, and SSHR-H references.
- `main`: large-scale placeholder; still needs staged tuning before it should
  be treated as paper-grade evidence.

Outputs are written to `results/`.  The neural prior is saved at
`models/action_scorer.pt`.
