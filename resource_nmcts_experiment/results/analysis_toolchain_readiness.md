# External Toolchain Readiness

This audit checks whether the current workstation can run external
logic/reversible-synthesis baselines beyond the in-repository ABC path.
It distinguishes local availability from upstream source reachability
and build prerequisites, because mockturtle is a C++ library and
RevKit 3.x is a Python package backed by C++ code.

## Build Prerequisites

| prerequisite | status | detected command/path | probe | needed for |
|---|---|---|---|---|
| git | available | `/usr/bin/git` | git version 2.50.1 (Apple Git-155) | fetching mockturtle/RevKit/CirKit sources |
| cmake | available | `/opt/anaconda3/envs/mcts-qoracle/bin/cmake` | cmake version 4.3.4 | building RevKit/CirKit-style C++ toolchains |
| cmake | available (additional) | `/opt/homebrew/bin/cmake` | cmake version 4.3.4 | building RevKit/CirKit-style C++ toolchains |
| C++17 compiler | available | `/usr/bin/clang++` | Apple clang version 21.0.0 (clang-2100.1.1.101) | building mockturtle/RevKit dependencies |
| C++17 compiler | available (additional) | `/usr/bin/g++` | Apple clang version 21.0.0 (clang-2100.1.1.101) | building mockturtle/RevKit dependencies |
| Python/pip | available | `/opt/anaconda3/envs/mcts-qoracle/bin/python` | pip 26.0.1 from /opt/anaconda3/envs/mcts-qoracle/lib/python3.11/site-packages/pip (python 3.11) | probing RevKit 3.x Python package installation |

## Tool Availability

| tool | kind | local status | role | detected path/module | probe |
|---|---|---|---|---|---|
| ABC | binary | available | implemented AIG/XAG/LUT/ESOP external estimates | `file: /Users/zhouzixiang/Desktop/tzb/src/tmp/abc/abc` | usage: /Users/zhouzixiang/Desktop/tzb/src/tmp/abc/abc [-c cmd] [-q cmd] [-C cmd] [-Q cmd] [-f script] [-h] [-o file] [-s] [-t type] [-T type] [-x] [-b] [file] |
| mockturtle | cxx_header_library | available | official-header KLUT-to-XAG probe adapter; full ROS flow remains separate | `source: /Users/zhouzixiang/Desktop/tzb/src/tmp/mockturtle` | local source checkout exists |
| RevKit | binary_or_python | available | Python oracle_synth baseline adapter; legacy CLI flow remains separate | `python: revkit` | /opt/anaconda3/envs/mcts-qoracle/lib/python3.11/site-packages/revkit/__init__.py |
| RevKit CLI / CirKit legacy | binary_or_source | missing | legacy command-line reversible synthesis flow for RevKit-style baselines |  | not found in configured paths, PATH, or Python modules |

## Upstream Source Reachability

| tool | source | branch | status | commit |
|---|---|---|---|---|
| ABC | <https://github.com/berkeley-abc/abc> | master | reachable | `bcfdf592289a408cd67ec19260f8a60a37b085b6` |
| mockturtle | <https://github.com/lsils/mockturtle> | master | reachable | `25beb0e294e4613bb9fe62319b91d9f2ab764e88` |
| RevKit | <https://github.com/msoeken/revkit> | develop | reachable | `20d7d5ff72b33441583ed381fb0011964008d86b` |
| RevKit | <https://github.com/msoeken/revkit> | master | reachable | `a59fa132f73a2483a00b11c23f5f1c599a34f074` |
| RevKit CLI / CirKit legacy | <https://github.com/msoeken/cirkit> | master | reachable | `8a098dae1f09f9e8af6e132b1fa76f05948689ed` |
| RevKit CLI / CirKit legacy | <https://github.com/msoeken/cirkit> | develop | reachable | `104eb35f1933b080aa228ad419756f04682d4a2e` |

## Reproduction Commands to Try Next

### ABC

- `already vendored under tmp/abc/abc in this project`

### mockturtle

- `git clone --recursive https://github.com/lsils/mockturtle.git tmp/mockturtle`
- `/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/run_mockturtle_xag_probe.py --workers 4 --timeout 20`

### RevKit

- `/opt/anaconda3/envs/mcts-qoracle/bin/python -m pip install 'git+https://github.com/msoeken/revkit@develop'`
- `or: git clone -b develop https://github.com/msoeken/revkit tmp/revkit && cd tmp/revkit && make devbuild`

### RevKit CLI / CirKit legacy

- `git clone --recursive https://github.com/msoeken/cirkit.git tmp/cirkit`
- `cd tmp/cirkit && mkdir -p build && cd build && cmake .. && make revkit`

## Interpretation

- ABC is already usable through the bundled `tmp/abc/abc` binary and is the basis of the current AIG/XAG/LUT/ESOP export baselines.
- No basic build prerequisite blocker was detected.
- mockturtle source and the project KLUT-to-XAG adapter are available; `run_mockturtle_xag_probe.py` has produced a reproducible official-header probe. This is still not the full official ROS flow.
- RevKit Python API is locally available and can support an API-level `oracle_synth` baseline; this is distinct from the legacy RevKit/CirKit CLI flow.
- RevKit/CirKit legacy CLI is not yet available, so legacy command-line reversible-synthesis reproduction remains pending.
- This audit is intentionally environment-specific; rerun it after installing external tools before claiming reproduced external reversible-toolchain results.

## Primary References / Tool Sources

- mockturtle: <https://github.com/lsils/mockturtle>
- RevKit: <https://github.com/msoeken/revkit>
- RevKit/CirKit legacy CLI: <https://msoeken.github.io/revkit.html>
- Back-end-aware fault-tolerant oracle synthesis: <https://dl.acm.org/doi/10.1145/3658617.3697776>
