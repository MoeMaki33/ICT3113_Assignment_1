# Accuracy: `llama3.2:3b` (run-1)

Golden set `data/golden_set_final.csv` (sha256 `54ae476fc87e…`), 180 tickets, status `completed`.

- Overall accuracy: **60.6%** (109/180)
- Lowest per-category accuracy: **20.0%**
- Failed requests (counted incorrect): 0 
- Single-request latency excl. first: p50 5.218 s, p95 11.141 s, p99 12.748 s (n=179)

| Category | Golden | Correct | Accuracy (recall) | Predicted as | Precision | Failed |
|---|---|---|---|---|---|---|
| Credit reporting | 38 | 33 | 86.8% | 63 | 52.4% | 0 |
| Debt collection | 17 | 8 | 47.1% | 22 | 36.4% | 0 |
| Mortgage | 32 | 26 | 81.2% | 30 | 86.7% | 0 |
| Credit card | 26 | 11 | 42.3% | 19 | 57.9% | 0 |
| Bank account or service | 29 | 21 | 72.4% | 35 | 60.0% | 0 |
| Consumer loan | 20 | 4 | 20.0% | 5 | 80.0% | 0 |
| Money transfer or service | 18 | 6 | 33.3% | 6 | 100.0% | 0 |

Confusion matrix (rows = golden, columns = predicted):

| golden \ predicted | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service | FAILED |
|---|---|---|---|---|---|---|---|---|
| Credit reporting | 33 | 3 | 1 | 0 | 1 | 0 | 0 | 0 |
| Debt collection | 6 | 8 | 0 | 1 | 2 | 0 | 0 | 0 |
| Mortgage | 4 | 1 | 26 | 0 | 0 | 1 | 0 | 0 |
| Credit card | 11 | 1 | 0 | 11 | 3 | 0 | 0 | 0 |
| Bank account or service | 2 | 0 | 0 | 6 | 21 | 0 | 0 | 0 |
| Consumer loan | 5 | 8 | 3 | 0 | 0 | 4 | 0 | 0 |
| Money transfer or service | 2 | 1 | 0 | 1 | 8 | 0 | 6 | 0 |
