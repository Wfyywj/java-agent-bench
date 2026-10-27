# Executed verification (v0.1.1)

Two fresh sequential selfcheck runs exited 0 with byte-identical JSON. See `verification-results.json`, `evidence/selfcheck-run2.json`, and `evidence/audit-repeatability.json`.

Normal-return state is now independently checked on disk, after restart, and against a second return token.
- baseline: 5/8 groups passed; failed: B02-A01_replay_restart, B02-A02_payload_conflicts, B02-A05_concurrent_http.
- conflict_ignored: 7/8 groups passed; failed: B02-A02_payload_conflicts.
- damaged_available: 7/8 groups passed; failed: B02-A05_damaged_review.
- normal_loan_state_omitted: 6/8 groups passed; failed: B02-A01_replay_restart, B02-A05_concurrent_http.
- partial_commit: 5/8 groups passed; failed: B02-A03_rollback_write_1, B02-A03_rollback_write_2, B02-A03_rollback_write_3.
- reference: 8/8 groups passed; failed: none.

These are fixture discrimination results, not model scores. PostgreSQL, SQL uniqueness, separate database connections, and power-loss durability were not executed.
