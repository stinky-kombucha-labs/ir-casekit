---
name: ir-plan
description: Build or update the investigation plan for an incident response case. Use when the user asks for an investigation plan, "what should we check", "break the incident into review items", or wants new items after new evidence. Produces numbered "Review X" items with question, client claim, data, checks and expected result, writes the order of work into the worklog session plan, and pushes the items to the tracker.
---

# IR plan

`<kit>` is the plugin folder two levels above this file (`plugins/ir-casekit/` in the workspace).

## Item format (one per question)
```
## N. Review <object>
- Question. <one question the item answers>
- Client claim. <what the client says, if anything>
- Data. <sources from item00 that can answer it, in the order they will be checked>
- Checks.
  - <concrete check with field names / identifiers>
- Result. <what makes it Confirmed, and what is delivered: table, list, Not determinable + missing data>
```

## Steps
1. Read `case.md`, `timeline.md`, `sources/` (including `trigger_*.md`), `analysis/item00_data_inventory.md`.
2. Cover the standard IR questions, adapted to the case:
   - initial access point; how the actor moved from it;
   - every credential the actor obtained and its origin;
   - persistence (jobs, DaemonSets, CronJobs, PATs, SSH keys, OAuth apps, webhooks, deploy keys, IAM keys, CI workflows, config files the service reloads);
   - privileged/host access and which nodes or hosts are compromised;
   - data accessed and data sent out (channels, type, volume);
   - integrity of code, images and packages (git, CI, registry, artifact repository);
   - scope outside SIEM coverage;
   - early or unrelated events (pentest, bug bounty, AppSec tests, vendor scanners) to discard, and the client's own testing of the same vulnerability during the incident (workstation command lines and EDR alerts that mention the product, its hosts or OAST domains);
   - final item: exposed credentials inventory.
3. **Vulnerability-triggered cases** (the trigger is a CVE or advisory). Add these items first, before the standard ones:
   - exposure: which assets run the affected product and version, since when, and when each was patched (EDR inventory, vulnerability scanner, image tags, deployment history);
   - delivery: requests that match the attack path from `trigger_*.md` (endpoint, parameters, authentication used), and who sent them;
   - execution: the post-exploitation artifact the CVE gives (process spawned by the service account, file written outside the expected directory, config file changed);
   - existing detections: SIEM and EDR alerts on the affected assets in the exposure window, including closed and low-severity ones;
   - follow-on: cloud findings (GuardDuty and similar), credential use from outside, new workloads in the clusters that host the product, in the days after the publication date.
4. Tag each item with the data it needs and whether only the client has it. Add client-only data to `data_gaps.md` now (status `open`, item numbers, retention deadline; for example SSM Run Command history is kept 30 days). Run `ir-data-gaps` the same day for rows with a retention deadline.
5. Save as `plan.md`. Add one column per item to `coverage.md`. Pre-fill `n/a: <reason>` only where the reason is certain; leave the rest empty for `ir-investigate`. In sequential mode, write the session plan in `worklog.md`: one line per item and source to query (`Item 03 / falcon ngsiem`, `Item 03 / elastic falco`), in the order they will run.
6. Run `ir-tracker` to add rows under "Define the entry point and scope of the attack".

## Updating the plan
Evidence often leads outside the first plan (a CVE case turns into cloud credential theft). When `ir-investigate` finds a new actor artifact or a new affected account, cluster, role or data store:
- append items to `plan.md` under a dated heading ("Added <UTC> after item NN"), numbered after the last item;
- add their columns to `coverage.md` and their lines to the `worklog.md` session plan before the containment step;
- add tracker rows;
- keep the original items; mark the ones the new evidence answers.

## Rules
- One question per item. Split items that ask two things.
- Write checks a teammate can run without asking you (field names, IDs, time windows in UTC).
- Every source from item00 that could answer an item is listed in its `Data` line, not only the most likely one. The other sources still get a cell in `coverage.md` (`n/a` with a reason).
