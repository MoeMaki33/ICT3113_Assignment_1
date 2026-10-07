# Prediction versus results

Status: **BLOCKED UNTIL FORMAL TESTING**. No formal results exist. Do not edit
`prediction_record.md` after freezing it. Populate this separate document from
the frozen record and reconciled raw evidence only.

| Exact model tag | Frozen predicted accuracy | Actual accuracy | Frozen predicted latency (median / p95) | Actual sequential latency (median / p95) | Assessment and evidence |
|---|---|---|---|---|---|
| `gemma2:2b` | TODO: frozen prediction | TODO | TODO: frozen prediction | TODO | TODO |
| `llama3.2:3b` | TODO: frozen prediction | TODO | TODO: frozen prediction | TODO | TODO |
| `qwen2.5:7b` | TODO: frozen prediction | TODO | TODO: frozen prediction | TODO | TODO |
| `llama3.1:8b` | TODO: frozen prediction | TODO | TODO: frozen prediction | TODO | TODO |

Use `results/accuracy/<model>/run-N/metrics.json` for sequential latency and
accuracy. The latency field excluding the first request excludes the first
attempt, even if it failed. Compare load latency separately; it includes waiting
under concurrent arrivals and is a different operation condition.

TODO: record frozen prediction commit and SHA-256, golden SHA-256, actual model
digest, test environment and result paths for each comparison.

TODO: compare the predicted bottleneck with `bottleneck_analysis.md`, predicted
difficult categories with every confusion matrix, and model-size trade-offs
with measured accuracy, latency and throughput. Explain incorrect predictions
without retroactively changing requirements or predictions.
