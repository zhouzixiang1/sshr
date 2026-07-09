#!/usr/bin/env python3
"""Create an ignored private submission-metadata starter file.

The public template intentionally keeps author and venue fields blank.  This
helper fills only non-private fields that are safer to derive from the current
checkout, then writes `submission_package/submission_metadata.json` only when
the author explicitly requests it.  The output file is ignored by Git.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from analyze_submission_metadata_audit import METADATA_FILE, METADATA_TEMPLATE, THIS_DIR, rel, value_at


AUTHOR_PLACEHOLDER = "AUTHOR INPUT REQUIRED"


def run_git(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=THIS_DIR,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
        )
    except Exception:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def normalize_remote_url(url: str) -> str:
    if url.startswith("git@github.com:"):
        owner_repo = url.removeprefix("git@github.com:").removesuffix(".git")
        return f"https://github.com/{owner_repo}"
    if url.startswith("ssh://git@ssh.github.com:443/"):
        owner_repo = url.removeprefix("ssh://git@ssh.github.com:443/").removesuffix(".git")
        return f"https://github.com/{owner_repo}"
    if url.startswith("https://github.com/"):
        return url.removesuffix(".git")
    return url


def set_if_placeholder(data: dict[str, object], dotted_path: str, value: str) -> bool:
    if not value:
        return False
    current: object = data
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    if not isinstance(current, dict):
        return False
    leaf = parts[-1]
    existing = value_at(data, dotted_path)
    if isinstance(existing, str) and AUTHOR_PLACEHOLDER in existing:
        current[leaf] = value
        return True
    return False


def detect_public_values() -> dict[str, str]:
    remote = normalize_remote_url(run_git(["config", "--get", "remote.origin.url"]))
    head = run_git(["rev-parse", "HEAD"])
    branch = run_git(["branch", "--show-current"])
    status = run_git(["status", "--short"])
    return {
        "code_availability.repository_url": remote,
        "code_availability.commit_hash": head,
        "code_availability.environment_notes": (
            "mcts-qoracle environment; direct interpreter path "
            "/opt/anaconda3/envs/mcts-qoracle/bin/python; lightweight rebuild "
            "command ./rebuild_submission_package.sh; generated from branch "
            f"{branch or 'unknown'} with {'a clean' if not status else 'a dirty'} worktree."
        ),
    }


def build_starter() -> tuple[dict[str, object], list[str], list[str]]:
    data = json.loads(METADATA_TEMPLATE.read_text(encoding="utf-8"))
    public_values = detect_public_values()
    filled: list[str] = []
    unavailable: list[str] = []
    for path, value in public_values.items():
        if set_if_placeholder(data, path, value):
            filled.append(path)
        elif not value:
            unavailable.append(path)
    return data, filled, unavailable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-private",
        action="store_true",
        help=f"write {rel(METADATA_FILE)}; without this flag, only report what would be filled",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="allow replacing an existing private metadata file",
    )
    args = parser.parse_args()

    if not METADATA_TEMPLATE.exists():
        print(f"missing template: {rel(METADATA_TEMPLATE)}", file=sys.stderr)
        return 2

    data, filled, unavailable = build_starter()
    print("Public fields available for starter metadata:")
    for path in filled:
        print(f"- filled: {path}")
    for path in unavailable:
        print(f"- unavailable: {path}")
    print("- left for author/venue input: author identities, target venue, funding, declarations, archive links, license, and review policy fields")

    if not args.write_private:
        print(f"dry run only; use --write-private to create {rel(METADATA_FILE)}")
        return 0

    if METADATA_FILE.exists() and not args.overwrite:
        print(f"refusing to overwrite existing {rel(METADATA_FILE)}; pass --overwrite if this is intentional", file=sys.stderr)
        return 3

    METADATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote ignored private starter: {rel(METADATA_FILE)}")
    print("next: fill remaining AUTHOR INPUT REQUIRED values, then run ./rebuild_submission_package.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
