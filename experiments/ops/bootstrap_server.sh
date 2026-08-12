#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
python_bin="${XA_PYTHON_BIN:-python3.11}"
venv_dir="${XA_VENV_DIR:-${repo_root}/.venv}"

if ! command -v "${python_bin}" >/dev/null 2>&1; then
  echo "Missing ${python_bin}. Install Python 3.11 or set XA_PYTHON_BIN." >&2
  exit 1
fi

if [[ ! -x "${venv_dir}/bin/python" ]]; then
  "${python_bin}" -m venv "${venv_dir}"
fi

"${venv_dir}/bin/python" -m pip install --upgrade pip
"${venv_dir}/bin/python" -m pip install -r "${repo_root}/experiments/environment/requirements/dev.txt"

if [[ "${XA_INSTALL_QUANTUM:-0}" == "1" ]]; then
  "${venv_dir}/bin/python" -m pip install -r "${repo_root}/experiments/environment/requirements/quantum.txt"
fi

if [[ "${XA_INSTALL_RESEARCH:-0}" == "1" ]]; then
  "${venv_dir}/bin/python" -m pip install -r "${repo_root}/experiments/environment/requirements/research.txt"
fi

if [[ "${XA_INSTALL_SERVER:-0}" == "1" ]]; then
  "${venv_dir}/bin/python" -m pip install -r "${repo_root}/experiments/environment/requirements/server.txt"
fi

cd "${repo_root}/experiments"
"${venv_dir}/bin/python" -c "from src.synthesizers import synthesize; print('imports ok')"
"${venv_dir}/bin/python" -m pytest tests -q
"${venv_dir}/bin/python" tests/tests_smoke.py

echo "Server bootstrap and core verification completed."
