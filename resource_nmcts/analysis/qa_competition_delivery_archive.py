#!/usr/bin/env python3
"""Extract the final delivery to a temporary directory and run package QA."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ZIP = ROOT / "submission_package" / "dist" / "XA-202609_Resource-NMCTS_final.zip"
PACKAGE_ROOT = "XA-202609_Resource-NMCTS_final"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    args = parser.parse_args()
    zip_path = args.zip.resolve()
    commands: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="xa202609_delivery_qa_") as temporary:
        temporary_root = Path(temporary).resolve()
        with zipfile.ZipFile(zip_path, "r") as archive:
            for name in archive.namelist():
                destination = (temporary_root / name).resolve()
                try:
                    destination.relative_to(temporary_root)
                except ValueError as exc:
                    raise ValueError(f"unsafe ZIP member: {name}") from exc
                if not name.startswith(f"{PACKAGE_ROOT}/"):
                    raise ValueError(f"unexpected ZIP root: {name}")
            archive.extractall(temporary_root)
        package_root = temporary_root / PACKAGE_ROOT
        environment = os.environ.copy()
        environment["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        for command in (
            [sys.executable, "verify_delivery_manifest.py"],
            [sys.executable, "tests/tests_smoke.py"],
        ):
            completed = subprocess.run(
                command,
                cwd=package_root,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            row = {
                "command": command[1:],
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
            commands.append(row)
            if completed.returncode != 0:
                print(json.dumps({"zip": str(zip_path), "commands": commands, "verified": False}, indent=2))
                return completed.returncode
    print(json.dumps({"zip": str(zip_path), "commands": commands, "verified": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
