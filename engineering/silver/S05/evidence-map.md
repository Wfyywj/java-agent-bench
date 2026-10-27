# Evidence map

Main -> Database.load -> SearchRepository.search; SQL statement constant; explain command is actual H2 EXPLAIN.

N+1 mutation actually executes an extra COUNT query for every returned row. Query count changes, not result set. Missing-index hypothesis is separately evidenced by H2 plan; this is not PostgreSQL plan evidence.

`fixtures/cases.json` maps each scenario to original acceptance IDs, but passing mapped assertions only covers the narrowed executable slice, not the entire criterion. Actual outcomes: `evidence/selfcheck.json`. All source variants are compiled independently. Three reference runs repeat acceptance outcomes; S04 intentionally allows either legal concurrent winner.

Unmeasured: H2 is not PostgreSQL; PostgreSQL EXPLAIN ANALYZE, production cardinality estimates, index lock duration, latency/SLO and connection pooling remain unmeasured. Counter covers search SQL, excludes fixture loading and EXPLAIN.

Independent audit regressions: `evidence/external-audit-regressions.json`; evaluator-controlled statement probe `evaluator/TrustedSearchProbe.java`; exact since=1800 set checked independently by `oracle.py`.
