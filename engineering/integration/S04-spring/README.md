# S04 — real Spring transaction integration

An additional **narrowed integration variant**, not a replacement for catalog S04 or a claim of full-catalog readiness. Actual Spring 6.2.12 `AnnotationConfigApplicationContext`, CGLIB transaction proxy, `@Transactional`, `DataSourceTransactionManager`, `JdbcTemplate`, and H2 2.3.232. No handwritten proxy or transaction imitation.

## Reproduce

Requires Python 3 and Java 21 including `jdk.compiler` (the current runtime has this module but no `javac` launcher).

```sh
python3 tools/bootstrap.py       # first time: official Maven Central only
python3 run_selfcheck.py         # subsequent compile/test runs are offline
python3 run_selfcheck.py --candidate /absolute/path/to/package
```

`pom.xml` documents every exact dependency; `dependencies.lock.json` freezes the 11 jars with official URLs and SHA-256. Maven is not installed or required; the Maven lifecycle was **not tested**. Canonical compilation uses `java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21` (this runtime lacks release-symbol metadata). No system installations/settings, Docker, external service, model call, or publication.

The candidate package contains exactly the five `src/bench/*.java` files enumerated by `agent-files.json`. The export whitelist also includes the public `PROMPT.md` briefing, but no reference answers or evaluator tests. The Java source-to-target entries are the compilation whitelist; the evaluator rejects missing/extra source files and symlinks, stages only listed sources, and compiles them with evaluator-owned configuration and SQL assertions. Extra documentation outside `src` is ignored. It never copies candidate tests, build hooks or dependencies. `--candidate` uses the same real checks, not selfcheck labels. Candidate execution is for reviewed/trusted local code only: **not a hostile-code sandbox**. Java has ordinary process privileges; external evaluation needs OS/network/filesystem isolation.

## Business and concurrency contract

Cancel is all-or-nothing for the batch, including checked domain errors. Already-cancelled rows do not release stock again. Any delivered row rejects and rolls back the whole batch. Delivery cannot follow cancellation, and does not return reserved stock. Both operations serialize on one batch row, not an order table/global lock. Distinct batches sharing a SKU add inventory through SQL arithmetic to prevent stale-read overwrite. Fixtures use exact integer units; initial SKU 1 available 11 + reserved 9 = total 20; SKU 2 available 9 + reserved 1 = 10.

The baseline retains the annotation on `cancelInside` but removes it on external `cancel`: real Spring same-object self-invocation bypasses transaction advice. Reference places the transaction on the external entry and explicitly rolls back `BusinessFailure`. Runtime and checked fault injection occurs after actual JDBC writes.

## Verification

20 independent checks in `regression-tests/bench/IntegrationVerifier.java`; state expectations come from fixed business fixtures/direct SQL, not reference-generated answers. Tests call the actual context bean. Separate JDBC connection `FOR UPDATE NOWAIT` proves the batch row lock is held; callback verifies active Spring transaction. Concurrency uses latches/barriers and separate JDBC connections. The shared-SKU stale-read schedule is forced before either increment, deterministically killing lost-update writes. Two ordered races force cancellation-first and delivery-first outcomes. The global-lock rejection uses a 2-second bounded progress deadline, not a performance score; overloaded machines may need calibration.

Selfcheck requires baseline to compile but fail, reference to pass three runs, and all ten compiling mutants to fail. `evidence/selfcheck.json` captures commands, source digests, outputs and durations; `evidence/candidate-reference.json` records a separate candidate run. The public tests are **not hidden evaluation** and do not prove anti-overfitting. Mutants: self-invocation, default checked rollback, swallowing checked failure, repeated release, allowing delivered rows, stale inventory overwrite, missing batch row lock, global batch locking, and early return at cancelled/delivered prefixes. Mixed pre-cancelled + pending/delivered fixtures cover continued processing, required rejection and late failure rollback. Mixed delivered-prefix fixtures also enforce processing/rejection of later rows.

## Explicit gaps

H2 is not PostgreSQL: no PostgreSQL execution, lock/isolation/deadlock parity, driver behavior, migration compatibility or production load claim. `JdbcDataSource` opens independent connections, not a bounded production pool; pool exhaustion/timeouts remain untested. No HTTP/controller/auth, persistence across process restart, deadlock retry, mixed SKU cancellation ordering or broad randomized schedule coverage. This variant deliberately requires per-batch pessimistic locking; it is not a universal oracle for alternative optimistic implementations. Spring 6.2.12 is a reproducibility pin, not a latest-version or security recommendation.

Official documentation consulted:
- https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/annotations.html (external proxy entry vs self-invocation)
- https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html (checked exceptions need rollback rules)
- https://h2database.com/html/advanced.html (H2 transaction/isolation limits)
