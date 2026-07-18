#!/usr/bin/env python3
"""Single synthesis worker - outputs JSON to stdout."""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.synthesizers import synthesize
from src.bool_func import BooleanFunction
from src.factor_plan import SearchConfig

name, n, tt_hex, method, model_path = sys.argv[1:6]
bf = BooleanFunction(int(n), int(tt_hex, 16))
config = SearchConfig()
t0 = time.time()
r = synthesize(method, bf, config, seed=42, model_path=model_path)
elapsed = time.time() - t0
result = {
    'name': name, 'n': int(n), 'method': method, 'model_path': model_path,
    'score': r.cost.score(config.weights), 'T': r.cost.T, 'CNOT': r.cost.CNOT,
    'depth': r.cost.depth, 'peak_ancilla': r.cost.peak_ancilla,
    'correct': r.correct, 'time_s': round(elapsed, 2),
}
print(json.dumps(result))
