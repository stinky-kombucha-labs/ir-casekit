# Item 01. Review exposure of the ci-deployer access key
Checked: 2026-09-14. Sources: S1, S2. Times UTC.

## Question
When did the key become public, and when was it first used from outside?

## Client claim
A `.env` file was pushed to the public mirror on 2026-09-12.

## Source coverage
| Source | Window (UTC) | Newest event in source | Query (exact) | Result |
|---|---|---|---|---|
| S2 github audit | 2026-09-10 - 2026-09-14 | 2026-09-14 06:55 | log-profile `--where action~^git.push` (w9) | 1 push, 2026-09-12 20:41:37 |
| S1 cloudtrail | 2026-09-12 20:41 - 2026-09-13 | 2026-09-13 08:12 | first call after push (w10) | 2026-09-12 21:07:44 from 203.0.113.45 |

## Facts
- 2026-09-12 20:41:37 `dev-jlee` pushed to the public repository `example-corp/deploy-scripts` (w9).
- 2026-09-12 21:07:44 first call with key `AKIA...EXMPL` from 203.0.113.45 (`GetCallerIdentity`), 26 minutes after the push (w10).

## Status
Confirmed. The push and the first external use are both logged.

## Needed from client
- none

## Recommendations
- Enable GitHub secret scanning with push protection on every public repository.
