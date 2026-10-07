# All configurations under results/load

Generated 2026-10-07T15:36:44.948163+00:00 from raw .jtl files. Rows marked Official = False are not evidence.

| Model | Official | Tickets/h set | Searches/h set | Endpoint | Runs | Missing | Offered/h (mean) | Achieved/h (mean ± sd) | Error rate (mean) | p50 s (mean) | p95 s (mean ± sd) | p99 s (mean) | p99 s pooled | Growing-latency runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma2:2b | True | 125 | 0 | POST /tickets | 3 | none | 128 | 124 ± 9.165 | 0.00% | 6.272 | 12.725 ± 1.447 | 13.836 | 15.477 | 0 |
| gemma2:2b | True | 250 | 450 | GET /search | 3 | none | 450 | 450 ± 15.874 | 0.00% | 0.029 | 0.055 ± 0.009 | 0.082 | 0.069 | 0 |
| gemma2:2b | True | 250 | 450 | POST /tickets | 3 | none | 260 | 254 ± 18.33 | 0.00% | 7.587 | 18.351 ± 1.655 | 23.542 | 26.059 | 2 |
| gemma2:2b | True | 500 | 0 | POST /tickets | 3 | none | 524 | 456 ± 21.633 | 3.62% | 47.491 | 82.381 ± 30.367 | 86.978 | 118.144 | 3 |
