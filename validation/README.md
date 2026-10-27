# Validation evidence

Local logs are development checks, not evaluated-model results. `engineering-selfchecks-initial.txt` preserves an actual failed integration attempt caused by a wrong aggregate entrypoint; the corrected aggregate is rerun separately. Individual task evidence distinguishes baseline, reference and seeded wrong implementations.

Unit tests for web code use a Node VM with a deliberately limited DOM stub. They are not real-browser/layout/accessibility verification. Managed preview startup timed out, and the deployed private site requires user login in the cloud browser. Deployment success does not erase this UI verification gap.

GitHub Actions, when present, must be checked on the exact pushed commit. Empty statuses are not a passing run. No secrets, paid model calls or model rankings are included.

The final 25-task aggregate returned exit 0. S05 was then rechecked after the JDBC-observation/boundary audit fix (`s05-final-audit-regression.txt`); its updated 9-case reference passes all three runs. The additional real Spring variant is checked separately in `spring-final-selfcheck.txt`. Local unit suite currently 34 tests; web handler/data-shape suite 14 tests. These counts are test gates, not model scores.
