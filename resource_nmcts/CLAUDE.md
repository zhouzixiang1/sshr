# CLAUDE.md — Resource-NMCTS

Resource-Constrained Neural MCTS for Boolean Oracle synthesis.
See the parent `CLAUDE.md` for the full project guide.

## Quick Commands

```bash
# Working directory: resource_nmcts/

# Import check
/opt/anaconda3/envs/mcts-qoracle/bin/python -c "from src.synthesizers import synthesize; print('OK')"

# Smoke test
/opt/anaconda3/envs/mcts-qoracle/bin/python tests/tests_smoke.py

# Run experiments
./scripts/run_experiments.py --preset smoke
```

## Package Paths

All imports use `from src.xxx import ...` from the project root.
SSHR vendored deps at `src/sshr_lib/`.
