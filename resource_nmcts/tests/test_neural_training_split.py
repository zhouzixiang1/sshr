#!/usr/bin/env python3
"""Leakage and provenance tests for neural-prior training."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.train_neural_policy import (  # noqa: E402
    SPLIT_NAMES,
    build_arg_parser,
    build_dataset_bundle,
    load_excluded_function_hashes,
    run_training,
    split_dataset_by_function,
    train_only_normalization,
    truth_table_sha256,
)
from src.factor_plan import SearchConfig  # noqa: E402
from src.neural_policy import NeuralScorer, file_sha256  # noqa: E402


BENCHMARK_MANIFEST = PROJECT_ROOT / "submission_competition" / "benchmark_suite_v1.json"


def small_bundle(*, label_mode: str = "immediate", exclude_hashes: set[str] | None = None):
    return build_dataset_bundle(
        "smoke",
        42,
        SearchConfig(candidate_top_k=8),
        label_mode,
        0,
        1,
        "factor",
        4,
        80,
        "direct",
        2,
        exclude_hashes or set(),
    )


class NeuralTrainingSplitTests(unittest.TestCase):
    def test_legacy_model_payload_still_loads_on_cpu(self) -> None:
        scorer = NeuralScorer(PROJECT_ROOT / "models" / "action_scorer.pt")
        self.assertEqual(scorer.device.type, "cpu")
        self.assertEqual(scorer.metadata, {})
        self.assertIsInstance(scorer.score_one([0.0] * scorer.model.feature_dim), float)

    def test_final_benchmark_manifest_all_hashes_are_supported(self) -> None:
        payload = json.loads(BENCHMARK_MANIFEST.read_text(encoding="utf-8"))
        expected = {case["function_key"] for case in payload["cases"]}
        loaded = load_excluded_function_hashes([BENCHMARK_MANIFEST])
        self.assertEqual(payload["case_count"], 30)
        self.assertEqual(len(expected), 30)
        self.assertEqual(loaded, expected)
        for case in payload["cases"]:
            self.assertEqual(
                truth_table_sha256(case["n_inputs"], case["truth_table_hex"]),
                case["function_key"],
            )

    def test_same_function_and_pairwise_state_group_never_cross_split(self) -> None:
        bundle = small_bundle(label_mode="root_teacher")
        split = split_dataset_by_function(bundle, split_seed=991, train_frac=0.60, valid_frac=0.20)
        split_sets = {name: set(split.hashes(name)) for name in SPLIT_NAMES}
        self.assertFalse(split_sets["train"] & split_sets["valid"])
        self.assertFalse(split_sets["train"] & split_sets["test"])
        self.assertFalse(split_sets["valid"] & split_sets["test"])

        assigned_rows: set[int] = set()
        hash_to_split: dict[str, str] = {}
        for name in SPLIT_NAMES:
            for function_hash in split.hashes(name):
                self.assertNotIn(function_hash, hash_to_split)
                hash_to_split[function_hash] = name
            indices = set(int(index) for index in split.indices(name).tolist())
            self.assertFalse(assigned_rows & indices)
            assigned_rows |= indices
            self.assertTrue(
                all(bundle.row_function_hashes[index] in split_sets[name] for index in indices)
            )
        self.assertEqual(assigned_rows, set(range(len(bundle.row_function_hashes))))

        group_owners: dict[int, set[str]] = {}
        for group, function_hash in zip(bundle.state_groups.tolist(), bundle.row_function_hashes):
            if group >= 0:
                group_owners.setdefault(int(group), set()).add(function_hash)
        self.assertTrue(group_owners, "root_teacher should retain pairwise state groups")
        self.assertTrue(all(len(owners) == 1 for owners in group_owners.values()))
        self.assertTrue(
            all(len({hash_to_split[owner] for owner in owners}) == 1 for owners in group_owners.values())
        )

    def test_competition_exclusion_hashes_are_effective(self) -> None:
        excluded = load_excluded_function_hashes([BENCHMARK_MANIFEST])
        bundle = small_bundle(exclude_hashes=excluded)
        retained = {record.function_hash for record in bundle.functions}
        retained |= {record.function_hash for record in bundle.zero_row_functions}
        matched = {str(record["function_hash"]) for record in bundle.excluded_functions}
        self.assertFalse(retained & excluded)
        self.assertTrue(matched, "structured smoke data should overlap the final benchmark")
        self.assertTrue(matched <= excluded)

    def test_normalization_uses_train_rows_only(self) -> None:
        features = torch.tensor(
            [[0.0, 10.0], [2.0, 14.0], [1000.0, -1000.0], [2000.0, -2000.0]],
            dtype=torch.float32,
        )
        train_idx = torch.tensor([0, 1], dtype=torch.long)
        mean, std = train_only_normalization(features, train_idx)
        torch.testing.assert_close(mean, torch.tensor([1.0, 12.0]))
        torch.testing.assert_close(std, torch.tensor([1.0, 2.0]))
        changed_holdout = features.clone()
        changed_holdout[2:] *= 1_000_000.0
        mean_again, std_again = train_only_normalization(changed_holdout, train_idx)
        torch.testing.assert_close(mean_again, mean)
        torch.testing.assert_close(std_again, std)

    def test_smoke_training_writes_auditable_model_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "temporary_action_scorer.pt"
            manifest_path = root / "temporary_action_scorer.manifest.json"
            args = build_arg_parser().parse_args(
                [
                    "--preset",
                    "smoke",
                    "--seed",
                    "17",
                    "--split-seed",
                    "23",
                    "--samples",
                    "2",
                    "--epochs",
                    "1",
                    "--max-depth",
                    "0",
                    "--child-branch",
                    "1",
                    "--device",
                    "cpu",
                    "--exclude-manifest",
                    str(BENCHMARK_MANIFEST),
                    "--out",
                    str(model_path),
                    "--manifest",
                    str(manifest_path),
                ]
            )
            returned = run_training(args)
            on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(returned["model"]["sha256"], on_disk["model"]["sha256"])
            self.assertEqual(on_disk["model"]["sha256"], file_sha256(model_path))
            self.assertEqual(len(on_disk["model"]["sha256"]), 64)
            self.assertEqual(on_disk["metrics"]["test_evaluations"], 1)
            self.assertFalse(on_disk["integrity"]["checkpoint_uses_test"])
            self.assertEqual(on_disk["normalization"]["source_split"], "train")
            self.assertEqual(on_disk["exclusion"]["requested_hash_count"], 30)
            self.assertEqual(
                {item["function_hash"] for item in on_disk["dataset"]["splits"]["train"]["functions"]}
                & {item["function_hash"] for item in on_disk["dataset"]["splits"]["test"]["functions"]},
                set(),
            )

            dataset_evidence = on_disk["dataset"]
            canonical = json.dumps(
                dataset_evidence,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            self.assertEqual(
                on_disk["dataset_manifest_sha256"], hashlib.sha256(canonical).hexdigest()
            )
            payload = torch.load(model_path, map_location="cpu")
            self.assertEqual(payload["format_version"], 2)
            self.assertEqual(payload["metadata"]["data_provenance"]["normalization_source"], "train")
            self.assertEqual(
                payload["metadata"]["data_provenance"]["dataset_manifest_sha256"],
                on_disk["dataset_manifest_sha256"],
            )
            self.assertIn("cuda_available", payload["metadata"]["runtime"])
            scorer = NeuralScorer(model_path)
            self.assertEqual(scorer.device.type, "cpu")
            self.assertEqual(len(scorer.score_many([[0.0] * len(payload["mean"])])), 1)


if __name__ == "__main__":
    unittest.main()
