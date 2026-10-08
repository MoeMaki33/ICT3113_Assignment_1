# Accuracy: `qwen2.5:7b` (run-1)

Golden set `data/golden_set_final.csv` (sha256 `54ae476fc87e…`), 180 tickets, status `completed`.

- Overall accuracy: **80.6%** (145/180)
- Lowest per-category accuracy: **73.1%**
- Failed requests (counted incorrect): 2 {'HTTP 502': 2}
- Single-request latency excl. first: p50 11.237 s, p95 23.96 s, p99 27.057 s (n=177)

| Category | Golden | Correct | Accuracy (recall) | Predicted as | Precision | Failed |
|---|---|---|---|---|---|---|
| Credit reporting | 38 | 33 | 86.8% | 46 | 71.7% | 0 |
| Debt collection | 17 | 13 | 76.5% | 21 | 61.9% | 0 |
| Mortgage | 32 | 25 | 78.1% | 25 | 100.0% | 0 |
| Credit card | 26 | 19 | 73.1% | 21 | 90.5% | 0 |
| Bank account or service | 29 | 25 | 86.2% | 29 | 86.2% | 0 |
| Consumer loan | 20 | 15 | 75.0% | 18 | 83.3% | 0 |
| Money transfer or service | 18 | 15 | 83.3% | 18 | 83.3% | 2 |

Confusion matrix (rows = golden, columns = predicted):

| golden \ predicted | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service | FAILED |
|---|---|---|---|---|---|---|---|---|
| Credit reporting | 33 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| Debt collection | 4 | 13 | 0 | 0 | 0 | 0 | 0 | 0 |
| Mortgage | 2 | 0 | 25 | 0 | 1 | 3 | 1 | 0 |
| Credit card | 4 | 1 | 0 | 19 | 2 | 0 | 0 | 0 |
| Bank account or service | 0 | 0 | 0 | 2 | 25 | 0 | 2 | 0 |
| Consumer loan | 3 | 2 | 0 | 0 | 0 | 15 | 0 | 0 |
| Money transfer or service | 0 | 0 | 0 | 0 | 1 | 0 | 15 | 2 |
