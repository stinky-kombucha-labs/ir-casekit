# Case folder layout

All case files are Markdown. Lives in the workspace `cases/` folder (ignored by git) or in a protected share mounted locally (`$IR_CASES_ROOT`). Never in git.

```
<client>-<incident-id>/
├── case.md                # metadata (YAML front matter), trigger, scope, data sources
├── worklog.md             # session plan + every query and its result, in order (sequential mode)
├── sources/               # raw material, verbatim: channel exports, client log exports, screenshots
│   └── trigger_<id>.md    # CVE / advisory / alert research (ir-intake)
├── plan.md                # investigation plan (ir-plan)
├── coverage.md            # every item00 source x every plan item: checked / n/a + reason / missing G<N>
├── analysis/
│   ├── item00_data_inventory.md
│   └── itemNN_<name>.md   # one per plan item (ir-investigate)
├── timeline.md            # UTC | host/user | event
├── iocs.md                # IPs, domains, user agents, session names, hashes
├── credentials.md         # exposed credentials inventory
├── recommendations.md     # containment / eradication actions with status
├── tracker.md             # local tracker when there is no Google Sheet (ir-tracker)
├── data_request.md        # what we asked the client for, built from data_gaps.md rows, with deadlines
├── data_gaps.md           # running list of missing data from intake on (G1, G2, ...), status, proof, onboarding
├── comms/                 # sent client messages, dated
└── report/                # ir-report: narrative.json (written by Claude), report-data.json (generated), <id>-<audience>-<date>.html / .pdf
```

Raw exports that are not text (jsonl, csv, images) keep their own format under `sources/`. Everything the team writes is `.md`, except `report/narrative.json`, which `report.py` reads.
