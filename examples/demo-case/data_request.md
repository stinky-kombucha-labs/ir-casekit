# Data request: Example Corp, inc-0042

Prepared by the demo IR team on 2026-09-13. All times are UTC. Fictional data.

## Summary
| # | Gap | Data | Priority | Deadline |
|---|---|---|---|---|
| R1 | G1 | CloudTrail, all regions | P1 | 2026-09-15 (answers whether the persistence user was used) |
| R2 | G2 | S3 server access logs, other buckets | P1 | 2026-09-15 |

## Priority 1 (data theft, active access, retention-limited)

### R1 (G1) CloudTrail, all regions
- **Deadline:** 2026-09-15. Event history keeps 90 days, but the answer decides whether the incident is closed.
- **Why we need it:** to see whether `svc-backup-sync` or `AKIA...EXMPL` made calls outside eu-central-1 (item 03).
- **What we already have:** eu-central-1 in the SIEM (w2).
- **Where it lives:** AWS account 111122223333, CloudTrail event history in every enabled region.
- **Scope:** user names `ci-deployer`, `svc-backup-sync`; source IP 203.0.113.45.
- **Time window:** 2026-09-12 20:00 - 2026-09-13 10:00.
- **Fields we need:** full event JSON.
- **How to export:**
```bash
for r in $(aws ec2 describe-regions --query 'Regions[].RegionName' --output text); do
  aws cloudtrail lookup-events --region "$r" \
    --lookup-attributes AttributeKey=Username,AttributeValue=svc-backup-sync \
    --start-time 2026-09-12T20:00:00Z --end-time 2026-09-13T10:00:00Z \
    --output json > "R1_cloudtrail_${r}_svc-backup-sync.json"
done
```
- **Output:** one JSON file per region, no redaction needed.
- **Completeness check:** eu-central-1 must contain the CreateAccessKey event at 2026-09-12 21:19:31.
- **If it does not exist:** reply "no events" per region.

### R2 (G2) S3 server access logs, other buckets
- **Deadline:** 2026-09-15.
- **Why we need it:** ListBuckets ran 9 times; we cannot tell whether other buckets were read (item 04).
- **What we already have:** data events for `exampleco-customer-exports` only.
- **Where it lives:** server access log target bucket, if logging is on.
- **Scope:** every bucket in account 111122223333; requester IP 203.0.113.45.
- **Time window:** 2026-09-12 20:00 - 2026-09-13 10:00.
- **Fields we need:** time, bucket, key, operation, remote IP, bytes sent.
- **How to export:**
```bash
aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n' | \
  xargs -I{} aws s3api get-bucket-logging --bucket {}
```
- **Output:** raw log objects, `R2_s3access_<bucket>.log`.
- **Completeness check:** first and last timestamp per bucket.
- **If it does not exist:** reply "logging off" per bucket.

## Already have (no need to send)
- GitHub organization audit log: received 2026-09-14.
