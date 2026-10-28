# Exposed credentials inventory

"Not visible" means no change event in our sources. It does not prove nothing changed; ask the client.

Credentials and access material only: passwords, keys, tokens, sessions, MFA methods, OAuth grants, certificates. Inbox rules, implants and stolen data belong in the item files and recommendations.

| # | Credential | How the actor got it | Evidence | Used by actor | Rotated / revoked |
|---|---|---|---|---|---|
| 1 | <type + id, never the value> | <path or [hypothesis]> | <source, UTC> | <yes: what / no / unknown> | <evidence or "not visible"> |

Priority for containment: <list row numbers>.
