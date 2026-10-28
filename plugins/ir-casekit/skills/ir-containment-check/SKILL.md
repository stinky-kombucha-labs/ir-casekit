---
name: ir-containment-check
description: Verify from logs which containment and eradication actions the client has actually done, and watch for the threat coming back. Use when the user asks "what did the client already do", "is it fixed", "check before we send recommendations", "is the attack stopped", or wants recurring monitoring of attacker activity (for example a job that runs every 30 minutes). Produces done / not visible / still active per recommendation with evidence.
---

# IR containment check

`<kit>` is the plugin folder two levels above this file (`plugins/ir-casekit/` in the workspace).

## Steps
1. Load the recommendation list (`recommendations*.md` or tracker Containment rows) and `credentials.md`.
2. For each action, look for the event that proves it:
   - attacker resources removed: last Falco/EDR event per resource family, compared with how fresh the data is;
   - commits reverted: merged PRs and pushes in the affected repos (GitHub audit);
   - accounts and tokens: `org.block_user`, PAT/OAuth revocation, last use of the token id;
   - cloud sessions revoked: `PutRolePolicy AWSRevokeOlderSessions` per role. A revoke does not stop an actor who still holds a source of fresh credentials (running pods, CronJobs, service account tokens, OIDC trust): check for new `AssumeRole*` calls by the actor after the revoke time;
   - secrets rotated: `PutSecretValue`/`UpdateSecret`/`RotateSecret`/`PutParameter`;
   - services patched or closed: pod name/version change, last request from the actor, last exploit-like event.
3. **Active threat test.** For anything recurring, count events per interval (for example 30 min) before and after the fix, and confirm the data source is fresh past the last expected cycle. Look for behaviour, not only names (images, commands, egress domains).
4. Mark each action: `Done (evidence)`, `Not visible in logs`, `Still active`. "Not visible" is not "not done": ask the client to confirm.
5. Update `recommendations*.md` and run `ir-tracker`.

## Monitoring
If the user wants ongoing checks, offer `/loop <interval>` with the exact queries from step 3, and report only when something appears.

## Rules
- Lead with what is still active or exposed.
- Flag client actions that create new risk (for example unblocking an IP that the actor used, reusing a compromised token).
