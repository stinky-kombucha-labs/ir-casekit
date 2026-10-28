# Data gaps: Example Corp inc-0042

## Running list
| ID | Missing data | Needed for item(s) | Found (item, UTC) | Why missing | Proof of absence (sources and worklog rows) | Retention deadline | Status |
|---|---|---|---|---|---|---|---|
| G1 | CloudTrail for all regions except eu-central-1 | 03 | item00, 2026-09-13 08:20 | SIEM integration filtered to one region | S1 w2 | 90 days in CloudTrail event history (2026-12-11) | requested 2026-09-13 |
| G2 | S3 server access logs for buckets other than `exampleco-customer-exports` | 04 | item04, 2026-09-13 09:24 | data events enabled for one bucket only | S1 w7, w8 | none known | not available (client confirmed 2026-09-14: server access logging was off) |
| G3 | GitHub organization audit log 2026-09-10 to 2026-09-14 | 01 | item01, 2026-09-13 09:00 | not in the SIEM | S1 w1 | 180 days | received 2026-09-14 (`sources/client_export_2026-09-14/github_audit.jsonl`) |

## Onboarding for the future
| ID | Source | How to onboard (integration, collector, sensor, log setting) | Owner |
|---|---|---|---|
| G1 | CloudTrail, all regions | Use the organization trail for all regions in the SIEM integration | Client platform team |
| G2 | S3 data events | Enable data events (or server access logs) for every bucket with customer data | Client platform team |
