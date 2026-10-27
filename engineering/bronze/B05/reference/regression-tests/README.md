Execute `python3 engineering/bronze/B05/run_selfcheck.py` from repo root.
The independent Java verifier runs 28 assertions: six scenarios × four checks, an independent committed CSV/header/escaping assertion,
120-import zero-resource-tolerance, staging setup failure, and input read failure.
Diagnosis anchors cover A01/A05; executable lifecycle checks cover A02–A04.
No assertion is skipped for baseline or mutants; all must compile first.
