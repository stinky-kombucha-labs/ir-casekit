---
name: ir-report
description: Build the final incident report from the case files as HTML, PDF or both. Use when the analyst asks for a report, an incident report, a PDF, a management or executive summary report, a technical report for the client, a case quality review, or a portfolio / monthly / quarterly report across cases ("make the report", "generate PDF", "report for management", "quarterly report"), in any language. Asks who the report is for, the format and the classification, writes the narrative from the case evidence, then renders it with scripts/report.py.
---

# IR report

`<kit>` is the plugin folder two levels above this file (`plugins/ir-casekit/` in the workspace).

## Goal
One report per audience, built only from what the case files prove. Every number and claim in the report points to a worklog row (`w<N>`), an item (`item<NN>`), a gap (`G<N>`) or a request (`R<N>`). The script draws the charts and tables; you write the narrative.

## Audiences
| Audience | Reader | What it contains (section ids for `--skip` / `--only`) |
|---|---|---|
| `technical` | client IT / security team, auditors | `kpis`, `phases`, `attack_chain`, `charts`, `items`, `timeline`, `coverage`, `iocs`, `credentials`, `data_gaps`, `recommendations`, `evidence` (queries with results), `method` |
| `executive` | management, C-level | `overview` (severity gauge, KPIs), `story`, `key_questions`, `assets`, `services`, `recovery`, `charts`, `progress` (NIST phases), `risks` (matrix), `decisions`, `open_actions` |
| `quality` | internal: lead analyst, reviewer | `score` (0-100, weighted), `profile`, `findings` (what to fix, file and place), `coverage`, `retention`, `items`, `progress` |
| `portfolio` | internal: team lead, monthly / quarterly review | cases by month and type, initial access, time to detect and contain against targets, ATT&CK tactics heat map, missing logs, recommendation status, case list |

`python3 -I <kit>/scripts/report.py sections` prints the current section ids.

## Steps
1. **Find the case** as `ir` does (named case, current folder, newest folder under `cases/`). For `portfolio`, the cases root instead.
2. **Check readiness.** Run `python3 -I <kit>/scripts/check-case.py <case-dir>`. If it says NOT READY, tell the analyst what is open in two or three lines and ask: finish the case first (route to `ir`), or build a draft. A draft gets `--draft` (red DRAFT label and footer line).
3. **Ask the analyst** in one message. Use the `AskUserQuestion` tool when the session has it (load it with ToolSearch if it is deferred); otherwise one chat message with numbered options. Ask all of these together, with the recommended option first:
   - Who is the report for? (multi-select) Technical / Executive / Case quality / Portfolio.
   - Format? HTML and PDF (recommended) / HTML only / PDF only.
   - Classification? TLP:AMBER (recommended for a client report) / TLP:GREEN (internal and portfolio default) / TLP:AMBER+STRICT / TLP:RED / TLP:CLEAR.
   - What to leave out? (multi-select) Nothing, full report (recommended) / Queries and evidence / IOCs and credentials / Coverage and data gaps. Map the answer to `--skip` ids: queries and evidence -> `evidence`; IOCs and credentials -> `iocs,credentials`; coverage and data gaps -> `coverage,data_gaps,retention`.
   Skip a question the analyst already answered in the request. The report language is English unless the analyst names another language for this report.
4. **Ask for what the case files cannot hold**, only for the chosen audiences and only when it is missing:
   - executive: business impact (affected assets by state, downtime per service, recovery over time), decisions the client must take with deadlines and owners, legal or regulatory clocks (for example GDPR 72 hours). One short message; the analyst may answer "skip", and those sections are left out.
5. **Build the data.** `python3 -I <kit>/scripts/report.py build <case-dir>`. It parses the case files into `report/report-data.json`, creates `report/narrative.json` when missing, prints the quality score and the narrative fields each audience still needs.
6. **Write `report/narrative.json`** (field reference: `<kit>/templates/report-narrative.md`). Read the case files, not the raw logs:
   - Use only facts that sit in `analysis/`, `worklog.md`, `timeline.md`, `credentials.md`, `data_gaps.md`, `recommendations.md`. Copy numbers exactly. Every KPI, question, risk, chart and evidence entry gets `refs`. A client statement gets `"refs": ["client"]` and the words "client statement", never unrelated worklog rows.
   - Check the front matter time fields against their definitions in `<kit>/templates/case.md` before the portfolio uses them.
   - A chart needs data that is already in the worklog. If an aggregation is missing (for example calls per hour), run one count query through the connector, log it as the next `w<N>` row in `worklog.md`, then use it. Otherwise leave the chart out.
   - ATT&CK: map only actions with status Confirmed or Partially; use Enterprise technique ids and names. On a large multi-source case suggest `/model opus` for this mapping, then `/model sonnet`.
   - Executive text: plain words, one fact per sentence, no tool or field names, no query syntax. Say what is not known.
   - Technical text: exact identifiers, UTC, defanged indicators. Never a secret value.
   - `title` names what happened; `summary` is three to five sentences: entry, what the actor did, impact, containment, what is still open.
7. **Render.** `python3 -I <kit>/scripts/report.py render <case-dir> --audience <list> --format <html,pdf> --tlp <LEVEL> [--skip <ids>] [--draft]`. Portfolio: `python3 -I <kit>/scripts/report.py portfolio <cases-root> --format <html,pdf> [--from YYYY-MM-DD --to YYYY-MM-DD]`. Output goes to `<case-dir>/report/<incident>-<audience>-<YYYYMMDD>.html|pdf`.
   - If PDF fails, run `report.py pdf-check` and tell the analyst the options: install Chrome / Edge / Chromium, set `IR_PDF_BROWSER` to a browser path, or `pip install weasyprint`. The HTML is still there and prints to PDF from any browser (Ctrl+P, "Save as PDF").
8. **Check before handing over.**
   - Run `build` again. A client report (technical, executive) must have no Critical or High finding about `report/narrative.json` (claims without refs). Fix and re-render.
   - Read the narrative once against the case files: every number equals its source, every status matches the item file, indicators are defanged.
   - Open each PDF once (the Read tool renders PDF pages) and look for cut tables, empty pages and labels that overlap. Fix the narrative (shorter labels, fewer columns) or report the layout problem.
   - Deadlines are counted from the report time. When the report is built days after the evidence, overdue decisions show as overdue; that is correct for a client report. For a replay of an old case use `--as-of <UTC>`.
9. **Reply** in under 10 lines: the file paths, quality score, sections left out and why (missing data or the analyst's choice), and anything the analyst must check by hand. Offer `ir-comms` for the cover message. Never send the report to anyone; the analyst does.

## Credits
The report design follows ideas from [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo). See `docs/reports.md`.

## Rules
- The report never says more than the case files prove. "Not determinable" stays "Not determinable"; a hypothesis is labelled as one or left out.
- Do not edit case files to make the report look complete. A gap in the report is a gap in the case: route it to the skill that owns it (`ir-investigate`, `ir-data-gaps`, `ir-containment-check`).
- `report/` lives inside the case folder, so it never goes into git. Copy a report elsewhere only when the analyst asks.
- The HTML is self-contained (no JavaScript, no external fonts or requests), so it is safe to open offline and to attach.
