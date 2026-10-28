# Item 00. Data inventory: Example Corp inc-0042
Checked: 2026-09-13. Times UTC.

| # | Connector | Index / repo / file | What it logs | Oldest event | Newest event | Hosts / services / accounts covered | Incident questions it can answer | Gaps (filtered fields, missing hosts, sampling) |
|---|---|---|---|---|---|---|---|---|
| S1 | siem-demo | logs-aws.cloudtrail-*, logs-aws.guardduty-* | CloudTrail management events, S3 data events for one bucket, GuardDuty findings | 2026-06-01 00:00 | 2026-09-13 08:12 | account 111122223333, eu-central-1 | 01-05 | eu-central-1 only (w2); S3 data events only for `exampleco-customer-exports` |
| S2 | file | sources/client_export_2026-09-14/github_audit.jsonl | GitHub organization audit log | 2026-09-10 03:50 | 2026-09-14 09:25 | org example-corp | 01 | none found |

## Not present in any connector
- CloudTrail for regions other than eu-central-1 (G1).
- S3 data events for buckets other than `exampleco-customer-exports` (G2).

## Connector notes
- The SIEM CloudTrail integration is filtered to one region; `cloud.region` has a single value (w2).
