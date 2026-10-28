# Tracker in Google Sheets

## Option A: claude.ai Google Sheets connector (preferred, to test)
- Works in Claude Code when you log in with a claude.ai subscription (not an API key).
- Each analyst authenticates with their own Google account; the sheet must be shared with them.
- To verify before rollout: read the tracker, add one row, change one status cell. Official docs do not state cell editing explicitly.
Docs: https://support.claude.com/en/articles/10166901-use-google-workspace-connectors

## Option B: community Google Workspace MCP server
Servers with Sheets write support exist (for example distrihub/mcp-google-workspace, ve-gws). They need a Google Cloud project with the Sheets/Drive APIs and admin approval of the OAuth app. Treat as third-party code: review and pin.

## Option C: fallback
`ir-tracker` prints a TSV block to paste into the sheet.

## Sheet setup
- Columns and sections from `templates/tracker.md`.
- Data validation (dropdowns) for Status and RACI columns.
- Put the sheet link in each case `case.md` -> `tracker_url` (empty = local `tracker.md`).
