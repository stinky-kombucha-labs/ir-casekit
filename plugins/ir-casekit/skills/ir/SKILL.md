---
name: ir
description: Orchestrator for client incident response cases. Use when the user starts or continues an incident ("new incident", "what's next on the case", "where are we", "status of the investigation", "що далі по інциденту"), pastes an incident channel, alert, CVE or advisory and wants it handled, asks for a "full analysis" of an incident, or names an IR step without naming a skill. Reads the case folder, reports the current phase and blockers, and routes to the right ir-casekit skill.
---

# IR orchestrator

`<kit>` is the plugin folder two levels above this file (`plugins/ir-casekit/` in the workspace).

## Goal
Tell the analyst where the case stands in under 15 lines and start the next step.

## Work mode
Read `work_mode` in `case.md`. Default is `sequential`.

- **sequential** (default): one session, no subagents. Before each step write the session plan in `worklog.md` (`templates/worklog.md`): which item, which source, in what order. Then work one item and one source at a time. Log every query and its result in `worklog.md` right after it runs. Write findings into the case files before moving to the next source. Tick the plan line only when its result is written.
- **parallel**: only when the user asks for speed or parallel agents. `ir-investigate` groups items by data source and runs them as subagents.

A "full analysis" request in sequential mode means: `ir-intake` -> `ir-plan` -> every plan item through `ir-investigate` -> `ir-containment-check` -> `ir-data-gaps` -> `ir-tracker`, in that order, in the same session. Then offer `ir-report`; it asks the analyst who the report is for and in which format. Do not skip a source because an earlier one already answered the question. A second source either confirms the answer or contradicts it, and both outcomes go into the item file. When an item leads outside the first scope, extend the plan (`ir-plan`, "Updating the plan") and continue in the same session; the trigger is where the analysis starts, not where it ends.

## Token discipline (one session)
- Case files are the memory. Read `case.md`, the `## Status` lines of `analysis/` and the tail of `worklog.md`; do not re-read raw exports or re-run queries whose result is already logged.
- Count before listing in every source; list with `KEEP` / `project` / `--keep` and a `LIMIT`. Big tool outputs go to a file and are parsed by a script.
- Client files: `scripts/log-profile.py` first, rows only through `--where` / `--keep`.
- Suggest `/compact` after a finished plan item when the session is long; everything needed to continue is already in the case files.
- Model: run the session on Sonnet (`claude --model sonnet`). `ir-tracker` pins `model: sonnet` itself. Switch to Opus (`/model opus`) only for steps that need cross-source reasoning on a large case: building or extending the plan, attribution (actor vs testers), and correlating several sources into the attack chain. Switch back after the step. See `docs/models-and-tokens.md`.

## Steps
1. Find the case folder: the current directory if it has `case.md`, otherwise look under `$IR_CASES_ROOT` and the workspace `cases/` folder, otherwise ask for the path once. If none exists, run `ir-intake`.
2. Read `case.md`, `worklog.md`, `plan.md`, `coverage.md`, `data_gaps.md`, `analysis/`, `timeline.md`, `tracker.md` (or `tracker_url`) and `comms/` (newest files first).
3. Build the status:
   - Phase (Scoping / Containment / Eradication / Recovery / Post-incident).
   - Plan items by status: Confirmed, Partially, Not determinable, Open.
   - Open lines in the `worklog.md` session plan; empty and `error` cells in `coverage.md` per item (`python3 -I <kit>/scripts/check-case.py <case-dir>`).
   - Data gaps by status (`open`, `requested`, `received`, `not available`) and the nearest retention deadline.
   - Active threat signals (for example a recurring job that may come back) and when they were last checked.
   - Waiting on client: open data requests and their retention deadlines.
4. Recommend one next action and name the skill that does it:
   - no plan yet -> `ir-plan`
   - open plan items or empty `coverage.md` cells -> `ir-investigate` (in parallel mode, offer to run independent items as subagents)
   - `open` rows in `data_gaps.md`, a retention deadline within 7 days, or data received from the client -> `ir-data-gaps`
   - client says something is fixed, or before sending recommendations -> `ir-containment-check`
   - "is this data really missing", "what do we ask the client" -> `ir-data-gaps`
   - client message to answer or a draft to validate -> `ir-comms`
   - tracker out of date -> `ir-tracker`
   - analysis closed (`check-case.py` READY), or the analyst asks for a report, PDF, management summary or a portfolio across cases -> `ir-report`
5. Run that skill if the user agrees or already asked for it.

## Output
```
Case: <client> / <incident id>   Phase: <phase>   Mode: <sequential|parallel>   Last update: <UTC>
Done: ...
Open: ...
Coverage: <empty cells> empty, <error cells> errors (items ...)
Data gaps: <open> open, <requested> requested (nearest deadline ...)
Active risk: ...
Waiting on client: ... (deadline ...)
Next: <action> via <skill>
```

## Rules
- Do not re-derive findings that already sit in `analysis/`. Read them.
- Never mark an item Confirmed yourself. Only `ir-investigate` changes item status.
- All files the team writes are Markdown (`.md`).
