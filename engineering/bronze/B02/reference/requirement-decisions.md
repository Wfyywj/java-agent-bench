# Decisions
Provided contract: tokens are tenant-scoped, bind all payload fields, and survive restart. Damaged equipment is held in REVIEW without cleaning jobs. No stakeholder answers were invented.

Implementation decision: one synchronized service writer stages complete snapshots and atomically replaces the file. Validation precedes mutation; exact replay precedes the already-returned lifecycle gate. Tenant existence checks precede lookup of replay results to avoid disclosure.

Unresolved deployment dependency: the catalog requires PostgreSQL. This offline adapter does not answer database isolation, SQL constraint or multi-process crash questions. Do not promote this development result to full PostgreSQL acceptance.
