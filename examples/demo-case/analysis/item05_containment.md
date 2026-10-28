# Item 05. Review containment
Checked: 2026-09-14. Sources: S1. Times UTC.

## Question
Is the actor locked out?

## Client claim
The client deactivated the key at about 09:40 UTC on 2026-09-13.

## Source coverage
| Source | Window (UTC) | Newest event in source | Query (exact) | Result |
|---|---|---|---|---|
| S1 cloudtrail | 2026-09-13 - 2026-09-14 08:00 | 2026-09-14 07:58 | key and user changes (w11); actor calls after (w12, w14) | key inactive 09:41:12; 0 actor calls after 09:52:20 |
| S2 github audit | | | | n/a: no AWS events |

## Facts
- 2026-09-13 09:41:12 `sec-admin` set `AKIA...EXMPL` to Inactive (w11).
- 2026-09-13 09:47:55 `svc-backup-sync` key and user deleted (w11).
- 3 actor calls after deactivation, all `InvalidClientTokenId`, the last at 09:52:20 (w12).
- 0 actor events up to 2026-09-14 07:58 (w14).

## Status
Confirmed. The actor has no working credential in the logged region.
