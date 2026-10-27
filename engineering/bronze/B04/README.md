# B04: quotation PR review development package

`python run_selfcheck.py` builds candidate and maintainer-corrected Java modules in clean temporary directories. Java 21's compiler module is invoked directly (this environment has no `javac` launcher/`ct.sym`; `-source 21 -target 21` is used). Python 3 standard library only; no dependencies/network installation.

- `baseline/src/`: five-file candidate PR snapshot to review, **not** to modify as an agent submission.
- `reference/src/`: separate maintainer correction, not a changed pricing policy.
- `evidence/`: synthetic PR, policy, before-PR source, diagnostic smoke artifact, actual selfcheck JSON transcripts.
- `verifier/check.py`: independent Python Decimal model plus frozen verdict-anchor validation.
- `reference/review.json` / `review.md`: structured review and human-readable exemplar.
- `regression-tests/smoke.py`: demonstrates why the candidate's original smoke test misses the defects.

Acceptance mapping is in `reference/evidence-map.md`. Selfcheck verifies 39 decimal/boundary scenarios, all four concrete review counterexamples, negative/overflow non-defects, baseline review rejection, corrected review acceptance, four semantic Java mutants and one false-positive review mutant. It runs with a 20-second per-process timeout, capped JVM heap, 64 KiB per output stream and temp-directory cleanup. These controls are **not secure sandboxing**; do not run untrusted code without external OS/container isolation.

No real PR, payment, production customer, deployment, model score, or hidden holdout is involved. Review prose nuance and novel findings still require human review; exact public structured anchors are a calibration mechanism, not a claim to grade all legitimate reviews. Transport is a stdin/stdout adapter rather than HTTP. No database or distributed state is involved in this task.

## Candidate package evaluation

`python3 engineering/bronze/B04/run_selfcheck.py --candidate /absolute/path/to/package`

The package contains `review.json`. This evaluates frozen structured review anchors only; it does not compile submitted source, require repair of the reviewed PR, or automatically judge prose/novel findings. Invalid inputs exit 2, measured review failures exit 1.
