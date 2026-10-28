# Evidence map
- `evidence/incident.log`: synthetic response-loss retry correlates with two cleaning rows but one event. This excludes a necessary second cabinet action; it does not independently establish production causes.
- `baseline/src/ReturnService.java::submit`: repeat CLEANING lifecycle accepted, event overwritten, cleaning appended. Explains observed duplicate job without needing a parser bug.
- `reference/src/ReturnService.java::submit`: payload-bound replay, lifecycle gate and staged publication.
- `reference/src/Store.java::commit`: same snapshot contains loan/event/jobs; atomic rename publishes them together. Not evidence of PostgreSQL transaction behavior or fsync durability.
- `verifier/check.py`: independent HTTP/snapshot assertions for all five acceptance IDs, with A03/A05 restricted to local-adapter scope.
- `B02-A04_equipment_binding_false/true`: first-use wrong equipment must return `409 NOT_RETURNABLE` without any snapshot effects, including after restart; correcting the same token must succeed exactly once. `wrong_equipment_binding` deletes only the corresponding guard.
