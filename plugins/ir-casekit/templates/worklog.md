# Worklog: <client> <incident-id>

Sequential mode. One session, one item and one source at a time. Write the plan line before the query, the result line right after it. Times UTC.

One row per query, also for errors, timeouts and empty results. Keep the result to the numbers and identifiers that change the next step; details go to the item file. Never paste secret values.

## Session plan
Order of work for this session. Tick a line only after its result is written below.

- [ ] Intake: access check per connector
- [ ] Intake: data inventory, source by source
- [ ] Plan: items written to plan.md
- [ ] Item 01 / source <name>
- [ ] Item 01 / source <name>
- [ ] ...
- [ ] Coverage matrix: no empty or error cell
- [ ] Containment check
- [ ] Data gaps: no open row, data request sent
- [ ] Tracker

## Log
| # | UTC | Item | Source | Query / action (exact) | Result (count, key values, or error) | Next |
|---|---|---|---|---|---|---|
| 1 | HH:MM | 00 | <connector / index / repo> | <query> | <result> | <what this changes> |
