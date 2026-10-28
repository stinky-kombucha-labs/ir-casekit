---
name: ir-comms
description: Write and validate client-facing incident messages. Use when the user wants a short client update, recommendations, an answer to a client question in the incident channel, wants to "add queries as proof", or asks to validate that a draft is 100% accurate against the logs. Checks every claim against evidence, adds ready-to-run queries, defangs IOCs and keeps the message short.
---

# IR comms

`<kit>` is the plugin folder two levels above this file (`plugins/ir-casekit/` in the workspace).

## Message shape
- Lead with the answer or the ask. Three to eight short lines, then numbered asks if any.
- One fact per sentence, UTC times, exact identifiers (pod, instance id, account id, token id).
- Separate `Confirmed` from `not confirmed` explicitly.
- Asks are concrete: exact data, time window, why we need it.

## Validation (when asked to check a draft)
1. Split the draft into claims.
2. For each claim, find the evidence in `analysis/` or run the query.
3. Return a table: claim | result (accurate / overstated / wrong / missing context) | evidence.
4. Give the corrected text. Keep the author's wording where it is accurate.
Typical overstatements: "ran commands" when only SendCommand success is logged; "denied everything" when nothing else was attempted; "got into the cluster" when only a node key was used.

## Evidence queries
When the user wants proof attached, add one short query per claim (ES|QL / CQL / SPL) that the client can paste. Prefer queries already run in this case; flag any query not executed yet.

## Rules
- Write in English unless the analyst explicitly asks for another language for this message.
- Defang IOCs. Never include secrets or customer data.
- Check the addressee and names against the thread before sending.
- Do not mention internal visibility the client may not expect (for example process command lines from employees' laptops) without softening it.
