# Timeline: <client> <incident-id>

One row per meaningful step. Merge repetitive events into one row with a range and a count. Keep context (who, where, what it gave the actor).

| Time (UTC) | Host / User | Event |
|---|---|---|
| YYYY-MM-DD HH:MM:SS | <host, pod, account, token id> | <what happened, short>. (<source>) |
| YYYY-MM-DD HH:MM–HH:MM | <...> | <N events of type X>. (<source>) |
