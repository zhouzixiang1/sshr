# RL-MCTS Block Synthesis Experiment

This folder contains an experiment that turns the RL+MCTS idea in
`../../new-idea.pdf` into a tractable SSHR-style block search.

The document idea uses states, actions, policy priors, value estimates, and
MCTS. Directly searching gate sequences with full unitary matrices is too large
for the Boolean-function scales already studied in this repository, so this
experiment uses:

- state: remaining active on-set bitmask `A`;
- action: choose one `Parallelotope` block;
- transition: monotone update `A <- A - vertices(P)`;
- policy: a cost-aware prior over valid blocks;
- value: a greedy cost-to-go estimator;
- search: PUCT-style MCTS over block actions.

Run:

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/rl_mcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset smoke
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset main
```

Outputs are written to `results/`.

Generate the paper tables and compile the Chinese manuscript:

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/rl_mcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python make_report_assets.py
cd paper
mkdir -p build
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
```

The compiled manuscript is `paper/build/main.pdf`.
