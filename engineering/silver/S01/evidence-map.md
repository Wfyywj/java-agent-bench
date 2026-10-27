# Evidence map

RefundService.callback -> Store.commit; Signature.valid; Main callback/get

Terminal overwrite and duplicate posting are independent faults: ordered-sequence checks alone do not protect terminal monotonicity; durable receipts protect restarts.

`fixtures/cases.json` maps each scenario to original acceptance IDs, but passing mapped assertions only covers the narrowed executable slice, not the entire criterion. Actual outcomes: `evidence/selfcheck.json`. All source variants are compiled independently. Three reference runs repeat acceptance outcomes; S04 intentionally allows either legal concurrent winner.

Unmeasured: No HTTP adapter, real payment dispatch, database transaction engine, distributed delivery, fsync/power-loss guarantees, or production secrets.
