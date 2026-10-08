# Accuracy: `gemma2:2b` (run-2)

Golden set `data/golden_set_final.csv` (sha256 `54ae476fc87e…`), 180 tickets, status `completed`.

- Overall accuracy: **67.2%** (121/180)
- Lowest per-category accuracy: **15.0%**
- Failed requests (counted incorrect): 0 
- Single-request latency excl. first: p50 7.081 s, p95 12.937 s, p99 15.286 s (n=179)

| Category | Golden | Correct | Accuracy (recall) | Predicted as | Precision | Failed |
|---|---|---|---|---|---|---|
| Credit reporting | 38 | 33 | 86.8% | 50 | 66.0% | 0 |
| Debt collection | 17 | 9 | 52.9% | 19 | 47.4% | 0 |
| Mortgage | 32 | 30 | 93.8% | 32 | 93.8% | 0 |
| Credit card | 26 | 16 | 61.5% | 33 | 48.5% | 0 |
| Bank account or service | 29 | 21 | 72.4% | 32 | 65.6% | 0 |
| Consumer loan | 20 | 3 | 15.0% | 5 | 60.0% | 0 |
| Money transfer or service | 18 | 9 | 50.0% | 9 | 100.0% | 0 |

Confusion matrix (rows = golden, columns = predicted):

| golden \ predicted | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service | FAILED |
|---|---|---|---|---|---|---|---|---|
| Credit reporting | 33 | 3 | 1 | 0 | 1 | 0 | 0 | 0 |
| Debt collection | 7 | 9 | 0 | 0 | 1 | 0 | 0 | 0 |
| Mortgage | 0 | 1 | 30 | 0 | 1 | 0 | 0 | 0 |
| Credit card | 5 | 1 | 0 | 16 | 4 | 0 | 0 | 0 |
| Bank account or service | 0 | 0 | 0 | 8 | 21 | 0 | 0 | 0 |
| Consumer loan | 5 | 4 | 1 | 5 | 2 | 3 | 0 | 0 |
| Money transfer or service | 0 | 1 | 0 | 4 | 2 | 2 | 9 | 0 |
