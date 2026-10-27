# Evidence map

sdk Client.wire -> gateway Gateway.forward -> service Eligibility.decide; contract/eligibility.schema.json is source definition; no generated sources are present.

Client-trust bypass grants STUDENT to bob without owned entitlement; legacy-precedence mutation ignores explicit empty/new fields.

`fixtures/cases.json` maps each scenario to original acceptance IDs, but passing mapped assertions only covers the narrowed executable slice, not the entire criterion. Actual outcomes: `evidence/selfcheck.json`. All source variants are compiled independently. Three reference runs repeat acceptance outcomes; S04 intentionally allows either legal concurrent winner.

Unmeasured: No real separate Git histories, remote HTTP schemas, generated client runtime, deployed telemetry, or rolling production experiment.
