#!/usr/bin/env python3
"""Profile and query a log export (CSV, TSV, JSON, JSONL/NDJSON, optionally .gz) without loading it into the model.

Usage:
  python3 -I log-profile.py <file> [<file> ...]                     profile: rows, time range, fields, fill %, top values
  python3 -I log-profile.py <file> --count-by user.name,source.ip   counts per value combination (top 50)
  python3 -I log-profile.py <file> --where 'source.ip~^203\\.0\\.113' --keep @timestamp,event.action --limit 40
  python3 -I log-profile.py <file> --iocs <case>/iocs.md            hits of every IOC value in any field
  python3 -I log-profile.py <file> --per-day                        events per UTC day (needs a time field)

Options:
  --where FIELD~REGEX   keep rows whose FIELD matches REGEX (case-insensitive); repeat for AND.
                        FIELD=VALUE for an exact match, FIELD!~REGEX to exclude, *~REGEX to match any field.
  --from / --to UTC     time window, ISO (2026-10-15T14:00) on the detected time field.
  --time FIELD          time field to use when auto-detection picks the wrong one.
  --keep F1,F2          fields printed per row (default: time field + 6 most filled fields).
  --limit N             rows printed (default 20) / top values per field in the profile (default 5).
  --max-rows N          stop reading after N rows (default: all).

Output is compact Markdown that can be pasted into worklog.md. Values that look like secrets are masked.
Nested JSON is flattened to dotted keys (a.b.c), also JSON held in a CSV cell (M365 `AuditData` -> AuditData.ClientIP);
Name/Value lists become keys (AuditData.Parameters.MoveToFolder). Time offsets (+02:00) are converted to UTC. Elastic `_source`, Splunk `result` and `{"hits":{"hits":[...]}}`,
`{"resources":[...]}`, `{"data":[...]}`, `{"events":[...]}` wrappers are unwrapped.
Standard library only. Never executes anything from the file.
"""
import csv
import datetime as dt
import gzip
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

TIME_FIELDS = ["@timestamp", "timestamp", "_time", "time", "eventTime", "event_time", "EventTime", "TimeCreated",
               "date", "Date", "ts", "datetime", "event.created", "event.ingested", "creationTime", "CreatedTime",
               "TimeGenerated", "published", "createdAt", "created_at", "timestamp_ms", "ContextTimeStamp"]
SECRET = [re.compile(p) for p in (
    r"AKIA[0-9A-Z]{16}", r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{30,}",
    r"xox[abpr]-[A-Za-z0-9-]{10,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    r"(?i)(password|passwd|pwd|secret|api[_-]?key|token|authorization)(\"?\s*[=:]\s*\"?)([^\s\"&,;]{6,})")]
csv.field_size_limit(1 << 28)
NAIVE = set()  # set when a time value carried no zone (assumed UTC)
OFFSET = set()  # non-UTC offsets seen in time values (converted to UTC)


def mask(s):
    s = str(s)
    for rx in SECRET:
        s = rx.sub(lambda m: (m.group(1) + m.group(2) + "<REDACTED>") if m.lastindex and m.lastindex >= 3 else "<REDACTED>", s)
    return s


def short(v, n=70):
    s = mask(v).replace("\n", " ").replace("|", "\\|")
    return s if len(s) <= n else s[: n - 1] + "…"


def name_value(obj):
    """[{"Name": "From", "Value": "x"}, ...] (M365 audit Parameters, ExtendedProperties) -> {"From": "x"}."""
    if isinstance(obj, list) and obj and len(obj) <= 60 and all(isinstance(x, dict) and "Name" in x for x in obj):
        return {str(x["Name"]): (x.get("Value") if set(x) <= {"Name", "Value"} else {k: v for k, v in x.items() if k != "Name"})
                for x in obj}
    return obj


def flatten(obj, prefix="", out=None, depth=0):
    out = {} if out is None else out
    obj = name_value(obj)
    if isinstance(obj, dict) and depth < 6:
        for k, v in obj.items():
            flatten(v, f"{prefix}.{k}" if prefix else str(k), out, depth + 1)
    elif isinstance(obj, list) and obj and all(not isinstance(x, (dict, list)) for x in obj):
        out[prefix] = ", ".join(str(x) for x in obj[:20])
    elif isinstance(obj, list) and obj and depth < 6 and len(obj) <= 5:
        for i, v in enumerate(obj):
            flatten(v, f"{prefix}[{i}]", out, depth + 1)
    else:
        out[prefix] = "" if obj is None else (json.dumps(obj)[:2000] if isinstance(obj, (dict, list)) else obj)
    return out


def unwrap(doc):
    """Return a list of records from common export wrappers."""
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        if isinstance(doc.get("hits"), dict) and isinstance(doc["hits"].get("hits"), list):
            return doc["hits"]["hits"]
        for k in ("resources", "data", "events", "results", "records", "Records", "items", "rows", "logs", "values"):
            if isinstance(doc.get(k), list):
                return doc[k]
        if "result" in doc and isinstance(doc["result"], dict):
            return [doc["result"]]
    return [doc]


def record(r):
    if isinstance(r, dict):
        if isinstance(r.get("_source"), dict):
            base = {k: v for k, v in r.items() if k != "_source"}
            base.update(r["_source"])
            r = base
        elif isinstance(r.get("result"), dict) and len(r) <= 3:
            r = r["result"]
    return flatten(r) if isinstance(r, (dict, list)) else {"value": r}


def json_cells(row):
    """Expand cells that hold a JSON object or array (M365 audit `AuditData`, Sentinel `AdditionalFields`)
    into dotted fields under the column name: AuditData.Operation, AuditData.Parameters.From, ..."""
    out = {}
    for k, v in row.items():
        s = v.strip() if isinstance(v, str) else ""
        if len(s) > 1 and s[0] in "{[" and s[-1] in "}]":
            try:
                obj = json.loads(s)
            except ValueError:
                obj = None
            if isinstance(obj, (dict, list)):
                flatten(obj, k, out)
                continue
        out[k] = v
    return out


def opener(path):
    p = Path(path)
    raw = gzip.open(p, "rb") if p.suffix == ".gz" else open(p, "rb")
    return io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")


def read(path, max_rows=None):
    name = path[:-3] if path.endswith(".gz") else path
    ext = Path(name).suffix.lower()
    n = 0
    with opener(path) as f:
        head = f.read(4096)
        f.seek(0) if not path.endswith(".gz") else None
        if path.endswith(".gz"):
            f = opener(path)
        stripped = head.lstrip()
        if ext in (".csv", ".tsv") or (ext not in (".json", ".jsonl", ".ndjson") and not stripped[:1] in "[{"):
            dialect = "excel-tab" if ext == ".tsv" or head.count("\t") > head.count(",") else "excel"
            for row in csv.DictReader(f, dialect=dialect):
                yield json_cells({k.strip().lstrip("﻿") if k else "_": v for k, v in row.items()})
                n += 1
                if max_rows and n >= max_rows:
                    return
            return
        if stripped.startswith("[") or (ext == ".json" and not re.match(r"\{[^\n]*\}\s*\n\s*\{", stripped)):
            try:
                doc = json.load(f)
                for r in unwrap(doc):
                    yield record(r)
                    n += 1
                    if max_rows and n >= max_rows:
                        return
                return
            except json.JSONDecodeError:
                f = opener(path)
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                yield {"_raw": line}
            else:
                for r in unwrap(obj) if isinstance(obj, dict) and ("hits" in obj or "resources" in obj) else [obj]:
                    yield record(r)
            n += 1
            if max_rows and n >= max_rows:
                return


def to_time(v):
    if v in (None, ""):
        return None
    s = str(v).strip()
    if re.fullmatch(r"\d{9,19}(\.\d+)?", s):
        x = float(s)
        for div in (1, 1e3, 1e6, 1e9):
            if 1e9 <= x / div < 4.1e9:
                return dt.datetime.fromtimestamp(x / div, dt.timezone.utc).replace(tzinfo=None)
        return None
    s = s.replace("Z", "+00:00")
    m = re.match(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}(:\d{2})?)(\.\d+)?\s*([+-]\d{2}:?\d{2})?", s)
    if m:
        try:
            t = dt.datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}" + (m.group(3) and "" or ":00" if not m.group(3) else ""))
        except ValueError:
            return None
        if not m.group(5) and "+00:00" not in s:
            NAIVE.add(True)
        if m.group(5):
            off = m.group(5).replace(":", "")
            if off not in ("+0000", "-0000"):
                OFFSET.add(m.group(5))
            t -= dt.timedelta(hours=int(off[:3]), minutes=int(off[0] + off[3:5]))
        return t
    NAIVE.add(True)
    for fmt in ("%b %d, %Y @ %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S", "%d/%b/%Y:%H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(s.split(" +")[0], fmt)
        except ValueError:
            pass
    return None


def pick_time(fields, sample, forced=None):
    if forced:
        return forced
    for f in TIME_FIELDS:
        if f in fields and any(to_time(r.get(f)) for r in sample[:50]):
            return f
    for f in fields:
        if re.search(r"(?i)time|date|@ts|received|created|logged|generated|occurred", f) and any(to_time(r.get(f)) for r in sample[:50]):
            return f
    # last resort: the first field whose values parse as times in most sample rows
    for f in fields:
        vals = [r.get(f) for r in sample[:50] if r.get(f) not in (None, "")]
        if vals and not re.fullmatch(r"\d+(\.\d+)?", str(vals[0])) and sum(1 for v in vals if to_time(v)) >= 0.9 * len(vals):
            return f
    return None


def parse_where(exprs):
    conds = []
    for e in exprs:
        m = re.match(r"^(.+?)(!~|~|=)(.*)$", e)
        if not m:
            sys.exit(f"bad --where: {e}")
        f, op, v = m.groups()
        conds.append((f, op, re.compile(v, re.I) if "~" in op else v))
    return conds


def match(r, conds):
    for f, op, v in conds:
        vals = [str(x) for x in r.values()] if f == "*" else [str(r.get(f, ""))]
        if op == "=":
            ok = any(x == v for x in vals)
        else:
            ok = any(v.search(x) for x in vals)
            ok = not ok if op == "!~" else ok
        if not ok:
            return False
    return True


IOC_RX = re.compile(r"""(?ix)
    (?<![/\w.])(?:\d{1,3}\.){3}\d{1,3}\b                          # IPv4 (not a version like Chrome/131.0.0.0)
  | \bhttps?://[^\s|`'"]+                                       # URL
  | \b[a-f0-9]{32}\b | \b[a-f0-9]{40}\b | \b[a-f0-9]{64}\b       # md5 / sha1 / sha256
  | \b(?:AKIA|ASIA)[A-Z0-9]{16}\b                               # AWS key ids
  | \b[\w.+-]+@[\w-]+\.[\w.-]+\b                                # email
  | \b(?:[a-z0-9-]+\.)+(?:com|net|org|io|xyz|sh|site|ru|cn|top|info|biz|me|cc|de|ms|app|dev|cloud|link|live|online)\b  # domain
""")


def ioc_values(path):
    """Indicator-shaped values from iocs.md: IPs, URLs, hashes, key ids, e-mails, domains, and `backticked` names."""
    text = Path(path).read_text(encoding="utf-8").replace("[.]", ".").replace("hxxp", "http")
    vals = set()
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() == "type":
            continue
        vals.update(m.group(0).rstrip(".,") for m in IOC_RX.finditer(cells[1]))
        for b in re.findall(r"`([^`]{6,120})`", cells[1]):
            if not re.fullmatch(r"[\d: .-]+", b) and "<" not in b and "*" not in b:
                vals.add(b.strip())
    return sorted(v for v in vals if len(v) >= 6)


def main(argv):
    files, opts, multi = [], {"where": []}, {"where"}
    it = iter(argv)
    for a in it:
        if a.startswith("--"):
            k = a[2:].replace("-", "_")
            if k in ("per_day",):
                opts[k] = True
            elif k in multi:
                opts[k].append(next(it))
            else:
                opts[k] = next(it)
        else:
            files.append(a)
    if not files:
        print(__doc__.strip())
        return 2
    conds = parse_where(opts["where"])
    t_from = to_time(opts["from"]) if opts.get("from") else None
    t_to = to_time(opts["to"]) if opts.get("to") else None
    limit = int(opts.get("limit", 20 if (conds or opts.get("keep")) else 5))
    max_rows = int(opts["max_rows"]) if opts.get("max_rows") else None
    iocs = ioc_values(opts["iocs"]) if opts.get("iocs") else []

    for path in files:
        rows_total = rows_kept = 0
        fill, top, distinct = Counter(), defaultdict(Counter), defaultdict(set)
        sample, printed, counts, per_day, ioc_hits = [], [], Counter(), Counter(), defaultdict(Counter)
        tfield, tmin, tmax = None, None, None
        count_by = opts.get("count_by", "").split(",") if opts.get("count_by") else None
        for r in read(path, max_rows):
            rows_total += 1
            if len(sample) < 200:
                sample.append(r)
                if len(sample) == 50 or rows_total == 1:
                    tfield = pick_time(list(r.keys()), sample, opts.get("time"))
            t = to_time(r.get(tfield)) if tfield else None
            if (t_from and (not t or t < t_from)) or (t_to and (not t or t > t_to)):
                continue
            if conds and not match(r, conds):
                continue
            rows_kept += 1
            if t:
                tmin = t if not tmin or t < tmin else tmin
                tmax = t if not tmax or t > tmax else tmax
                per_day[t.date().isoformat()] += 1
            if count_by:
                counts[tuple(short(r.get(f, ""), 60) for f in count_by)] += 1
            if iocs:
                blob = "\x00".join(f"{k}={v}" for k, v in r.items())
                for v in iocs:
                    if v in blob:
                        for k, x in r.items():
                            if v in str(x):
                                ioc_hits[v][k] += 1
            for k, v in r.items():
                if v not in ("", None):
                    fill[k] += 1
                    if len(distinct[k]) < 1000:
                        distinct[k].add(str(v)[:200])
                    if len(top[k]) < 5000 or str(v)[:200] in top[k]:
                        top[k][str(v)[:200]] += 1
            if (conds or opts.get("keep")) and len(printed) < limit:
                printed.append(r)
        if tfield and rows_total and not sample:
            pass
        print(f"## {Path(path).name}")
        span = f"{tmin:%Y-%m-%d %H:%M:%S} – {tmax:%Y-%m-%d %H:%M:%S} UTC" if tmin else "no parsable time"
        filt = f", filter {' AND '.join(opts['where'])}" if conds else ""
        print(f"rows read {rows_total:,}; matched {rows_kept:,}{filt}; time field `{tfield}`: {span}; fields {len(fill)}")
        if tfield and NAIVE:
            print("WARNING: time values carry no zone and were read as UTC. Kibana/Splunk UI exports use the viewer's zone: confirm the offset before using these times.")
        if tfield and OFFSET:
            print(f"NOTE: time values carry the offset(s) {', '.join(sorted(OFFSET))}; every time shown here is converted to UTC.")
        NAIVE.clear()
        OFFSET.clear()
        if per_day and (opts.get("per_day") or not (conds or count_by)):
            days = sorted(per_day.items())
            print("\nper day (UTC): " + "; ".join(f"{d} {n:,}" for d, n in days[-40:]))
        if count_by:
            print(f"\n| {' | '.join(count_by)} | count |\n|{'---|' * (len(count_by) + 1)}")
            for k, n in counts.most_common(50):
                print(f"| {' | '.join(k)} | {n:,} |")
            print(f"\n{len(counts):,} distinct combinations")
        if iocs:
            print("\n| IOC | hits | fields |\n|---|---|---|")
            for v in iocs:
                if ioc_hits[v]:
                    print(f"| `{short(v, 60)}` | {sum(ioc_hits[v].values()):,} | {', '.join(f'{k} ({n})' for k, n in ioc_hits[v].most_common(4))} |")
            print(f"\n{sum(1 for v in iocs if ioc_hits[v])} of {len(iocs)} IOC values found")
        if printed:
            keep = opts["keep"].split(",") if opts.get("keep") else ([tfield] if tfield else []) + [k for k, _ in fill.most_common(7) if k != tfield][:6]
            print(f"\n| {' | '.join(keep)} |\n|{'---|' * len(keep)}")
            for r in printed:
                cell = lambda k: (f"{to_time(r.get(k)):%Y-%m-%d %H:%M:%S}" if k == tfield and to_time(r.get(k)) else short(r.get(k, ""), 90))
                print("| " + " | ".join(cell(k) for k in keep) + " |")
            if rows_kept > len(printed):
                print(f"\n({rows_kept - len(printed):,} more rows not shown; raise --limit or narrow --where)")
        if not (conds or count_by or iocs or opts.get("keep")):
            print("\n| field | fill % | distinct | top values |\n|---|---|---|---|")
            for k, n in sorted(fill.items(), key=lambda x: (-x[1], x[0])):
                d = len(distinct[k])
                tv = "; ".join(f"{short(v, 50)} ({c:,})" for v, c in top[k].most_common(limit)) if d > 1 or rows_kept == 1 else f"{short(next(iter(distinct[k])), 50)} (all)"
                print(f"| `{k}` | {n * 100 / max(rows_kept, 1):.0f} | {d if d < 1000 else '1000+'} | {tv} |")
            empty = sorted(set().union(*[set(r.keys()) for r in sample]) - set(fill)) if sample else []
            if empty:
                print(f"\nfields empty in every matched row ({len(empty)}): {', '.join(empty[:40])}")
        print()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to a legacy code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main(sys.argv[1:]))
    except BrokenPipeError:
        sys.exit(0)
