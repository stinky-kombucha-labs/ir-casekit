---
name: ir-tracker
description: Keep the incident response project tracker in sync with the case, either the Google Sheet or the local tracker.md. Use when the user says "update the tracker", "add this to the tracker", "mark item done", after ir-plan, ir-investigate or ir-containment-check change something, or asks what is done and in progress. Adds rows, sets status, RACI, owner and date, never deletes rows.
model: sonnet
---

# IR tracker

`<kit>` is the plugin folder two levels above this file (`plugins/ir-casekit/` in the workspace).

## Sheet layout
See `templates/tracker.md`. Sections follow NIST SP 800-61 phases:
`Define the entry point and scope of the attack` -> `Containment` -> `Eradication` -> `Recovery` -> `Post-incident`.

Columns: `Task | Status | Responder (RACI) | Client (RACI) | Owner | Date | Evidence`.
Status values: `To do`, `In progress`, `Done`, `Blocked (client data)`, `Not determinable`.

## Where the tracker lives
- `tracker_url` in `case.md` is set: the Google Sheet is the tracker.
- `tracker_url` is empty: the tracker is `tracker.md` in the case folder (`templates/case-tracker.md`). Same columns and sections, so rows can be pasted into a sheet later.

## Steps
1. Read the current tracker (sheet or `tracker.md`). Match rows by task text; never duplicate a task.
2. Apply changes:
   - plan items -> scope section, responder Responsible, client Informed;
   - containment/eradication actions -> client Responsible, responder Informed (or Consulted);
   - status from `analysis/itemNN` (Confirmed/Partially -> Done for the review task; Not determinable -> Not determinable; waiting for client data -> Blocked);
   - Date = UTC date of the change; Evidence = file name or PR/query reference.
3. Sheet: show the user a diff (rows added / changed) before writing, unless they asked to write directly. Write through the Google Sheets connector. If writing is not possible, produce a paste-ready block (TSV) and say so.
4. `tracker.md`: edit the file directly and list the changed rows in the reply.

## Rules
- Never delete rows or overwrite a status set by the client team without telling the user.
- Containment rows are "Done" only when `ir-containment-check` found evidence, or the client confirmed in writing (note which).
