#!/usr/bin/env bash
# Create a new IR case folder from the kit templates.
# Usage: new-case.sh <client> <incident-id> [cases-root]
# cases-root defaults to $IR_CASES_ROOT, then the current directory.
set -euo pipefail

client="${1:?client name required}"
incident="${2:?incident id required}"
root="${3:-${IR_CASES_ROOT:-$PWD}}"
kit="$(cd "$(dirname "$0")/.." && pwd)"   # plugin root
tpl="$kit/templates"
case_dir="$root/${client}-${incident}"

if [ -e "$case_dir" ]; then
  echo "Case folder already exists: $case_dir" >&2
  exit 1
fi

fill() {
  sed -e "s/<client>/$client/g" -e "s/<incident-id>/$incident/g" -e "s/<id>/$incident/g" \
      -e "s/<YYYY-MM-DDTHH:MMZ>/$(date -u +%Y-%m-%dT%H:%MZ)/" "$1"
}

mkdir -p "$case_dir"/{sources,analysis,comms}
fill "$tpl/case.md"            > "$case_dir/case.md"
fill "$tpl/worklog.md"         > "$case_dir/worklog.md"
fill "$tpl/timeline.md"        > "$case_dir/timeline.md"
fill "$tpl/case-tracker.md"    > "$case_dir/tracker.md"
fill "$tpl/recommendations.md" > "$case_dir/recommendations.md"
fill "$tpl/coverage.md"        > "$case_dir/coverage.md"
fill "$tpl/data-gaps.md"       > "$case_dir/data_gaps.md"
cp "$tpl/credentials.md" "$case_dir/credentials.md"
printf '# IOCs: %s %s\n\n| Type | Value (defanged) | First seen UTC | Source |\n|---|---|---|---|\n' \
  "$client" "$incident" > "$case_dir/iocs.md"

echo "Created $case_dir"
echo "Next: fill case.md; connectors come from the Claude account, log files go to inbox/ or $case_dir/sources/"
