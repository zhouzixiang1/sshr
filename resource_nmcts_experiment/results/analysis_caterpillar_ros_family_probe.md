# Caterpillar ROS-Family Probe

This audit records the local Caterpillar source-family evidence and its boundary relative to full ROS reproduction.

## Status counts

- pass: 8

## Coverage counts

- API present: 1
- claim boundary explicit: 1
- documented role: 1
- local compile smoke: 1
- not available: 1
- partial build present: 1
- solver surface present: 1
- source available: 1

## Compile smoke

- source tree available: True
- git remote: `https://github.com/gmeuli/caterpillar.git`
- git commit: `4c6f766`
- standalone CLI detected: False
- compile return code: 0
- run return code: 0
- warnings: 19

| item | status | coverage | evidence | supported claim | excluded claim |
|---|---|---|---|---|---|
| Local Caterpillar checkout | pass | source available | path=tmp/caterpillar; remote=https://github.com/gmeuli/caterpillar.git; branch=master; commit=4c6f766 | The workstation has a provenance-recorded Caterpillar source checkout for a ROS-family source probe. | A source checkout alone is not a reproduced ROS benchmark. |
| README-stated synthesis role | pass | documented role | tmp/caterpillar/README.md tokens=4/4 | Caterpillar is relevant because it targets Boolean-function quantum-circuit synthesis with quantum memory management. | This documentation role is not evidence that the paper ran full ROS. |
| Core API surface | pass | API present | tmp/caterpillar/include/caterpillar/synthesis/lhrs.hpp tokens=3/3; tmp/caterpillar/include/caterpillar/synthesis/strategies/pebbling_mapping_strategy.hpp tokens=3/3; tmp/caterpillar/include/caterpillar/structures/stg_gate.hpp tokens=3/3; tmp/caterpillar/include/caterpillar/verification/circuit_to_logic_network.hpp tokens=3/3 | The local source exposes logic-network synthesis, single-target gates, pebbling strategies, and circuit-to-logic verification. | Header availability is not a matched benchmark result over the paper's function suite. |
| SAT/pebbling implementation surface | pass | solver surface present | tmp/caterpillar/include/caterpillar/solvers/solver_manager.hpp tokens=3/3; tmp/caterpillar/include/caterpillar/solvers/bsat_solver.hpp tokens=3/3; tmp/caterpillar/include/caterpillar/solvers/z3_solver.hpp tokens=3/3 | The source contains bounded-pebbling controls and BSAT/Z3-oriented solver hooks relevant to garbage/memory management. | These hooks are not the official ROS SAT garbage-management optimizer used as a reproduced baseline. |
| CMake build artifacts | pass | partial build present | build_cache=True; build_test_cache=True; test_objects=19; libabcsat=tmp/caterpillar/build-test/lib/abcsat/liblibabcsat.a exists=True | The local CMake probe built core object files and the abcsat support library. | The build artifacts do not include a standalone ROS or Caterpillar benchmark executable. |
| Toy AIG compile/run smoke | pass | local compile smoke | compile_rc=0; run_rc=0; warnings=19; reason=none | A tiny local AIG can be synthesized through Caterpillar's API and converted back for semantic checking on this workstation. | This is a toy API smoke test, not a published ROS reproduction or performance comparison. |
| Standalone baseline executable | pass | not available | candidate_executables=0; examples_cpp=0; experiments_cpp=0 | The audit records why Caterpillar source availability is currently source-family evidence rather than a standalone CLI benchmark row. | No standalone Caterpillar/ROS executable baseline is claimed or used in the result tables; API-adapter performance rows must remain in their separate manifest. |
| Manuscript and ROS-gap boundary | pass | claim boundary explicit | paper_latex/resource_nmcts_submission_v1.tex tokens=3/3; DELIVERABLE_zh.md tokens=2/2; results/analysis_ros_reproduction_gap_audit.md tokens=2/2 | The paper can mention Caterpillar as a stronger implementation-family probe while preserving the full-ROS boundary. | The manuscript must not describe the Caterpillar probe as full ROS SAT garbage management. |
