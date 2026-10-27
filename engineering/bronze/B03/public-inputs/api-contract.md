# API v1
GET /boxes?tenant=north&status=all&direction=asc&limit=5&cursor=...

Tenant is a trusted synthetic caller identity in this fixture, not authentication. This package does not establish production authorization. status = all|READY|HOLD; direction = asc|desc; limit = 1..100. IDs are unique restricted ASCII warehouse identifiers. receivedAt is UTC Instant.

200: {"items":[{"id":"BOX000","receivedAt":"2026-01-20T10:00:00Z"}],"next":"opaque-token-or-null"}.
No rows and final page return next=null; the page size is an upper bound, never enlarged.
400: {"error":"invalid_request"}, no stack trace. Cursor version 1 is base64url of six pipe-separated values: version, tenant, status filter, direction, timestamp, id. Invalid/truncated/unknown versions reject. Cursor must bind tenant, status and direction. Limit may change between requests.

Non-snapshot traversal: records strictly beyond the cursor can appear if inserted; deletions disappear; insertions behind the cursor are not replayed. The last-seen row may be deleted and continuation must still work. No OFFSET. Cursor encoding is not authentication, encryption or tamper-proof signing.
