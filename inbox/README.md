# Inbox

Drop log exports here (CSV, TSV, JSON, JSONL, NDJSON, .gz) and tell Claude which case they belong to.
Claude moves each file to `cases/<case>/sources/<origin>_<YYYY-MM-DD>/`, profiles it with `plugins/ir-casekit/scripts/log-profile.py` and adds it to the case. Files are never pasted into the chat. Everything here except this README is ignored by git.
