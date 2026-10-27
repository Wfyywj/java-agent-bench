# Request changes
- Blocking / QuoteCalculator.total / Math.round: `1.005, discount=0, tax=0` returns 1.00 rather than policy 1.01. Binary floating-point changes the half-cent boundary. Parse and retain decimal arithmetic.
- Blocking / QuoteCalculator.total / per-line tax: two 0.05 lines at 10% tax return 0.12, not 0.11. Tax is applied once to subtotal, not each line.
- Blocking / QuoteCalculator.total / discount assignment: omitted discount now returns 500; prior contract requires zero default and 10.00 for a 10-unit line.
- Blocking / AuditLog.rejected: invalid discount emits user note to stderr. Log a fixed code, never user fields.
- Nonblocking readability: rename running to express its domain role. Do not confuse this with a correctness issue.
Discount values outside [0,1] and overflow already return controlled 422: tested, no defect alleged. No policy modifications proposed. See review.json for exact anchors and verifier/cases.json for executable requests. Corrected maintainer implementation passes those regressions independently of this review.
