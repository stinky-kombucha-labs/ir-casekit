#!/usr/bin/env python3
"""Check that the analysis of a case is complete.

Usage: python3 -I check-case.py <case-dir>

Reads coverage.md and data_gaps.md and reports:
- empty and `error` cells in the coverage matrix, per item column;
- `missing G<N>` cells without a row in data_gaps.md;
- data gaps by status, with the `open` ones listed.
Exit code 0 when ready (no empty / error cell, no orphan gap id, no open gap), 1 otherwise.
"""
import re
import sys
from pathlib import Path


def table_rows(text, header_start):
    """Return the rows of the first Markdown table whose header starts with header_start."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and line.strip().lstrip("|").strip().startswith(header_start):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            rows = []
            for row in lines[i + 2:]:
                if not row.strip().startswith("|"):
                    break
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                cells += [""] * (len(header) - len(cells))
                rows.append(cells[: len(header)])
            return header, rows
    return None, []


def main():
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2
    case = Path(sys.argv[1])
    ready = True

    missing = [f for f in ("coverage.md", "data_gaps.md") if not (case / f).is_file()]
    if missing:
        print(f"Missing: {', '.join(missing)} (create from templates/coverage.md and templates/data-gaps.md)")
        print("NOT READY: analysis incomplete")
        return 1

    header, rows = table_rows((case / "coverage.md").read_text(encoding="utf-8"), "Source")
    if header is None:
        print("coverage.md: no table found")
        return 1
    items = header[1:]
    rows = [r for r in rows if not r[0].startswith("<")]
    used_gaps = set()
    print(f"Coverage: {len(rows)} sources x {len(items)} items")
    for col, item in enumerate(items, start=1):
        empty = [r[0] for r in rows if not r[col]]
        errors = [r[0] for r in rows if r[col].lower().startswith("error")]
        for r in rows:
            used_gaps.update(re.findall(r"\bG\d+\b", r[col]))
        if empty or errors:
            ready = False
            print(f"  item {item}: {len(empty)} empty, {len(errors)} error -> {', '.join(empty + errors)}")
    if ready:
        print("  no empty or error cell")

    gaps_file = case / "data_gaps.md"
    header, gap_rows = table_rows(gaps_file.read_text(encoding="utf-8"), "ID")
    known = {}
    for r in gap_rows:
        if re.fullmatch(r"G\d+", r[0]):
            # status is the first word of the last cell: "open (future)" counts as open
            words = r[-1].strip("` ").lower().split()
            known[r[0]] = words[0] if words else ""
    orphan = sorted(used_gaps - set(known), key=lambda g: int(g[1:]))
    if orphan:
        ready = False
        print(f"Gap ids in coverage.md without a row in data_gaps.md: {', '.join(orphan)}")
    by_status = {}
    for gid, status in known.items():
        by_status.setdefault(status or "(no status)", []).append(gid)
    print("Data gaps: " + (", ".join(f"{s} {len(g)}" for s, g in sorted(by_status.items())) or "none"))
    for status in ("open", "(no status)"):
        if status in by_status:
            ready = False
            print(f"  {status}: {', '.join(by_status[status])}")

    print("READY: every source checked, no open data gap" if ready else "NOT READY: analysis incomplete")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
