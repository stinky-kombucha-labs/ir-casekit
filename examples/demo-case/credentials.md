# Exposed credentials inventory

| # | Credential | How the actor got it | Evidence | Used by actor | Rotated / revoked |
|---|---|---|---|---|---|
| 1 | IAM access key `AKIA...EXMPL` (user ci-deployer) | `.env` pushed to a public repository | S2 w9 | yes: 1 214 calls (w4) | revoked: set Inactive 2026-09-13 09:41:12 (w11) |
| 2 | IAM access key of `svc-backup-sync` | created by the actor | S1 w5 | no calls in eu-central-1 (w6) | deleted 2026-09-13 09:47:55 (w11) |
| 3 | Other secrets in the same `.env` (database URL) | same push | S2 w9 | unknown | not visible |

Priority for containment: 3.
