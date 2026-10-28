---
name: ir-data-gaps
description: Prove which logs are really missing for an incident and build the client data request from the running data_gaps.md list. Use when the user asks "do we have these logs", "is it really not in the SIEM", "what should we request from the client", "validate this data request", when a retention-limited gap is found, when the client sends data, or when a colleague's request list needs review. Checks every index/repository, reconciles data_gaps.md with coverage.md, removes requests for data the team already has, adds missing ones with priority and retention deadline, tracks the status of each gap, and suggests how to onboard the source.
---

# IR data gaps

`<kit>` is the plugin folder two levels above this file (`plugins/ir-casekit/` in the workspace).

`data_gaps.md` is the running list of missing data (`templates/data-gaps.md`). `ir-intake`, `ir-plan` and `ir-investigate` add rows during the case. This skill proves each row, turns rows into `data_request.md`, and keeps statuses current.

## Steps
1. **Collect.** Read `data_gaps.md` and `coverage.md`. Every `missing G<N>` cell must point to a row in `data_gaps.md`; add the rows that are missing. Read the `Needed from client` sections of the item files and add any need that has no row.
2. **Prove absence in every source** for each `open` row, not only the first one:
   - Elastic: all data streams and indices; field-level check (for example CloudTrail `event_category` and `event.provider` to detect filtering);
   - CrowdStrike: NGSIEM repositories and `#type` over the last 7 days, host coverage for the affected hosts, missing API scopes;
   - Falco/EDR: sources present (syscall vs k8s_audit), cluster labels;
   - files already received from the client: time coverage and fields (for example an export that covers only the last 3 days, or only errors);
   - broken sources count as missing: fields empty in every document, ingest pipeline errors, wrong timestamps, provider filters that differ between connectors (`ir-investigate/connector-notes.md`).
   Write the sources and worklog rows into the row's "Proof of absence" cell. If a source has the data after all, set the row to `received` with the location and change the `coverage.md` cells from `missing` to the real result.
3. For each row decide: `Have it (where)`, `Partial (what is missing)`, `Client only`.
4. Write or update `data_request.md` from `templates/data-request.md`:
   - Priority 1 = answers whether data was stolen or the actor is still in; time-limited data. Sort P1 by deadline;
   - Priority 2 = completes scope and root cause;
   - one section per request (`R<N>`, linked to `G<N>`) with every field of the template: deadline and its reason, why we need it (the open question, the plan item, and what each answer changes for the client), what we already have, where it lives (system, account, region, cluster, log group, bucket, Loki labels, repository, host), scope (exact identifiers from the case: instance IDs, command IDs, pods, namespaces, service accounts, role ARNs, token IDs, SHAs, hosts), UTC window, fields, ready-to-run export commands with the identifiers filled in, output format, completeness check, and what to answer if the data does not exist;
   - the request must be executable by a client engineer or the client's AI agent without questions. Test it: could someone who has never seen the case run it? If a name is unknown (for example the cluster name), give the command that finds it;
   - take identifiers from evidence, never from memory; when an identifier comes from a client claim, verify it first or say so.
   Set the rows that went into the request to `requested` with the date.
5. Fill "Onboarding for the future" in `data_gaps.md`: how to onboard each missing source (Elastic integration, collector exporter, EDR sensor, CloudTrail data events, log setting).
6. **When the client answers:** `received` rows get the location (`sources/...`, new index); add the source to item00 and as a new row in `coverage.md` (every item gets a cell) and reopen the items that need it. `not available` rows make the items that depend only on them `Not determinable`.

## Rules
- Remove requests for data you already hold, and say where it is (including exports the client already sent).
- Never ask for secret values. Ask the client to replace them with `<redacted>`, or to compare fingerprints (for example the SHA-256 `hashed_token` in the GitHub audit) instead of sending a token. When the stolen data itself is the evidence, say so, ask for the secure channel, and state that values will not be copied into reports.
- Check times and identifiers in a colleague's request against the evidence before it goes out.
- Never delete a row in `data_gaps.md`; change its status.
- No `open` row may stay without a decision when the analysis is closed.
