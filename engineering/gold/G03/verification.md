# Executed verification

Reference: INVARIANTS=31 FAILURES=0; three fresh compile/workdir repeats.
All 8 negative variants rejected behaviorally in each repeat; compilation failure never counts as mutation detection.

| Variant | Results over three runs |
|---|---|
| reference | PASS x3 |
| baseline | REJECT x3: FAIL duplicate different content conflict |
| mutant_duplicate_overwrite | REJECT x3: FAIL duplicate different content conflict |
| mutant_trust_disk | REJECT x3: FAIL disk tampering detected |
| mutant_ignore_signature | REJECT x3: FAIL bad signature; FAIL cross session signature; FAIL wrong HMAC key v1; FAIL wrong HMAC key v2 |
| mutant_reverse_assembly | REJECT x3: exception on violated independent request contract |
| mutant_fixed_hmac_key | REJECT x3: exception on violated independent request contract |
| mutant_constant_hash | REJECT x3: exception on violated independent request contract |
| mutant_v2_legacy_canonical | REJECT x3: exception on violated independent request contract |

## Independent oracle correction
The original suite had a common-mode flaw: it built signed requests through candidate Signing methods. Independent audit proved a fixed-key implementation survived. This was a real verifier false positive, not a reference failure. The previous 20-invariant report is superseded.
Every accepted fragment digest/HMAC is now a literal generated with Python standard-library hashlib/hmac. Direct known-answer checks cover SHA256, protocol v1/v2 canonical forms and two distinct signing keys; independent wrong-key requests must reject. New fixed-key, constant-digest and legacy-v2 mutants are retained.
Run `python3 verifier/generate_crypto_vectors.py` to independently audit frozen vector provenance. `fixtures/crypto-vectors.json` and the generator are immutable evaluator fixtures, not staged agent input.

Full evidence: verification-results.json. Public development checks only; no hidden holdout or production integration claim.
