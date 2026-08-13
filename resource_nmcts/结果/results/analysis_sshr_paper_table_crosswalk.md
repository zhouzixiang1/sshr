# SSHR Published-Table Crosswalk

This report maps the main published SSHR tables to the current package's reproducible evidence and explicit claim boundaries.

## Status counts

- pass: 5

## Coverage counts

- bounded reference: 1
- exact count reproduction: 1
- same-task matched slice: 1
- timed matched slice plus n<=4 pilot: 2

## Crosswalk

| SSHR table | audit status | current coverage | current artifact | permitted claim | excluded claim |
|---|---|---|---|---|---|
| Table IV | pass | bounded reference | No headline comparison uses this raw-gate table; the current package keeps it as SSHR source context only. | The SSHR paper provides a CNOT-oriented raw-gate decomposition context. | The lightweight package does not claim a full Table IV rerun. |
| Table V | pass | same-task matched slice | The paper uses 177 same-function SSHR-H rows and resource-weight audits rather than importing the published aggregate as a headline win. | SSHR-H is a matched CNOT-specialized baseline on the current Boolean-oracle suite. | The current paper does not claim to rerun every SSHR Table V random-function aggregate. |
| Table VI | pass | timed matched slice plus n<=4 pilot | The package includes 177 same-function SSHR-I CNOT rows at n<=6 and 72 n<=4 pilot rows, with correctness checks and timeout metadata. | SSHR-I CNOT is a time-limited CNOT-oriented counterpoint on the matched current suite. | These rows are not an exact certificate for the full published SSHR-I Table VI aggregate. |
| Table VII | pass | timed matched slice plus n<=4 pilot | The package includes 177 same-function SSHR-I T-objective rows at n<=6 and 72 n<=4 pilot rows under the current logical-resource projection. | SSHR-I T is a relevant T-oriented counterpoint on the matched current suite. | These rows are not a full rerun of all published Table VII random/NPN settings. |
| Table VIII | pass | exact count reproduction | The local parallelotope enumerator is rerun on the full n=3--8 hypercubes and matches all six published counts. | The paper can use Table VIII to explain SSHR's candidate-space role. | Candidate-count reproduction is not a substitute for rerunning every SSHR-I random benchmark. |
