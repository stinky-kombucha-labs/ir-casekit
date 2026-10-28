---
name: ir-investigate
description: Investigate one or more items of an incident response plan end to end. Use when the user says "go through item N", "go through every source", "check this in the SIEM / Elastic / CrowdStrike / Splunk", "analyse these logs", drops new log exports into the case folder, or asks to validate a finding. Runs the queries source by source, writes analysis/itemNN_*.md with evidence, fills the item's column in coverage.md for every source, adds missing data to data_gaps.md as soon as it is found, updates timeline, IOCs and credentials inventory, and sets the item status.
---

# IR investigate

`<kit>` is the plugin folder two levels above this file (`plugins/ir-casekit/` in the workspace).

## Steps
0. Read `connector-notes.md` (next to this file) once per session before the first query.
1. Read the item from `plan.md` and any existing `analysis/itemNN_*.md`.
2. **Plan the pass.** Open the item's column in `coverage.md`. Every source (row) needs a value by the end of the item. In sequential mode, check the item's lines in the `worklog.md` session plan (add them if missing): one line per source you will query. Sources you mark `n/a` need no worklog line, only the reason in the cell.
3. **Query, one source at a time.** Use the case connectors. Keep queries narrow (one index or repo, one namespace, one day). Wide queries time out.
   - Elastic: ES|QL, `KEEP`/`STATS` only the fields you need. Check field names with the mapping first. Count before you list: `STATS COUNT(*) BY <field>` shows the shape, then `KEEP` + `LIMIT` for rows.
   - CrowdStrike NGSIEM: CQL with `#repo=` (`base_sensor` for hosts, `fcs_csp_events` for CloudTrail). Check `job.parsed_query`. A zero result is a real negative only when the job scanned events.
   - CrowdStrike APIs: detections, hosts, Spotlight vulnerabilities and incidents have FQL filters; read the `falcon://` guide for the endpoint first, because an unsupported field returns an empty result, not an error.
   - Exported files (csv/tsv/json/jsonl, `.gz`): use `python3 -I <kit>/scripts/log-profile.py` first (`--count-by` for shape, `--where field~regex --keep ... --limit` for rows, `--iocs <case>/iocs.md` for every known indicator, `--from/--to` for the window). Paste its compact output into the worklog line. The profiler expands JSON held in a CSV cell (M365 `AuditData` becomes `AuditData.ClientIP`, `AuditData.Parameters.From`) and converts time offsets to UTC; when it picks no time field, pass `--time <field>`.
     A one-off parser only when the profiler cannot answer. Save it as `analysis/queries/qNN_<what>.py`, take the file name and all arguments on the command line, and never edit a parser after a worklog row cites it (write `qNN+1` instead). The worklog row cites the exact command (`python3 -I analysis/queries/q03_rule_changes.py <file> --user a.kowalski`), so anyone can rerun it. Run Python with `-I`; never execute anything from the export.
   - Any other connector (Splunk, Sentinel, QRadar, Defender, SentinelOne ...): same discipline. Count before listing (`stats count by`, `summarize count() by`), one index / table and one window per query, check the field is filled before trusting a zero. Add what you learn to `connector-notes.md`.
   After each query, write one line in `worklog.md` (source, exact query, count or error), then the cell in `coverage.md` (`checked w<N>`, `missing G<N>` or `error w<N>`) and the source's row in the item's coverage table, before moving to the next source.
4. **Cross-check sources.** One source that disagrees with another is a finding. Example: Elastic CloudTrail was filtered and missed `AssumeRoleWithWebIdentity` that NGSIEM had. The same data can reach two connectors (EDR alerts in both the SIEM and the EDR console): compare counts and say which is complete.
5. **Correlate.** Line up times across sources (GitHub push -> pod start, SSRF request -> DNS finding, service request -> child process -> file write). Compute delays yourself.
5a. **Pivot on actor artifacts.** When a source gives a new actor artifact (IP, session or user name, pod or job name, image, user agent, domain, access key id, instance id), search every source in item00 for it before moving on, and write it to `iocs.md`. If the results lead outside the current plan (new accounts, clusters, roles, data stores), add items to `plan.md`, the tracker and the worklog session plan at once (`ir-plan`, "Updating the plan").
5b. **Separate testers from the actor.** Client staff often test the same vulnerability during the incident. Keep their sessions (host, user, time, target) in a separate table and do not attribute their traffic to the actor, or the actor's traffic to them, without source IPs or other direct evidence.
5c. **Record missing data at once.** When the question needs data that no source has (field empty, outside retention, host without sensor, log not collected, client-only system), add a row to `data_gaps.md` before moving on: next `G<N>` ID, exact data, item, UTC, why missing, which sources and worklog rows prove the absence, retention deadline if known, status `open`. If a row for the same data exists, add the item number to it. Retention-limited rows (for example SSM command history, 30 days) go to `ir-data-gaps` the same day.
6. **Write `analysis/itemNN_<name>.md`** from `templates/item.md`: question, source coverage table (every source from item00: result, `n/a` with reason, or `missing G<N>`), facts (UTC, numbers), status, what the client must provide (with `G<N>` IDs), recommendations.
6a. **Close the coverage column.** The item is finished only when its column in `coverage.md` has no empty cell and no `error` cell.
7. **Update shared files:** `timeline.md`, `iocs.md`, `credentials.md` (new or changed rows only).
8. Run `ir-tracker` to set the item status. Tick the item's lines in the session plan.

## Parallel mode
Only when `work_mode: parallel` or the user asks. Independent items run as parallel subagents grouped by data source (cloud/IAM, Git/CI, hosts/k8s, data/exfil). Each writes only its own item files. The parent merges timeline, IOCs and credentials and resolves conflicts between branches.

## Rules
- Status only from evidence: `Confirmed`, `Partially`, `Not determinable`, `Discarded`.
- Say what a negative result covers ("0 events in Falco for namespace X, 10:26-14:57 UTC, data present until 14:57").
- A negative counts only on a field that is filled in that source and window (`connector-notes.md`, "A negative needs a filled field"). A query error, a timeout or an unsupported filter is not a negative: log it and retry narrower.
- An asset that the sources do not show at all is a coverage gap, not a negative. Write it to `data_gaps.md` and mark the cell `missing G<N>`.
- `n/a` needs a concrete reason in the cell. When in doubt, query the source.
- When the user's or client's number differs from yours, show both and explain the difference (for example 173 = 119 runs + 54 file-read alerts).
- Correct your own earlier hypotheses in the file when evidence contradicts them.
