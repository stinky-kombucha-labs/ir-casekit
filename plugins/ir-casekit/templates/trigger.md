# Trigger: <CVE / advisory / alert id>
Researched: <YYYY-MM-DD>. Sources: <primary first: vendor advisory, NVD/CVE record, CISA KEV, GHSA; then third party>.

## Summary
- Product and component:
- Affected versions / fixed version:
- Published (UTC):
- Severity (source):
- Preconditions (authentication, configuration, exposure):
- Public exploit / KEV listing / known exploitation:

## Attack path
1. <request or action the attacker sends>
2. <what the vulnerable component does with it>
3. <what the attacker gets: file write, command execution, data>

## Observable artifacts
Each row says where the artifact would be logged and whether we have that source (see item00).

| Stage | Artifact | Where it is logged | Field / value to search | Source available |
|---|---|---|---|---|
| Delivery | <HTTP method + path, parameter> | <web / ingress / app log> | <...> | <yes: connector / no: client only> |
| Execution | <process, parent, user> | <EDR / runtime security> | <...> | <...> |
| Persistence / config change | <file path> | <EDR file events / FIM> | <...> | <...> |
| Follow-on | <network, credentials, data> | <...> | <...> | <...> |

## Unverified points
- <anything taken only from an aggregator or a blog: mark [unverified] until a primary source confirms it>
