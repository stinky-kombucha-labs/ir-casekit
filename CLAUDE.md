# Incident response workspace (ir-casekit)

This folder runs incident investigations with ir-casekit. No install and no arguments: the analyst writes in plain words (English, Ukrainian or any other language), you pick the procedure below and follow it.

## Layout
- `plugins/ir-casekit/` the kit. `<kit>` in any instruction means this folder.
  - `skills/<name>/SKILL.md` procedures (also exposed as project skills when `.claude/skills/` links exist).
  - `templates/` file templates. `scripts/` helper scripts (Python 3 standard library only).
- `cases/<client>-<incident-id>/` one folder per case. All case work lives here. Ignored by git.
- `examples/demo-case/` a fictional case that shows every file. Never mix real data into it.
- `inbox/` the analyst drops log files here (CSV, TSV, JSON, JSONL, `.gz`), or anywhere in the chat.
- `.env` credentials of this machine's MCP connectors, if any. Never read it, never copy it into a case or another folder.

## What the analyst says -> what you do
| Request (examples) | Procedure |
|---|---|
| "analyse incident ...", "проаналізуй інцидент ...", pastes a channel / alert / CVE, "full analysis", "повний аналіз" | `ir` (full analysis in one session): intake -> plan -> every item -> containment check -> data gaps -> tracker |
| "what's next", "where are we", "що далі", "статус" | `ir` status |
| "here are the logs", files in `inbox/` | `ir-intake` "New source mid-case": move each file from `inbox/` to `cases/<case>/sources/<origin>_<YYYY-MM-DD>/`, profile it, add it to item00 and coverage |
| "what should we ask the client", "запит клієнту" | `ir-data-gaps` |
| "is it contained", "що клієнт уже зробив" | `ir-containment-check` |
| a client message to answer / a draft to check | `ir-comms` |
| "make the report", "PDF", "report for management", "case quality", "monthly report" | `ir-report` |

Before each step, read that skill's `SKILL.md` (and `ir-investigate/connector-notes.md` once per session). If `.claude/skills/` is missing or its links are broken, read the skills from `plugins/ir-casekit/skills/` directly and offer to run `bash plugins/ir-casekit/scripts/link-skills.sh` (WSL / macOS / Linux).

**Which case.** The case named in the message; otherwise the most recently changed folder under `cases/`; if that is ambiguous, ask once. A new incident gets `bash plugins/ir-casekit/scripts/new-case.sh <client> <incident-id> cases` (lowercase, no spaces).

**Data sources.** Use every MCP connector of this client that the session has (list the tools; load deferred ones with ToolSearch). Read-only queries only. Files are profiled with `python3 -I plugins/ir-casekit/scripts/log-profile.py <file>` and never read raw. With no connector and no files, start with the executable data request (`ir-data-gaps`) and tell the analyst which files to drop into `inbox/`.

## Rules (always)
1. Evidence first: every fact in a case file has a query logged in `worklog.md` (`w<N>`) or a case file behind it. No query, no claim. Hypotheses are labelled.
2. UTC everywhere; convert UI exports (they carry the viewer's zone).
3. No secrets in files (`<REDACTED>`); defang indicators in anything for the client (`203.0.113[.]10`, `hxxp://`).
4. Prove absence: a zero counts only on a field that is filled in that source and window; missing data goes to `data_gaps.md` at once.
5. Every file you write (case files, queries, comments, requests, skills) is in English unless the analyst asks for another language for that document. Chat replies are in the analyst's language.
6. Client data requests are executable without questions: system and location, identifiers, UTC window, fields, export commands, format, completeness check, what to answer if the data does not exist.
7. Earlier notes and client statements are claims until a query confirms them.

## Tokens and model
- This folder's `.claude/settings.json` starts sessions on Sonnet. Work in one session, sequentially, no subagents unless the analyst asks for speed.
- Count before listing; keep few fields; big outputs go to a file and a script reads them. Do not re-read raw data whose result is already in `worklog.md` or `analysis/`.
- After a finished plan item in a long session, suggest `/compact`: the case files hold everything needed to continue.
- When a step needs deeper reasoning (plan for a large multi-account case, actor vs client testers, joining several sources into one attack chain), say so in one line and suggest `/model opus` for that step, then `/model sonnet` after it.

## Needs on the machine
Start `claude` in this folder, so this file and `.claude/settings.json` load. If the session started elsewhere, use absolute paths to this folder for every kit command and case file.

Python 3.8+ (`python3`). On Windows `python3` is often the Microsoft Store alias ("Python was not found"); then run the same command with `py -3` or `python` instead. Nothing else. PDF reports also need Chrome, Edge or Chromium (or WeasyPrint); HTML reports need nothing.
