# Report narrative: `report/narrative.json`

`report.py build` creates this file empty in the case folder. Claude (skill `ir-report`) or the analyst fills it. `report.py` reads everything else from the case files: timeline, coverage, IOCs, credentials, data gaps, recommendations, tracker, worklog and item statuses.

Rules for every field:
- Facts only from the case files. Numbers copied exactly.
- `refs` on every claim: `w<N>` (worklog row), `item<NN>`, `G<N>`, `R<N>`. The quality review flags claims without refs.
- UTC. Defanged indicators. No secrets.
- An empty field is fine: its section is left out of the report.

Full example: [`examples/demo-case/report/narrative.json`](../../../examples/demo-case/report/narrative.json).

## Fields
| Field | Used by | Shape | Notes |
|---|---|---|---|
| `title` | technical, executive | string | What happened, in one line. Not "Incident report". |
| `summary` | technical (lead), executive (verdict box) | string | Three to five sentences: entry, actor actions, impact, containment, what is open. |
| `status_label` | all | string | `Contained`, `Eradication in progress`, `Recovered`, `Closed`, `Active`. |
| `severity` | executive gauge, header | string | `SEV-1` (highest) to `SEV-4`. |
| `kpis[]` | technical, executive | `{value, unit, label, level, refs, audience?}` | `level`: critical, serious, warning, good, neutral. `audience` limits a tile to `["technical"]` or `["executive"]`. Four to six tiles. |
| `phases` | technical | `{milestones: [{time, event, refs}], segments: [{label, level}]}` | N milestones make N-1 segments. Segment width is the real duration. |
| `attack_chain[]` | technical, portfolio | `{tactic, technique, name, what, time, refs, key}` | ATT&CK Enterprise ids. `key: true` marks the main steps. Portfolio counts tactics from here. |
| `charts[]` | technical (default), executive | see below | Data must already be in the worklog (`refs`). |
| `evidence[]` | technical | `{claim, status, refs}` | The report prints the exact query and result of each `w<N>` from the worklog. |
| `key_questions[]` | executive | `{question, answer, status, confidence, refs}` | `confidence` 1-5. Plain words. |
| `story[]` | executive | `{time, title, text}` | Four to six steps, one short sentence each. |
| `impact.assets[]` | executive | `{label, value, level}` | Waffle chart, one square per asset (for example encrypted / actor access / clean / not checked). |
| `impact.services[]` | executive | `{name, downtime_hours, status, level}` | Bars per business service. |
| `impact.recovery` | executive | `{x: [hours], values: [percent], x_ticks?, note?}` | Share of critical services available over time. |
| `risks[]` | executive | `{id, text, likelihood, impact, refs}` | 1-5 each; placed on a 5x5 matrix. |
| `decisions[]` | executive | `{decision, why, deadline_utc, owner, level}` | The report shows the time left at report time. |
| `methodology_notes[]` | technical | string list | Limits of the data, added to "Method and limits". |

## Charts
Every chart: `{type, title, note?, refs, audience?}`. `audience` defaults to `["technical"]`.

| `type` | Extra fields | Good for |
|---|---|---|
| `columns` | `labels`, `series: [{name, values}]`, `markers?: [{at, label, tip}]`, `height?`, `y_max?` | Activity per hour or day (stacked), size buckets. `at` is a position in label units (10.87 = 52 min into the 11th bar). |
| `hbar` | `rows: [{label, value, level?}]`, `unit?` | Top actions, top hosts, top users. |
| `split` | `parts: [{label, value, tip?}]` | Share of one total (data by prefix, by host). |
| `line` | `x`, `series: [{name, values, area?, dash?}]`, `x_format?`, `y_max?`, `y_suffix?`, `reference?: [{value, label}]` | Trends, burn-down, recovery. |
| `donut` | `parts: [{label, value, level?}]`, `center`, `sub` | Status mix. |
| `waffle` | `groups: [{label, value, level}]` | Counts of things (hosts, accounts). |

## Case front matter used by reports
`case.md` front matter fields read by `report.py`: `client`, `incident_id`, `opened_utc`, `team.lead`, `severity`, `incident_type`, `initial_access`, `status`, `first_actor_activity_utc`, `detected_utc`, `contained_utc`, `closed_utc`. The portfolio report computes time to detect (`detected_utc - first_actor_activity_utc`) and time to contain (`contained_utc - detected_utc`) from them, so fill them by the definitions in `templates/case.md`: the first actor action (not the lure delivery), the earliest proof of awareness (not the time we were told), and full containment (empty while any persistence remains).

## Client statements
A KPI, question, risk or decision that rests on what the client said (a payment, a call, an outage) gets `"refs": ["client"]` and says so in the text ("client statement"). Never attach worklog rows that do not prove the statement.
