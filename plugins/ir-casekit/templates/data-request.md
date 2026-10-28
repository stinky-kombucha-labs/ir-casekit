# Data request: <client>, <incident>

Prepared by <team> on <YYYY-MM-DD>. All times are UTC.

## How to use this document
- Each request (R1, R2, ...) stands on its own: what we need, why, where the data lives, exact identifiers and window, export commands, output format and a completeness check. An engineer or an AI agent can run it without asking us.
- Run the requests in the order listed. Priority 1 is sorted by deadline.
- If a log source was never enabled, or its retention has passed, reply "not enabled" or "retention passed" with the date. We will record the question as not determinable.
- Output rules for every request: raw records (not screenshots or summaries); JSONL or CSV, one file per source, UTC timestamps; IPs, account IDs, ARNs, instance IDs, pod names and commit SHAs unredacted; secret values replaced with `<redacted>` unless the request says otherwise; file name `R<N>_<source>_<from>_<to>.<ext>`; delivery through the agreed secure share, never chat or email.
- For each file, send the query or command you ran, the first and last timestamp and the line count.

## Summary
| # | Gap | Data | Priority | Deadline |
|---|---|---|---|---|
| R1 | G<N> | <short name> | P1 | <date and reason> |

## Priority 1 (data theft, active access, retention-limited)

### R1 (G<N>) <short name>
- **Deadline:** <date and the reason, for example "SSM keeps command history 30 days">
- **Why we need it:** <the open question in plain words, the plan item, and what each possible answer changes for the client>
- **What we already have:** <source, window, why it is not enough>
- **Where it lives:** <system, account ID, region, cluster, log group / bucket / Loki labels / repository / host; the command that finds a name we do not know>
- **Scope:** <exact identifiers: instance IDs, command IDs, pods, namespaces, service accounts, role ARNs, token IDs, SHAs, hosts, IPs>
- **Time window:** <from - to, UTC>
- **Fields we need:** <list>
- **How to export:**
```bash
<ready-to-run commands with every identifier filled in>
```
- **Output:** <format, file name, redaction rule>
- **Completeness check:** <first and last timestamp, line count, an event that must be present>
- **If it does not exist:** <what to tell us>

## Priority 2 (scope and root cause)

### R<N> (G<N>) <short name>
<same fields>

## Already have (no need to send)
- <data>: we have it in <source>.
