# results/load/llama3.1_8b/rate-250_search-450

Generated 2026-10-08T06:48:49.583991+00:00 by scripts/process_jmeter_results.py from the raw .jtl files in this folder.

| Model | Official | Tickets/h set | Searches/h set | Endpoint | Runs | Missing | Offered/h (mean) | Achieved/h (mean ± sd) | Error rate (mean) | p50 s (mean) | p95 s (mean ± sd) | p99 s (mean) | p99 s pooled | Growing-latency runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama3.1:8b | True | 250 | 450 | GET /search | 3 | none | 450 | 450 ± 15.874 | 0.00% | 0.026 | 0.063 ± 0.01 | 0.099 | 0.087 | 0 |
| llama3.1:8b | True | 250 | 450 | POST /tickets | 3 | none | 260 | 228 ± 15.874 | 2.22% | 44.6 | 97.311 ± 17.02 | 103.68 | 113.977 | 3 |

Problems:
- none
