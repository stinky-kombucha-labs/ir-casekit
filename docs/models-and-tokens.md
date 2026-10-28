# Models and tokens

How to run a case in one session, on Sonnet, with as few tokens as possible.

## Where the tokens go
| Step | Cost driver | What the kit does about it |
|---|---|---|
| Intake / inventory | Index lists, raw sample documents | Big outputs go to a file and a script parses them; `log-profile.py` turns any CSV/JSON export into a ~40-line profile |
| Investigation | Raw rows in query results | Count first (`STATS`, `stats`, `summarize`, `--count-by`), then `KEEP` / `--keep` a few fields with a `LIMIT` |
| Re-reading | Reading the same logs twice | Results live in `worklog.md` and `analysis/`; the next step reads the case files, not the logs |

## One session
Default `work_mode: sequential`: no subagents, one item and one source at a time. Everything needed to continue is in the case folder, so `/compact` after a finished plan item (or a fresh session that starts with `/ir`) loses nothing.

## Which model
Start the session on Sonnet: `claude --model sonnet` (or `/model sonnet`).

| Step | Model | Why |
|---|---|---|
| `ir-intake`, inventory, access checks | Sonnet | Mechanical: list, count, record |
| `ir-investigate` on a clear question (one source, one artifact) | Sonnet | Narrow queries with a known answer shape |
| `ir-plan` on a large or multi-cloud case; "Updating the plan" | Opus | Choosing what to check next decides the outcome of the case |
| Attribution (actor vs client testers), correlation of several sources into one chain | Opus | Easy to over-claim; needs careful reasoning over contradicting sources |
| `ir-data-gaps` requests | Sonnet | Template-driven |
| `ir-tracker` | Sonnet (pinned with `model: sonnet` in the skill) | Table edits only |
| `ir-report` | Sonnet; Opus for the ATT&CK mapping and summary of a large case | The script does parsing, charts and PDF; the model writes only `narrative.json` |

Switch with `/model opus` for the step and `/model sonnet` after it. `opusplan` (Opus in plan mode, Sonnet for execution) also works if you plan in plan mode.

### When a case needs Opus
A case that starts from one CVE and grows into several cloud accounts, repositories and databases, with client testers mixed into the actor's traffic and two log pipelines that disagree, needs Opus for planning, attribution and correlation. Sonnet is enough for intake, single-source checks, data requests and the tracker. A single-host alert or a phishing case can run on Sonnet end to end.

## Habits that save the most
1. Never paste a raw export into the chat: drop the file into `sources/` and let `log-profile.py` read it.
2. One query, one line in `worklog.md`; cite `w<N>` instead of repeating results.
