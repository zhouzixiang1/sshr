#!/usr/bin/env python3
"""Focused tests for recovered-source selection in the formal coverage audit."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis import audit_formal_coverage as audit


class FormalCoverageRecoveredSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="formal-coverage-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _write_row(path: Path, row_id: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"row_id": row_id}) + "\n", encoding="utf-8")

    def test_default_selector_preserves_legacy_final_core_pattern(self) -> None:
        recovered = self.root / "results" / "recovered"
        expected = [
            recovered / "final_core_aes_v1_ok.jsonl",
            recovered / "final_core_random_anf_v1_ok.jsonl",
            recovered / "final_core_random_truth_v1_ok.jsonl",
            recovered / "final_core_structured_v1_ok.jsonl",
        ]
        for index, path in enumerate(expected):
            self._write_row(path, index)
        self._write_row(recovered / "new_recovery_v3.jsonl", 99)

        actual = audit._resolve_recovered_paths(None, None, project=self.root)

        self.assertEqual(actual, [path.resolve() for path in expected])

    def test_repeated_globs_and_explicit_paths_are_unioned_and_deduplicated(self) -> None:
        first = self.root / "recovery_a.jsonl"
        second = self.root / "recovery_b.jsonl"
        self._write_row(first, 1)
        self._write_row(second, 2)

        paths = audit._resolve_recovered_paths(
            [str(self.root / "recovery_*.jsonl"), str(first)],
            [first, second],
            project=self.root,
        )
        rows, parse_errors = audit._load_recovered(paths)

        self.assertEqual(paths, [first.resolve(), second.resolve()])
        self.assertEqual([row["row_id"] for row in rows], [1, 2])
        self.assertEqual(parse_errors, [])

    def test_each_custom_selector_is_strict(self) -> None:
        existing = self.root / "existing.jsonl"
        self._write_row(existing, 1)

        with self.assertRaisesRegex(FileNotFoundError, "glob matched no files"):
            audit._resolve_recovered_paths(
                [str(self.root / "missing_*.jsonl")],
                [existing],
                project=self.root,
            )
        with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
            audit._resolve_recovered_paths(
                None,
                [self.root / "missing.jsonl"],
                project=self.root,
            )
        with self.assertRaisesRegex(FileNotFoundError, "is not a file"):
            audit._resolve_recovered_paths(None, [self.root], project=self.root)

    def test_parser_accepts_repeated_globs_and_jsonls(self) -> None:
        args = audit._parse_args(
            [
                "--recovered-glob",
                "old/*.jsonl",
                "--recovered-glob",
                "new/*.jsonl",
                "--recovered-jsonl",
                "one.jsonl",
                "--recovered-jsonl",
                "two.jsonl",
            ]
        )

        self.assertEqual(args.recovered_globs, ["old/*.jsonl", "new/*.jsonl"])
        self.assertEqual(args.recovered_jsonls, [Path("one.jsonl"), Path("two.jsonl")])


if __name__ == "__main__":
    unittest.main()
