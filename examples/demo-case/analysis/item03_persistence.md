# Item 03. Review persistence
Checked: 2026-09-13. Sources: S1. Times UTC.

## Question
Did the actor create users, keys, roles or policies that survive the key revocation?

## Client claim
none

## Source coverage
| Source | Window (UTC) | Newest event in source | Query (exact) | Result |
|---|---|---|---|---|
| S1 cloudtrail | 2026-09-12 - 2026-09-13 | 2026-09-13 08:12 | IAM create / attach calls (w5); use of new user (w6) | 1 user, 1 key, 0 uses in eu-central-1 |
| S2 github audit | | | | n/a: no AWS IAM events |

## Facts
- 2026-09-12 21:19:10 CreateUser `svc-backup-sync` (w5).
- 2026-09-12 21:19:31 CreateAccessKey for `svc-backup-sync` (w5).
- 2026-09-12 21:20:02 AttachUserPolicy AdministratorAccess failed with AccessDenied (w5).
- 0 calls by `svc-backup-sync` in eu-central-1 on a filled `user_name` field (w6).

## Status
Partially. The identity and its key are known and removed (item05). Use outside eu-central-1 cannot be checked without G1.

## Needed from client
- G1 CloudTrail for all regions, 2026-09-12 20:00 to 2026-09-13 10:00.

## Hypotheses
- [hypothesis] The key of `svc-backup-sync` was not used in other regions (G1 would confirm).
