# Evidence map
- B03-A01: PageService comparator and directional reversal; verifier `ordering` independently sorts the CSV in Python, for asc/desc and all/READY/HOLD.
- B03-A02: CSV contains 12 rows at each second. `ties` uses limit=3 and checks all 36 north IDs exactly once. Baseline visits only nine records.
- B03-A03: Cursor.decode catches malformed format/version/date and Server translates exceptions to the existing 400 body; `malformed` uses five independent invalid tokens.
- B03-A04: Cursor.decode compares all three request-context fields; `binding` replays each changed context separately.
- B03-A05: BoxRepository reloads every request; `changing` deletes a consumed row, adds before/after keys and independently predicts suffix membership. Empty and terminal pages checked.
- Ingestion loss ruled out by complete CSV; retry or increasing page size does not repair comparator incompleteness. No evidence of database failure is supplied.
