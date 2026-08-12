# Competition submission tools

`build_competition_staging.py` and `verify_competition_package.py` are the current
XA-202609 competition-package path.  The other scripts in this directory belong
to the archived academic-paper submission workflow and must not be used as the
competition whitelist.

The builder reads `competition_staging_spec.json`, resolves every source from
the repository root, copies only listed files, creates compact E2/E3/E4,
canonical E4-v2, and E5 v1/v1.1 evidence snapshots, and writes
`MANIFEST.json`, `CHECKSUMS.sha256`, `SBOM-LITE.json`,
`PROVENANCE.json`, and `AUTHORIZATION_STATUS.json`.  It refuses to overwrite an
existing staging directory or archive.

Eight exact E5 bundles are the only raw/log exception: portable negative audit
V3, fresh-v2, the three anchor predecessors, the original unaccepted 90-row
scientific-source predecessor, and its linked preflight/seal inputs.  This
minimal dependency closure supports in-package 19/19 native verification and
is bound to external anchor SHA
`036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686`.
The predecessors are provenance-only inputs, never performance evidence or a
recommended result.  The immutable fresh-v1/fresh-v2 raw streams each contain
one historical stdout local path; only those exact two fields/targets are
allowed and every other local path remains fail-closed.
The package verifier re-runs the fresh-v2 19-check verifier with that expected
anchor SHA.  Its 9/9 command and 383-test record is software/portability
evidence only; protocol acceptance, scientific performance, hardware execution,
and quantum advantage all remain false.

Final mode requires a separately supplied, human-approved authorization bundle.
No license, IP statement, provenance conclusion, third-party notice, registration
record, identity record, or transitive SBOM is synthesized by these tools.  See
`docs/competition/submission/README.md` for the gate schema and commands.

Final mode also requires `TECHNICAL_RELEASE_STATUS.json` to be ready.  Formal
v4 now closes command/config/split/seed/log/checkpoint/source-SHA provenance,
but remains a development candidate and is not performance evidence.  The
independent verifier additionally preserves E4-v2 as post-E4 replication,
E5 as having no accepted endpoint, and E6 as a mechanism-only MVP with no
formal result.  A human declaration cannot promote any of these states: final
still requires a non-development final-frozen model card, accepted external
performance evidence, and a clean frozen Git state.
