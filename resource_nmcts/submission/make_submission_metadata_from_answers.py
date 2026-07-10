#!/usr/bin/env python3
"""Build private submission metadata from a concise private answer file.

The public metadata template is intentionally complete but verbose.  This
helper lets the author fill a shorter ignored answer file, then merges those
answers with safe public checkout values such as repository URL, current commit
hash, and environment notes.  It never writes private metadata unless
`--write-private` is passed.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from analyze_submission_metadata_audit import (
    METADATA_FILE,
    REQUIRED_METADATA_PATHS,
    SUBMISSION_PACKAGE,
    THIS_DIR,
    has_author_placeholder,
    rel,
    value_at,
)
from make_submission_metadata_starter import AUTHOR_PLACEHOLDER, build_starter


ANSWERS_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_answers_template.json"
ANSWERS_FILE = SUBMISSION_PACKAGE / "submission_metadata_answers.json"
IGNORED_TOP_LEVEL_KEYS = {"instructions"}


def is_empty_answer(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return not stripped or stripped == AUTHOR_PLACEHOLDER
    if isinstance(value, list):
        return not value or all(is_empty_answer(item) for item in value)
    if isinstance(value, dict):
        return not value or all(is_empty_answer(item) for item in value.values())
    return False


def placeholder_paths(value: object, prefix: str = "") -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [prefix or "<root>"] if not stripped or stripped == AUTHOR_PLACEHOLDER else []
    if isinstance(value, list):
        if not value:
            return [prefix or "<root>"]
        paths: list[str] = []
        for idx, item in enumerate(value):
            paths.extend(placeholder_paths(item, f"{prefix}[{idx}]" if prefix else f"[{idx}]"))
        return paths
    if isinstance(value, dict):
        if not value:
            return [prefix or "<root>"]
        paths = []
        for key, item in value.items():
            paths.extend(placeholder_paths(item, f"{prefix}.{key}" if prefix else str(key)))
        return paths
    return []


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{rel(path)} is not valid JSON: {exc}") from exc


def merge_answers(base: object, answers: object, prefix: str = "") -> tuple[object, list[str], list[str]]:
    """Merge non-placeholder answer values into base.

    Returns the merged object, filled paths, and unknown answer paths.  Unknown
    paths are treated as typos because otherwise a private answer could appear
    filled while never reaching the submission metadata consumed by validators.
    """
    if isinstance(answers, dict):
        if not isinstance(base, dict):
            return base, [], [prefix or "<root>"]
        filled: list[str] = []
        unknown: list[str] = []
        for key, value in answers.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            if not prefix and key in IGNORED_TOP_LEVEL_KEYS:
                continue
            if key not in base:
                unknown.append(child)
                continue
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                merged, child_filled, child_unknown = merge_answers(base[key], value, child)
                base[key] = merged
                filled.extend(child_filled)
                unknown.extend(child_unknown)
            elif not is_empty_answer(value):
                base[key] = value
                filled.append(child)
        return base, filled, unknown
    if not is_empty_answer(answers):
        return answers, [prefix or "<root>"], []
    return base, [], []


def build_from_answers(answers_path: Path) -> tuple[dict[str, object], list[str], list[str], list[str], list[str]]:
    starter, public_filled, public_unavailable = build_starter()
    if not isinstance(starter, dict):
        raise ValueError("metadata starter did not return a JSON object")
    answers = read_json(answers_path)
    merged, answer_filled, unknown = merge_answers(starter, answers)
    if not isinstance(merged, dict):
        raise ValueError("merged metadata is not a JSON object")
    remaining = {path for path in REQUIRED_METADATA_PATHS if has_author_placeholder(value_at(merged, path))}
    remaining.update(placeholder_paths(merged))
    filled = sorted(set(public_filled + answer_filled))
    return merged, filled, sorted(set(public_unavailable)), sorted(set(unknown)), sorted(remaining)


def init_private_answers(overwrite: bool) -> int:
    if not ANSWERS_TEMPLATE.exists():
        print(f"missing answer template: {rel(ANSWERS_TEMPLATE)}", file=sys.stderr)
        return 2
    if ANSWERS_FILE.exists() and not overwrite:
        print(f"refusing to overwrite existing {rel(ANSWERS_FILE)}; pass --overwrite if intentional", file=sys.stderr)
        return 3
    shutil.copyfile(ANSWERS_TEMPLATE, ANSWERS_FILE)
    print(f"wrote ignored private answer file: {rel(ANSWERS_FILE)}")
    print("next: fill AUTHOR INPUT REQUIRED values, then run make_submission_metadata_from_answers.py --write-private")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", default=str(ANSWERS_FILE), help="private answer JSON to merge")
    parser.add_argument("--init-private-answers", action="store_true", help=f"copy the public answer template to {rel(ANSWERS_FILE)}")
    parser.add_argument("--write-private", action="store_true", help=f"write {rel(METADATA_FILE)} after merging answers")
    parser.add_argument("--overwrite", action="store_true", help="allow replacing existing private answer or metadata files")
    args = parser.parse_args()

    if args.init_private_answers:
        return init_private_answers(args.overwrite)

    answers_path = Path(args.answers)
    if not answers_path.is_absolute():
        answers_path = THIS_DIR / answers_path
    if not answers_path.exists():
        print(f"private answers missing: {rel(answers_path)}")
        print(f"run with --init-private-answers, or copy {rel(ANSWERS_TEMPLATE)} to {rel(ANSWERS_FILE)}")
        return 2 if args.write_private else 0

    try:
        data, filled, public_unavailable, unknown, remaining = build_from_answers(answers_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"filled metadata paths: {len(filled)}")
    if public_unavailable:
        print("unavailable public checkout fields:", "; ".join(public_unavailable))
    print(f"remaining required/placeholder paths: {len(remaining)}")
    if unknown:
        print("unknown answer paths:", "; ".join(unknown[:12]), file=sys.stderr)
        return 2
    if remaining:
        print("remaining examples:", "; ".join(remaining[:12]))
    if not args.write_private:
        print(f"dry run only; use --write-private to create {rel(METADATA_FILE)}")
        return 0
    if remaining:
        print("refusing to write incomplete metadata; fill remaining answer fields first", file=sys.stderr)
        return 4
    if METADATA_FILE.exists() and not args.overwrite:
        print(f"refusing to overwrite existing {rel(METADATA_FILE)}; pass --overwrite if intentional", file=sys.stderr)
        return 3
    METADATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote ignored private metadata: {rel(METADATA_FILE)}")
    print("next: run validate_submission_metadata.py, make_submission_text_preview.py, rebuild, and verify")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
