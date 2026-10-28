# Item 02. Review the actor's API activity
Checked: 2026-09-13. Sources: S1. Times UTC.

## Question
What did the actor do with the key?

## Client claim
none

## Source coverage
| Source | Window (UTC) | Newest event in source | Query (exact) | Result |
|---|---|---|---|---|
| S1 cloudtrail | 2026-09-12 - 2026-09-13 09:38 | 2026-09-13 08:12 | calls by key id and source IP (w3, w4) | 1 214 calls from 203.0.113.45 |
| S1 guardduty | 2026-09-12 - 2026-09-13 | 2026-09-13 08:12 | findings by rule (w13) | 2 findings, first 07:52 |
| S2 github audit | | | | n/a: GitHub audit holds no AWS API calls |

## Facts
- 1 214 calls from 203.0.113.45 between 2026-09-12 21:07:44 and 2026-09-13 09:38:02 (w4).
- GetObject 1 090, ListObjectsV2 61, ListBuckets 9, GetCallerIdentity 6, CreateUser 1, CreateAccessKey 1, AttachUserPolicy 1 (AccessDenied), other 45 (w4).
- 37 calls from 198.51.100.7 belong to the client's CI runner (w3).
- GuardDuty raised the first finding at 2026-09-13 07:52, about 10.7 h after first use (w13).

## Status
Confirmed.

## Recommendations
- Alert on any use of long-term IAM user keys from IPs outside the CI runner range.
