# results/load/gemma2_2b/rate-250_search-450

Generated 2026-10-07T14:02:35.121216+00:00 by scripts/process_jmeter_results.py from the raw .jtl files in this folder.

| Model | Official | Tickets/h set | Searches/h set | Endpoint | Runs | Missing | Offered/h (mean) | Achieved/h (mean ± sd) | Error rate (mean) | p50 s (mean) | p95 s (mean ± sd) | p99 s (mean) | p99 s pooled | Growing-latency runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma2:2b | True | 250 | 450 | GET /search | 3 | none | 450 | 450 ± 15.874 | 0.00% | 0.029 | 0.055 ± 0.009 | 0.082 | 0.069 | 0 |
| gemma2:2b | True | 250 | 450 | POST /tickets | 3 | none | 260 | 254 ± 18.33 | 0.00% | 7.587 | 18.351 ± 1.655 | 23.542 | 26.059 | 2 |

Problems:
- none
