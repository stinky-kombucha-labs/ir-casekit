# Coverage: <client> <incident-id>

Every source from item00 against every plan item. One cell per pair. No cell may stay empty when the analysis is closed.

Rows: one per source in `analysis/item00_data_inventory.md` (use its `#`). Columns: one per plan item. `ir-intake` adds rows, `ir-plan` adds columns, `ir-investigate` fills the cells of its item.

Cell values:
- `checked w<N>`: the source was queried for this item; `w<N>` is the worklog row (or rows, `w12,w15`) with the exact query and result.
- `n/a: <reason>`: the source cannot hold evidence for this question. The reason is concrete (other platform, other account, events end before the window, data type unrelated). "Not relevant" alone is not a reason.
- `missing G<N>`: the question needs data this source should have but does not (empty fields, outside retention, host not covered); `G<N>` is the row in `data_gaps.md`.
- `error w<N>`: the query failed or timed out. Not a result: retry narrower. Not allowed in the final matrix.

| Source (item00 #) | 01 | 02 | 03 |
|---|---|---|---|
| E1 <connector / index> | | | |
| C1 <connector / repo> | | | |

## Data outside the connectors
Client exports and other files get a row here as soon as they arrive (`ir-intake`, step "New source mid-case").
