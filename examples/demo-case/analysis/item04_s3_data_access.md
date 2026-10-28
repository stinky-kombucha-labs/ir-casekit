# Item 04. Review data access in S3
Checked: 2026-09-13. Sources: S1. Times UTC.

## Question
Which objects did the actor read, and how much data left?

## Client claim
none

## Source coverage
| Source | Window (UTC) | Newest event in source | Query (exact) | Result |
|---|---|---|---|---|
| S1 s3 data events | 2026-09-12 - 2026-09-13 | 2026-09-13 08:12 | GetObject distinct keys and bytes (w7); by prefix (w8) | 1 090 objects, 2.31 GB |
| S2 github audit | | | | n/a: no S3 events |

## Facts
- 1 090 GetObject calls on 1 090 distinct objects in `exampleco-customer-exports/2026/`, 2.31 GB sent out (w7).
- Prefix `2026/07/` 512 objects, `2026/08/` 578 objects (w8).
- ListBuckets ran 9 times (w4); reads in buckets other than `exampleco-customer-exports` are not logged (G2).

## Status
Confirmed for `exampleco-customer-exports`. Other buckets: not determinable without data events (G2).

## Needed from client
- G2 S3 server access logs for every bucket listed by ListBuckets, 2026-09-12 20:00 to 2026-09-13 10:00.

## Recommendations
- Treat the July and August 2026 customer exports as disclosed; start the notification review.
