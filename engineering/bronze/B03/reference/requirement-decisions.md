# Decisions
- The catalog requires total order by `(receivedAt,id)`, and the comparison reverses with descending order. ID is not an offset.
- Cursor version 1 binds tenant, status filter and direction. Page size may change. Unsupported cursor versions are client errors; do not guess a version.
- Repository snapshots are request-local only. Insertions behind a consumed key do not reappear; ahead-of-key insertions may appear. Deleted rows are absent, and continuation does not look up the cursor row.
- This fixture trusts loopback tenant input. Production authentication is not implemented or claimed; cursor binding is not authorization.
- No stakeholder responses are invented. SQL deployment and production performance remain outside this public file-adapter exercise.
