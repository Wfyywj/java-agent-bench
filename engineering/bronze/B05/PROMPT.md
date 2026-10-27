# B05 · Nursery tag import incident

The nursery's single-JVM CSV import stopped accepting uploads. The alert title says
“database timeout”. You have no production access. Investigate the supplied synthetic
incident evidence and repair **baseline/src** without changing the verifier. The
service owns the input stream passed to `Importer.run`, including failed imports.

## Inputs and work

- `evidence/incident.log`, `fd-samples.csv`, and `thread-dump.txt`: authored incident
  artifacts, not an actual production capture. Samples are cumulative importer-owned
  open handles, not total process descriptors.
- `evidence/normal.csv` and `malformed.csv`: synthetic reproductions.
- `baseline/src`: the existing command-line import adapter, parser, staging-file
  repository, and import service. `Main input.csv output.csv` is the operator entry.

Preserve the three-column `label,name,email` header in both input and committed output, and the single-physical-line CSV
contract. Quoted commas and doubled quotes are valid; multiline fields are not.
An import replaces the output atomically only after the complete input validates.
On invalid input, cancellation, or I/O failure leave the previous output untouched.
Labels match `[A-Z][A-Z0-9-]{0,31}` and are unique within the upload; name is nonblank;
email must contain `@` (this fixture does not promise RFC email validation).
Return stable `CSV_HEADER`, `CSV_SYNTAX`, `CSV_FIELDS`, `CSV_DUPLICATE`, `CANCELLED`,
or `OK` plus a one-based physical line and committed count. No raw row/PII in errors
or logs. I/O errors map to `IMPORT_IO` at the CLI. Close the owned input and clean
staging files on every exit. Preserve interruption-driven cancellation in the CLI.

Deliver a focused patch plus `requirement-decisions.md`, `evidence-map.md`,
`regression-tests/`, and `delivery-note.md`. Include `diagnosis.json` with the fields
`root_cause`, `database_timeout`, `evidence` (artifact/symbol references),
`excluded_remedy`, and `unproven` (array). Do not claim that an alert proves a DB
root cause, or claim production evidence you have not observed. Discuss alternatives.
The public verifier directory freezes structured evidence anchors; it is grading
material, not a stakeholder message. It remains public in this development set.

## Reproduction

`python3 engineering/bronze/B05/run_selfcheck.py` checks supplied baseline, reference,
and five semantic mutants in clean temporary directories. Java 21 with jdk.compiler
and Python 3.10+ only. Compile using `java -m jdk.compiler/com.sun.tools.javac.Main
-source 21 -target 21 -d /tmp/b05-classes baseline/src/*.java`, then invoke Main.
Use a fresh output directory; do not overwrite real files.

To evaluate a trusted solution directory containing `src/` and `diagnosis.json`,
run `python3 engineering/bronze/B05/run_selfcheck.py --candidate /path/to/solution`.
Structured diagnosis anchors are exact machine-readable values in
`verifier/diagnosis-contract.json`; prose quality is not automatically graded.

Resource tolerance is **zero** unclosed tracked input streams and **zero** leftover
`.import-*.tmp` files after 120 mixed successful/invalid imports. The deterministic
adapter is the primary resource oracle; no production FD limit or real DB timeout
is reproduced. Tests use actual temporary files and real Java I/O. This is trusted
local functional testing, **not a secure sandbox**, not hidden evaluation, and not
model scoring or difficulty calibration.

## Prepared workspace layout
The sanitized presentation copy contains `src/` (from repository `baseline/src/`), the prompt, task metadata, and the explicitly listed public input files under `evidence/`. It does not include the local evaluator, reference answers, verdict/diagnosis contracts, or selfcheck results. Run evaluation commands from the benchmark repository, passing this package root with `--candidate`. The original repository remains public; this is presentation separation, not a hidden or secure evaluation.
