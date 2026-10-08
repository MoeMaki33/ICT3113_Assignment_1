# results/load/llama3.2_3b/rate-250_search-450

Generated 2026-10-07T23:01:11.645625+00:00 by scripts/process_jmeter_results.py from the raw .jtl files in this folder.

| Model | Official | Tickets/h set | Searches/h set | Endpoint | Runs | Missing | Offered/h (mean) | Achieved/h (mean ± sd) | Error rate (mean) | p50 s (mean) | p95 s (mean ± sd) | p99 s (mean) | p99 s pooled | Growing-latency runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama3.2:3b | True | 250 | 450 | GET /search | 3 | none | 450 | 450 ± 15.874 | 0.00% | 0.034 | 0.111 ± 0.084 | 0.282 | 0.526 | 0 |
| llama3.2:3b | True | 250 | 450 | POST /tickets | 3 | none | 260 | 256 ± 15.1 | 0.00% | 4.695 | 12.8 ± 2.056 | 16.838 | 19.217 | 3 |

Problems:
- none
