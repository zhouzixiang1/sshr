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
| RevKit | binary_or_python | available | Python oracle_synth phase-netlist baseline adapter | `python: revkit` | /opt/anaconda3/envs/mcts-qoracle/lib/python3.11/site-packages/revkit/__init__.py |
| CirKit 3 shell | binary_or_source | available | official CirKit shell for AIG/LUT optimization probes; not legacy RevKit reversible synthesis | `file: /Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit/build/cli/cirkit` | Usage: /Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit/build/cli/cirkit [OPTIONS] |
| CirKit 3 shell | binary_or_source | available (additional) | official CirKit shell for AIG/LUT optimization probes; not legacy RevKit reversible synthesis | `source: /Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit` | local source checkout exists |
| RevKit CLI / CirKit legacy | binary_or_source | available | legacy command-line reversible synthesis flow for exact oracle-permutation baselines | `file: /Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit_legacy/build/programs/revkit` | Usage: /Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit_legacy/build/programs/revkit [OPTIONS] |
| RevKit CLI / CirKit legacy | binary_or_source | available (additional) | legacy command-line reversible synthesis flow for exact oracle-permutation baselines | `source: /Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit_legacy` | local source checkout exists |
| caterpillar | cxx_source_library | available | open-source LSI quantum Boolean synthesis library with XAG synthesis and SAT-based pebbling components; source/build probe only, not standalone ROS CLI | `source: /Users/zhouzixiang/Desktop/tzb/src/tmp/caterpillar` | local source checkout exists |
| caterpillar | cxx_source_library | available (additional) | open-source LSI quantum Boolean synthesis library with XAG synthesis and SAT-based pebbling components; source/build probe only, not standalone ROS CLI | `file: /Users/zhouzixiang/Desktop/tzb/src/tmp/caterpillar/build/CMakeCache.txt` | local file exists |
| caterpillar | cxx_source_library | available (additional) | open-source LSI quantum Boolean synthesis library with XAG synthesis and SAT-based pebbling components; source/build probe only, not standalone ROS CLI | `file: /Users/zhouzixiang/Desktop/tzb/src/tmp/caterpillar/build-test/lib/abcsat/liblibabcsat.a` | local file exists |

## Upstream Source Reachability

| tool | source | branch | status | commit |
|---|---|---|---|---|
| ABC | <https://github.com/berkeley-abc/abc> | master | reachable | `bcfdf592289a408cd67ec19260f8a60a37b085b6` |
| mockturtle | <https://github.com/lsils/mockturtle> | master | reachable | `25beb0e294e4613bb9fe62319b91d9f2ab764e88` |
| RevKit | <https://github.com/msoeken/revkit> | develop | reachable | `20d7d5ff72b33441583ed381fb0011964008d86b` |
| RevKit | <https://github.com/msoeken/revkit> | master | reachable | `a59fa132f73a2483a00b11c23f5f1c599a34f074` |
| CirKit 3 shell | <https://github.com/msoeken/cirkit> | cirkit3 | reachable | `4531533394725864a304e710d82087ff74fbe801` |
| CirKit 3 shell | <https://github.com/msoeken/cirkit> | master | reachable | `8a098dae1f09f9e8af6e132b1fa76f05948689ed` |
| RevKit CLI / CirKit legacy | <https://github.com/msoeken/cirkit> | master | reachable | `8a098dae1f09f9e8af6e132b1fa76f05948689ed` |
| RevKit CLI / CirKit legacy | <https://github.com/msoeken/cirkit> | develop | reachable | `104eb35f1933b080aa228ad419756f04682d4a2e` |
| caterpillar | <https://github.com/gmeuli/caterpillar> | master | reachable | `4c6f766cd0ffc62d37ab45edfe80c9f1eae44764` |

## Reproduction Commands to Try Next

### ABC

- `already vendored under tmp/abc/abc in this project`

### mockturtle

- `git clone --recursive https://github.com/lsils/mockturtle.git tmp/mockturtle`
- `/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/run_mockturtle_xag_probe.py --workers 4 --timeout 20`

### RevKit

- `/opt/anaconda3/envs/mcts-qoracle/bin/python -m pip install 'git+https://github.com/msoeken/revkit@develop'`
- `or: git clone -b develop https://github.com/msoeken/revkit tmp/revkit && cd tmp/revkit && make devbuild`

### CirKit 3 shell

- `git clone --recursive https://github.com/msoeken/cirkit.git tmp/cirkit`
- `cd tmp/cirkit && mkdir -p build && cd build && cmake .. && cmake --build . --target cirkit --parallel 8`
- `/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/run_cirkit_aig_probe.py --workers 8 --timeout 45`

### RevKit CLI / CirKit legacy

- `git -C tmp/cirkit worktree add ../cirkit_legacy origin/develop && git -C tmp/cirkit_legacy submodule update --init --recursive`
- `cd tmp/cirkit_legacy && mkdir -p build && cd build && cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -Denable_cirkit-addon-reversible=ON .. && cmake --build . --target revkit --parallel 8`
- `/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/run_revkit_cli_probe.py --workers 8 --timeout 20 --flow tbs=tbs --flow dbs=dbs --flow rms=rms`

### caterpillar

- `git clone --depth 1 https://github.com/gmeuli/caterpillar.git tmp/caterpillar`
- `cmake -S tmp/caterpillar -B tmp/caterpillar/build -DCATERPILLAR_TEST=OFF -DCATERPILLAR_EXAMPLES=ON -DCATERPILLAR_EXPERIMENTS=OFF && cmake --build tmp/caterpillar/build --parallel 8`
- `optional test probe: cmake -S tmp/caterpillar -B tmp/caterpillar/build-test -DCATERPILLAR_TEST=ON -DCATERPILLAR_EXAMPLES=OFF -DCATERPILLAR_EXPERIMENTS=OFF && cmake --build tmp/caterpillar/build-test --parallel 8`

## Interpretation

- ABC is already usable through the bundled `tmp/abc/abc` binary and is the basis of the current AIG/XAG/LUT/ESOP export baselines.
- No basic build prerequisite blocker was detected.
- mockturtle source and the project KLUT-to-XAG adapter are available; `run_mockturtle_xag_probe.py` has produced a reproducible official-header probe. This is still not the full official ROS flow.
- RevKit Python API is locally available and can support an API-level `oracle_synth` baseline; this is distinct from the legacy RevKit/CirKit CLI flow.
- CirKit 3 shell is locally available and `run_cirkit_aig_probe.py` has produced a reproducible AIG/multiplicative-complexity probe. This is not legacy RevKit reversible synthesis or full ROS.
- RevKit/CirKit legacy CLI is locally available and `run_revkit_cli_probe.py` has produced a reproducible reversible-synthesis CLI portfolio probe on exact oracle permutations.
- caterpillar source is locally available as the open-source LSI quantum Boolean synthesis library cited by the XAG compilation line. It exposes XAG synthesis and SAT-based pebbling/memory-management components, but no standalone ROS executable was detected in this checkout.
- The local caterpillar minimal CMake probe configured successfully; the optional all-test build is environment-sensitive on this macOS/AppleClang toolchain because the bundled Catch2 trap uses an x86 `int $3` inline-assembly mnemonic.
- This audit is intentionally environment-specific; rerun it after installing external tools before claiming reproduced external reversible-toolchain results.

## Primary References / Tool Sources

- mockturtle: <https://github.com/lsils/mockturtle>
- RevKit: <https://github.com/msoeken/revkit>
- RevKit/CirKit legacy CLI: <https://msoeken.github.io/revkit.html>
- caterpillar: <https://github.com/gmeuli/caterpillar>
- Back-end-aware fault-tolerant oracle synthesis: <https://dl.acm.org/doi/10.1145/3658617.3697776>
