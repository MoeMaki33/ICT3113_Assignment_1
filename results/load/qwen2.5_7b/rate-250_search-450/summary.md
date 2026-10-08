# results/load/qwen2.5_7b/rate-250_search-450

Generated 2026-10-08T02:17:34.711924+00:00 by scripts/process_jmeter_results.py from the raw .jtl files in this folder.

| Model | Official | Tickets/h set | Searches/h set | Endpoint | Runs | Missing | Offered/h (mean) | Achieved/h (mean ± sd) | Error rate (mean) | p50 s (mean) | p95 s (mean ± sd) | p99 s (mean) | p99 s pooled | Growing-latency runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5:7b | True | 250 | 450 | GET /search | 3 | none | 450 | 450 ± 15.874 | 0.00% | 0.029 | 0.076 ± 0.039 | 0.151 | 0.137 | 0 |
| qwen2.5:7b | True | 250 | 450 | POST /tickets | 3 | none | 260 | 236 ± 6.928 | 0.72% | 34.028 | 77.689 ± 32.434 | 85.489 | 110.181 | 3 |

Problems:
- none
