#!/usr/bin/env python3
"""Verify all files in an extracted XA-202609 delivery against its manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "DELIVERY_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[dict[str, object]] = []
    checked = 0
    for row in manifest["files"]:
        path = (root / row["path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            failures.append({"path": row["path"], "error": "path escapes delivery root"})
            continue
        if not path.is_file():
            failures.append({"path": row["path"], "error": "missing"})
            continue
        actual_size = path.stat().st_size
        actual_sha = sha256_file(path)
        checked += 1
        if actual_size != row["size_bytes"] or actual_sha != row["sha256"]:
            failures.append(
                {
                    "path": row["path"],
                    "error": "size/hash mismatch",
                    "expected_size": row["size_bytes"],
                    "actual_size": actual_size,
                    "expected_sha256": row["sha256"],
                    "actual_sha256": actual_sha,
                }
            )
    result = {
        "package": manifest["package_name"],
        "expected_files": manifest["file_count_excluding_manifest"],
        "checked_files": checked,
        "failures": failures,
        "verified": not failures and checked == manifest["file_count_excluding_manifest"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
