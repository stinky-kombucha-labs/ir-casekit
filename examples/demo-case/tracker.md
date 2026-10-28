# Tracker: Example Corp inc-0042

Status: To do, In progress, Done, Blocked (client data), Not determinable.

## 1. Define the entry point and scope of the attack
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|
| Review exposure of the ci-deployer access key | Done | Responsible | Informed | Responder | 2026-09-14 | item01 |
| Review the actor's API activity | Done | Responsible | Informed | Responder | 2026-09-13 | item02 |
| Review persistence | Blocked (client data) | Responsible | Informed | Responder | 2026-09-13 | item03, G1 |
| Review data access in S3 | Done | Responsible | Informed | Responder | 2026-09-13 | item04 |
| Build the exposed credentials inventory | Done | Responsible | Consulted | Responder | 2026-09-13 | credentials.md |

## 2. Containment
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|
| Deactivate the leaked key | Done | Informed | Responsible | Client | 2026-09-13 | w11 |
| Delete the actor's IAM user | Done | Informed | Responsible | Client | 2026-09-13 | w11 |

## 3. Eradication
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|
| Rotate the database password from the `.env` | To do | Consulted | Responsible | Client | | |

## 4. Recovery
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|

## 5. Post-incident
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|
| Lessons learned | In progress | Responsible | Informed | Responder | 2026-09-14 | |
