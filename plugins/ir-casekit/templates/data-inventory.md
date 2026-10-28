# Item 00. Data inventory: <client> <incident-id>
Checked: <YYYY-MM-DD>. Times UTC.

One row per index / data stream / repository / exported file. "Newest event" comes from a query, not from the index name.

| # | Connector | Index / repo / file | What it logs | Oldest event | Newest event | Hosts / services / accounts covered | Incident questions it can answer | Gaps (filtered fields, missing hosts, sampling) |
|---|---|---|---|---|---|---|---|---|
| 1 | <elastic-client> | <logs-x-default> | <...> | <UTC> | <UTC> | <...> | <plan item numbers or questions> | <...> |

## Not present in any connector
- <source the incident needs that no connector has, e.g. web server access logs of the vulnerable service>

## Connector notes
- <API limits, hidden indices, timeouts, scopes that returned 403>
