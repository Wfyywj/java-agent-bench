# Requirements and stakeholder decisions
Operations mail conflicts on per-building versus shared capacity and labels midnight-ending visits with the wrong date. The frozen facilitator reply establishes site + slot capacity and start-date ownership. This reference is authored after that reply; candidate agents must explicitly request it, not claim a nonexistent conversation.

Today means the configured zone date; same-day booking window is [midnight,17:00), and appointment start must be strictly after Clock.now. Unknown occupancy statuses reserve capacity. Missing site zone and DST ambiguous/nonexistent wall times reject. Holiday opening remains unresolved: POLICY_PENDING, no booking. Optional note omission remains accepted. See decisions.json for machine-readable decision table.
