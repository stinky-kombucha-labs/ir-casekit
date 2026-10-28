# Automation options

| Need | Tool | Notes |
|---|---|---|
| Watch for attacker activity coming back during an incident (e.g. every 30 min) | `/loop 30m <prompt>` in the analyst's session | Stops when the session ends; recurring tasks expire after 7 days. https://code.claude.com/docs/en/scheduled-tasks.md |
| Start a new case | `scripts/new-case.sh` then `claude -p "/ir-intake"` | Headless mode for scripts and cron. https://code.claude.com/docs/en/headless.md |
| Daily case summary to the team | Routines (cloud) | Research preview, owned by one account, no access to local files: needs data in git or via connectors. https://code.claude.com/docs/en/routines.md |
| Checks on kit changes | GitHub Actions | Lint skills, validate JSON on PR. https://code.claude.com/docs/en/github-actions.md |

## Example monitoring prompt for /loop
```
Check <runtime source> and CloudTrail since the last run for: pods with the actor's name prefixes (<prefix>-*), the actor's images in namespaces <ns1>, <ns2>, commands containing the exfiltration domains from iocs.md, calls with the actor's session names or from the actor's IPs, and web-identity role assumptions by the abused roles. Report only if something appears, with the query and UTC times. Also report if the newest event in any watched source is older than 30 minutes.
```
