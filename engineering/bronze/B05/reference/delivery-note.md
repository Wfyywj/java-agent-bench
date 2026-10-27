# Delivery

Scope: import lifecycle fix; CSV public codes and CLI retained. No third-party
libraries, schema changes, external services, real PII, or network calls.
Reproduce with run_selfcheck.py. Reference passes and baseline/mutant rejection is
recorded separately. To recover an interrupted upload, retain the previous output
and rerun the upload after cleanup; do not blindly replay downstream side effects.
Reverting to baseline restores the leak and is not a safe operational rollback.

Limitations: no secure execution sandbox; fixtures and expected answers are public;
no real DB or production FD exhaustion reproduced. CSV is explicitly single-line.
Directory fsync and crash durability across power loss, concurrent writers, close
failure injection, upload size limits, and production memory budgets are unverified.

Audit follow-up: committed files now retain the required CSV header. An independent verifier parses output fields (not the candidate parser), checking values and quoted comma/doubled-quote preservation; data-corruption and missing-header mutations are rejected.
