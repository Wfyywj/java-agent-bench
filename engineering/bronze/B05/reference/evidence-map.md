# Evidence map

- B05-A01: `fd-samples.csv` increases both upload and staging handles by one per
  completed import while DB active/waiters remain flat. `Importer.run` transfers
  input ownership but baseline has no resource scope. The successful-import leak
  therefore exists independently of parsing errors. The database alert follows the
  failed file open; a later healthy probe and no waiters contradict a persistent
  DB pool bottleneck. This supports upstream resource exhaustion as the fixture's
  root cause; it does not prove all production DB timeouts have this cause.
- B05-A02/A04: Verify uses tracked real reader ownership, actual staging files,
  normal/syntax/field/duplicate/empty/cancel/I/O/setup failures, and 120 imports.
  Success-only closure and deleting the final output are insufficient remedies.
- B05-A03: parser failures map to codes and line numbers without logging raw rows.
- B05-A05: run_selfcheck preserves baseline failures and kills stream/temp/privacy
  mutants. See evidence/selfcheck-*.json for actual execution, not estimates.

No real DB, OS descriptor exhaustion, GC dependency, production incident, or
multi-process import concurrency is tested. Increasing a database pool alone
cannot repair importer-owned descriptor and temporary-file leakage.
