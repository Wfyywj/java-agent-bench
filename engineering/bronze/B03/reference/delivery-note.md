# Delivery
Change: add unique ID tie-breaker to existing timestamp ordering; existing directional comparator, cursor fields and HTTP shape remain unchanged. No page-size inflation.

Verification: `python3 run_selfcheck.py` compiled each variant in a fresh temporary directory, started actual loopback HTTP service, and ran five acceptance groups. The reference passes; baseline and four semantic mutants are rejected. Two complete outputs were identical. Full evidence: `../evidence/selfcheck-results.json`.

Rollback: restore baseline source only in an isolated development reproduction; it knowingly reintroduces skipped records. There is no production deployment here, and no data migration or write endpoint.

Limits: public fixtures are not secure isolation or hidden evaluation. Read-only file adapter is not a SQL index/query-plan exercise. No authentication, performance calibration, real-world model scores, or human qualitative rubric scoring is asserted. Agent-controlled source must not be executed as untrusted code without an external sandbox. Compiler uses Java 21's bundled jdk.compiler module because javac launcher and ct.sym are absent in this environment.
