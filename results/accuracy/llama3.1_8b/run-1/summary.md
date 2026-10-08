# Accuracy: `llama3.1:8b` (run-1)

Golden set `data/golden_set_final.csv` (sha256 `54ae476fc87e…`), 180 tickets, status `completed`.

- Overall accuracy: **84.4%** (152/180)
- Lowest per-category accuracy: **52.9%**
- Failed requests (counted incorrect): 0 
- Single-request latency excl. first: p50 11.004 s, p95 24.092 s, p99 28.736 s (n=179)

| Category | Golden | Correct | Accuracy (recall) | Predicted as | Precision | Failed |
|---|---|---|---|---|---|---|
| Credit reporting | 38 | 35 | 92.1% | 44 | 79.5% | 0 |
| Debt collection | 17 | 9 | 52.9% | 13 | 69.2% | 0 |
| Mortgage | 32 | 30 | 93.8% | 32 | 93.8% | 0 |
| Credit card | 26 | 19 | 73.1% | 24 | 79.2% | 0 |
| Bank account or service | 29 | 25 | 86.2% | 27 | 92.6% | 0 |
| Consumer loan | 20 | 17 | 85.0% | 23 | 73.9% | 0 |
| Money transfer or service | 18 | 17 | 94.4% | 17 | 100.0% | 0 |

Confusion matrix (rows = golden, columns = predicted):

| golden \ predicted | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service | FAILED |
|---|---|---|---|---|---|---|---|---|
| Credit reporting | 35 | 2 | 0 | 0 | 0 | 1 | 0 | 0 |
| Debt collection | 3 | 9 | 0 | 2 | 0 | 3 | 0 | 0 |
| Mortgage | 1 | 0 | 30 | 0 | 0 | 1 | 0 | 0 |
| Credit card | 4 | 1 | 0 | 19 | 2 | 0 | 0 | 0 |
| Bank account or service | 0 | 0 | 0 | 3 | 25 | 1 | 0 | 0 |
| Consumer loan | 1 | 0 | 2 | 0 | 0 | 17 | 0 | 0 |
| Money transfer or service | 0 | 1 | 0 | 0 | 0 | 0 | 17 | 0 |
