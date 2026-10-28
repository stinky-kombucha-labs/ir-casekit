# Connector notes

Behaviour of the SIEM / EDR connectors that changes results. Read before the first query of a case. Add a line when a connector surprises you.

## Any source
- **A negative needs a filled field.** Before trusting "0 rows" on a field, run `STATS COUNT(*) BY <field>` (ES|QL) or `groupBy([<field>])` (CQL) on the same window. A field that exists in the mapping can be empty in every document (broken ingest pipeline, other integration version, field moved to ECS).
- The same data can arrive twice with different quality (two datasets of one product, an alert copy in the SIEM next to the EDR console). Pick the stream with filled fields and say why.
- One alert can be stored many times (each status update). Count distinct alert ids, not documents.
- Large raw documents fill the context. List fields first (mapping or one `KEEP`), then select only what you need; cut long text with `SUBSTRING` / `format("%.300s")`.
- Command lines and URLs in telemetry can carry base64 payloads and credentials. Decode in the scratchpad (`python3 -I`), print key ids only, write `<REDACTED>` for secrets and tokens.
- Workstation DNS and network telemetry is often partial (macOS). Absence of a DNS lookup or a connection does not prove absence of the request.

## Elastic (ES|QL through the agent-builder MCP)
- The execute tool asks for queries from its own generator; hand-written ES|QL after a mapping check works and is easier to log.
- `first` and `last` are reserved words: name columns `first_seen`, `last_seen`.
- `text` fields cannot be used in `STATS ... BY` or compared directly: `EVAL x = TO_STRING(field)` first. On tens of millions of documents this times out; filter on `keyword` fields (image, rule, host, cluster) and a narrow window before the `EVAL`.
- `MATCH()` on `text` fields can also time out on large windows; shrink the window.
- Hidden indices (for example `.alerts-security.alerts-*`) are not returned by the index list but can be queried by name.
- `list_indices` on a large cluster returns hundreds of KB and lands in a file: parse it with a script.
- CloudTrail in the SIEM may be filtered by provider. Run `STATS COUNT(*) BY event.provider` before a negative on any AWS service.
- An integration can fill ECS fields and leave its own namespace empty, or the other way round (GuardDuty: `aws.guardduty.*` empty, `rule.name`, `host.id`, `dns.question.name` filled; Falco: `orchestrator.*` empty, `falco.eks_cluster_name` filled). Check both before calling a source broken.
- The summarized mapping can omit fields that exist (ECS fields of the GitHub and Falco integrations). If a field from an earlier query is "unknown", try the integration's namespace (`falco.output_fields.*`, `github.workflow_id`) and the ECS name.

## CrowdStrike Falcon (falcon-mcp)
- NGSIEM: `processed_events: 0` means nothing reached the filter (often retention). Find the real retention per repository with `#repo=<repo> | head(1)` over a wide window.
- NGSIEM: compare `job.parsed_query` with the intent; unknown words become free-text filters.
- NGSIEM CQL: `regex("...(?<name>...)", field=X, strict=false)` creates the field; do not assign it with `:=`. `min()` / `max()` work on `@timestamp`, not on a formatted time string.
- NGSIEM `fcs_csp_events` (cloud events) and SIEM CloudTrail can be filtered differently: compare provider counts and query both for actor activity.
- Alerts API: an FQL filter on an unsupported field returns empty, not an error. `cmdline:'*x*'` wildcards and `~` in aggregations can return nothing on known hits; use `q='<text>'` full-text search to confirm.
- Alerts API: the alert-level `platform` can be wrong; filter by `device.platform_name`.
- Hosts API: ephemeral cloud nodes leave the host list after termination; their old alerts and telemetry stay.
- Missing API scopes return 403 with the scope name (for example `Vulnerabilities:read`, `Falcon Container Image:read`): record them in item00 and data_gaps.md.
- NGSIEM `search-all` with a bare IP string finds client staff who typed the actor IP in command lines (whois, scans, log queries). Split such hits from actor activity before counting; they can also reveal staff contact with actor infrastructure.

## Splunk (SPL through an MCP server)
- Inventory: `| tstats count min(_time) max(_time) where index=* by index, sourcetype` is cheap; raw `index=* | stats` over days is not.
- Always set `earliest=` / `latest=` in the query; the MCP default window can be short. `_time` is epoch; rendered times follow the search user's time zone. Print `strftime(_time, "%Y-%m-%d %H:%M:%S %z")` once to see the offset, and convert to UTC before writing.
- Count before listing: `| stats count by <field>`; then `| table` the fields you need with `| head 50`.
- Field extraction can differ per sourcetype; a field missing in `stats` output is not an empty field until `| fieldsummary` confirms it.

## Microsoft Sentinel / Defender (KQL)
- `union withsource=T * | where TimeGenerated > ago(1d) | summarize count() by T` lists the populated tables.
- `TimeGenerated` is UTC. Limit columns with `project`, count with `summarize`, page with `take`.

## Client log exports
- An access-log export can be filtered at the source (Istio Telemetry, EnvoyFilter): count status codes before concluding that a request type is absent. A 2.5-hour export with only 5xx lines is a filtered log, not a quiet service.
- Join exports on shared ids (request id, document key, job name) to find requests one log lost and the other kept.
- Profile every export with `scripts/log-profile.py` before reading rows. It unwraps Elastic `_source` / `hits.hits`, Splunk `result`, Falcon `resources`; flattens nested JSON; detects ISO and epoch s/ms/us/ns times.
- UI exports (Kibana Discover CSV, Splunk CSV) carry the viewer's time zone without an offset: the profiler warns; convert before writing a time.

## Kubernetes runtime alerts (Falco and similar)
- Alerts only show what a rule matched. File reads outside the rule's path list, writes, and network calls usually do not appear.
- Alerts on tools installed at runtime ("drop and execute new binary") give a process list of attacker pods built on minimal images; read `proc.cmdline` of those alerts.
- Pod names carry Job / CronJob suffixes (`-<id>-<5 chars>`, `-<schedule id>-<5 chars>`): group by a normalised name to count runs and see persistence.
