# Evidence map
- `evidence/incident.log`: synthetic response-loss retry correlates with two cleaning rows but one event. This excludes a necessary second cabinet action; it does not independently establish production causes.
- `baseline/src/ReturnService.java::submit`: repeat CLEANING lifecycle accepted, event overwritten, cleaning appended. Explains observed duplicate job without needing a parser bug.
- `reference/src/ReturnService.java::submit`: payload-bound replay, lifecycle gate and staged publication.
- `reference/src/Store.java::commit`: same snapshot contains loan/event/jobs; atomic rename publishes them together. Not evidence of PostgreSQL transaction behavior or fsync durability.
- `verifier/check.py`: independent HTTP/snapshot assertions for all five acceptance IDs, with A03/A05 restricted to local-adapter scope.
