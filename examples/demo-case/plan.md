# Investigation plan: Example Corp inc-0042

## 1. Review exposure of the ci-deployer access key
- Question. When did the key become public, and when was it first used from outside?
- Client claim. A `.env` file was pushed to the public mirror on 2026-09-12.
- Data. S2 github audit, S1 cloudtrail.
- Checks.
  - push events to `example-corp/deploy-scripts` on 2026-09-12;
  - first call with key `AKIA...EXMPL` after the push from a non-client IP.
- Result. Exposure start and first external use, UTC.

## 2. Review the actor's API activity
- Question. What did the actor do with the key?
- Data. S1 cloudtrail, S1 guardduty.
- Checks.
  - calls by key id, grouped by source IP and action;
  - error codes (AccessDenied) per action.
- Result. Table of actions with counts and window.

## 3. Review persistence
- Question. Did the actor create users, keys, roles or policies that survive the key revocation?
- Data. S1 cloudtrail.
- Checks.
  - IAM create / attach / put calls from 203.0.113.45;
  - use of any created identity.
- Result. List of created identities, their use, and removal.

## 4. Review data access in S3
- Question. Which objects did the actor read, and how much data left?
- Data. S1 s3 data events (`exampleco-customer-exports` only).
- Checks.
  - GetObject from 203.0.113.45, distinct keys, bytes out, prefixes.
- Result. Object count, volume, prefixes. Other buckets: data gap.

## 5. Review containment
- Question. Is the actor locked out?
- Data. S1 cloudtrail.
- Checks.
  - key deactivation and removal of created users;
  - actor calls after deactivation.
- Result. Done / still active, with the last check time.
