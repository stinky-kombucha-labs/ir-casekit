# Reports

`ir-report` turns a finished (or draft) case into reports for different readers. Ask in plain words: "make the report", "PDF for management", "case quality review", "quarterly report".

## How it runs
```
check-case.py  ->  questions to the analyst  ->  report.py build  ->  Claude writes report/narrative.json  ->  report.py render
                   (audience, format, TLP,         (case files ->        (title, summary, KPIs, ATT&CK,             (HTML, PDF)
                    what to leave out)              report-data.json)     charts, evidence, questions, risks)
```
The script does the parsing, the quality score, the charts and the PDF. Claude only writes the narrative, from the case files, with a reference on every claim. This keeps tokens low and stops the report from saying more than the evidence.

## The four reports
| Report | Reader | Highlights |
|---|---|---|
| Technical | client IT / security, auditors | KPI tiles, phase durations, ATT&CK chain, activity charts, item statuses, timeline, coverage matrix, IOCs, credentials, data gaps with retention countdown, recommendations, every claim with its exact query and result |
| Executive | management | verdict, severity gauge, five-step story, answers to the key questions with confidence, asset waffle, service downtime, recovery curve, NIST phase progress, 5x5 risk matrix, decisions with deadlines |
| Case quality | lead analyst, reviewer | weighted score 0-100 (traceability 25, coverage 20, data gaps 15, containment 15, timeline 10, IOC hygiene 10, secrets 5), radar profile, findings with file and place, coverage heat map, days until data is deleted |
| Portfolio | team lead | cases by month and type, initial access, time to detect and contain per case against targets, ATT&CK tactics by month, most frequent missing logs, recommendation status |

Rendered examples from the demo case: [`examples/demo-case/report/`](../examples/demo-case/report/).

## Commands
```bash
python3 -I plugins/ir-casekit/scripts/report.py build cases/acme-inc-0001
python3 -I plugins/ir-casekit/scripts/report.py render cases/acme-inc-0001 --audience technical,executive --format html,pdf --tlp AMBER
python3 -I plugins/ir-casekit/scripts/report.py render cases/acme-inc-0001 --audience quality --format html --draft
python3 -I plugins/ir-casekit/scripts/report.py portfolio cases --from 2026-07-01 --to 2026-09-30 --format pdf
python3 -I plugins/ir-casekit/scripts/report.py sections     # section ids for --skip / --only
python3 -I plugins/ir-casekit/scripts/report.py pdf-check    # which PDF engine is available
```
`--as-of 2026-09-14T11:30Z` fixes the report time (retention countdowns, deadlines), which keeps reruns identical.

## Output
- One HTML file per audience: inline CSS and SVG, no JavaScript, no web fonts, no external requests. It opens offline, follows the reader's light or dark theme on screen and prints in light.
- PDF: A4, page numbers and a `TLP:<level> · <client> <incident>` footer on every page; tables keep their header row across pages.
- Files go to `<case>/report/`, inside the case folder, so they never reach git.

## PDF engines
The script tries, in order: the browser in `$IR_PDF_BROWSER`; Chrome, Chromium, Edge or Brave found on `PATH` or in the usual install folders (Windows, macOS, Linux); WeasyPrint if it is installed (`pip install weasyprint`). With none of them, it keeps the HTML and says so. Any browser can still print the HTML to PDF by hand.

## Where the idea came from
The structure borrows from [claude-seo](https://github.com/AgriciDaniel/claude-seo): one JSON file between analysis and rendering, a weighted 0-100 score per category, severity with a fix deadline, and a methodology and limits section at the end. Unlike claude-seo, this kit draws charts as SVG in the standard library instead of matplotlib, so it keeps the "nothing to pip install" rule.
