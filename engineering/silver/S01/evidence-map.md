# Evidence map

RefundService.callback -> Store.commit; Signature.valid; Main callback/get

Terminal overwrite and duplicate posting are independent faults: ordered-sequence checks alone do not protect terminal monotonicity; durable receipts protect restarts.

`fixtures/cases.json` maps each scenario to original acceptance IDs, but passing mapped assertions only covers the narrowed executable slice, not the entire criterion. Actual outcomes: `evidence/selfcheck.json`. All source variants are compiled independently. Three reference runs repeat acceptance outcomes; S04 intentionally allows either legal concurrent winner.

Unmeasured: No HTTP adapter, real payment dispatch, database transaction engine, distributed delivery, fsync/power-loss guarantees, or production secrets.

- `terminal_{succeeded,failed}_to_*_{newer,older}_restart` → S01-A02: both conflict directions, older unseen sequences, unchanged terminal/ledger, persistent review, duplicate and stale controls.
- `terminal_*_precommit_retry_restart` → S01-A04: review/receipt rollback, safe retry and persistent replay in both directions. Each step is a new JVM.
- `mutants/reverse_terminal_conflict` removes only the FAILED → SUCCEEDED guard; the paired A02 cases must reject its `200 stale` instead of `409 manual_review`.
