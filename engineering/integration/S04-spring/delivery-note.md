# Delivery

Scope: only engineering/integration/S04-spring. No central catalog, ranking, packaging, other task or remote publication changed. Source snapshots, independent verifier, whitelist, lock, manifest and captured execution evidence are included.

Revert/remove this directory to roll back the additional variant; no external service or schema is deployed. Jars are cached outside the source tree at `/tmp/java-agent-bench-s04-spring-deps` (override with `S04_SPRING_DEPS`). Fresh users fetch checksum-locked jars from Maven Central; subsequent tests do not fetch dependencies. Frozen checksums establish reproducibility, not independent publisher-signature verification.

Known gaps and trust boundaries are in README.md. This is an executable public integration pilot, not a PostgreSQL production qualification, secret test suite, adversarial execution sandbox, model benchmark result or security audit.
