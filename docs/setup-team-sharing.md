# Sharing the kit with a team

## As a plugin marketplace (git repo)
1. Fork or clone this repository (private fork if you add your own playbooks).
2. Each analyst, once:
   ```
   /plugin marketplace add stinky-kombucha-labs/ir-casekit
   /plugin install ir-casekit@ir-casekit
   ```
3. Changes to skills go through pull requests. Bump `version` in `plugins/ir-casekit/.claude-plugin/plugin.json` on every release.

Docs: https://code.claude.com/docs/en/plugins/host-marketplace.md

## Auto-prompt install in a working folder
Commit a `.claude/settings.json` in a shared working repo with:
```json
{
  "extraKnownMarketplaces": {
    "ir-casekit": { "source": { "source": "github", "repo": "stinky-kombucha-labs/ir-casekit" } }
  },
  "enabledPlugins": { "ir-casekit@ir-casekit": true }
}
```
It applies after the analyst accepts the folder trust dialog.

## Organisation-wide
An admin can set the same keys in managed settings (claude.ai console, MDM or `managed-settings.json`) and restrict sources with `strictKnownMarketplaces`.
Docs: https://code.claude.com/docs/en/plugins/org.md

## claude.ai users
Team/Enterprise admins can provision the same skills for the organisation. Claude Code syncs skills from the claude.ai account one way (into `~/.claude/skills/synced/`, local edits are overwritten). Keep git as the source of truth.
Docs: https://support.claude.com/en/articles/12512180-use-skills-in-claude

## Credentials
- `.mcp.json` holds `${VAR}` only. Each analyst keeps values in their own `.env` or shell.
- Never commit `.env`, logs or case data. `cases/` is in `.gitignore`.
- Plugin hooks and MCP servers run outside the sandbox: review PRs, pin versions.
Docs: https://code.claude.com/docs/en/mcp.md
