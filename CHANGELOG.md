# Changelog

## 0.6.1 (2026-10-23) - fixes from the first end-to-end run (M365 BEC test case)
- `log-profile.py`: expands JSON held in a CSV cell (M365 `AuditData`), turns Name/Value lists into fields, detects more time columns (`Received`), says when offsets were converted to UTC, prints UTF-8 on Windows.
- `report.py`: wide coverage tables fit the page, no clipped tables or pills in PDF, split charts get a legend, repeated evidence queries are shown once, worklog comments after the query are kept apart, header shows "Evidence up to", executive report lists only Critical and High open actions and services without downtime as a table.
- `ir-investigate`: one-off parsers are saved as numbered files and cited with their exact command.
- `case.md`: definitions of `first_actor_activity_utc`, `detected_utc`, `contained_utc`. `ir-report`: client statements use `refs: ["client"]`; check the PDF layout before handing over.
- Windows: `py -3` fallback documented and allowed in `.claude/settings.json`.

## 0.6.0 (2026-10-23) - reports
- New skill `ir-report`: asks who the report is for (technical, executive, case quality, portfolio), the format (HTML, PDF, both) and the TLP level, writes `report/narrative.json` from the case evidence and renders the reports.
- New script `scripts/report.py` (standard library only): parses the case files, scores case quality (0-100, weighted), draws charts as inline SVG, writes self-contained HTML and prints PDF through headless Chrome / Edge / Chromium or WeasyPrint.
- `case.md` template: report fields `severity`, `incident_type`, `initial_access`, `status`, `first_actor_activity_utc`, `detected_utc`, `contained_utc`, `closed_utc`.
- `templates/report-narrative.md`, `docs/reports.md`. Demo case: front matter, worklog rows w15-w16, `report/` with narrative and rendered reports.
- CI renders the demo reports and a portfolio.

## 0.5.0 (2026-10-23) - first public release
- One repository is both the workspace (folder mode: `CLAUDE.md`, `.claude/`, `inbox/`, `cases/`) and a plugin marketplace (`plugins/ir-casekit`).
- Scripts live inside the plugin, so `<kit>` is the same folder in folder mode and plugin mode. New `scripts/link-skills.sh`.
- `examples/demo-case/`: a complete fictional case (leaked CI key in AWS).
- Environment variable `IR_CASES_ROOT`. Tracker column `Responder (RACI)`.
- CI: manifests, readiness check of the demo case, profiler, `new-case.sh`.
