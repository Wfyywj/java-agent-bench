# Decisions

The caller transfers stream ownership immediately. Try-with-resources closes it
even if staging construction fails. A staging file is also owned and closed on
parse failures, cancellation, normal completion, and propagated I/O failures.
CSV is one physical line per record; malformed quotes are not silently repaired.
Cancellation returns no committed rows and leaves the previous file unchanged.
Import commit uses same-directory atomic replacement; unsupported atomic moves
fail rather than silently weakening atomicity. No retry or database change.

Unconfirmed: actual production FD limit, actual DB pool exhaustion, multi-process
concurrent writes. No stakeholder answer or production observation is fabricated.
