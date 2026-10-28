# Worklog: Example Corp inc-0042

Sequential mode. One session, one item and one source at a time. Times UTC. Fictional data.

## Session plan
- [x] Intake: access check per connector
- [x] Intake: data inventory, source by source
- [x] Plan: items written to plan.md
- [x] Item 01 / S2 github audit
- [x] Item 01 / S1 cloudtrail
- [x] Item 02 / S1 cloudtrail
- [x] Item 03 / S1 cloudtrail
- [x] Item 04 / S1 s3 data events
- [x] Item 05 / S1 cloudtrail
- [x] Coverage matrix: no empty or error cell
- [x] Containment check
- [x] Data gaps: no open row, data request sent
- [x] Tracker

## Log
| # | UTC | Item | Source | Query / action (exact) | Result (count, key values, or error) | Next |
|---|---|---|---|---|---|---|
| 1 | 08:14 | 00 | S1 siem | `FROM logs-aws.cloudtrail-* \| STATS MIN(@timestamp), MAX(@timestamp), COUNT(*)` | 2026-06-01 00:00 to 2026-09-13 08:12, 41 882 310 events | Source fresh; use for items 01-05 |
| 2 | 08:20 | 00 | S1 siem | `FROM logs-aws.cloudtrail-* \| STATS COUNT(*) BY cloud.region` | eu-central-1 only (41 882 310) | Other regions missing: G1 |
| 3 | 08:31 | 02 | S1 siem | `FROM logs-aws.cloudtrail-* \| WHERE aws.cloudtrail.user_identity.access_key_id == "AKIA...EXMPL" \| STATS COUNT(*) BY source.ip` | 203.0.113.45: 1 214; 198.51.100.7: 37 (client CI runner) | 203.0.113.45 is not a client address; pivot |
| 4 | 08:40 | 02 | S1 siem | `... WHERE source.ip == "203.0.113.45" \| STATS MIN(@timestamp), MAX(@timestamp), COUNT(*) BY event.action \| SORT COUNT(*) DESC` | 1 214 calls 2026-09-12 21:07:44 to 2026-09-13 09:38:02; GetObject 1 090, ListObjectsV2 61, ListBuckets 9, GetCallerIdentity 6, CreateUser 1, CreateAccessKey 1, AttachUserPolicy 1 (AccessDenied), other 45 | Items 03 and 04 |
| 5 | 08:52 | 03 | S1 siem | `... WHERE event.action IN ("CreateUser","CreateAccessKey","AttachUserPolicy","PutUserPolicy","CreateLoginProfile") AND @timestamp >= "2026-09-12"` | CreateUser `svc-backup-sync` 2026-09-12 21:19:10; CreateAccessKey for it 21:19:31; AttachUserPolicy AdministratorAccess 21:20:02 AccessDenied | New user is persistence; check its use |
| 6 | 09:03 | 03 | S1 siem | `... WHERE aws.cloudtrail.user_identity.user_name == "svc-backup-sync" \| STATS COUNT(*) BY source.ip, event.action` | 0 events on a filled field (user_name filled in 100% of IAM user events, w2 window) | Key created, never used in eu-central-1 |
| 7 | 09:15 | 04 | S1 siem | `FROM logs-aws.cloudtrail-* \| WHERE event.action == "GetObject" AND source.ip == "203.0.113.45" \| STATS COUNT_DISTINCT(aws.s3.object.key), SUM(aws.cloudtrail.additional_eventdata.bytes_transferred_out)` | 1 090 GetObject on 1 090 distinct keys, 2.31 GB out, all in `exampleco-customer-exports/2026/` | Data was read; tell the client today |
| 8 | 09:24 | 04 | S1 siem | `... WHERE event.action == "GetObject" AND source.ip == "203.0.113.45" \| STATS COUNT(*) BY aws.s3.object.key_prefix` | `2026/07/` 512, `2026/08/` 578 | Months July and August 2026 |
| 9 | 09:30 | 01 | S2 github audit | `log-profile.py sources/client_export_2026-09-14/github_audit.jsonl --where action~^git.push --where repo~deploy-scripts --keep @timestamp,actor,repo,action` | 1 push to example-corp/deploy-scripts 2026-09-12 20:41:37 by `dev-jlee`; repo public since 2025-11-02 | Exposure start 20:41:37 |
| 10 | 09:36 | 01 | S1 siem | `... WHERE aws.cloudtrail.user_identity.access_key_id == "AKIA...EXMPL" AND @timestamp >= "2026-09-12T20:41:37" \| SORT @timestamp \| LIMIT 1` | First external call 2026-09-12 21:07:44 from 203.0.113.45 (GetCallerIdentity) | 26 minutes from push to first use |
| 11 | 09:44 | 05 | S1 siem | `... WHERE event.action IN ("UpdateAccessKey","DeleteAccessKey","DeleteUser") AND @timestamp >= "2026-09-13"` | UpdateAccessKey Inactive `AKIA...EXMPL` 09:41:12 by `sec-admin`; DeleteAccessKey + DeleteUser `svc-backup-sync` 09:47:55 | Containment confirmed |
| 12 | 10:30 | 05 | S1 siem | `... WHERE source.ip == "203.0.113.45" AND @timestamp > "2026-09-13T09:41:12" \| STATS COUNT(*) BY event.action, aws.cloudtrail.error_code` | 3 calls after deactivation, all `InvalidClientTokenId`; none after 09:52:20 | Actor locked out |
| 13 | 10:41 | 02 | S1 siem | `FROM logs-aws.guardduty-* \| WHERE @timestamp >= "2026-09-12" \| STATS COUNT(*) BY rule.name` | 2 findings, both for `ci-deployer` from 203.0.113.45, first 2026-09-13 07:52 | Detection delay about 10.7 h |
| 14 | 11:05 | 05 | S1 siem | `FROM logs-aws.cloudtrail-* \| WHERE source.ip == "203.0.113.45" AND @timestamp > "2026-09-13T09:52:20"` (re-run at 2026-09-14 08:00) | 0 events; newest event in source 2026-09-14 07:58 | No return in 22 h |
| 15 | 11:20 | 02 | S1 siem | `FROM logs-aws.cloudtrail-* \| WHERE source.ip == "203.0.113.45" \| EVAL hour = DATE_TRUNC(1 hour, @timestamp), kind = CASE(event.action == "GetObject", "GetObject", "other") \| STATS COUNT(*) BY hour, kind` | 13 hours 2026-09-12 21:00 to 2026-09-13 09:00. GetObject per hour: 64, 112, 98, 41, 12, 0, 0, 38, 96, 104, 131, 187, 207 (1 090). Other: 96, 6, 4, 2, 0, 0, 0, 3, 4, 3, 2, 2, 2 (124). No calls 02:00 to 03:59 | Hourly chart for the report |
| 16 | 11:26 | 04 | S1 siem | `... WHERE event.action == "GetObject" AND source.ip == "203.0.113.45" \| EVAL mb = aws.cloudtrail.additional_eventdata.bytes_transferred_out / 1048576 \| EVAL bucket = CASE(mb < 0.5, "<0.5", mb < 1, "0.5-1", mb < 2, "1-2", mb < 4, "2-4", ">4") \| STATS COUNT(*) BY bucket` | <0.5 MB 190, 0.5-1 MB 241, 1-2 MB 352, 2-4 MB 268, >4 MB 39 (1 090) | Object size chart for the report |
