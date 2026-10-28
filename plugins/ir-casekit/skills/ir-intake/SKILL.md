---
name: ir-intake
description: Open a new incident response case. Use when the user starts a new client incident, pastes an incident Slack channel, alert, email, timeline, CVE or vendor advisory and wants it saved "as a base", or asks to "set up the case", "create the case folder", "save this as md". Creates the case folder from templates, stores the raw material verbatim, researches the CVE or advisory that triggered the case, checks access to the client's SIEM/EDR connectors, builds the data inventory source by source and writes the first timeline and scope hypothesis.
---

# IR intake

`<kit>` is the plugin folder two levels above this file (`plugins/ir-casekit/` in the workspace).

## Steps
1. **Case folder.** Run `<kit>/scripts/new-case.sh <client> <incident-id> [cases-root]` or create the layout from `<kit>/templates/case-structure.md`. Root: `$IR_CASES_ROOT` if set, otherwise the workspace `cases/` folder. Fill `case.md` (client, incident id, channel, ticket links, work mode, accounts/clusters in scope, data sources, team). Start `worklog.md` with the intake lines of the session plan. The script also creates `coverage.md` and `data_gaps.md` from templates.
2. **Raw material.** Save every paste verbatim under `sources/` as `.md` with a descriptive name and date (`sources/slack_<channel>_<YYYY-MM-DD>.md`). Do not summarise into the raw file. Redact secrets only. A one-line user statement is raw material too.
   **Earlier work.** If other analysts or the client already investigated (notes, plans, timelines, query results, log exports), list each file with what it holds and treat every statement in it as a claim. Plan a reconciliation item (`ir-plan`): one row per claim with the query that confirms or contradicts it. Exports from the client become sources (step 5 and "New source mid-case"); never re-request data the client already sent.
3. **Trigger research.** When the case starts from a CVE, a vendor advisory or a named technique, fill `sources/trigger_<id>.md` from `templates/trigger.md`:
   - read primary sources first (vendor advisory or changelog, CVE/NVD record, CISA KEV, GHSA); use aggregators only to find them;
   - write the attack path as steps, and for each step the artifact it leaves (HTTP path and parameters, process and parent, user, file path, network) and the log source that would hold it;
   - mark facts found only on a third-party site as `[unverified]`;
   - note the fixed version and the date the fix shipped. The exposure window ends at the patch date on each asset.
4. **Find the data, whatever the platform.** The case can use any SIEM / EDR / cloud MCP connector, client log files, or both.
   - **Connectors.** List the MCP tools available in this session (server names in the tool list, `.mcp.json` of the case). Group them by role: SIEM (Elastic, Splunk, Sentinel, QRadar, Chronicle, Sumo ...), EDR (CrowdStrike, Defender, SentinelOne ...), cloud, identity, ticketing. Use only the ones that belong to this client (`case.md` -> Data sources; ask once if the mapping is unclear). Load deferred tool schemas with ToolSearch before the first call.
   - For each connector run one cheap read (list indices / indexes, `falcon_check_connectivity`, one host search, one count over 1 hour). Record what works and what returns 403 with the missing scope (for example `NGSIEM:write`, `Falcon Container Image:read`). If an MCP server failed to start, diagnose it (missing binary, env file, CRLF, wrong base URL) before telling the user.
   - **Files.** Every CSV / TSV / JSON / JSONL / NDJSON (also `.gz`) the analyst drops into the case or the chat goes to `sources/<origin>_<YYYY-MM-DD>/` unchanged. Profile each one with `python3 -I <kit>/scripts/log-profile.py <file>`: rows, UTC time range, fields with fill %, top values. Never read a raw export into the context; read the profile, then query with `--where` / `--count-by` / `--keep`. A `WARNING: time values carry no zone` line means the export used the viewer's time zone: find the offset (compare one event with a connector or ask) before writing any time.
   - **No connector and no files.** Do not stop. Go straight to `ir-data-gaps`: write the first executable data request (which logs, where, window, export command, format) and tell the analyst exactly which files to drop where. Continue intake when they arrive.
   - Large outputs (an index list on a big cluster) land in a file: parse them with a script instead of reading them in chunks.
5. **Data inventory, source by source.** Fill `analysis/item00_data_inventory.md` from `templates/data-inventory.md`. One connector or file at a time, one index/repo at a time (examples below are for Elastic and CrowdStrike; use the same checks in any other product: streams, time range, host/account field, filled fields, retention):
   - Elastic: data streams and indices from the list, plus hidden ones the list does not show (`.alerts-security.alerts-*`, `.internal.*` alert indices). For each relevant stream run `STATS MIN(@timestamp), MAX(@timestamp), COUNT(*)` and the main host/service field (`host.name`, `orchestrator.cluster.name`, `cloud.account.id`);
   - CrowdStrike: hosts (platform, last seen, containment), detections in the window, NGSIEM `#repo` and `#event_simpleName`/`#type` counts, Spotlight vulnerabilities for the trigger CVE, enabled modules;
   - client files: the `log-profile.py` output gives time range, fill and top values; record it as the inventory row;
   - for each trigger artifact (step 3), name the source that would log it, or write "not present in any connector";
   - for each source you will rely on, check that its key fields are filled (`STATS COUNT(*) BY <field>`), that it is not a second, broken copy of another stream, and its real retention (`head(1)` over a wide window). Rules in `ir-investigate/connector-notes.md`.
   Log every query in `worklog.md`.
5a. **Coverage rows and first gaps.** Add one row per item00 source to `coverage.md` (use the item00 `#`). Add to `data_gaps.md` every row of "Not present in any connector", every broken source (empty fields, pipeline errors) and every missing API scope, as `G1`, `G2`, ... with status `open`.
6. **First timeline.** Extract confirmed events from the raw material into `timeline.md` (format in `templates/timeline.md`). Mark anything unverified as `[client claim]`. Add the CVE publication and fix dates when the trigger is a CVE.
7. **Scope hypothesis.** Three to six lines in `case.md` -> `Scope hypothesis`: entry point, affected accounts/clusters/hosts, active or stopped.

## New source mid-case
When data arrives later (client export, new connector, a source found by accident): save it under `sources/`, check it like step 5, add a row to item00 and to `coverage.md` (every existing item gets a cell, empty until checked), close the matching `data_gaps.md` row as `received`, and tell the user which items to reopen.

## Output
Short message: folder path, connectors OK/failed (with fix), trigger summary (product, affected versions, attack path in one line), sources that can and cannot see the attack path, top 3 scope questions, and the suggestion to run `ir-plan`.

## Rules
- Client claims from the channel are not facts. They become facts only after `ir-investigate` confirms them.
- Note the client's local time zone and convert to UTC on intake.
- A CVE description is not evidence that the client was exploited. It tells you what to look for.
