# Original acceptance coverage (partial, not full acceptance)

- K03-A01: approved correction vs blocked unknown policy; limited taxonomy.
- K03-A02: independent Python arithmetic table; no timestamp buckets.
- K03-A03: shadow does not increase confirmed bill count.
- K03-A04: tenant-period routes and immutable confirmed bill snapshots.
- K03-A05: blocked unapproved shadow then approved canary and rollback.
- K03-A06: operational timeout only; NO calibrated performance test/customer materials.

Evidence lives in selfcheck-evidence.json. Public checks validate the declared slice, not every original acceptance criterion.

## Independent audit hardening
A narrowing-to-int mutant previously survived small-number checks. Added exact Python integer expectations for readings above Integer.MAX_VALUE, largest safe v1/v2 products, multiplication/addition overflow rejection, no-confirmation after failure, and rollback pinning of large bills. The new semantic mutant must fail.
