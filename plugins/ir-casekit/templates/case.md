---
client: "<client>"
incident_id: "<id>"
opened_utc: "<YYYY-MM-DDTHH:MMZ>"
client_timezone: "<e.g. Europe/Kyiv, UTC+3>"
channel: "<slack channel / email thread>"
tickets: []
tracker_url: ""          # empty = local tracker.md in the case folder
work_mode: sequential    # sequential (one session, one source at a time) | parallel
# Report fields (ir-report). Fill when known; the portfolio report reads them.
severity: ""             # SEV-1 (highest) .. SEV-4
incident_type: ""        # e.g. Cloud credentials, Ransomware, BEC / M365, Malware on host
initial_access: ""       # e.g. Key in public repository, VPN account without MFA, Phishing (AiTM)
status: "open"           # open | contained | eradicated | recovered | closed
first_actor_activity_utc: ""   # first action by the actor in the client environment (sign-in, API call, process); not the delivery of a lure
detected_utc: ""               # earliest proof that the client or the SOC knew (alert, ticket, first response action such as a reset); not when we were told
contained_utc: ""              # when the actor lost every access the logs show; leave empty while persistence (rule, key, MFA method, implant) is not proven removed
closed_utc: ""
team:
  lead: "<name>"
  analysts: []
---

# Case: <client> <id>

## Trigger
<what started the case: alert, client message, CVE / advisory id. Link to sources/trigger_*.md>

## Scope hypothesis
- Entry point:
- Affected accounts / clusters / hosts:
- Status (active / stopped / unknown):

## In scope
- Cloud accounts:
- Clusters:
- Hosts:
- Repos:
- Applications / services:

## Data sources
| Name | Type | Covers | Access check |
|---|---|---|---|
| elastic-client | siem | <e.g. cloudtrail (management only), guardduty, falco syscall, github audit> | <OK / 403 + missing scope / not started> |
| falcon-mcp | edr | <e.g. hosts, detections, ngsiem base_sensor, fcs_csp_events, spotlight> | <...> |

## Client-only data
- <e.g. application access logs, ingress logs, EKS audit, SSM Run Command (30 days)>
