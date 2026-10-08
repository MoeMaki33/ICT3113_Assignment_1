# Bottleneck analysis

Status: **COMPLETE - reconciled request evidence; resource attribution unverified**.
The frozen hypothesis was CPU inference, especially narrative prefill, with queue growth and Ollama timeouts at overload. Request evidence supports classification-path congestion and timeout failures. It does not directly measure CPU saturation or a prefill/decode split.

## Directly observed load behaviour

These are means of three per-run successful-POST percentiles, not pooled percentiles. Each window is ten minutes after two minutes warm-up. Failed requests are excluded from latency, but included in error rates. Exact mixed-load per-run counts and links appear in [recommendation.md](recommendation.md).

| Model | Mixed 250/h + 450 searches/h POST p50 / p95 / p99 (s) | Mean achieved/h; errors | GET search mean p95 (s) | POST runs with growth |
|---|---|---|---|---:|
| Gemma | 7.587 / 18.351 / 23.542 | 254; 0% | 0.055 | 2/3 |
| Llama 3.2 | 4.695 / 12.800 / 16.838 | 256; 0% | 0.111 | 3/3 |
| Qwen | 34.028 / 77.689 / 85.489 | 236; 0.72% | 0.076 | 3/3 |
| Llama 3.1 | 44.600 / 97.311 / 103.680 | 228; 2.22% | 0.063 | 3/3 |

At configured 500/h (POST only), the same arrival seeds offered 528 / 492 / 552 per hour. The model-specific [load evidence](../results/load/) contains:

| Model | Mean achieved/h | Mean POST p95 / p99 (s) | Window failures runs 1 / 2 / 3 | Runs with growth |
|---|---:|---|---|---|
| Gemma | 456 | 82.381 / 86.978 | 0/88; 0/82; 10/92 | 3/3 |
| Llama 3.2 | 450 | 58.039 / 66.515 | 34/88; 0/82; 0/92 | 2/3 |
| Qwen | 170 | 118.746 / 119.201 | 59/88; 59/82; 65/92 | 2/3 |
| Llama 3.1 | 190 | 118.870 / 119.457 | 56/88; 55/82; 59/92 | 2/3 |

For each model see `results/load/<model>/rate-500/summary.csv`, `runs.csv`, raw `run-N.jtl` and the matching reconciliation/service extract. All 36 formal load runs are completed and reconciled; request IDs, response codes and endpoints match the saved extracts. Every captured load failure has service error `OllamaTimeoutError`: 10 Gemma, 34 Llama 3.2, 184 Qwen (one mixed + 183 at 500/h), 173 Llama 3.1 (three mixed + 170 at 500/h). No other service error type appears in those load extracts.

Medium models complete fewer requests as offered load rises from the mixed baseline to 500/h, while successful tail latency approaches 120 s and errors increase. This is observed degradation consistent with saturation of the classification path. Comparison changes both POST rate and search traffic, so it does not isolate a single cause. The substantial Llama 3.2 run-to-run variation also prevents a single capacity estimate.

The configured application timeout is 120 s. Timeout records near that duration support the frozen prediction of timeout failure rather than captured crashes or invalid category failures. Successful-only p95 below 120 s does not mean all requests finish before the timeout.

## Reconciled Qwen stress observations

| Configured rate | Total / measured starts | Offered/h | Successful completions; achieved/h | Error rate | p50 / p95 / p99 (s) | Trend; slope (s/min) | Stopping verdict |
|---|---|---:|---|---|---|---|---|
| 75/h | 15 / 12 | 72 | 13; 78 | 0% | 19.526 / 37.316 / 37.316 | 2.096x; +0.987 | UNSUSTAINABLE by trend only |
| 250/h | 50 / 45 | 270 | 23; 138 | 24/45 (53.3%) | 45.954 / 94.447 / 99.394 | 2.250x; +12.617 | UNSUSTAINABLE by errors, achieved/offered and trend |

Sources: [75/h summary](../results/stress/qwen2.5_7b/lower-rates/stress_summary.json), [75/h reconciliation](../results/stress/qwen2.5_7b/lower-rates/rate-75/run-1.reconciliation.json), [250/h steps](../results/stress/qwen2.5_7b/stress_steps.csv), [250/h reconciliation](../results/stress/qwen2.5_7b/rate-250/run-1.reconciliation.json). Matching `run-1.jtl`, metadata and service extracts are in those run directories. Reconciliation matches 15/15 and 50/50 requests, with no unexplained records. All 24 stress failures are HTTP 502 with `OllamaTimeoutError` in the [250/h service extract](../results/stress/qwen2.5_7b/rate-250/run-1.service_log_extract.jsonl); there are no failures at 75/h.

Stopping criteria are errors >5%, achieved/offered <0.9, growing latency, or p95 >120 s. Growth is operationalised as last-third/first-third median >=1.5 with positive fitted slope; it does not prove every successive latency increased. The 75/h ratio is 1.083 and the 250/h ratio is 0.511. Completions can include warm-up arrivals, explaining achieved above offered at 75/h.

The 75/h step has only 12 measured starts, four observations per trend third. Narrative variability or runtime state could influence the trend. No resource capture explains it. It fails only the configured trend rule, not throughput, errors or the 120 s p95 rule. The generated summary's claim that the limit is below 75/h is stronger than the empirical evidence supports. Neither session includes a passing stress step to bracket a maximum. Do not claim an established maximum sustainable rate or that the service cannot process 75 tickets/h. These POST-only stress sessions also cannot replace the three-run mixed baseline, whose Qwen mean error rate is 0.72%, not 53.3%.

## Measured versus inferred attribution

| Evidence | Available finding | Interpretation limit |
|---|---|---|
| Client JTL and reconciled service extracts | Slow POSTs, load-related throughput degradation, growth flags and timeout errors | Supports classification-path congestion; does not locate an exact internal queue |
| Service request duration and client-minus-service summaries | Service timings and matched IDs are available per run | Application duration includes blocking inference and waiting; client-minus-service includes network and waiting outside middleware, not uniquely network cost |
| Host CPU%, memory, paging and power/thermal traces | Unavailable in committed results | Cannot claim measured CPU saturation, memory pressure, throttling or paging |
| Per-model `ollama ps` during tests | Unavailable; `num_gpu: 0` is configured | Runtime CPU-only execution and residency are not independently verified |
| Docker stats / WSL resource captures | Unavailable | Cannot verify predicted service CPU below 10% or rule out container limits |
| Ollama prefill/decode durations and token rates | Unavailable | Prefill dominance, assumed speeds and prefix reuse remain hypotheses |
| Fresh PC1 model digests | Unavailable; historical provenance exists | Exact benchmark model binaries are not verified |

`results/environment/` and stress observation captures are absent; stress observation notes are empty. [test_environment.md](test_environment.md) preserves the actual hardware/configuration record and gaps. Historical model captures on another machine are not benchmark resource observations.

GET search remains fast under mixed load: all per-run p95 values are 0.045-0.208 s, all measured searches succeed, and no GET run shows the processor's growth flag. The [search route](../app/routes/search.py) accesses stored tickets without generation; POST waits synchronously for Ollama before insertion. This separation plausibly explains why search remains responsive while classification degrades. It weakens a hypothesis of a shared database/API/network bottleneck dominating both routes, but does not prove these components incur no cost or quantify CPU contention.

The frozen inference/queueing hypothesis is therefore consistent with observed symptoms and timeout types. Its stronger claims of measured CPU saturation and prefill dominance cannot be confirmed. Preserve this unoptimised baseline; any hardware or optimisation evaluation is future work.
