#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.competition_benchmarks import competition_suite, function_key, suite_manifest


class CompetitionBenchmarkTests(unittest.TestCase):
    def test_suite_is_frozen_unique_and_bounded(self) -> None:
        cases = competition_suite()
        self.assertEqual(len(cases), 30)
        self.assertEqual(len({case.case_id for case in cases}), 30)
        self.assertEqual(len({case.function_key for case in cases}), 30)
        self.assertTrue(all(3 <= case.function.n <= 8 for case in cases))
        self.assertEqual({case.family for case in cases}, {"structured", "random_truth", "random_anf", "aes_sbox"})

    def test_content_hash_is_stable_and_truth_sensitive(self) -> None:
        first = competition_suite()
        second = competition_suite()
        self.assertEqual([case.function_key for case in first], [case.function_key for case in second])
        self.assertTrue(all(function_key(case.function) == case.function_key for case in first))

    def test_manifest_suite_id_covers_case_content(self) -> None:
        manifest = suite_manifest()
        self.assertEqual(manifest["case_count"], 30)
        self.assertEqual(len(manifest["suite_id"]), 64)
        encoded = json.dumps(manifest, ensure_ascii=False)
        self.assertIn("truth_table_hex", encoded)
        self.assertIn("generator_params", encoded)


if __name__ == "__main__":
    unittest.main()
