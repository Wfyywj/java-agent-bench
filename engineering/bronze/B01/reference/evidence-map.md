# Evidence to conclusions
- operations-mail.txt 08:12 host UTC vs Shanghai -> Site.zone, not systemDefault; verified persisted UTC instant.
- 08:31 shared capacity correction -> Scheduler count matches site + slot, ignores building; unknown states not treated as cancellation.
- Stale midnight example -> frozen start-date reply; cutoff test rejects 23:30 start after 17:00.
- Legacy error snapshot -> exact 422 INVALID_SLOT JSON; rejected requests leave file unchanged.
- Unapproved holidays -> POLICY_PENDING, not a fabricated holiday calendar.
Alternative server timezone and building-local capacity explanations are rejected by site configuration and later mail respectively.
