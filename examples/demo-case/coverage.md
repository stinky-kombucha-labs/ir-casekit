# Coverage: Example Corp inc-0042

Every source from item00 against every plan item. Fictional data.

| Source (item00 #) | 01 | 02 | 03 | 04 | 05 |
|---|---|---|---|---|---|
| S1 siem-demo cloudtrail / guardduty | checked w10 | checked w3,w4,w13,w15 | checked w5,w6; missing G1 | checked w7,w8,w16; missing G2 | checked w11,w12,w14 |
| S2 github audit export | checked w9 | n/a: no AWS API events in GitHub audit | n/a: no IAM events | n/a: no S3 events | n/a: no AWS events |

## Data outside the connectors
- S2 arrived as a file on 2026-09-14 (`sources/client_export_2026-09-14/`).
