# F0: automatic Textual debt ratchet

Use the existing packaged `agent-comms-ratchet` on `src/textual` for every
pull request targeting `main`. Any measured increase fails the job.

The measurement owner is `agent_comms.debt_ratchet.Measure` and its existing
families; the source boundary and nonzero failure policy belong to its
`compare` and `main`. This PR wires those owners into GitHub Actions. It adds
no scanner, waiver, native builder, or full native test suite.

Pin the checker to Core `d41601c16d74e9e3e4195b6527fb218b8fe14af9`,
the exact `[tool.uv.sources].agent-comms.rev` in Toad main at dispatch.
Read-only token permissions, full history, original PR base/head revisions,
and no production-path filter keep the stable **Debt ratchet** status present
for every main PR. Parse failures and checker failures remain failures.

Implementation first; validate the complete workflow afterward through its
actual pull-request job. Tristan owns required-check settings and administrator
bypass policy. This PR makes the check automatic; it does not change settings.

Native performance branches 52 and 53, their source, and retained wheels stay
published and unchanged. Their joined installed sidebar journey remains open.
