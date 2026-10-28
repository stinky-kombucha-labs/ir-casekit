# ir-casekit

**Evidence-first incident response analysis for [Claude Code](https://code.claude.com).** Describe the incident in plain words; the kit walks Claude through intake, an investigation plan, every data source, a coverage matrix, containment checks and client data requests. Every finding in the case files points to the query that proves it.

- **No claim without a query.** Every fact in a case file cites a worklog row (`w12`), an analysis file (`item03`), a data gap (`G2`) or a request (`R1`).
- **Proves absence.** A zero counts only on a field that is filled in that source and window. Every source gets a cell for every question in `coverage.md`.
- **Any SIEM / EDR.** Uses whatever MCP connectors the session has (Elastic, Splunk, Sentinel, CrowdStrike, ...) and any CSV / JSON / JSONL export, profiled by a stdlib script instead of being pasted into the chat.
- **Cheap on tokens.** Sonnet by default, Opus only for planning, attribution and correlation.

- **Reports for every reader.** Technical, executive, case-quality and portfolio reports in HTML and PDF, with charts, ATT&CK chain, coverage matrix and the query behind each claim. See [`docs/reports.md`](docs/reports.md).

See a complete fictional case in [`examples/demo-case/`](examples/demo-case/) (a leaked CI key in AWS), with its reports in [`examples/demo-case/report/`](examples/demo-case/report/).

## Quick start

### Folder mode (no install)
```bash
git clone https://github.com/stinky-kombucha-labs/ir-casekit && cd ir-casekit
bash plugins/ir-casekit/scripts/link-skills.sh   # optional: exposes the skills as /ir, /ir-plan, ...
claude
```
Then write, for example:

| You write | You get |
|---|---|
| Analyse the incident at Acme: `<alert / Slack thread / CVE>` | Case folder, plan, every source checked, data request for the client |
| Here are the logs (files in `inbox/`) | Files moved into the case and profiled |
| What's next? | Where the case stands and the next step |
| What should we ask the client? | An executable data request |
| Make the report | Questions on audience, format and TLP, then HTML / PDF reports |

Other languages work too ("проаналізуй інцидент", "що далі", "запит клієнту").

### Plugin mode
```
/plugin marketplace add stinky-kombucha-labs/ir-casekit
/plugin install ir-casekit@ir-casekit
```

### Requirements
Python 3.8+ (on Windows, if `python3` opens the Microsoft Store, the kit uses `py -3`). Nothing to `pip install`. PDF reports use Chrome, Edge or Chromium in headless mode (or WeasyPrint if installed); HTML reports need nothing.

## How a case flows
```
ir-intake -> ir-plan -> ir-investigate (x N) -> ir-containment-check + ir-data-gaps -> ir-comms -> ir-report
                     \________ ir-tracker updates the tracker at every step ________/
```
Ask `ir` at any point ("what's next?") and it routes to the right skill.

| Skill | What it does |
|---|---|
| `ir` | Orchestrator: status in 15 lines, next step, full analysis in one session |
| `ir-intake` | Case folder, raw material saved verbatim, CVE / advisory research, connector access check, data inventory |
| `ir-plan` | Numbered "Review X" items with question, data, checks and expected result |
| `ir-investigate` | One item end to end, source by source; pivots on every actor artifact |
| `ir-containment-check` | What the client actually did, proven from logs; recurring checks with `/loop` |
| `ir-data-gaps` | Proves data is missing and writes requests a client engineer can run without questions |
| `ir-comms` | Short client updates; validates a draft claim by claim |
| `ir-tracker` | NIST-style tracker in Google Sheets or local `tracker.md` |
| `ir-report` | Technical, executive, case-quality and portfolio reports as self-contained HTML and PDF, every claim linked to its query |

## Repository layout
```
ir-casekit/
├── CLAUDE.md                      # routes plain requests to the skills (folder mode)
├── .claude/settings.json          # Sonnet by default, kit scripts allowed
├── .claude-plugin/marketplace.json
├── plugins/ir-casekit/
│   ├── skills/                    # 9 skills, one per IR step
│   ├── templates/                 # case.md, worklog, plan item, coverage, data gaps, data request ...
│   ├── scripts/                   # new-case.sh, check-case.py, log-profile.py, report.py, link-skills.sh
│   └── .mcp.json.example          # connector config with ${VAR} placeholders only
├── examples/demo-case/            # fictional case with every file filled in
├── docs/                          # models and tokens, team sharing, Drive logs, Sheets tracker, automation
├── inbox/                         # drop log files here (ignored by git)
└── cases/                         # your cases (ignored by git)
```

## Core rules
1. **Evidence first.** Every claim has a source and a query.
2. **Fixed status vocabulary.** `Confirmed`, `Partially`, `Not determinable`, `Discarded`. Hypotheses are labelled.
3. **UTC everywhere.** UI exports carry the viewer's zone; the profiler warns about it.
4. **No secrets in files.** Write `<REDACTED>`; the profiler masks values that look like secrets.
5. **Defang indicators** in anything that leaves the team (`203.0.113[.]10`, `hxxp://`).
6. **Case data never goes into git.** `cases/`, `inbox/` and `.env` are ignored.
7. **Cover every source.** No empty cell in `coverage.md` when the analysis is closed.
8. **Data requests are executable**: system, identifiers, UTC window, fields, export commands, completeness check.
9. **Earlier notes are claims** until a query confirms them.

## Works well with

**Data source connectors (MCP)**
- [CrowdStrike/falcon-mcp](https://github.com/CrowdStrike/falcon-mcp): Falcon detections, hosts, NGSIEM.
- [elastic/mcp-server-elasticsearch](https://github.com/elastic/mcp-server-elasticsearch): Elasticsearch queries (newer Elastic versions also expose an Agent Builder MCP endpoint).
- [livehybrid/splunk-mcp](https://github.com/livehybrid/splunk-mcp): community Splunk MCP server.
- [microsoft/mcp](https://github.com/microsoft/mcp): Microsoft MCP servers, including Azure and security tooling.

**DFIR tools whose output the profiler reads (CSV / JSON)**
- [Velocidex/velociraptor](https://github.com/Velocidex/velociraptor), [Yamato-Security/hayabusa](https://github.com/Yamato-Security/hayabusa), [WithSecureLabs/chainsaw](https://github.com/WithSecureLabs/chainsaw), [google/timesketch](https://github.com/google/timesketch).
- Detection content: [SigmaHQ/sigma](https://github.com/SigmaHQ/sigma).

**Case management**
- [dfir-iris/iris-web](https://github.com/dfir-iris/iris-web), [TheHive-Project/TheHive](https://github.com/TheHive-Project/TheHive).

**Process**
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) (April 2025, aligned with CSF 2.0).
- [counteractive/incident-response-plan-template](https://github.com/counteractive/incident-response-plan-template), [meirwah/awesome-incident-response](https://github.com/meirwah/awesome-incident-response).

## Credits
- Report design (one JSON file between analysis and rendering, weighted 0-100 scores, severity with a fix deadline, methodology section) is inspired by [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo).

## Disclaimer
The kit runs read-only queries and writes files; it does not take containment actions. Claude can be wrong: check the findings and the queries behind them before anything goes to a client.

## License
MIT, see [LICENSE](LICENSE).
