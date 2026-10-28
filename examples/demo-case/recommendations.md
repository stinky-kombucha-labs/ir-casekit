# Recommendations: Example Corp inc-0042

| # | Priority | Action | Why (item / evidence) | Owner | Status | Evidence / last check UTC |
|---|---|---|---|---|---|---|
| 1 | Critical | Deactivate and delete the `ci-deployer` key | item02 | Client | Done | w11, 2026-09-13 09:41 |
| 2 | Critical | Delete `svc-backup-sync` and its key | item03 | Client | Done | w11, 2026-09-13 09:47 |
| 3 | Critical | Rotate the database password from the same `.env` | credentials #3 | Client | Not visible in logs | no source holds DB credential changes |
| 4 | High | Remove the `.env` from git history and enable push protection | item01 | Client | Not checked | |
