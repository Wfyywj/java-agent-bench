# G05 — bounded executor starvation and cancellation

Status: **runnable_slice**, not full catalog ready. Java 21, standard library only.
Three separately compiled implementation modules: API, synthetic resource-owning
seat client, gateway implementation; independent verifier compiled afterward.

```
python selfcheck.py --write-evidence             # all variants, 3 clean repeats
python selfcheck.py --variant reference --repeats 1
python3 run_selfcheck.py --candidate /absolute/path/to/trusted/package
```

Every run compiles into a new temporary workspace using
`java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21`; this runtime
has no usable `--release 21` symbol archive. Compilation has a 30-second process
limit; verification 60 seconds; incident 10 seconds; each process output is capped
at 128 KiB. JVM verification heap is capped at 96 MiB. Tests need no network.
Timeouts and output caps are **not a security sandbox**. Never run untrusted
candidate code under an account with secrets or broad filesystem/network access;
use a disposable OS/container isolation boundary with CPU, memory, process,
filesystem and network restrictions. This runner executes arbitrary Java.

`verification-results.json` contains actual individual repeat outputs. These are
public development checks, no hidden tests or model scores. `fixture-lock.json`
freezes the contract and verifier; it is integrity checking, not tamper-proofing
against an attacker who can modify the runner and lock together.
