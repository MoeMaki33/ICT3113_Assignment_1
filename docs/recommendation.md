# Model recommendation

Status: **BLOCKED UNTIL FORMAL TESTING**. No candidate is recommended yet.
TODO means unmeasured; it is neither PASS nor FAIL.

| Candidate | R1 POST latency | R2 throughput and errors | R3 overall accuracy | R3 all seven category floors | R4 search latency | Evidence |
|---|---|---|---|---|---|---|
| `gemma2:2b` | TODO | TODO | TODO | TODO | TODO | TODO |
| `llama3.2:3b` | TODO | TODO | TODO | TODO | TODO | TODO |
| `qwen2.5:7b` | TODO | TODO | TODO | TODO | TODO | TODO |
| `llama3.1:8b` | TODO | TODO | TODO | TODO | TODO | TODO |

Use the team-approved frozen `requirements.md` without changing thresholds
after seeing results. Current proposed decision rules are:

- R1: mean of three run p95 values <= 15 s and mean p99 <= 30 s at design peak.
- R2: each of three runs achieves >= 245 successful classifications/h and < 1% errors.
- R3: >= 80% overall and >= 70% recall for each of the seven golden categories.
- R4: mean of three search p95 values <= 1 s during mixed peak traffic.

R1/R2/R4 use the 250 tickets/h + 450 searches/h configuration. All required
runs must be completed and reconciled. Missing categories, runs, digests or
reconciliation remain TODO. Use raw counts for accuracy threshold comparisons,
not rounded displayed percentages. See `completion_audit.md` for pre-freeze
questions about the proposed performance decision rules.

TODO: cite exact summary/raw evidence for every cell, then explain the
accuracy/performance trade-off, resource constraints and uncertainty. If no
candidate passes all requirements, state that explicitly and explain which
requirements remain unmet. Do not choose a winner solely by size, speed or
overall accuracy.
