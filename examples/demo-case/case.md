---
client: "Example Corp"
incident_id: "inc-0042"
opened_utc: "2026-09-13T08:10Z"
client_timezone: "Europe/Berlin, UTC+2"
channel: "#inc-0042 (fictional)"
tickets: []
tracker_url: ""
work_mode: sequential
severity: "SEV-2"
incident_type: "Cloud credentials"
initial_access: "Key in public repository"
status: "contained"
first_actor_activity_utc: "2026-09-12T21:07:44Z"
detected_utc: "2026-09-13T07:52Z"
contained_utc: "2026-09-13T09:41:12Z"
closed_utc: ""
team:
  lead: "Demo Analyst"
  analysts: []
---

# Case: Example Corp inc-0042

> Fictional case. Every name, account ID, IP address (RFC 5737 ranges) and domain (`example.*`) is invented to show how the kit works. It describes no real company or incident.

## Trigger
GuardDuty finding `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS` style alert on 2026-09-13 07:52 UTC for the IAM user `ci-deployer` in account `111122223333`. The client's platform team reported that the user's access key may have been committed to a public repository. Raw message: `sources/slack_inc-0042_2026-09-13.md`.

## Scope hypothesis
- Entry point: long-term access key of IAM user `ci-deployer` (key id `AKIA...EXMPL`) pushed to a public GitHub repository on 2026-09-12.
- Affected accounts / clusters / hosts: AWS account `111122223333` (eu-central-1); S3 bucket `exampleco-customer-exports`.
- Status (active / stopped / unknown): stopped since 2026-09-13 09:41 UTC (key deactivated, see item05).

## In scope
- Cloud accounts: 111122223333
- Clusters: none
- Hosts: none
- Repos: example-corp/deploy-scripts (public mirror)
- Applications / services: S3, IAM, STS

## Data sources
| Name | Type | Covers | Access check |
|---|---|---|---|
| siem-demo | siem | CloudTrail management events eu-central-1, S3 data events for `exampleco-customer-exports`, GuardDuty | OK (w1) |
| github audit export | file | Organization audit log 2026-09-10 to 2026-09-14 | received 2026-09-14 (w9) |

## Client-only data
- CloudTrail for regions other than eu-central-1 (not collected by the SIEM).
