CLI Main loads a locked snapshot, delegates to the domain orchestration module, and persists through DurableState. Every CLI call is a separate JVM. Atomic snapshot replacement establishes process-restart semantics, not distributed atomicity.
Domain modules are deterministic local simulations; see original-contract.json for broader unimplemented requirements.
