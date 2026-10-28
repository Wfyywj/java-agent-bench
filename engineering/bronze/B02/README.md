# B02 runnable local-adapter engineering fixture

Four cooperating Java files per variant: HTTP entrypoint, domain records, return service, durable snapshot repository. The deliberately faulty starter overwrites replay events and generates duplicate jobs. The reference checks the bound payload before the lifecycle gate and commits only a fully staged snapshot.

Run from any directory:

```sh
python3 /path/to/B02/run_selfcheck.py
```

To evaluate a trusted candidate independently:

```sh
mkdir -p /tmp/b02-classes
java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21 -d /tmp/b02-classes candidate/src/*.java
python3 verifier/check.py /tmp/b02-classes evidence/seed.tsv
```

The selfcheck uses clean temporary build/data directories, a 30-second subprocess deadline, 64 KiB combined-output cap, Java server startup and request deadlines, a 96 MiB server heap, and process-group cleanup. These are reliability limits, not a security boundary or complete CPU/disk quota. The compiler module invocation works on the provided Java 21 runtime where the `javac` launcher and `ct.sym` are absent; no Java version compatibility beyond 21 is claimed.

`verification-results.json` records the executed check outcomes; exact repeat equality is checked separately in `verification.md`. Reference results are not benchmark/model performance measurements. The public Python oracle reads HTTP responses and snapshots independently of the Java implementation; it never derives expected results by calling the reference.

See prompt.md for exact scope limitations, especially the missing PostgreSQL acceptance layer.

## Candidate package evaluation

`python3 engineering/bronze/B02/run_selfcheck.py --candidate /absolute/path/to/package`

The package contains `src/`; compilation uses a fresh temporary directory with annotation processing disabled. Existing class files are never reused. Results distinguish build failure from functional failure; infrastructure/input errors exit 2.

The verifier distinguishes `FAIL:` business assertions from `ERROR:` infrastructure exceptions; infrastructure errors are not semantic mutant kills. Classification regression: `python3 -m unittest discover -s tests -p 'test_b02_failure_classes.py' -v` from repository root.
