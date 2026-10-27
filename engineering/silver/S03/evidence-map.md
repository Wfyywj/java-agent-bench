# Evidence map

Main create/download -> ExportPolicy.allowed; ExportWorker.execute uses explicit owner/tenant; Store.commit writes object payload.

Cached authorization at creation is not valid at download after revocation; formula data escaping is separate from authorization.

`fixtures/cases.json` maps each scenario to original acceptance IDs, but passing mapped assertions only covers the narrowed executable slice, not the entire criterion. Actual outcomes: `evidence/selfcheck.json`. All source variants are compiled independently. Three reference runs repeat acceptance outcomes; S04 intentionally allows either legal concurrent winner.

Unmeasured: CLI rather than REST/object-store URLs; principal is trusted adapter input, not authentication. No real object-storage signing, HTTP non-enumeration policy, cross-process worker pool or external IAM.
