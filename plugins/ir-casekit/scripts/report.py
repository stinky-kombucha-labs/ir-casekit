#!/usr/bin/env python3
"""Build and render incident reports (HTML, PDF) from a case folder.

Usage:
  python3 -I report.py build <case-dir> [--as-of UTC]
      Parse the case files into <case-dir>/report/report-data.json and merge
      <case-dir>/report/narrative.json (written by the analyst / Claude; created
      empty when missing). Prints which narrative fields each audience still needs.
  python3 -I report.py render <case-dir> --audience technical,executive,quality
                              --format html,pdf [--tlp AMBER] [--skip id,id]
                              [--only id,id] [--draft] [--as-of UTC] [--out DIR]
      Rebuild the case data (narrative kept) and write one report per audience:
      <out>/<incident>-<audience>-<YYYYMMDD>.html / .pdf (default out: <case-dir>/report).
  python3 -I report.py portfolio <cases-root> --format html,pdf [--from YYYY-MM-DD]
                              [--to YYYY-MM-DD] [--tlp GREEN] [--out DIR]
      One report across every case folder under <cases-root> (default out: <cases-root>/_portfolio).
  python3 -I report.py sections        section ids per audience (for --skip / --only)
  python3 -I report.py pdf-check       which PDF engine this machine has

Audiences: technical (client IT / security team), executive (management),
quality (internal review of the case files), portfolio (all cases, internal).

HTML is one self-contained file: inline CSS and SVG, no JavaScript, no external
requests, so it opens offline and prints the same as it looks. PDF uses a
Chromium-based browser in headless mode (Chrome, Edge, Chromium, Brave; or the
path in $IR_PDF_BROWSER), or WeasyPrint when it is installed. Standard library only.

Report design inspired by https://github.com/AgriciDaniel/claude-seo (author: AgriciDaniel).
"""
import datetime as dt
import html
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA = 1
REF_RX = re.compile(r"\b(?:w\d+|G\d+|R\d+|item\d+)\b|\bsrc\b|credentials #\d+")
W_RX = re.compile(r"\bw(\d+)\b")
SECRET = [re.compile(p) for p in (
    r"AKIA[0-9A-Z]{16}", r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{30,}",
    r"xox[abpr]-[A-Za-z0-9-]{10,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")]
IPV4 = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
NARRATIVE_SKELETON = {
    "_help": "Filled by the analyst / Claude (skill ir-report). Every claim carries refs: w<N>, item<NN>, G<N>, R<N>. See templates/report-narrative.md.",
    "title": "", "summary": "", "status_label": "", "severity": "",
    "kpis": [], "phases": {"milestones": [], "segments": []}, "attack_chain": [], "charts": [],
    "evidence": [], "key_questions": [], "story": [],
    "impact": {"assets": [], "services": [], "recovery": {}},
    "risks": [], "decisions": [], "methodology_notes": [],
}
NEEDS = {
    "technical": ["title", "summary", "kpis", "phases", "attack_chain", "charts", "evidence"],
    "executive": ["title", "summary", "severity", "kpis", "story", "key_questions", "risks", "decisions"],
    "quality": [],
}


# ---------------------------------------------------------------- parsing
def read(case, name):
    p = case / name
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def split_row(line):
    cells, cur, tick = [], "", False
    for ch in line.strip().strip("|"):
        if ch == "`":
            tick = not tick
        if ch == "|" and not tick and not cur.endswith("\\"):
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
    cells.append(cur.strip())
    return [c.replace("\\|", "|") for c in cells]


def tables(text):
    """Yield (heading, header, rows) for every Markdown table."""
    lines, heading, i = text.splitlines(), "", 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("#"):
            heading = s.lstrip("#").strip()
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            header = split_row(s)
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = split_row(lines[j])
                cells += [""] * (len(header) - len(cells))
                rows.append(cells[: len(header)])
                j += 1
            yield heading, header, rows
            i = j
            continue
        i += 1


def table(text, first, heading=None):
    for h, header, rows in tables(text):
        if header and header[0].startswith(first) and (heading is None or heading.lower() in h.lower()):
            return header, [r for r in rows if not r[0].startswith("<")]
    return [], []


def frontmatter(text):
    meta, parent = {}, ""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return meta
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        if line[0] in " \t":
            if not parent:
                continue
            k = f"{parent}.{k.strip()}"
        else:
            parent = k.strip()
        v = v.strip()
        if v and v[0] in "\"'":
            q = v[0]
            v = v[1:v.find(q, 1)] if v.find(q, 1) > 0 else v[1:]
        else:
            v = re.sub(r"\s+#.*$", "", v)
        meta[k.strip()] = v
    return meta


def section(text, name):
    m = re.search(r"^##\s+" + re.escape(name) + r"\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def refs(s):
    return sorted(set(REF_RX.findall(s or "")), key=lambda r: (r[0], int(re.sub(r"\D", "", r) or 0)))


def plain(s):
    return re.sub(r"\*\*|`", "", s or "").strip()


def parse_utc(s):
    m = re.search(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?", s or "")
    if not m:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", s or "")
        return dt.datetime.fromisoformat(m.group(1)).replace(tzinfo=dt.timezone.utc) if m else None
    return dt.datetime(*map(int, m.group(1).split("-")), int(m.group(2)), int(m.group(3)), int(m.group(4) or 0),
                       tzinfo=dt.timezone.utc)


def cell_state(text):
    t = text.lower()
    if not t:
        return "empty"
    if t.startswith("error"):
        return "error"
    if t.startswith("n/a"):
        return "na"
    if "missing" in t:
        return "gap" if "checked" in t else "missing"
    return "ok"


def gap_state(s):
    t = plain(s).lower()
    known = ("open", "requested", "received", "not available", "closed")
    return next((k for k in known if t.startswith(k)), t.split(" ")[0] if t else "open")


def time_range(s):
    """Start and end of a timeline cell: '2026-09-12 21:08-21:18' or '2026-09-12 21:24-2026-09-13 09:38'."""
    a = parse_utc(s)
    if not a:
        return None, None
    tail = re.split(r"\s*[–-]\s*(?=\d)", re.sub(r"^\d{4}-\d{2}-\d{2}", "", plain(s)), maxsplit=1)
    if len(tail) < 2 or not re.search(r"\d{2}:\d{2}", tail[1]):
        return a, a
    b = parse_utc(tail[1])
    if not b:
        hh, mm = map(int, re.search(r"(\d{2}):(\d{2})", tail[1]).groups())
        b = a.replace(hour=hh, minute=mm, second=0)
        if b < a:
            b += dt.timedelta(days=1)
    return a, b


def status_word(s):
    w = plain(s).split(".")[0].strip()
    for v in ("Confirmed", "Partially", "Not determinable", "Discarded"):
        if w.lower().startswith(v.lower()):
            return v
    return w[:30] or "Open"


def parse_case(case, as_of):
    case_md = read(case, "case.md")
    meta = frontmatter(case_md)
    d = {"schema": SCHEMA, "generated_utc": as_of.strftime("%Y-%m-%dT%H:%MZ"), "case_dir": case.name, "meta": meta}
    d["trigger"] = plain(section(case_md, "Trigger").split("\n\n")[0])
    _, rows = table(case_md, "Name")
    d["sources"] = [{"name": r[0], "type": r[1], "covers": r[2], "access": r[3]} for r in rows if len(r) >= 4]

    items = []
    for f in sorted((case / "analysis").glob("item*.md")):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"^#\s*Item\s*(\d+)\.?\s*(.*)$", t, re.M)
        facts = [plain(x[1:]) for x in section(t, "Facts").splitlines() if x.strip().startswith("-")]
        st = section(t, "Status")
        items.append({"id": m.group(1) if m else f.stem[4:6], "title": (m.group(2).strip() if m else f.stem),
                      "status": status_word(st) if st else "", "file": f"analysis/{f.name}", "facts": facts})
    d["items"] = items

    _, rows = table(read(case, "timeline.md"), "Time")
    d["timeline"] = [{"time": plain(r[0]), "who": plain(r[1]), "event": plain(r[2]), "refs": refs(r[2]),
                      "key": r[0].startswith("**")} for r in rows if len(r) >= 3]

    header, rows = table(read(case, "coverage.md"), "Source")
    d["coverage"] = {"items": header[1:], "rows": [
        {"source": r[0], "cells": [{"text": c, "state": cell_state(c), "refs": refs(c)} for c in r[1:]]} for r in rows]}

    _, rows = table(read(case, "iocs.md"), "Type")
    d["iocs"] = [{"type": r[0], "value": plain(r[1]), "first_seen": r[2], "source": r[3]} for r in rows if len(r) >= 4]

    header, rows = table(read(case, "credentials.md"), "#")
    d["credentials"] = [{"n": r[0], "credential": plain(r[1]), "how": plain(r[2]), "evidence": r[3],
                         "used": plain(r[4]), "rotated": plain(r[5])} for r in rows if len(r) >= 6]

    gt = read(case, "data_gaps.md")
    header, rows = table(gt, "ID", "Running")
    if not header:
        header, rows = table(gt, "ID")
    gaps = []
    for r in rows:
        if not re.fullmatch(r"G\d+", r[0]):
            continue
        col = {h.lower(): v for h, v in zip(header, r)}
        ret = next((v for k, v in col.items() if k.startswith("retention")), "")
        dl = re.findall(r"\d{4}-\d{2}-\d{2}", ret)
        st = r[-1]
        gaps.append({"id": r[0], "missing": plain(r[1]), "items": r[2], "why": col.get("why missing", ""),
                     "retention": ret, "deadline": dl[-1] if dl else None, "status": plain(st),
                     "state": gap_state(st)})
    d["gaps"] = gaps

    _, rows = table(read(case, "recommendations.md"), "#")
    d["recommendations"] = [{"n": r[0], "priority": r[1], "action": plain(r[2]), "why": r[3], "owner": r[4],
                             "status": r[5], "evidence": r[6]} for r in rows if len(r) >= 7]

    tracker = []
    tt = read(case, "tracker.md")
    for h, header, rows in tables(tt):
        if header and header[0] == "Task":
            tracker.append({"phase": re.sub(r"^\d+\.\s*", "", h), "tasks": [
                {"task": plain(r[0]), "status": r[1], "owner": r[4] if len(r) > 4 else "",
                 "date": r[5] if len(r) > 5 else "", "evidence": r[6] if len(r) > 6 else ""}
                for r in rows if r[0]]})
    d["tracker"] = tracker

    _, rows = table(read(case, "worklog.md"), "#", "Log")
    d["worklog"] = {}
    for r in rows:
        if r[0].isdigit() and len(r) >= 6:
            m = re.match(r"^`([^`]*)`\s*(.*)$", r[4].strip(), re.S)
            if m and not re.match(r"^\s*(,|\+|and\b)", m.group(2)):
                q, note = m.group(1), m.group(2)
            else:
                q, note = r[4].replace("`", "").strip(), ""
            d["worklog"][f"w{r[0]}"] = {"utc": r[1], "item": r[2], "source": r[3], "query": q, "note": note, "result": r[5]}
    d["secrets_found"] = sorted({f.relative_to(case).as_posix() for f in case.rglob("*.md")
                                 if any(rx.search(f.read_text(encoding="utf-8", errors="replace")) for rx in SECRET)})
    return d


# ---------------------------------------------------------------- quality
def quality(d, as_of):
    findings = []

    def add(sev, file, where, issue, fix):
        findings.append({"severity": sev, "file": file, "where": where, "issue": issue, "fix": fix})

    n = d.get("narrative", {})
    claims = [(f, it["file"]) for it in d["items"] for f in it["facts"]]
    claims += [(c["evidence"] + " " + c["rotated"], "credentials.md") for c in d["credentials"]]
    nclaims = [(k.get("label", ""), k.get("refs")) for k in n.get("kpis", [])]
    nclaims += [(k.get("question", ""), k.get("refs")) for k in n.get("key_questions", [])]
    nclaims += [(k.get("claim", ""), k.get("refs")) for k in n.get("evidence", [])]
    nclaims += [(k.get("technique", ""), k.get("refs")) for k in n.get("attack_chain", [])]
    traced = sum(1 for c, _ in claims if refs(c)) + sum(1 for _, r in nclaims if r)
    total = len(claims) + len(nclaims)
    for it in d["items"]:
        if it["status"] == "Confirmed" and it["facts"] and not any(refs(f) for f in it["facts"]):
            add("Critical", it["file"], "Status", "Status is Confirmed but no fact cites a worklog row.",
                "Add the queries (w<N>) or change the status")
        if not it["status"] and it["id"] != "00":
            add("Medium", it["file"], "Status", "Item has no status.", "Set Confirmed, Partially, Not determinable or Discarded")
    missing_n = [c for c, r in nclaims if not r]
    if missing_n:
        add("High", "report/narrative.json", "", f"{len(missing_n)} report claims without refs: "
            + "; ".join(missing_n[:3]), "Add w<N> / item<NN> / G<N> refs or drop the claim")

    cells = [(row["source"], d["coverage"]["items"][i] if i < len(d["coverage"]["items"]) else str(i), c)
             for row in d["coverage"]["rows"] for i, c in enumerate(row["cells"])]
    good = sum(1 for *_, c in cells if c["state"] in ("ok", "na", "gap") or (c["state"] == "missing" and c["refs"]))
    by_src = {}
    for s, it, c in cells:
        if c["state"] in ("empty", "error"):
            by_src.setdefault((s, c["state"]), []).append(it)
    for (s, st), its in by_src.items():
        add("High", "coverage.md", f"{s} x {', '.join(its)}", f"{len(its)} {st} cell(s).",
            "Query the source or write n/a with a concrete reason")

    open_g = [g for g in d["gaps"] if g["state"] == "open"]
    retention = []
    for g in d["gaps"]:
        days = None
        if g["deadline"]:
            days = (parse_utc(g["deadline"]) - as_of).days
        if g["state"] in ("received", "closed"):
            continue
        retention.append({"id": g["id"], "label": g["missing"], "days": days, "deadline": g["deadline"], "state": g["state"]})
        if days is not None and days <= 7 and g["state"] in ("open", "requested"):
            add("Critical", "data_gaps.md", g["id"], f"Retention ends in {max(days, 0)} days ({g['deadline']}), status {g['state']}.",
                "Send or chase the data request today")
        elif g["state"] == "open":
            add("High", "data_gaps.md", g["id"], "Gap is open, no request sent.", "Write the request with ir-data-gaps")

    known = {g["id"] for g in d["gaps"]}
    orphan = sorted({r for *_, c in cells for r in c["refs"] if r.startswith("G")} - known)
    if orphan:
        add("Medium", "coverage.md", ", ".join(orphan), "Gap ids without a row in data_gaps.md.", "Add the rows")

    recs = d["recommendations"]
    proven = sum(1 for r in recs if W_RX.search(r["evidence"]))
    for r in recs:
        if r["status"].lower().startswith("done") and not W_RX.search(r["evidence"]):
            add("High", "recommendations.md", f"#{r['n']}", f"'{r['action']}' is Done without a log reference.",
                "Find the event that proves it or set 'Not visible in logs'")
        elif r["priority"].lower() == "critical" and not r["status"].lower().startswith("done"):
            add("Medium", "recommendations.md", f"#{r['n']}", f"Critical action still {r['status'] or 'open'}: {r['action']}.",
                "Chase the owner; re-check with ir-containment-check")

    tl = d["timeline"]
    tl_ok = sum(1 for e in tl if e["refs"])
    no_ref = [str(i + 1) for i, e in enumerate(tl) if not e["refs"]]
    if no_ref:
        add("Medium", "timeline.md", "rows " + ", ".join(no_ref[:8]), f"{len(no_ref)} event(s) without a source.", "Add w<N> refs")
    spans = [s for s in (time_range(e["time"]) for e in tl) if s[0]]
    stop = parse_utc(d["meta"].get("contained_utc"))
    for (_, a), (b, _) in zip(spans, spans[1:]):
        if (b - a).total_seconds() > 6 * 3600 and (not stop or b <= stop):
            add("Low", "timeline.md", f"{a:%m-%d %H:%M} to {b:%m-%d %H:%M}",
                f"{(b - a).total_seconds() / 3600:.1f} h without events before containment.",
                "Confirm the quiet period with a query, or note it")

    ioc_ok = 0
    for i, x in enumerate(d["iocs"]):
        v, bad = x["value"], False
        if IPV4.match(v) or re.match(r"^https?://", v) or re.fullmatch(r"[a-z0-9-]+\.(com|net|org|io|ru|xyz|top|info)", v, re.I):
            bad = True
            add("Medium", "iocs.md", f"row {i + 1}", f"Indicator {v} is not defanged.", "Write it as 203.0.113[.]10 / hxxp://")
        if not x["source"]:
            bad = True
            add("Low", "iocs.md", f"row {i + 1}", "Indicator without a source.", "Add the worklog ref")
        ioc_ok += not bad
    for c in d["credentials"]:
        if re.search(r"not visible|unknown|^$", c["rotated"], re.I):
            add("Medium", "credentials.md", f"#{c['n']}", f"Rotation of '{c['credential']}' is not proven.",
                "Ask the client for proof or keep it as an open recommendation")
    for f in d["secrets_found"]:
        add("Critical", f, "", "Value that looks like a secret.", "Replace with <REDACTED>")

    pct = lambda a, b: round(100 * a / b) if b else 100
    cats = [
        ("traceability", "Claim traceability", 25, pct(traced, total), f"{traced} of {total} claims cite a worklog row, item or gap"),
        ("coverage", "Source coverage", 20, pct(good, len(cells)), f"{good} of {len(cells)} coverage cells filled"),
        ("gaps", "Data gaps handled", 15, pct(len(d['gaps']) - len(open_g), len(d['gaps'])), f"{len(open_g)} of {len(d['gaps'])} gaps still open"),
        ("containment", "Containment proven", 15, pct(proven, len(recs)), f"{proven} of {len(recs)} recommendations have a log reference"),
        ("timeline", "Timeline sourced", 10, pct(tl_ok, len(tl)), f"{tl_ok} of {len(tl)} events cite a source"),
        ("iocs", "IOC hygiene", 10, pct(ioc_ok, len(d['iocs'])), f"{ioc_ok} of {len(d['iocs'])} indicators defanged and sourced"),
        ("secrets", "No secrets in files", 5, 0 if d["secrets_found"] else 100, f"{len(d['secrets_found'])} file(s) with secret-like values"),
    ]
    score = round(sum(w * s / 100 for _, _, w, s, _ in cats))
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    findings.sort(key=lambda f: order[f["severity"]])
    return {"score": score, "categories": [{"key": k, "name": nm, "short": k.capitalize() if k != "iocs" else "IOCs", "weight": w, "score": s, "detail": de}
                                           for k, nm, w, s, de in cats],
            "findings": findings, "retention": retention}


def build(case, as_of, quiet=False):
    case = Path(case)
    if not (case / "case.md").is_file():
        sys.exit(f"No case.md in {case}")
    out = case / "report" / "report-data.json"
    nfile = case / "report" / "narrative.json"
    out.parent.mkdir(exist_ok=True)
    narrative = dict(NARRATIVE_SKELETON)
    if nfile.is_file():
        try:
            narrative.update(json.loads(nfile.read_text(encoding="utf-8")))
        except json.JSONDecodeError as ex:
            sys.exit(f"{nfile}: invalid JSON ({ex})")
    else:
        nfile.write_text(json.dumps(NARRATIVE_SKELETON, indent=2) + "\n", encoding="utf-8")
    d = parse_case(case, as_of)
    d["narrative"] = narrative
    d["quality"] = quality(d, as_of)
    out.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not quiet:
        print(f"Wrote {out} (narrative from {nfile})")
        print(f"Parsed: {len(d['items'])} items, {len(d['timeline'])} timeline rows, {len(d['coverage']['rows'])} sources, "
              f"{len(d['iocs'])} IOCs, {len(d['gaps'])} gaps, {len(d['recommendations'])} recommendations, {len(d['worklog'])} worklog rows")
        print(f"Quality score: {d['quality']['score']}/100, {len(d['quality']['findings'])} findings")
        for aud, keys in NEEDS.items():
            empty = [k for k in keys if not filled(narrative.get(k))]
            print(f"Narrative for {aud}: " + ("complete" if not empty else "missing " + ", ".join(empty)))
    return d


def filled(v):
    if isinstance(v, dict):
        return any(filled(x) for x in v.values())
    return bool(v)


# ---------------------------------------------------------------- html helpers
def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


LEVEL = {"critical": "crit", "serious": "serious", "high": "serious", "warning": "warn", "medium": "warn",
         "good": "good", "neutral": "na", "low": "na", "info": "na"}
SERIES = ["s1", "s2", "s3", "s4", "s7"]
PILL = {"confirmed": "good", "done": "good", "received": "good", "closed": "good", "contained": "good",
        "partially": "warn", "in progress": "warn", "requested": "warn", "eradication": "warn", "recovery": "warn",
        "revoked": "good", "deleted": "good", "rotated": "good", "removed": "good", "not determinable": "na", "discarded": "na", "to do": "na", "not checked": "na", "open": "crit",
        "blocked": "serious", "not available": "serious", "not visible": "crit", "waiting": "serious",
        "still active": "crit", "active": "crit", "misused": "crit", "overdue": "crit", "available": "good", "restored": "good",
        "no fixed deadline": "na", "partly": "warn"}
SEV_CLS = {"Critical": "crit", "High": "serious", "Medium": "warn", "Low": "na"}


def lvl(x, default="s1"):
    return LEVEL.get(str(x or "").lower(), default)


def pill_cls(text):
    t = plain(text).lower()
    return next((v for k, v in PILL.items() if t.startswith(k)), "na")


def pill(text, cls=None):
    cls = cls or pill_cls(text)
    return f'<span class="pill p-{cls}">{e(plain(text))}</span>'


def short_status(s):
    return re.split(r"[:(;]|\s\d", plain(s), maxsplit=1)[0].strip()


def short_source(name):
    m = re.match(r"^(S\d+)\b\s*(.*)$", name)
    if m:
        rest = re.sub(r"[_-]?\d{4}-\d{2}-\d{2}.*$", "", m.group(2)).strip(" _-")
        return f"{m.group(1)} {rest[:24]}".strip()
    return name[:30]


def short_text(s, n=90):
    s = re.split(r"[:;(]", plain(s), maxsplit=1)[0].strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def note_if_longer(s):
    return f'<div class="note">{e(plain(s))}</div>' if plain(s) != short_status(s) else ""


def ref_chips(rs):
    return " ".join(f'<span class="ref">{e(r)}</span>' for r in (rs or []))


def fnum(v):
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.1f}".replace(",", " ")
    return f"{int(v):,}".replace(",", " ")


def svg(w, h, inner, label):
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{e(label)}" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'


def tip(s):
    return f"<title>{e(s)}</title>"


def nice_max(v):
    if v <= 0:
        return 1
    p = 10 ** math.floor(math.log10(v))
    m = v / p
    return (1 if m <= 1 else 2 if m <= 2 else 2.5 if m <= 2.5 else 5 if m <= 5 else 10) * p


def hbars(rows, unit=""):
    mx = max([r.get("value", 0) for r in rows] + [1])
    out = []
    for i, r in enumerate(rows):
        v = r.get("value", 0)
        cls = lvl(r.get("level"), "s1") if r.get("level") else "s1"
        lab = r.get("text") or f"{fnum(v)}{(' ' + unit) if unit else ''}"
        out.append(f'<div class="hrow" title="{e(r.get("tip") or r["label"] + ": " + lab)}"><span class="lab">{e(r["label"])}</span>'
                   f'<div class="track"><div class="bar b-{cls}" style="width:{v / mx * 100:.2f}%"></div></div><span class="val">{e(lab)}</span></div>')
    return '<div class="hbars">' + "".join(out) + "</div>"


def columns(labels, series, markers=None, h=250, y_max=None, ticks=4, top=True, label="chart", W=760):
    L, R, T, B = 44, 10, 16, 30
    iw, ih = W - L - R, h - T - B
    n = len(labels)
    tot = [sum(s["values"][i] for s in series) for i in range(n)]
    ym = y_max or nice_max(max(tot + [1]))
    bw = iw / max(n, 1)
    gap = max(4, bw * .28)
    g = []
    for k in range(ticks + 1):
        y = T + ih - ih * k / ticks
        g.append(f'<line class="{"grid" if k else "axis"}" x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}"/>'
                 f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end">{fnum(ym * k / ticks)}</text>')
    for i, lab in enumerate(labels):
        y0, x, w = T + ih, L + i * bw + gap / 2, bw - gap
        for si, s in enumerate(series):
            v = s["values"][i]
            if not v:
                continue
            hh = v / ym * ih
            last = all(not x2["values"][i] for x2 in series[si + 1:])
            cls = s.get("cls") or SERIES[si % len(SERIES)]
            if last and hh > 4:
                d = f"M{x:.1f},{y0:.1f}V{y0 - hh + 4:.1f}q0,-4 4,-4h{w - 8:.1f}q4,0 4,4V{y0:.1f}Z"
            else:
                d = f"M{x:.1f},{y0:.1f}V{y0 - hh + 1:.1f}h{w:.1f}V{y0:.1f}Z"
            g.append(f'<path class="f-{cls}" d="{d}">{tip(f"{lab} · {s["name"]}: {fnum(v)}")}</path>')
            y0 -= hh
        if top and tot[i]:
            g.append(f'<text x="{x + w / 2:.1f}" y="{y0 - 5:.1f}" text-anchor="middle">{fnum(tot[i])}</text>')
        g.append(f'<text x="{x + w / 2:.1f}" y="{h - 10}" text-anchor="middle">{e(lab)}</text>')
    for m in markers or []:
        x = L + float(m["at"]) * bw
        g.append(f'<line class="mark" x1="{x:.1f}" x2="{x:.1f}" y1="{T}" y2="{T + ih}">{tip(m.get("tip") or m["label"])}</line>'
                 f'<text class="markt" x="{x - 4:.1f}" y="{T + 10}" text-anchor="end">{e(m["label"])}</text>')
    return svg(W, h, "".join(g), label)


def line_chart(xs, series, y_max=None, y_suffix="", x_ticks=None, x_fmt="{x}", refs_=None, h=230, label="chart", W=760):
    L, R, T, B = 48, 16, 16, 30
    iw, ih = W - L - R, h - T - B
    xmin, xmax = min(xs), max(xs)
    ym = y_max or nice_max(max(v for s in series for v in s["values"]))
    X = lambda v: L + (v - xmin) / ((xmax - xmin) or 1) * iw
    Y = lambda v: T + ih - v / ym * ih
    g = []
    for k in range(5):
        v = ym * k / 4
        g.append(f'<line class="{"grid" if k else "axis"}" x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                 f'<text x="{L - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{fnum(v)}{e(y_suffix)}</text>')
    for v in x_ticks if x_ticks is not None else xs:
        lab = x_fmt(v) if callable(x_fmt) else x_fmt.format(x=fnum(v) if isinstance(v, (int, float)) else v)
        g.append(f'<text x="{X(v):.1f}" y="{h - 10}" text-anchor="middle">{e(lab)}</text>')
    for si, s in enumerate(series):
        cls = s.get("cls") or SERIES[si % len(SERIES)]
        pts = [(X(x), Y(v)) for x, v in zip(xs, s["values"])]
        d = "".join(("L" if i else "M") + f"{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(pts))
        if s.get("area"):
            g.append(f'<path class="area-{cls}" d="{d}L{pts[-1][0]:.1f},{T + ih}L{pts[0][0]:.1f},{T + ih}Z"/>')
        g.append(f'<path class="ln-{cls}{" dash" if s.get("dash") else ""}" d="{d}"/>')
        if not s.get("dash"):
            for i, (px, py) in enumerate(pts):
                t = s.get("tips", [None] * len(pts))[i] or f'{s.get("name", "")} {xs[i]}: {fnum(s["values"][i])}{y_suffix}'
                g.append(f'<circle class="dot-{cls}" cx="{px:.1f}" cy="{py:.1f}" r="{5 if i == len(pts) - 1 else 3.5}">{tip(t)}</circle>')
    for r in refs_ or []:
        y = Y(r["value"])
        g.append(f'<line class="mark" x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}"/><text class="markt" x="{W - R}" y="{y - 5:.1f}" text-anchor="end">{e(r["label"])}</text>')
    return svg(W, h, "".join(g), label)


def arc(cx, cy, r, a1, a2):
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
    return f"M{x1:.2f},{y1:.2f}A{r},{r} 0 {1 if a2 - a1 > math.pi else 0} 1 {x2:.2f},{y2:.2f}"


def donut(parts, center, sub):
    S, c, r, w = 220, 110, 84, 26
    tot = sum(p["value"] for p in parts) or 1
    a, g = -math.pi / 2, []
    for i, p in enumerate(parts):
        if not p["value"]:
            continue
        da = p["value"] / tot * 2 * math.pi
        a2 = a + da - (0.03 if da < 2 * math.pi - .01 else 0.001)
        cls = p.get("cls") or lvl(p.get("level"), SERIES[i % len(SERIES)])
        lg = 1 if a2 - a > math.pi else 0
        P = lambda ang, rr: (c + rr * math.cos(ang), c + rr * math.sin(ang))
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = P(a, r), P(a2, r), P(a2, r - w), P(a, r - w)
        g.append(f'<path class="f-{cls}" d="M{x1:.2f},{y1:.2f}A{r},{r} 0 {lg} 1 {x2:.2f},{y2:.2f}L{x3:.2f},{y3:.2f}'
                 f'A{r - w},{r - w} 0 {lg} 0 {x4:.2f},{y4:.2f}Z">{tip(f"{p["label"]}: {p["value"]} ({round(p["value"] / tot * 100)}%)")}</path>')
        a = a + da
    g.append(f'<text class="big" x="{c}" y="{c + 6}" text-anchor="middle">{e(center)}</text><text x="{c}" y="{c + 26}" text-anchor="middle">{e(sub)}</text>')
    leg = "".join(f'<span><i class="b-{p.get("cls") or lvl(p.get("level"), SERIES[i % len(SERIES)])}"></i>{e(p["label"])} · {fnum(p["value"])}</span>'
                  for i, p in enumerate(parts))
    return f'<div class="donut">{svg(S, S, "".join(g), center + " " + sub)}</div><div class="legend">{leg}</div>'


def score_gauge(score, critical=0):
    W, H, cx, cy, r = 280, 170, 140, 150, 110
    cls = "good" if score >= 80 else "warn" if score >= 50 else "crit"
    word = "ready" if score >= 80 else "needs work" if score >= 50 else "not ready"
    if critical and score >= 50:
        word = f"{critical} critical to fix"
    g = [f'<path class="track" d="{arc(cx, cy, r, math.pi, 2 * math.pi)}"/>',
         f'<path class="st-{cls}" d="{arc(cx, cy, r, math.pi, math.pi + math.pi * max(score, 1) / 100)}"/>']
    for v in (0, 50, 80, 100):
        a = math.pi + math.pi * v / 100
        g.append(f'<text x="{cx + (r + 18) * math.cos(a):.1f}" y="{cy + (r + 18) * math.sin(a) + 4:.1f}" text-anchor="middle">{v}</text>')
    g.append(f'<text class="huge" x="{cx}" y="{cy - 18}" text-anchor="middle">{score}</text><text x="{cx}" y="{cy + 4}" text-anchor="middle">of 100 · {word}</text>')
    return svg(W, H, "".join(g), f"Score {score}")


def severity_gauge(sev):
    m = re.search(r"([1-4])", sev or "")
    k = int(m.group(1)) if m else 0
    W, H, cx, cy, r = 260, 172, 130, 124, 100
    g = []
    bands = [("good", 4), ("warn", 3), ("serious", 2), ("crit", 1)]
    for i, (cls, s) in enumerate(bands):
        a1, a2 = math.pi + i * math.pi / 4 + .02, math.pi + (i + 1) * math.pi / 4 - .02
        g.append(f'<path class="band-{cls}{" on" if s == k else ""}" d="{arc(cx, cy, r, a1, a2)}">{tip(f"SEV-{s}")}</path>')
    if k:
        a = math.pi + (4 - k + .5) * math.pi / 4
        g.append(f'<line class="needle" x1="{cx}" y1="{cy}" x2="{cx + (r - 18) * math.cos(a):.1f}" y2="{cy + (r - 18) * math.sin(a):.1f}"/>'
                 f'<circle class="hub" cx="{cx}" cy="{cy}" r="6"/>')
    g.append(f'<text class="big" x="{cx}" y="{cy + 40}" text-anchor="middle">{e(sev or "n/a")}</text>')
    return svg(W, H, "".join(g), f"Severity {sev}")


def radar(cats):
    W, H, cx, cy, R = 440, 330, 220, 165, 110
    n = len(cats)
    P = lambda i, v: (cx + R * v / 100 * math.cos(-math.pi / 2 + i * 2 * math.pi / n),
                      cy + R * v / 100 * math.sin(-math.pi / 2 + i * 2 * math.pi / n))
    g = []
    for v in (25, 50, 75, 100):
        g.append('<polygon class="rgrid" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in (P(i, v) for i in range(n))) + '"/>')
    for i, c in enumerate(cats):
        x, y = P(i, 100)
        lx, ly = P(i, 122)
        anchor = "middle" if abs(lx - cx) < 10 else "start" if lx > cx else "end"
        g.append(f'<line class="axis" x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}"/><text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="{anchor}">{e(c.get("short") or c["name"])} {c["score"]}</text>')
    g.append('<polygon class="rarea" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in (P(i, c["score"]) for i, c in enumerate(cats))) + '"/>')
    for i, c in enumerate(cats):
        x, y = P(i, c["score"])
        g.append(f'<circle class="dot-s1" cx="{x:.1f}" cy="{y:.1f}" r="4">{tip(c["name"] + ": " + str(c["score"]) + ". " + c["detail"])}</circle>')
    return svg(W, H, "".join(g), "Quality profile")


def waffle(groups):
    total = sum(int(gr["value"]) for gr in groups)
    small = ' style="grid-template-columns:repeat(10,1fr);max-width:260px"' if total <= 60 else ""
    cells = "".join(f'<i class="b-{lvl(gr.get("level"), "na")}" title="{e(gr["label"])}"></i>' for gr in groups for _ in range(int(gr["value"])))
    leg = "".join(f'<span><i class="b-{lvl(gr.get("level"), "na")}"></i>{e(gr["label"])} · {fnum(gr["value"])}</span>' for gr in groups)
    return f'<div class="waffle"{small}>{cells}</div><div class="legend">{leg}</div>'


def risk_matrix(risks):
    def cls(l, i):
        s = l * i
        return "crit" if s >= 15 else "serious" if s >= 8 else "warn" if s >= 4 else "good"
    h = []
    for l in range(5, 0, -1):
        h.append(f'<div class="ax">{l}</div>')
        for i in range(1, 6):
            here = [r for r in risks if int(r.get("likelihood", 0)) == l and int(r.get("impact", 0)) == i]
            t = "; ".join(f'{r["id"]}: {r["text"]}' for r in here)
            h.append(f'<div class="c bg-{cls(l, i)}"{f" title={chr(34)}{e(t)}{chr(34)}" if t else ""}>'
                     + "".join(f'<span class="tag">{e(r["id"])}</span>' for r in here) + "</div>")
    h.append('<div></div>' + "".join(f'<div class="ax">{i}</div>' for i in range(1, 6)))
    lst = "".join(f'<div><b class="mono">{e(r["id"])}</b> {e(r["text"])} {ref_chips(r.get("refs"))}</div>' for r in risks)
    return f'<div class="rmwrap"><div class="rm">{"".join(h)}</div><div class="note rml"><div>Rows: likelihood 1-5. Columns: impact 1-5.</div>{lst}</div></div>'


def fmt_dur(sec):
    m = round(sec / 60)
    if m < 60:
        return f"{m} min"
    hh, mm = divmod(m, 60)
    if hh < 48:
        return f"{hh} h {mm} min" if mm else f"{hh} h"
    return f"{hh // 24} d {hh % 24} h"


# ---------------------------------------------------------------- sections
def sec(title, body, cls=""):
    return (title, f'<div class="{cls}">{body}</div>' if cls else body)


def s_kpis(d, ctx):
    ks = [k for k in d["narrative"].get("kpis", []) if ctx["audience"] in k.get("audience", [ctx["audience"]])]
    if not ks:
        return None
    out = []
    for k in ks:
        unit = f' <small>{e(k["unit"])}</small>' if k.get("unit") else ""
        r = f'<div class="r">{e(" · ".join(k.get("refs", [])))}</div>' if ctx["audience"] == "technical" else ""
        out.append(f'<div class="kpi k-{lvl(k.get("level"), "na")}"><div class="v">{e(k["value"])}{unit}</div><div class="l">{e(k["label"])}</div>{r}</div>')
    return None, '<div class="kpis">' + "".join(out) + "</div>"


def s_phases(d, ctx):
    p = d["narrative"].get("phases") or {}
    ms, segs = p.get("milestones", []), p.get("segments", [])
    if len(ms) < 2:
        return None
    ts = [parse_utc(m["time"]) for m in ms]
    durs = [max((b - a).total_seconds(), 1) for a, b in zip(ts, ts[1:])]
    tot = sum(durs)
    bar = []
    for i, du in enumerate(durs):
        sg = segs[i] if i < len(segs) else {}
        txt = fmt_dur(du) if du / tot >= 0.09 else ""
        bar.append(f'<div class="b-{lvl(sg.get("level"), "s1")}" style="flex:{du / tot:.4f} 1 0" title="{e((sg.get("label") or "") + " · " + fmt_dur(du))}">{e(txt)}</div>')
    miles = "".join(f'<div><b>{e(m["time"].replace("T", " ").replace("Z", ""))}</b>{e(m["event"])} {ref_chips(m.get("refs"))}</div>' for m in ms)
    leg = "".join(f'<span><i class="b-{lvl(s.get("level"), "s1")}"></i>{e(s.get("label", ""))} · {fmt_dur(durs[i])}</span>' for i, s in enumerate(segs) if i < len(durs))
    return "Incident phases", (f'<div class="card stack"><div class="phase">{"".join(bar)}</div><div class="legend">{leg}</div>'
                               f'<div class="miles">{miles}</div><p class="note">Segment width is proportional to duration. Total {fmt_dur(tot)}.</p></div>')


def s_chain(d, ctx):
    ch = d["narrative"].get("attack_chain", [])
    if not ch:
        return None
    steps = "".join(f'<div class="step{" hot" if c.get("key") else ""}"><span class="tac">{e(c.get("tactic", ""))}</span>'
                    f'<span class="tid">{e(c.get("technique", ""))}</span><span class="tname">{e(c.get("name", ""))}</span>'
                    f'<span>{e(c.get("what", ""))}</span><span class="t">{e(c.get("time", ""))} {ref_chips(c.get("refs"))}</span></div>' for c in ch)
    return "Attack chain (MITRE ATT&CK)", f'<div class="chain">{steps}</div>'


def chart_html(c):
    t = c.get("type")
    if t == "columns":
        body = columns(c["labels"], c["series"], c.get("markers"), h=c.get("height", 250), y_max=c.get("y_max"), label=c.get("title", ""))
        leg = "".join(f'<span><i class="b-{s.get("cls") or SERIES[i % len(SERIES)]}"></i>{e(s["name"])}</span>' for i, s in enumerate(c["series"]))
        if c.get("markers"):
            leg += '<span><i class="b-crit"></i>response events</span>'
        body = (f'<div class="legend">{leg}</div>' if len(c["series"]) > 1 or c.get("markers") else "") + f'<div class="chart">{body}</div>'
    elif t == "hbar":
        body = hbars(c["rows"], c.get("unit", ""))
    elif t == "split":
        tot = sum(p["value"] for p in c["parts"]) or 1
        body = '<div class="split">' + "".join(
            f'<div class="b-{p.get("cls") or SERIES[i % len(SERIES)]}" style="flex:{p["value"] / tot:.4f} 1 0" title="{e(p.get("tip") or p["label"])}">{e(fnum(p["value"]) if p["value"] / tot >= 0.07 else "")}</div>'
            for i, p in enumerate(c["parts"])) + "</div>"
        body += '<div class="legend">' + "".join(
            f'<span><i class="b-{p.get("cls") or SERIES[i % len(SERIES)]}"></i>{e(p["label"])} · {fnum(p["value"])}</span>'
            for i, p in enumerate(c["parts"])) + "</div>"
    elif t == "line":
        xf = c.get("x_format", "{x}")
        body = line_chart(c["x"], c["series"], c.get("y_max"), c.get("y_suffix", ""), c.get("x_ticks"), xf, c.get("reference"), label=c.get("title", ""))
        leg = "".join(f'<span><i class="b-{s.get("cls") or SERIES[i % len(SERIES)]}"></i>{e(s.get("name", ""))}</span>' for i, s in enumerate(c["series"]))
        body = f'<div class="legend">{leg}</div><div class="chart">{body}</div>'
    elif t == "donut":
        body = f'<div class="chart">{donut(c["parts"], c.get("center", ""), c.get("sub", ""))}</div>'
    elif t == "waffle":
        body = waffle(c["groups"])
    else:
        return ""
    note = f'<p class="note">{e(c.get("note", ""))} {ref_chips(c.get("refs"))}</p>' if c.get("note") or c.get("refs") else ""
    return f'<div class="card stack"><h3>{e(c.get("title", ""))}</h3>{body}{note}</div>'


def s_charts(d, ctx):
    cs = [c for c in d["narrative"].get("charts", []) if ctx["audience"] in c.get("audience", ["technical"])]
    if not cs:
        return None
    wide = [chart_html(c) for c in cs if c.get("type") in ("columns", "line")]
    small = [chart_html(c) for c in cs if c.get("type") not in ("columns", "line")]
    return "Activity and data", "".join(wide) + (f'<div class="grid2">{"".join(small)}</div>' if small else "")


def s_items(d, ctx):
    if not d["items"]:
        return None
    rows = "".join(f'<tr><td class="mono">{e(i["id"])}</td><td>{e(i["title"])}<div class="note mono">{e(i["file"])}</div></td><td>{pill(i["status"] or "Open")}</td>'
                   f'<td class="num">{len(i["facts"])}</td></tr>' for i in d["items"] if i["id"] != "00")
    counts = {}
    for i in d["items"]:
        if i["id"] != "00":
            counts[i["status"] or "Open"] = counts.get(i["status"] or "Open", 0) + 1
    parts = [{"label": k, "value": v, "cls": pill_cls(k)} for k, v in counts.items()]
    return "Findings by plan item", (f'<div class="grid-side"><div class="tbl"><table><thead><tr><th>#</th><th>Question</th><th>Status</th><th>Facts</th></tr></thead>'
                                     f'<tbody>{rows}</tbody></table></div><div class="card chart">{donut(parts, str(sum(counts.values())), "items")}</div></div>')


def s_timeline(d, ctx):
    if not d["timeline"]:
        return None
    ok_rx = re.compile(r"inactive|deleted|disabled|revoked|isolated|no actor|blocked|re-check|password reset|reset by|rotated|removed|contained", re.I)
    ev = "".join(f'<div class="ev {"ok" if ok_rx.search(t["event"]) else "key" if t["key"] else ""}"><time>{e(t["time"])}</time>'
                 f'<div><div>{e(re.sub(r"\s*\([^)]*\)\s*$", "", t["event"]))} {ref_chips(t["refs"])}</div><div class="who">{e(t["who"])}</div></div></div>'
                 for t in d["timeline"])
    return "Timeline (UTC)", f'<div class="card flow"><div class="tl">{ev}</div><p class="note">Red marks a key actor event, green a response action.</p></div>'


def coverage_table(d, labels=True):
    cov = d["coverage"]
    if not cov["rows"]:
        return ""
    lab = {"ok": "checked", "na": "n/a", "gap": "partial", "missing": "missing", "empty": "?", "error": "error"}
    head = "".join(f"<th>{e(i)}</th>" for i in cov["items"])
    body = ""
    for r in cov["rows"]:
        cells = ""
        for i, c in enumerate(r["cells"]):
            rr = c["refs"]
            txt = (" ".join(rr[:2]) + (f" +{len(rr) - 2}" if len(rr) > 2 else "")) if rr and c["state"] != "na" else lab[c["state"]]
            cells += f'<td><span class="cell c-{c["state"]}" title="{e(r["source"] + " x " + (cov["items"][i] if i < len(cov["items"]) else "") + ": " + (c["text"] or "empty"))}">{e(txt)}</span></td>'
        body += f'<tr><td class="srccol">{e(r["source"])}</td>{cells}</tr>'
    leg = ('<div class="legend"><span><span class="cell c-ok">w1</span> checked</span><span><span class="cell c-gap">G1</span> checked, part missing</span>'
           '<span><span class="cell c-na">n/a</span> not applicable</span><span><span class="cell c-missing">G2</span> data missing</span>'
           '<span><span class="cell c-empty">?</span> not checked</span></div>')
    dense = " dense" if len(cov["items"]) > 6 else ""
    return f'<div class="tbl"><table class="cov{dense}"><thead><tr><th>Source \\ plan item</th>{head}</tr></thead><tbody>{body}</tbody></table></div>{leg}'


def s_coverage(d, ctx):
    t = coverage_table(d)
    return ("Source coverage", t) if t else None


def s_iocs(d, ctx):
    if not d["iocs"]:
        return None
    rows = "".join(f'<tr><td>{e(i["type"])}</td><td class="mono">{e(i["value"])}</td><td class="mono">{e(i["first_seen"])}</td><td class="small">{e(i["source"])}</td></tr>' for i in d["iocs"])
    return "Indicators of compromise", f'<div class="tbl"><table><thead><tr><th>Type</th><th>Value (defanged)</th><th>First seen UTC</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table></div>'


def s_creds(d, ctx):
    if not d["credentials"]:
        return None
    rows = "".join(f'<tr><td>{e(c["credential"])}</td><td>{e(c["how"])}</td><td>{e(c["used"])}</td><td>{pill(short_status(c["rotated"]) or "unknown")}{note_if_longer(c["rotated"])}</td></tr>' for c in d["credentials"])
    return "Exposed credentials", f'<div class="tbl"><table><thead><tr><th>Credential</th><th>How the actor got it</th><th>Used by actor</th><th>Rotated / revoked</th></tr></thead><tbody>{rows}</tbody></table></div>'


def retention_bars(d, as_of):
    rows = []
    for g in d["gaps"]:
        days = (parse_utc(g["deadline"]) - as_of).days if g["deadline"] else None
        if days is None:
            bar = '<span class="note">no known deadline</span>'
        else:
            cls = "crit" if days <= 7 else "warn" if days <= 30 else "s1"
            bar = f'<div class="prow2"><div class="ptrack"><div class="b-{cls}" style="width:{min(max(days, 0) / 90, 1) * 100:.1f}%"></div></div><span class="mono">{max(days, 0)} d</span></div><div class="note">until {e(g["deadline"])}</div>'
        rows.append(f'<tr><td class="mono">{e(g["id"])}</td><td>{e(g["missing"])}</td><td class="mono">{e(g["items"])}</td><td class="wcol">{bar}</td><td>{pill(short_status(g["status"]) or "open")}{note_if_longer(g["status"])}</td></tr>')
    return ('<div class="tbl"><table><thead><tr><th>ID</th><th>Missing data</th><th>Items</th><th>Until the source deletes it</th><th>Status</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div><p class="note">Bar scale: 90 days. Red: 7 days or less.</p>')


def s_gaps(d, ctx):
    return ("Data gaps and retention", retention_bars(d, ctx["as_of"])) if d["gaps"] else None


def s_recs(d, ctx, open_only=False):
    rs = d["recommendations"]
    if open_only:
        rs = [r for r in rs if not r["status"].lower().startswith("done") and r["priority"].lower() in ("critical", "high")]
    if not rs:
        return None
    rows = "".join(f'<tr><td><span class="sev bg-{SEV_CLS.get(r["priority"].title(), "na")}">{e(r["priority"])}</span></td><td>{e(r["action"])}</td>'
                   f'<td>{ref_chips(refs(r["why"]) or [plain(r["why"])])}</td><td>{e(r["owner"])}</td><td>{pill(short_status(r["status"]) or "Not checked")}{note_if_longer(r["status"])} {ref_chips(W_RX.findall(r["evidence"]) and ["w" + x for x in W_RX.findall(r["evidence"])])}</td></tr>' for r in rs)
    return ("What is left to do" if open_only else "Recommendations"), f'<div class="tbl"><table><thead><tr><th>Priority</th><th>Action</th><th>Why</th><th>Owner</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>'


def s_evidence(d, ctx):
    ev = d["narrative"].get("evidence", [])
    if not ev:
        return None
    out, seen = [], set()
    for c in ev:
        qs = ""
        for r in c.get("refs", []):
            w = d["worklog"].get(r)
            if w and r in seen:
                qs += f'<div class="q"><div class="qh">{e(r)}: query and result shown above</div></div>'
            elif w:
                seen.add(r)
                note = f'<div class="qh">{e(w["note"])}</div>' if w.get("note") else ""
                qs += f'<div class="q"><div class="qh">{e(r)} · {e(w["utc"])} UTC · {e(w["source"])}</div><pre>{e(w["query"])}</pre>{note}<div class="res">Result: {e(w["result"])}</div></div>'
        out.append(f'<div class="evi"><div class="evh"><strong>{e(c["claim"])}</strong> {pill(c.get("status", "Confirmed"))} {ref_chips(c.get("refs"))}</div>{qs}</div>')
    return "Evidence", '<p class="note">Each claim of this report with the exact query and result from the worklog.</p><div class="card flow">' + "".join(out) + "</div>"


def s_method(d, ctx):
    src = "".join(f'<tr><td>{e(s["name"])}</td><td>{e(s["type"])}</td><td>{e(s["covers"])}</td></tr>' for s in d["sources"])
    notes = "".join(f"<li>{e(n)}</li>" for n in d["narrative"].get("methodology_notes", []))
    gaps = "".join(f'<li>{e(g["id"])}: {e(short_text(g["missing"]))} ({e(short_status(g["status"]))})</li>' for g in d["gaps"] if g["state"] not in ("received", "closed"))
    return "Method and limits", (f'<div class="grid2"><div class="tbl"><table><thead><tr><th>Source</th><th>Type</th><th>Covers</th></tr></thead><tbody>{src}</tbody></table></div>'
                                 f'<div class="card small"><ul class="plainlist"><li>All times are UTC.</li><li>Indicators are defanged; secrets are never included.</li>'
                                 f'<li>Item statuses: Confirmed, Partially, Not determinable, Discarded.</li><li>A negative result counts only on a field that is filled in the source and window checked.</li>'
                                 f'{notes}{"<li>Data we could not check:<ul>" + gaps + "</ul></li>" if gaps else ""}</ul></div></div>')


# executive
def s_exec_top(d, ctx):
    n = d["narrative"]
    ks = s_kpis(d, ctx)
    return None, (f'<div class="grid-side rev"><div class="card chart center">{severity_gauge(n.get("severity"))}<div class="note">Severity, SEV-1 is the highest</div></div>'
                  f'{ks[1] if ks else ""}</div>')


def s_story(d, ctx):
    st = d["narrative"].get("story", [])
    if not st:
        return None
    return "What happened", '<div class="story">' + "".join(f'<div><b>{e(s.get("time", ""))}</b><strong>{e(s.get("title", ""))}</strong><span>{e(s.get("text", ""))}</span></div>' for s in st) + "</div>"


def s_questions(d, ctx):
    qs = d["narrative"].get("key_questions", [])
    if not qs:
        return None
    out = []
    for q in qs:
        c = int(q.get("confidence", 0))
        bars = "".join(f'<i class="{"on" if i <= c else ""}"></i>' for i in range(1, 6))
        out.append(f'<div class="qcard"><h3>{e(q["question"])}</h3>{pill(q.get("status", ""))}<p>{e(q.get("answer", ""))}</p>'
                   f'<div class="conf">{bars}<span>confidence {c}/5</span></div></div>')
    return "Answers to the key questions", '<div class="grid2">' + "".join(out) + "</div>"


def s_assets(d, ctx):
    a = d["narrative"].get("impact", {}).get("assets", [])
    if not a:
        return None
    return f"State of {fnum(sum(x['value'] for x in a))} assets in scope", f'<div class="card stack">{waffle(a)}<p class="note">One square is one asset.</p></div>'


def s_services(d, ctx):
    sv = d["narrative"].get("impact", {}).get("services", [])
    if not sv:
        return None
    if not any(s.get("downtime_hours") for s in sv):
        notes = any(s.get("note") for s in sv)
        rows = "".join(f'<tr><td>{e(s["name"])}</td><td>{pill(s.get("status", ""), lvl(s.get("level"), "na"))}</td>'
                       + (f'<td class="note">{e(s.get("note", ""))}</td>' if notes else "") + "</tr>" for s in sv)
        head = "<th>Service</th><th>State</th>" + ("<th>Note</th>" if notes else "")
        return "Business services", f'<div class="tbl"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    mx = max([s.get("downtime_hours", 0) for s in sv] + [1])
    rows = "".join(f'<div class="hrow wide" title="{e(s["name"])}: {fnum(s.get("downtime_hours", 0))} h, {e(s.get("status", ""))}"><span class="lab">{e(s["name"])}</span>'
                   f'<div class="track"><div class="bar b-s1" style="width:{s.get("downtime_hours", 0) / mx * 100:.1f}%"></div></div>'
                   f'<span class="val">{fnum(s.get("downtime_hours", 0))} h {pill(s.get("status", ""), lvl(s.get("level"), "na"))}</span></div>' for s in sv)
    return "Business services downtime", f'<div class="card"><div class="hbars">{rows}</div></div>'


def s_recovery(d, ctx):
    r = d["narrative"].get("impact", {}).get("recovery", {})
    if not r or not r.get("x"):
        return None
    ch = line_chart(r["x"], [{"name": "available", "values": r["values"], "area": True, "cls": "s1"}], 100, "%",
                    r.get("x_ticks"), "+{x} h", [{"value": 100, "label": "normal operation"}], label="Recovery")
    return "Recovery of critical services", f'<div class="card stack"><div class="chart">{ch}</div><p class="note">{e(r.get("note", "Share of critical services available, hours after impact."))}</p></div>'


def s_progress(d, ctx):
    if not d["tracker"]:
        return None
    rows = ""
    for p in d["tracker"]:
        tot = len(p["tasks"])
        done = sum(1 for t in p["tasks"] if t["status"].lower().startswith(("done", "not determinable")))
        pc = round(100 * done / tot) if tot else 0
        rows += f'<div class="prow"><span>{e(p["phase"])}</span><div class="ptrack" title="{done} of {tot} tasks done"><div class="b-acc" style="width:{pc}%"></div></div><span class="mono">{f"{done}/{tot}" if tot else "-"}</span></div>'
    return "Progress by NIST SP 800-61 phase", f'<div class="card"><div class="prog">{rows}</div><p class="note">Closed tasks out of all tasks in the case tracker.</p></div>'


def s_risks(d, ctx):
    rs = d["narrative"].get("risks", [])
    return ("Remaining risks", f'<div class="card">{risk_matrix(rs)}</div>') if rs else None


def s_decisions(d, ctx):
    ds = d["narrative"].get("decisions", [])
    if not ds:
        return None
    rows = ""
    for x in ds:
        dl = x.get("deadline_utc", "")
        t = parse_utc(dl)
        left = ""
        if t:
            hrs = (t - ctx["as_of"]).total_seconds() / 3600
            left = f", {fmt_dur(max(hrs, 0) * 3600)} left" if hrs > 0 else ", overdue"
        rows += f'<tr><td>{e(x["decision"])}</td><td>{e(x.get("why", ""))}</td><td>{pill((dl.replace("T", " ").replace("Z", " UTC") + left) if dl else (x.get("deadline_text") or "no fixed deadline"), lvl(x.get("level"), "na") if dl else "na")}</td><td>{e(x.get("owner", ""))}</td></tr>'
    return "Decisions we need from you", f'<div class="tbl"><table><thead><tr><th>Decision</th><th>Why now</th><th>Deadline</th><th>Owner</th></tr></thead><tbody>{rows}</tbody></table></div>'


# quality
def s_q_score(d, ctx):
    q = d["quality"]
    cats = "".join(f'<div class="cat" title="{e(c["detail"])}"><span>{e(c["name"])}</span><span class="w">x{c["weight"]}%</span><span class="s">{c["score"]}</span>'
                   f'<div class="mini"><div class="b-{"good" if c["score"] >= 80 else "warn" if c["score"] >= 50 else "crit"}" style="width:{c["score"]}%"></div></div><span class="cd note">{e(c["detail"])}</span></div>' for c in q["categories"])
    return "Overall score", f'<div class="card scorebox"><div class="chart">{score_gauge(q["score"], sum(1 for f in q["findings"] if f["severity"] == "Critical"))}</div><div>{cats}</div></div>'


def s_q_profile(d, ctx):
    q = d["quality"]
    cnt = [{"label": s, "value": sum(1 for f in q["findings"] if f["severity"] == s), "cls": SEV_CLS[s]} for s in SEV_CLS]
    return None, (f'<div class="grid2"><div class="card stack"><h3>Profile by category</h3><div class="chart">{radar(q["categories"])}</div></div>'
                  f'<div class="card stack"><h3>Findings by severity</h3><div class="chart">{donut(cnt, str(len(q["findings"])), "findings")}</div></div></div>')


def s_q_findings(d, ctx):
    fs = d["quality"]["findings"]
    if not fs:
        return "What to fix", '<div class="card">No findings. Every check passed.</div>'
    rows = "".join(f'<tr><td><span class="sev bg-{SEV_CLS[f["severity"]]}">{e(f["severity"])}</span></td><td class="mono small">{e(f["file"])}<div class="note">{e(f["where"])}</div></td>'
                   f'<td>{e(f["issue"])}</td><td>{e(f["fix"])}</td></tr>' for f in fs)
    return "What to fix", f'<div class="tbl"><table><thead><tr><th>Severity</th><th>File</th><th>Issue</th><th>Fix</th></tr></thead><tbody>{rows}</tbody></table></div>'


def s_q_retention(d, ctx):
    rt = [r for r in d["quality"]["retention"]]
    if not rt:
        return None
    rows = [{"label": f'{r["id"]} {r["label"][:60]}', "value": max(r["days"], 0) if r["days"] is not None else 0,
             "text": None if r["days"] is not None else "no deadline",
             "level": "critical" if (r["days"] is not None and r["days"] <= 7) else "warning" if (r["days"] is not None and r["days"] <= 30) else None,
             "tip": f'{r["id"]}: ' + (f'{r["days"]} days, until {r["deadline"]}' if r["days"] is not None else "no known deadline") + f', {r["state"]}'} for r in rt]
    return "Days until the data is deleted", f'<div class="card">{hbars(rows, "d")}<p class="note">Open, requested and unavailable gaps. Red: 7 days or less.</p></div>'


SECTIONS = {
    "technical": [("kpis", s_kpis), ("phases", s_phases), ("attack_chain", s_chain), ("charts", s_charts), ("items", s_items),
                  ("timeline", s_timeline), ("coverage", s_coverage), ("iocs", s_iocs), ("credentials", s_creds),
                  ("data_gaps", s_gaps), ("recommendations", s_recs), ("evidence", s_evidence), ("method", s_method)],
    "executive": [("overview", s_exec_top), ("story", s_story), ("key_questions", s_questions), ("assets", s_assets),
                  ("services", s_services), ("recovery", s_recovery), ("charts", s_charts), ("progress", s_progress),
                  ("risks", s_risks), ("decisions", s_decisions), ("open_actions", lambda d, c: s_recs(d, c, True))],
    "quality": [("score", s_q_score), ("profile", s_q_profile), ("findings", s_q_findings), ("coverage", s_coverage),
                ("retention", s_q_retention), ("items", s_items), ("progress", s_progress)],
}
AUD_TITLE = {"technical": "Technical incident report", "executive": "Executive incident report",
             "quality": "Case quality review", "portfolio": "Incident portfolio"}


# ---------------------------------------------------------------- page
CSS = r"""
:root{--bg:#f3f5f8;--surface:#fff;--surface2:#f7f8fa;--ink:#12161c;--ink2:#4a5260;--muted:#6f7886;--line:#dde2e8;
--acc:#2140a8;--acc-soft:#e7ecfa;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s7:#6250d6;
--q1:#cde2fb;--q2:#9ec5f4;--q3:#5598e7;--q4:#256abf;--q5:#104281;
--good:#0ca30c;--warn:#fab219;--serious:#ec835a;--crit:#d03b3b;--na:#c3c9d2;
--good-bg:#e3f5e3;--warn-bg:#fdf1d4;--serious-bg:#fbe6dc;--crit-bg:#f9e0e0;--na-bg:#eceff3;
--f-body:"Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;--f-mono:"Cascadia Mono",Consolas,"SFMono-Regular",Menlo,monospace;color-scheme:light}
@media screen and (prefers-color-scheme:dark){:root{--bg:#0f1217;--surface:#171b21;--surface2:#1c2128;--ink:#eef1f5;--ink2:#b7bec9;--muted:#8a93a1;--line:#2a3039;
--acc:#93a9ff;--acc-soft:#1e2640;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s7:#9085e9;--q1:#16263d;--q2:#184f95;--q3:#2a78d6;--q4:#6da7ec;--q5:#cde2fb;
--na:#3b424d;--good-bg:#11301a;--warn-bg:#3a2f10;--serious-bg:#3b2318;--crit-bg:#3d1b1b;--na-bg:#232931;color-scheme:dark}}
*{box-sizing:border-box}html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.55 var(--f-body)}
.wrap{max-width:1120px;margin:0 auto;padding:28px max(16px,env(safe-area-inset-left,0px)) 56px;display:grid;gap:26px}
header.rh{display:grid;gap:12px;padding-bottom:20px;border-bottom:2px solid var(--ink)}
.eyebrow{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600}
.tlp{background:#000;padding:2px 8px;border-radius:3px;font-family:var(--f-mono);letter-spacing:.04em}
.tlp-CLEAR{color:#fff}.tlp-GREEN{color:#33ff00}.tlp-AMBER,.tlp-AMBER-STRICT{color:#ffc000}.tlp-RED{color:#ff2b2b}
.draft{background:var(--crit);color:#fff;padding:2px 8px;border-radius:3px}
h1{font-size:30px;line-height:1.18;margin:0;font-weight:700;letter-spacing:-.01em;text-wrap:balance}
h2{font-size:18px;margin:0;font-weight:650;display:flex;gap:10px;align-items:baseline;text-wrap:balance}
h2 .n{font-family:var(--f-mono);font-size:12.5px;color:var(--acc)}
h3{font-size:14.5px;margin:0;font-weight:650}
p{margin:0;max-width:78ch}.lead{font-size:16px;color:var(--ink2);max-width:82ch}
.verdict{background:var(--surface);border:1px solid var(--line);border-left:5px solid var(--crit);border-radius:8px;padding:16px 18px;font-size:15.5px}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:10px 22px;font-size:13px}
.meta div{display:grid;gap:2px;min-width:0}.meta b{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.meta span{font-family:var(--f-mono);font-size:12.5px;overflow-wrap:anywhere}
section{display:grid;gap:12px;break-inside:auto}
.card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:16px;min-width:0;break-inside:avoid}
.card.flow{break-inside:auto}.stack{display:grid;gap:12px;align-content:start}.center{justify-items:center;text-align:center}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.grid-side{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:14px;align-items:start}
.grid-side.rev{grid-template-columns:260px minmax(0,1fr)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:10px;break-inside:avoid}
.kpi{background:var(--surface);border:1px solid var(--line);border-top:3px solid var(--na);border-radius:8px;padding:12px 14px;display:grid;gap:3px;align-content:start}
.kpi .v{font-size:25px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.1}.kpi .v small{font-size:13px;font-weight:500;color:var(--ink2)}
.kpi .l{font-size:12.5px;color:var(--ink2)}.kpi .r{font-family:var(--f-mono);font-size:10.5px;color:var(--muted)}
.k-crit{border-top-color:var(--crit)}.k-serious{border-top-color:var(--serious)}.k-warn{border-top-color:var(--warn)}.k-good{border-top-color:var(--good)}
.note{font-size:12px;color:var(--muted)}.small{font-size:12px}.mono{font-family:var(--f-mono);font-size:12px}.num{text-align:right;font-variant-numeric:tabular-nums}
.ref{font-family:var(--f-mono);font-size:10.5px;color:var(--acc);background:var(--acc-soft);padding:1px 5px;border-radius:4px;white-space:nowrap}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;padding:2px 9px;border-radius:999px;white-space:nowrap;color:var(--ink)}
.pill::before{content:"";width:7px;height:7px;border-radius:50%}
.p-good{background:var(--good-bg)}.p-good::before{background:var(--good)}.p-warn{background:var(--warn-bg)}.p-warn::before{background:var(--warn)}
.p-serious{background:var(--serious-bg)}.p-serious::before{background:var(--serious)}.p-crit{background:var(--crit-bg)}.p-crit::before{background:var(--crit)}
.p-na{background:var(--na-bg)}.p-na::before{background:var(--na)}
.sev{font-family:var(--f-mono);font-size:10.5px;font-weight:600;padding:2px 7px;border-radius:4px;white-space:nowrap}
.bg-crit{background:var(--crit-bg)}.bg-serious{background:var(--serious-bg)}.bg-warn{background:var(--warn-bg)}.bg-good{background:var(--good-bg)}.bg-na{background:var(--na-bg)}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13px}thead{display:table-header-group}tr{break-inside:avoid}
th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;padding:9px 11px;border-bottom:1px solid var(--line);background:var(--surface2);white-space:nowrap}
td{padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top;font-variant-numeric:tabular-nums}tr:last-child td{border-bottom:0}
.legend{display:flex;flex-wrap:wrap;gap:5px 14px;font-size:12px;color:var(--ink2)}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.chart svg{display:block;width:100%;height:auto;overflow:visible}.chart text,svg text{fill:var(--ink2);font:11px var(--f-body)}
svg .big{font-size:26px;font-weight:700;fill:var(--ink)}svg .huge{font-size:46px;font-weight:700;fill:var(--ink)}
.axis{stroke:var(--line)}.grid,.rgrid{stroke:var(--line);stroke-dasharray:2 3;fill:none}
.mark{stroke:var(--crit);stroke-width:2;stroke-dasharray:4 3}.markt{fill:var(--crit)!important;font-weight:600}
.f-s1{fill:var(--s1)}.f-s2{fill:var(--s2)}.f-s3{fill:var(--s3)}.f-s4{fill:var(--s4)}.f-s7{fill:var(--s7)}.f-na{fill:var(--na)}
.f-good{fill:var(--good)}.f-warn{fill:var(--warn)}.f-serious{fill:var(--serious)}.f-crit{fill:var(--crit)}
.b-s1{background:var(--s1)}.b-s2{background:var(--s2)}.b-s3{background:var(--s3)}.b-s4{background:var(--s4)}.b-s7{background:var(--s7)}.b-na{background:var(--na)}
.b-good{background:var(--good)}.b-warn{background:var(--warn)}.b-serious{background:var(--serious)}.b-crit{background:var(--crit)}.b-acc{background:var(--acc)}
.ln-s1,.ln-s2,.ln-s3,.ln-s4,.ln-s7,.ln-na{fill:none;stroke-width:2;stroke-linejoin:round}.ln-s1{stroke:var(--s1)}.ln-s2{stroke:var(--s2)}.ln-s3{stroke:var(--s3)}.ln-s4{stroke:var(--s4)}.ln-s7{stroke:var(--s7)}.ln-na{stroke:var(--muted)}.dash{stroke-dasharray:5 4}
.area-s1{fill:var(--s1);opacity:.13}.area-s2{fill:var(--s2);opacity:.13}.area-s3{fill:var(--s3);opacity:.13}
.dot-s1,.dot-s2,.dot-s3,.dot-s4,.dot-s7{stroke:var(--surface);stroke-width:2}.dot-s1{fill:var(--s1)}.dot-s2{fill:var(--s2)}.dot-s3{fill:var(--s3)}.dot-s4{fill:var(--s4)}.dot-s7{fill:var(--s7)}
.rarea{fill:var(--s1);fill-opacity:.18;stroke:var(--s1);stroke-width:2}
.track{fill:none;stroke:var(--surface2);stroke-width:20}.st-good,.st-warn,.st-crit{fill:none;stroke-width:20;stroke-linecap:round}.st-good{stroke:var(--good)}.st-warn{stroke:var(--warn)}.st-crit{stroke:var(--crit)}
.band-good,.band-warn,.band-serious,.band-crit{fill:none;stroke-width:22;opacity:.28}.band-good{stroke:var(--good)}.band-warn{stroke:var(--warn)}.band-serious{stroke:var(--serious)}.band-crit{stroke:var(--crit)}.on{opacity:1}
.needle{stroke:var(--ink);stroke-width:3;stroke-linecap:round}.hub{fill:var(--ink)}
.donut{max-width:210px;margin:0 auto}
.hbars{display:grid;gap:7px}.hrow{display:grid;grid-template-columns:minmax(110px,200px) 1fr 76px;gap:10px;align-items:center;font-size:12.5px}
.hrow.wide{grid-template-columns:minmax(110px,160px) 1fr 170px}
.hrow .track{height:13px;background:var(--surface2);border-radius:0 4px 4px 0}.hrow .bar{height:100%;border-radius:0 4px 4px 0;min-width:2px}
.hrow .val{font-family:var(--f-mono);font-size:11.5px;text-align:right}.hrow .lab{overflow-wrap:anywhere}
.phase,.split{display:flex;height:32px;border-radius:6px;overflow:hidden;gap:2px}
.phase div,.split div{display:flex;align-items:center;justify-content:center;font-size:11.5px;font-weight:600;color:#fff;min-width:30px;white-space:nowrap;overflow:hidden;padding:0 6px}
.split div{justify-content:flex-start}
.miles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;font-size:12px}
.miles div{border-left:2px solid var(--line);padding-left:9px}.miles b{display:block;font-family:var(--f-mono);font-size:11.5px}
.chain{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:10px}
.step{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:11px;display:grid;gap:4px;align-content:start;font-size:12.5px;break-inside:avoid}
.step.hot{border-color:var(--crit);box-shadow:inset 3px 0 0 var(--crit)}
.step .tac{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:600}
.step .tid{font-family:var(--f-mono);font-size:12px;color:var(--acc);font-weight:600}.step .tname{font-weight:600}.step .t{font-family:var(--f-mono);font-size:10.5px;color:var(--ink2)}
.tl{border-left:2px solid var(--line);margin-left:6px}
.tl .ev{display:grid;grid-template-columns:170px 1fr;gap:14px;padding:7px 0 7px 18px;position:relative;break-inside:avoid}
.tl .ev::before{content:"";position:absolute;left:-7px;top:12px;width:12px;height:12px;border-radius:50%;background:var(--surface);border:2px solid var(--muted)}
.tl .ev.key::before{background:var(--crit);border-color:var(--crit)}.tl .ev.ok::before{background:var(--good);border-color:var(--good)}
.tl time{font-family:var(--f-mono);font-size:11.5px;color:var(--ink2)}.tl .who{font-size:11.5px;color:var(--muted)}
.cov td{text-align:center}.cov td.srccol{text-align:left;white-space:nowrap}
.cell{display:inline-block;min-width:62px;padding:3px 6px;border-radius:4px;font-size:11px;font-weight:600}
.c-ok{background:var(--good-bg)}.c-na{background:var(--na-bg);color:var(--muted)}.c-gap{background:var(--warn-bg)}.c-missing,.c-error{background:var(--crit-bg)}
.c-empty{border:1.5px dashed var(--crit);color:var(--crit)}
.cov.dense .cell{min-width:0;padding:2px 4px;font-size:10px}.cov.dense td,.cov.dense th{padding:5px 4px}
.prow,.prow2{display:grid;grid-template-columns:minmax(120px,240px) 1fr 50px;gap:10px;align-items:center;font-size:12.5px}.prow2{grid-template-columns:1fr 46px}
.prog{display:grid;gap:9px}.ptrack{height:10px;border-radius:5px;background:var(--surface2);overflow:hidden;border:1px solid var(--line)}.ptrack div{height:100%}
.wcol{min-width:170px}
.evi{padding:10px 0;border-bottom:1px solid var(--line);break-inside:avoid}.evi:last-child{border-bottom:0}.evh{display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}
.q{margin-top:7px;background:var(--surface2);border:1px solid var(--line);border-radius:6px;padding:9px 10px;font-size:12px}
.q pre{margin:4px 0;font-family:var(--f-mono);font-size:11.5px;white-space:pre-wrap;overflow-wrap:anywhere}.q .qh{font-family:var(--f-mono);font-size:10.5px;color:var(--muted)}.q .res{color:var(--ink2)}
.story{display:grid;grid-template-columns:repeat(auto-fit,minmax(108px,1fr));border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--surface);break-inside:avoid}
.story div{padding:13px;border-right:1px solid var(--line);display:grid;gap:3px;align-content:start}.story div:last-child{border-right:0}
.story b{font-family:var(--f-mono);font-size:11px;color:var(--acc)}.story span{font-size:12.5px;color:var(--ink2)}
.qcard{display:grid;grid-template-columns:1fr auto;gap:6px 12px;padding:14px;border:1px solid var(--line);border-radius:8px;background:var(--surface);break-inside:avoid}
.qcard p{grid-column:1/-1;font-size:13px;color:var(--ink2)}.conf{grid-column:1/-1;display:flex;gap:3px;align-items:center;font-size:11px;color:var(--muted)}
.conf i{width:18px;height:6px;border-radius:2px;background:var(--na)}.conf i.on{background:var(--acc)}.conf span{margin-left:6px}
.waffle{display:grid;grid-template-columns:repeat(30,1fr);gap:3px;max-width:540px}.waffle i{aspect-ratio:1;border-radius:2px;display:block}
.rmwrap{display:grid;grid-template-columns:minmax(0,420px) 1fr;gap:16px;align-items:start}
.rm{display:grid;grid-template-columns:24px repeat(5,1fr);gap:3px}.rm .c{aspect-ratio:1.4;border-radius:4px;display:flex;align-items:center;justify-content:center;gap:3px;flex-wrap:wrap}
.rm .ax{font-size:11px;color:var(--muted);display:flex;align-items:center;justify-content:center}
.rm .tag{background:var(--surface);border:1px solid var(--ink);border-radius:3px;padding:0 4px;font-family:var(--f-mono);font-size:10.5px;font-weight:600}.rml{display:grid;gap:3px}
.scorebox{display:grid;grid-template-columns:280px 1fr;gap:20px;align-items:center}
.cat{display:grid;grid-template-columns:1fr 46px 40px;gap:2px 8px;align-items:center;font-size:13px;padding:6px 0;border-bottom:1px solid var(--line)}.cat:last-child{border-bottom:0}
.cat .w{font-family:var(--f-mono);font-size:10.5px;color:var(--muted);text-align:right}.cat .s{font-family:var(--f-mono);font-weight:700;text-align:right}
.mini{height:5px;border-radius:3px;background:var(--surface2);grid-column:1/-1;overflow:hidden}.mini div{height:100%}.cd{grid-column:1/-1}
.heat td{padding:3px}.heat div{border-radius:4px;text-align:center;padding:5px 0;font-family:var(--f-mono);font-size:11.5px;font-weight:600}
.hq1{background:var(--q1)}.hq2{background:var(--q2)}.hq3{background:var(--q3);color:var(--surface)}.hq4{background:var(--q4);color:var(--surface)}.hq5{background:var(--q5);color:var(--surface)}.hq0{background:var(--surface2);color:var(--muted)}
.plainlist{margin:0;padding-left:18px;display:grid;gap:4px}
footer.rf{border-top:1px solid var(--line);padding-top:12px;font-size:11.5px;color:var(--muted);display:flex;gap:6px 18px;flex-wrap:wrap}
@media (max-width:700px){.grid-side,.grid-side.rev,.scorebox,.rmwrap{grid-template-columns:1fr}.tl .ev{grid-template-columns:1fr;gap:2px}.hrow,.hrow.wide{grid-template-columns:100px 1fr 64px}.waffle{gap:2px}h1{font-size:24px}}
@page{size:A4;margin:14mm 12mm 16mm;@bottom-left{content:var(--pdf-left,"");font:9px sans-serif;color:#6f7886}@bottom-right{content:"Page " counter(page) " of " counter(pages);font:9px sans-serif;color:#6f7886}}
@media print{body{background:#fff;font-size:12.5px}.wrap{padding:0;max-width:none;gap:18px}.card,.tbl,.kpi,.step,.story,.qcard{border-color:#d5dae1}
section{break-inside:auto}h2{break-after:avoid}.tbl{overflow:visible}td{overflow-wrap:break-word}.grid-side{grid-template-columns:minmax(0,1fr) 220px}.grid-side.rev{grid-template-columns:220px minmax(0,1fr)}a{color:inherit;text-decoration:none}}
"""


def page(title, aud, d_meta, header_html, body, tlp, draft, footer):
    tlp_cls = tlp.replace("+", "-")
    left = f"TLP:{tlp} · {d_meta}"
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title><style>{CSS}@page{{@bottom-left{{content:"{e(left)}"}}}}</style></head><body><main class="wrap">'
            f'<header class="rh"><div class="eyebrow"><span class="tlp tlp-{tlp_cls}">TLP:{e(tlp)}</span>{"<span class=draft>DRAFT</span>" if draft else ""}'
            f'<span>{e(AUD_TITLE[aud])}</span><span>· {e(d_meta)}</span></div>{header_html}</header>{body}'
            f'<footer class="rf">{footer}</footer></main></body></html>\n')


def render_case(d, aud, ctx, only=None, skip=None):
    n, m = d["narrative"], d["meta"]
    inc = m.get("incident_id", d["case_dir"])
    title = n.get("title") or f'{m.get("client", "")} {inc}'.strip()
    ctx = dict(ctx, audience=aud)
    parts, num = [], 0
    for sid, fn in SECTIONS[aud]:
        if (only and sid not in only) or (skip and sid in skip):
            continue
        r = fn(d, ctx)
        if not r:
            continue
        t, body = r
        if t:
            num += 1
            parts.append(f'<section id="{sid}"><h2><span class="n">{num:02d}</span>{e(t)}</h2>{body}</section>')
        else:
            parts.append(f'<section id="{sid}">{body}</section>')
    srcs = " · ".join(short_source(s["name"]) for s in d["sources"][:5])
    ends = [b for _, b in (time_range(t["time"]) for t in d["timeline"]) if b]
    meta = [("Client", m.get("client", "")), ("Incident", inc), ("Opened", m.get("opened_utc", "")),
            ("Report", ctx["as_of"].strftime("%Y-%m-%d %H:%MZ")), ("Severity", n.get("severity") or m.get("severity", "")),
            ("Status", n.get("status_label", "")), ("Evidence up to", f"{max(ends):%Y-%m-%d %H:%MZ}" if ends else "")]
    if aud == "technical":
        meta += [("Sources", srcs), ("Lead", m.get("team.lead", ""))]
    mh = "".join(f'<div><b>{e(k)}</b><span>{pill(v) if k == "Status" and v else e(v)}</span></div>' for k, v in meta if v)
    if aud == "quality":
        h1 = f"Case quality: {inc}"
        lead = ('<p class="lead">This review checks the case files against the kit rules: claims without a query, empty coverage cells, '
                'open data gaps, data close to deletion, unproven containment. It does not judge the conclusions.</p>')
    else:
        h1 = title
        lead = (f'<div class="verdict">{e(n.get("summary"))}</div>' if aud == "executive" else f'<p class="lead">{e(n.get("summary"))}</p>') if n.get("summary") else ""
    header = f"<h1>{e(h1)}</h1>{lead}<div class=\"meta\">{mh}</div>"
    foot = "<span>All times UTC</span><span>Indicators defanged</span><span>Generated by ir-casekit report.py from the case files</span>"
    if ctx["draft"]:
        foot += "<span>DRAFT: the case is not complete</span>"
    return page(f"{inc} {AUD_TITLE[aud]}", aud, f"{m.get('client', '')} {inc}".strip(), header, "".join(parts), ctx["tlp"], ctx["draft"], foot)


# ---------------------------------------------------------------- portfolio
def portfolio_data(root, as_of, date_from=None, date_to=None):
    cases = []
    for c in sorted(p for p in Path(root).iterdir() if p.is_dir() and not p.name.startswith(("_", ".")) and (p / "case.md").is_file()):
        d = parse_case(c, as_of)
        rd = c / "report" / "narrative.json"
        nar = {}
        if rd.is_file():
            try:
                nar = json.loads(rd.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        m = d["meta"]
        opened = parse_utc(m.get("opened_utc"))
        if not opened or (date_from and opened < date_from) or (date_to and opened > date_to):
            continue
        fa, de, co, cl = (parse_utc(m.get(k)) for k in ("first_actor_activity_utc", "detected_utc", "contained_utc", "closed_utc"))
        cases.append({
            "id": m.get("incident_id", c.name), "client": m.get("client", ""), "type": m.get("incident_type") or "Unclassified",
            "severity": m.get("severity", ""), "status": m.get("status") or ("closed" if cl else "open"),
            "initial_access": m.get("initial_access") or "Unknown", "opened": opened,
            "days_open": ((cl or as_of) - opened).days,
            "mttd": round((de - fa).total_seconds() / 3600, 1) if fa and de else None,
            "mttc": round((co - de).total_seconds() / 3600, 1) if de and co else None,
            "tactics": sorted({x.get("tactic") for x in nar.get("attack_chain", []) if x.get("tactic")}),
            "gaps": d["gaps"], "recs": d["recommendations"]})
    return cases


TACTICS = ["Reconnaissance", "Resource Development", "Initial Access", "Execution", "Persistence", "Privilege Escalation",
           "Defense Evasion", "Credential Access", "Discovery", "Lateral Movement", "Collection", "Command and Control",
           "Exfiltration", "Impact"]


def render_portfolio(cases, ctx, label):
    if not cases:
        sys.exit("No case folders with case.md (and opened_utc) in the window")
    months = sorted({c["opened"].strftime("%Y-%m") for c in cases})
    types = sorted({c["type"] for c in cases})
    med = lambda xs: round(statistics.median(xs), 1) if xs else None
    mttd = [c["mttd"] for c in cases if c["mttd"] is not None]
    mttc = [c["mttc"] for c in cases if c["mttc"] is not None]
    open_gaps = sum(1 for c in cases for g in c["gaps"] if g["state"] in ("open", "requested"))
    k = [("na", str(len(cases)), "", "cases"), ("serious", fnum(med(mttd)) if mttd else "n/a", "h", "median time to detect"),
         ("good", fnum(med(mttc)) if mttc else "n/a", "h", "median time to contain"), ("warn", str(open_gaps), "", "data requests still open")]
    parts = ['<section><div class="kpis">' + "".join(f'<div class="kpi k-{c}"><div class="v">{e(v)}{f" <small>{u}</small>" if u else ""}</div><div class="l">{e(l)}</div></div>' for c, v, u, l in k) + "</div></section>"]
    num = [0]

    def add(t, body):
        num[0] += 1
        parts.append(f'<section><h2><span class="n">{num[0]:02d}</span>{e(t)}</h2>{body}</section>')

    series = [{"name": t, "values": [sum(1 for c in cases if c["type"] == t and c["opened"].strftime("%Y-%m") == mo) for mo in months]} for t in types]
    leg = "".join(f'<span><i class="b-{SERIES[i % len(SERIES)]}"></i>{e(t)}</span>' for i, t in enumerate(types))
    vec = {}
    for c in cases:
        vec[c["initial_access"]] = vec.get(c["initial_access"], 0) + 1
    add("Cases by month and type", f'<div class="grid2"><div class="card stack"><div class="legend">{leg}</div><div class="chart">{columns(months, series, h=230, label="cases", W=420, y_max=max(4, math.ceil(max(sum(x["values"][i] for x in series) for i in range(len(months))) / 4) * 4))}</div></div>'
        f'<div class="card stack"><h3>How the actor got in</h3>{hbars([{"label": a, "value": v} for a, v in sorted(vec.items(), key=lambda x: -x[1])])}</div></div>')
    ids = [c["id"] for c in cases]
    blocks = []
    for key, name, sla, cls in (("mttd", "Time to detect per case, h", 24, "s2"), ("mttc", "Time to contain per case, h", 4, "s3")):
        pts = [(i, c[key]) for i, c in enumerate(cases) if c[key] is not None]
        if len(pts) >= 2:
            xs, vs = [p[0] for p in pts], [p[1] for p in pts]
            ticks = sorted({xs[0], xs[len(xs) // 2], xs[-1]})
            ch = line_chart(xs, [{"name": name, "values": vs, "cls": cls, "tips": [f"{ids[x]}: {v} h" for x, v in pts]}],
                            nice_max(max(vs + [sla]) * 1.1), "", ticks, lambda x: ids[x], [{"value": sla, "label": f"target {sla} h"}], h=230, label=name, W=440)
            blocks.append(f'<div class="card stack"><h3>{e(name)}</h3><div class="chart">{ch}</div></div>')
        elif pts:
            blocks.append(f'<div class="card stack"><h3>{e(name)}</h3>{hbars([{"label": ids[x], "value": v} for x, v in pts], "h")}</div>')
    if blocks:
        add("Detection and containment speed", f'<div class="grid2">{"".join(blocks)}</div>')
    used = [t for t in TACTICS if any(t in c["tactics"] for c in cases)]
    if used:
        head = "".join(f"<th>{e(mo)}</th>" for mo in months)
        mx = max(sum(1 for c in cases if t in c["tactics"] and c["opened"].strftime("%Y-%m") == mo) for t in used for mo in months) or 1
        rows = ""
        for t in used:
            cells = ""
            for mo in months:
                v = sum(1 for c in cases if t in c["tactics"] and c["opened"].strftime("%Y-%m") == mo)
                q = 0 if not v else max(1, math.ceil(v / mx * 5))
                cells += f'<td><div class="hq{q}" title="{e(t)}, {mo}: {v} case(s)">{v}</div></td>'
            rows += f"<tr><td>{e(t)}</td>{cells}</tr>"
        add("MITRE ATT&CK tactics by month", f'<div class="tbl"><table class="heat"><thead><tr><th>Tactic</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            '<p class="note">Cases with at least one confirmed technique of the tactic (from each case attack chain). Darker means more cases.</p>')
    miss = {}
    for c in cases:
        for g in c["gaps"]:
            key = " ".join(re.sub(r"[`*]", "", g["missing"]).split()[:7])
            miss[key] = miss.get(key, 0) + 1
    rs = {}
    for c in cases:
        for r in c["recs"]:
            s = plain(r["status"]) or "Not checked"
            rs[s] = rs.get(s, 0) + 1
    side = []
    if miss:
        side.append(f'<div class="card stack"><h3>Missing logs, most frequent</h3>{hbars([{"label": a, "value": v, "level": "serious"} for a, v in sorted(miss.items(), key=lambda x: -x[1])[:8]])}</div>')
    if rs:
        side.append(f'<div class="card stack"><h3>Recommendations to clients</h3><div class="chart">{donut([{"label": a, "value": v, "cls": pill_cls(a)} for a, v in rs.items()], str(sum(rs.values())), "actions")}</div></div>')
    if side:
        add("Data gaps and recommendations", f'<div class="grid2">{"".join(side)}</div>')
    rows = "".join(f'<tr><td class="mono">{e(c["id"])}</td><td>{e(c["client"])}</td><td>{e(c["type"])}</td><td class="mono">{e(c["severity"])}</td>'
                   f'<td>{pill(c["status"])}</td><td class="num">{c["days_open"]}</td><td class="num">{fnum(c["mttd"]) if c["mttd"] is not None else "-"}</td><td class="num">{fnum(c["mttc"]) if c["mttc"] is not None else "-"}</td></tr>'
                   for c in sorted(cases, key=lambda c: c["opened"], reverse=True))
    add("All cases", f'<div class="tbl"><table><thead><tr><th>Case</th><th>Client</th><th>Type</th><th>Severity</th><th>Status</th><th>Days open</th><th>Detect, h</th><th>Contain, h</th></tr></thead><tbody>{rows}</tbody></table></div>')
    header = f'<h1>Incident cases {e(label)}</h1><div class="meta"><div><b>Cases</b><span>{len(cases)}</span></div><div><b>Report</b><span>{ctx["as_of"]:%Y-%m-%d %H:%MZ}</span></div></div>'
    foot = "<span>Times to detect and contain come from case.md front matter</span><span>Generated by ir-casekit report.py</span>"
    return page(f"Incident portfolio {label}", "portfolio", label, header, "".join(parts), ctx["tlp"], False, foot)


# ---------------------------------------------------------------- pdf
def find_browser():
    env = os.environ.get("IR_PDF_BROWSER")
    if env and Path(env).exists():
        return env
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome", "brave-browser"):
        p = shutil.which(name)
        if p:
            return p
    cands = []
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            cands += [Path(base) / "Google/Chrome/Application/chrome.exe", Path(base) / "Microsoft/Edge/Application/msedge.exe",
                      Path(base) / "BraveSoftware/Brave-Browser/Application/brave.exe", Path(base) / "Chromium/Application/chrome.exe"]
    cands += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"), Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
              Path("/Applications/Chromium.app/Contents/MacOS/Chromium"), Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")]
    return next((str(p) for p in cands if p.exists()), None)


def weasy():
    try:
        import weasyprint  # noqa: F401  optional
        return True
    except Exception:
        return False


def to_pdf(html_path, pdf_path):
    pdf_path = Path(pdf_path).resolve()  # the browser resolves relative paths against its own folder
    b = find_browser()
    if b:
        with tempfile.TemporaryDirectory() as prof:
            cmd = [b, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={prof}",
                   "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw", f"--print-to-pdf={pdf_path}", Path(html_path).resolve().as_uri()]
            if sys.platform.startswith("linux") and hasattr(os, "geteuid") and os.geteuid() == 0:
                cmd.insert(1, "--no-sandbox")
            try:
                subprocess.run(cmd, check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except (subprocess.SubprocessError, OSError) as ex:
                return f"browser failed ({ex})"
        return None if Path(pdf_path).is_file() else "browser produced no file"
    if weasy():
        import weasyprint
        weasyprint.HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        return None
    return "no PDF engine: install Chrome / Edge / Chromium, set IR_PDF_BROWSER, or pip install weasyprint"


# ---------------------------------------------------------------- cli
def opt(args, name, default=None):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def as_of_arg(args):
    v = opt(args, "--as-of")
    return parse_utc(v) if v else dt.datetime.now(dt.timezone.utc)


def write_outputs(html_text, out_dir, stem, formats):
    out_dir.mkdir(parents=True, exist_ok=True)
    hp = out_dir / f"{stem}.html"
    hp.write_text(html_text, encoding="utf-8")
    done = []
    if "html" in formats:
        done.append(str(hp))
    if "pdf" in formats:
        err = to_pdf(hp, out_dir / f"{stem}.pdf")
        if err:
            print(f"PDF not created for {stem}: {err}. HTML kept at {hp}")
        else:
            done.append(str(out_dir / f"{stem}.pdf"))
    if "html" not in formats and (out_dir / f"{stem}.pdf").is_file():
        hp.unlink()
    return done


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    cmd = a[0]
    if cmd == "sections":
        for aud, secs in SECTIONS.items():
            print(f"{aud}: {', '.join(s for s, _ in secs)}")
        print("portfolio: fixed layout")
        return 0
    if cmd == "pdf-check":
        b = find_browser()
        print(f"Browser: {b}" if b else "Browser: none found")
        print(f"WeasyPrint: {'installed' if weasy() else 'not installed'}")
        return 0 if (b or weasy()) else 1
    if len(a) < 2:
        print(__doc__.strip())
        return 2
    as_of = as_of_arg(a)
    tlp = (opt(a, "--tlp") or ("GREEN" if cmd == "portfolio" else "AMBER")).upper().replace("TLP:", "")
    formats = set((opt(a, "--format") or "html").lower().replace("both", "html,pdf").split(","))
    if cmd == "build":
        build(a[1], as_of)
        return 0
    if cmd == "render":
        case = Path(a[1])
        d = build(case, as_of, quiet=True)
        auds = [x.strip() for x in (opt(a, "--audience") or "technical").split(",") if x.strip()]
        bad = [x for x in auds if x not in SECTIONS]
        if bad:
            sys.exit(f"Unknown audience: {', '.join(bad)} (use technical, executive, quality; portfolio has its own command)")
        only = set((opt(a, "--only") or "").split(",")) - {""}
        skip = set((opt(a, "--skip") or "").split(",")) - {""}
        out = Path(opt(a, "--out") or case / "report")
        ctx = {"as_of": as_of, "tlp": tlp, "draft": "--draft" in a}
        inc = re.sub(r"[^A-Za-z0-9_.-]+", "-", d["meta"].get("incident_id") or case.name)
        for aud in auds:
            missing = [k for k in NEEDS[aud] if not filled(d["narrative"].get(k))]
            if missing:
                print(f"{aud}: narrative missing {', '.join(missing)} (those sections are left out)")
            files = write_outputs(render_case(d, aud, ctx, only, skip), out, f"{inc}-{aud}-{as_of:%Y%m%d}", formats)
            for f in files:
                print(f"Wrote {f}")
        print(f"Quality score {d['quality']['score']}/100")
        return 0
    if cmd == "portfolio":
        root = Path(a[1])
        df, dtto = parse_utc(opt(a, "--from") or ""), parse_utc(opt(a, "--to") or "")
        if dtto:
            dtto += dt.timedelta(days=1)
        cases = portfolio_data(root, as_of, df, dtto)
        if opt(a, "--from") and opt(a, "--to"):
            label = f"{opt(a, '--from')} to {opt(a, '--to')}"
        else:
            label = f"{min(c['opened'] for c in cases):%Y-%m-%d} to {max(c['opened'] for c in cases):%Y-%m-%d}" if cases else ""
        html_text = render_portfolio(cases, {"as_of": as_of, "tlp": tlp}, label)
        out = Path(opt(a, "--out") or root / "_portfolio")
        for f in write_outputs(html_text, out, f"portfolio-{as_of:%Y%m%d}", formats):
            print(f"Wrote {f}")
        return 0
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
