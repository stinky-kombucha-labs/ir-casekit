# Tracker: <client> <incident-id>

Local tracker. Used when `tracker_url` in case.md is empty. Same columns and sections as the Google Sheets tracker (`templates/tracker.md`), so rows can be pasted into the sheet later.

Status: To do, In progress, Done, Blocked (client data), Not determinable.

## 1. Define the entry point and scope of the attack
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|
| Prepare initial recommendations | To do | Responsible | Informed | Responder | | |
| Build the exposed credentials inventory | To do | Responsible | Consulted | Responder | | |
| Review persistence (PATs, SSH keys, OAuth apps, webhooks, deploy keys, IAM keys, CI workflows, cluster resources) | To do | Responsible | Informed | Responder | | |
| Review accounts, clusters and projects outside SIEM coverage | To do | Responsible | Consulted | Responder | | |
| Request client-only data (with retention deadlines) | To do | Responsible | Informed | Responder | | |

## 2. Containment
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|
| Prepare critical containment recommendations | To do | Responsible | Informed | Responder | | |

## 3. Eradication
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|

## 4. Recovery
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|

## 5. Post-incident
| Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence |
|---|---|---|---|---|---|---|
| Lessons learned | To do | Responsible | Informed | Responder | | |
