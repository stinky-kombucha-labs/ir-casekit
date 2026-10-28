#!/usr/bin/env bash
# Expose the kit skills as project skills of this workspace (folder mode, no plugin install).
# Usage: bash plugins/ir-casekit/scripts/link-skills.sh   (run from the workspace root)
set -euo pipefail

root="$(cd "$(dirname "$0")/../../.." && pwd)"
mkdir -p "$root/.claude/skills"
for d in "$root"/plugins/ir-casekit/skills/*/; do
  name="$(basename "$d")"
  ln -sfn "../../plugins/ir-casekit/skills/$name" "$root/.claude/skills/$name"
  echo "linked .claude/skills/$name"
done
