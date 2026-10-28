# IR project tracker (Google Sheets)

## Columns
| Column | Values |
|---|---|
| Task | Imperative, specific ("Review origin of the CI deploy token <token id>") |
| Status | To do, In progress, Done, Blocked (client data), Not determinable |
| Responder (RACI) | Responsible, Accountable, Consulted, Informed |
| Client (RACI) | Responsible, Accountable, Consulted, Informed |
| Owner | Team or person |
| Date | Last change, UTC date |
| Evidence | analysis file, PR, query reference |

## Sections (NIST SP 800-61 phases)
1. Define the entry point and scope of the attack (plan items; responder Responsible)
2. Containment (client Responsible; responder prepares recommendations)
3. Eradication (remove persistence, rebuild nodes/hosts, rotate credentials)
4. Recovery (restore services, monitoring for return)
5. Post-incident (lessons learned, logging improvements)

## Standard rows to start every case with
- Prepare initial recommendations
- Prepare critical containment recommendations
- Build the exposed credentials inventory
- Review persistence (PATs, SSH keys, OAuth apps, webhooks, deploy keys, IAM keys, CI workflows, cluster resources)
- Review accounts, clusters and projects outside SIEM coverage
- Request client-only data (with retention deadlines)
