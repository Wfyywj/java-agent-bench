Deterministic explicitly labeled simulation of stale two-level cache rules, duplicate acceptance, out-of-order projection, backlog and lock-pressure recovery; raw offset clocks and structured diagnosis.
Limitations: Metrics are simulation counters, not measured hardware/database performance. Fixed causal fixture is not production diagnosis generalization.
Recovery: retain state.properties and audit.log; invoke only fenced documented commands. Never delete unknown effects to retry. Real deployment needs separate infrastructure review and trials.
