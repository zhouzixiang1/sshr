# Scaling and Resource Audit

This audit separates generated functions/settings, method rows, verified rows, and representative resource means.
The representative resources are method-specific and should not be read as averages over all baselines.

| slice | n scope | functions/settings | rows verified | representative resources | boundary |
|---|---|---:|---:|---|---|
| Large term-set frontier | n=24,28,32,40 | 96 | 960/960 | score 1090.0; T/CNOT/depth 986/1593/1593; anc. 5.3; time 7.40s | Term-set validation; no full truth table beyond bridge slices. |
| Stage-gated frontier | n=24,28,32,40 | 96 | 96/96 | score 1089.7; T/CNOT/depth 985/1593/1593; anc. 5.3; time 10.57s | Controller audit; still term-set symbolic verification. |
| Action-width probe | n=20,28,40 | 216 | 1512/1512 | score 1130.4; T/CNOT/depth 1023/1648/1648; anc. 5.2; time 1.27s | Sensitivity check; wider root screens are not claimed as better. |
| Complete truth-table bridge | n=21--25 | 40 | 400/400 | score 1126.2; T/CNOT/depth 1019/1647/1647; anc. 5.3; time 4.16s; truth check 0.08s | Complete checking on generated bridge slices only. |
