# Rotation-Synthesis Backend Audit

This audit records the local high-precision rotation-synthesis boundary for the phase/Rz branch.

## Status counts

- pass: 4

| item | status | availability | evidence | supported claim | excluded claim |
|---|---|---|---|---|---|
| Internal source-derived sequence smoke | pass | internal_matrix_beam | smoke=20/20; tight=5/20; max_error=0.11185337158122222 | The project emits and verifies concrete Clifford+T strings for source-derived Rz targets at coarse tolerance. | This does not certify high-precision or optimal rotation synthesis. |
| External command-line high-precision backends | pass | none available | gridsynth=missing; newsynth=missing; pgridsynth=missing | The manuscript can state whether a gridsynth-style backend was actually present in this environment. | Missing command-line backends mean the current package cannot claim a reproduced Ross--Selinger/gridsynth flow. |
| Python synthesis SDK backends | pass | none available | pyzx=missing; qiskit=missing; cirq=missing | The package records that no hidden Python SDK supplied high-precision rotation synthesis. | The internal beam smoke remains the only sequence emitter unless one of these backends is added and audited. |
| Tight-tolerance diagnostic | pass | 5/20 tight pass | tight_failed_targets=freq01-den8-15,freq02-den8-1,freq04-den32-61,freq05-den32-19,freq06-den32-59,freq07-den32-3,freq09-den16-31,freq11-den32-13,freq13-den16-1,freq15-den8-3,freq16-den16-3,freq17-den16-29,freq18-den32-11,freq19-den32-21,freq20-den8-13 | The remaining gap is explicitly measured, not hidden behind the coarse smoke result. | The phase/Rz branch is still a logical proxy and should not be used as a final Clifford+T compiler claim. |
