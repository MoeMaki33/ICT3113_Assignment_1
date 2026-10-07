# Bottleneck evidence worksheet

Status: **BLOCKED UNTIL FORMAL TESTING**. The prediction of CPU inference as
the bottleneck remains a hypothesis. No bottleneck or system limit is established.

| Evidence to collect | Location | Question it helps answer |
|---|---|---|
| Client latency, offered and completed rates, errors, trend | Raw `.jtl` and processed summaries | Does throughput saturate while latency grows? |
| Service duration, model, error type, request ID | Service logs and reconciliation extract | Is time spent inside the application or before reaching it? |
| Host CPU and available memory over each step | `results/stress/<model>/observations/` | Does inference saturate CPU, or does memory pressure/paging intervene? |
| Ollama processor split and model residency | `ollama ps` captured during requests | Is inference actually CPU-only and is model loading relevant? |
| Container resource usage | `docker stats` captures | Does service resource usage support the inference hypothesis? |

Follow the collection commands in `test_playbook.md` section 7.5. Retain actual
timestamps, intervals and gaps in every capture. Request logs do not currently
expose per-request Ollama prefill/decode time; do not claim a measured split
without separate Ollama evidence. Client-minus-service duration includes network
and waiting outside application middleware, and does not uniquely identify
either component. Same-endpoint service lines for timed-out clients are possible
matches, not proof of request identity.

TODO: join evidence by run and time window; explain saturation, p50/p95/p99,
error types and resource observations together. Report highest measured
sustainable and lowest measured unsustainable stress rates only after every
step is reconciled. Stress summaries remain provisional until then. Re-running
the unchanged stress command after reconciliation refreshes derived summaries
and preserves manually entered observation notes.

TODO: compare the observed bottleneck with the frozen prediction. Preserve the
unoptimised Assignment 1 baseline; any optimisation belongs to Assignment 2.
