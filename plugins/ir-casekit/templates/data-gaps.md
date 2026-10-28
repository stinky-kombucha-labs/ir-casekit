# Data gaps: <client> <incident-id>

Living document. `ir-intake` seeds it from item00, `ir-plan` adds client-only data, `ir-investigate` adds a row whenever an item needs data that no source has, `ir-data-gaps` proves each row and turns it into `data_request.md`. Rows are never deleted; their status changes.

## Running list
| ID | Missing data (exact source, filters) | Needed for item(s) | Found (item, UTC) | Why missing | Proof of absence (sources and worklog rows) | Retention deadline | Status |
|---|---|---|---|---|---|---|---|
| G1 | <e.g. ingress access logs of host X> | <03, 06> | <item00, YYYY-MM-DD HH:MM> | <not in any connector / broken: fields empty / outside retention / host without sensor / client-only system> | <E1 w12, C2 w15> | <date or "none known"> | open |

Status values:
- `open`: found, not yet requested;
- `requested`: in `data_request.md` (date sent);
- `received`: the client sent it; say where it is now (`sources/...`, new index) and which items to reopen;
- `not available`: the client confirmed it does not exist; the items that need it become `Not determinable`.

## Onboarding for the future
| ID | Source | How to onboard (integration, collector, sensor, log setting) | Owner |
|---|---|---|---|
| G1 | <source> | <how> | <client team> |
