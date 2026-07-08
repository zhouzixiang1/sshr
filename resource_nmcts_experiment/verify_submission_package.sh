#!/usr/bin/env bash
# Fast pre-upload/artifact check for the already-built submission package.
#
# This script does not rebuild the paper or rerun experiments.  It verifies
# terminal package invariants from the current PDF, payload archive, manifests,
# readiness audit, raw-rerun registry, and LaTeX log.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/opt/anaconda3/envs/mcts-qoracle/bin/python}"

cd "$ROOT_DIR"

"$PYTHON_BIN" analyze_submission_package_verifier.py

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
fi

if command -v rg >/dev/null 2>&1; then
  rg -n "pass:|needs author input|Payload SHA|registry_raw|file count|archive sha256" \
    results/analysis_submission_package_verifier.md \
    results/analysis_submission_readiness_audit.md \
    results/analysis_submission_payload_archive.md
fi

echo "Submission package verifier passed."
