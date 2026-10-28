# Timeline: Example Corp inc-0042

| Time (UTC) | Host / User | Event |
|---|---|---|
| **2026-09-12 20:41:37** | dev-jlee, example-corp/deploy-scripts | Push of a `.env` file with the `ci-deployer` key to the public repository. (S2 w9) |
| **2026-09-12 21:07:44** | ci-deployer, 203.0.113.45 | First external call, `GetCallerIdentity`. (S1 w10) |
| 2026-09-12 21:08–21:18 | ci-deployer, 203.0.113.45 | 9 `ListBuckets`, 61 `ListObjectsV2`. (S1 w4) |
| **2026-09-12 21:19:10** | ci-deployer, 203.0.113.45 | `CreateUser svc-backup-sync`, then `CreateAccessKey` at 21:19:31. (S1 w5) |
| 2026-09-12 21:20:02 | ci-deployer, 203.0.113.45 | `AttachUserPolicy AdministratorAccess` denied. (S1 w5) |
| **2026-09-12 21:24–2026-09-13 09:38** | ci-deployer, 203.0.113.45 | 1 090 `GetObject` in `exampleco-customer-exports/2026/`, 2.31 GB. (S1 w7) |
| **2026-09-13 07:52** | GuardDuty | First finding for `ci-deployer` from 203.0.113.45. (S1 w13) |
| 2026-09-13 07:58 | client platform team | Incident channel opened. (src slack) |
| **2026-09-13 09:41:12** | sec-admin | Key `AKIA...EXMPL` set to Inactive. (S1 w11) |
| 2026-09-13 09:47:55 | sec-admin | `svc-backup-sync` key and user deleted. (S1 w11) |
| 2026-09-13 09:52:20 | 203.0.113.45 | Last actor call, `InvalidClientTokenId`. (S1 w12) |
| 2026-09-14 07:58 | S1 | Re-check: no actor events. (S1 w14) |
