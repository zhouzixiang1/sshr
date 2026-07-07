# External Toolchain Readiness

This audit checks whether the current workstation can run external
logic/reversible-synthesis baselines beyond the in-repository ABC path.

| tool | local status | role | detected path/module | probe |
|---|---|---|---|---|
| ABC | available | implemented AIG/XAG/LUT/ESOP external estimates | `file: /Users/zhouzixiang/Desktop/tzb/src/tmp/abc/abc` | usage: /Users/zhouzixiang/Desktop/tzb/src/tmp/abc/abc [-c cmd] [-q cmd] [-C cmd] [-Q cmd] [-f script] [-h] [-o file] [-s] [-t type] [-T type] [-x] [-b] [file] |
| mockturtle | missing | future logic-network / reversible-toolchain baseline adapter |  | not found in configured paths, PATH, or Python modules |
| RevKit | missing | future reversible-synthesis baseline adapter |  | not found in configured paths, PATH, or Python modules |

## Interpretation

- ABC is already usable through the bundled `tmp/abc/abc` binary and is the basis of the current AIG/XAG/LUT/ESOP export baselines.
- mockturtle and RevKit are not available in the current environment, so a reproduced ROS/mockturtle/RevKit-style reversible-toolchain comparison still requires installing or vendoring those tools.
- This audit is intentionally environment-specific; rerun it after installing external tools before claiming reproduced external reversible-toolchain results.

## Primary References / Tool Sources

- mockturtle: <https://github.com/lsils/mockturtle>
- RevKit: <https://github.com/msoeken/revkit>
- Back-end-aware fault-tolerant oracle synthesis: <https://dl.acm.org/doi/10.1145/3658617.3697776>
