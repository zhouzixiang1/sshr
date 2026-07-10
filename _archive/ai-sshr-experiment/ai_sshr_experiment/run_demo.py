"""Small demo for the AI-SSHR experimental prototype."""
from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

from ai_guided_beam import ai_guided_beam
from feature_extractor import build_candidates, ensure_sshr_on_path
from pruned_candidates import select_pruned_candidates, write_candidate_csv
from rankers import RuleRanker

ensure_sshr_on_path()

from bool_func import BooleanFunction, mct_cost, mct_cost_rp  # noqa: E402
from sshr_h import sshr_h  # noqa: E402
from sshr_beam import sshr_beam  # noqa: E402


def circuit_cost(circuit, objective: str = "cnot") -> dict:
    cost_fn = mct_cost_rp if objective == "t" else mct_cost
    t_count = 0
    cnot = 0
    ancilla = 0
    for gate in circuit.gates:
        if gate.type == "CNOT":
            cnot += 1
        elif gate.type == "MCT":
            c = cost_fn(len(gate.controls))
            t_count += c["T"]
            cnot += c["CNOT"]
            ancilla += c["ancilla"]
    return {"T": t_count, "CNOT": cnot, "ancilla": ancilla}


def verify(circuit, bf: BooleanFunction) -> bool:
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        if circuit.simulate(bits)[n] != bf.evaluate(x):
            return False
    return True


def make_random_bf(n: int, seed: int) -> BooleanFunction:
    rng = random.Random(seed)
    N = 1 << n
    k = rng.randint(1, max(1, N // 2))
    onset = rng.sample(range(N), k)
    tt = sum(1 << v for v in onset)
    return BooleanFunction(n, tt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-SSHR prototype demo")
    parser.add_argument("--n", type=int, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hex", dest="hex_id", help="truth table hex id")
    group.add_argument("--tt", type=int, help="truth table integer id")
    group.add_argument("--random", action="store_true", help="generate a random function")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--objective", choices=["cnot", "t"], default="cnot")
    parser.add_argument("--width", type=int, default=50)
    parser.add_argument("--branch", type=int, default=10)
    parser.add_argument("--keep-ratio", type=float, default=0.1)
    parser.add_argument("--keep-min", type=int, default=100)
    parser.add_argument("--export-pruned", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.hex_id:
        bf = BooleanFunction.from_hex(args.n, args.hex_id)
    elif args.tt is not None:
        bf = BooleanFunction(args.n, args.tt)
    else:
        bf = make_random_bf(args.n, args.seed)

    print(f"n={bf.n} tt=0x{bf.truth_table:X} onset={len(bf.onset)}")
    candidates = build_candidates(bf.n)
    print(f"candidates={len(candidates)}")

    rows = []

    t0 = time.time()
    circ_h = sshr_h(bf)
    rows.append(("sshr_h", circuit_cost(circ_h, args.objective), time.time() - t0, verify(circ_h, bf)))

    t0 = time.time()
    circ_beam = sshr_beam(bf, objective=args.objective, width=args.width, branch=args.branch)
    rows.append(("beam", circuit_cost(circ_beam, args.objective), time.time() - t0, verify(circ_beam, bf)))

    t0 = time.time()
    result = ai_guided_beam(
        bf,
        objective=args.objective,
        width=args.width,
        branch=args.branch,
        ranker=RuleRanker(),
    )
    rows.append(("ai_guided_beam_rule", circuit_cost(result.circuit, args.objective), time.time() - t0, verify(result.circuit, bf)))

    pruned = select_pruned_candidates(
        bf,
        keep_ratio=args.keep_ratio,
        keep_min=args.keep_min,
        objective=args.objective,
        ranker=RuleRanker(),
    )
    if args.export_pruned:
        write_candidate_csv(args.export_pruned, pruned)
        print(f"wrote pruned candidates: {args.export_pruned}")
    print(f"pruned_candidates={len(pruned)} keep_ratio_actual={len(pruned)/len(candidates):.4f}")

    print("\nmethod,T,CNOT,ancilla,time_s,correct")
    for name, cost, elapsed, ok in rows:
        print(
            f"{name},{cost['T']},{cost['CNOT']},{cost['ancilla']},"
            f"{elapsed:.4f},{int(ok)}"
        )
    print(
        f"ai_path_len={len(result.path)} expanded={result.expanded} "
        f"completed={int(result.completed)}"
    )


if __name__ == "__main__":
    main()

