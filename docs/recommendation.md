# Model recommendation

Status: **COMPLETE - evidence verified on 2026-10-08**.
No candidate meets all requirements on the tested configuration, which requests CPU-only inference. Qwen is the quality-focused candidate for subsequent hardware/optimisation evaluation, not an already-compliant production deployment.

## Frozen rules and verified verdicts

[requirements.md](requirements.md), finalised in `2db5306d41a5b8dee9812cec005c4145dfd734fe`, is authoritative. Its rules agree with the former recommendation template. The old evaluation incorrectly treated mean throughput as sufficient for R2; thresholds have not changed.

- R1: mean of three POST p95 values <=15 s **and** mean p99 <=30 s.
- R2: **every run** achieves >=245 successful classifications/h and errors <1%.
- R3: >=144/180 correct overall (80%) and >=70% recall in every category; failed classifications count as incorrect.
- R4: mean of three GET search p95 values <=1 s under mixed load.

R1/R2/R4 use configured **250 tickets/h + 450 searches/h**. Each measured window is 600 s, after 120 s warm-up within a 720 s arrival schedule. Achieved rate counts successful completions within the window; errors count failed requests started within it. Latencies are nearest-rank percentiles of successful requests started within the window, including those finishing during drain. These are the existing [processor definitions](../scripts/process_jmeter_results.py), not all-attempt or pooled percentiles. Read success-only latency alongside errors because it excludes timeout attempts.

| Model | R1 mean POST p95 / p99 (s) | R2 achieved/h runs 1 / 2 / 3; errors (%) | R3 correct/180; lowest recall | R4 mean search p95 (s) |
|---|---|---|---|---|
| `gemma2:2b` | **FAIL** 18.351 / 23.542 | **FAIL** 258 / 234 / 270; 0 / 0 / 0 | **FAIL** 121/180 (67.2%); Consumer loan 3/20 (15.0%) | **PASS** 0.055 |
| `llama3.2:3b` | **PASS** 12.800 / 16.838 | **FAIL** 258 / 240 / 270; 0 / 0 / 0 | **FAIL** 109/180 (60.6%); Consumer loan 4/20 (20.0%) | **PASS** 0.111 |
| `qwen2.5:7b` | **FAIL** 77.689 / 85.489 | **FAIL** 228 / 240 / 240; 0 / 0 / 2.174 | **PASS** 145/180 (80.6%); Credit card 19/26 (73.1%) | **PASS** 0.076 |
| `llama3.1:8b` | **FAIL** 97.311 / 103.680 | **FAIL** 210 / 234 / 240; 6.667 / 0 / 0 | **FAIL** 152/180 (84.4%); Debt collection 9/17 (52.9%) | **PASS** 0.063 |

Display values are rounded; decisions use counts and individual-run evidence. Mean achieved rates (254 / 256 / 236 / 228 per hour) do not establish R2 compliance. Run 2 offered only 234/h for every model. Gemma completed 39 and Llama 3.2 completed 40 classifications in ten minutes, below 245/h. This fails the frozen absolute rule; it does not prove these two models lack 245/h processing capacity. Short Poisson windows limit this acceptance test. Replacing the rule with an offered-rate ratio after seeing results would change the requirement.

## Individual mixed-load evidence

POST counts are starts / successful starts / failed starts / successful completions in the window. Completion counts can include warm-up arrivals.

| Model | Run | POST counts | POST p95 / p99 (s) | GET starts; p95 (s) |
|---|---:|---|---|---|
| Gemma | 1 | 45 / 45 / 0 / 43 | 18.632 / 27.500 | 72; 0.045 |
| Gemma | 2 | 39 / 39 / 0 / 39 | 16.574 / 17.067 | 77; 0.056 |
| Gemma | 3 | 46 / 46 / 0 / 45 | 19.847 / 26.059 | 76; 0.064 |
| Llama 3.2 | 1 | 45 / 45 / 0 / 43 | 13.044 / 19.217 | 72; 0.208 |
| Llama 3.2 | 2 | 39 / 39 / 0 / 40 | 10.632 / 11.440 | 77; 0.056 |
| Llama 3.2 | 3 | 46 / 46 / 0 / 45 | 14.723 / 19.858 | 76; 0.070 |
| Qwen | 1 | 45 / 45 / 0 / 38 | 78.844 / 97.471 | 72; 0.050 |
| Qwen | 2 | 39 / 39 / 0 / 40 | 44.692 / 46.198 | 77; 0.056 |
| Qwen | 3 | 46 / 45 / 1 / 40 | 109.530 / 112.798 | 76; 0.121 |
| Llama 3.1 | 1 | 45 / 42 / 3 / 35 | 109.920 / 116.510 | 72; 0.052 |
| Llama 3.1 | 2 | 39 / 39 / 0 / 39 | 77.952 / 80.553 | 77; 0.072 |
| Llama 3.1 | 3 | 46 / 46 / 0 / 40 | 104.062 / 113.977 | 76; 0.066 |

All GET starts succeeded. Offered POST rates are 270 / 234 / 276 per hour; GET rates are 432 / 462 / 456. Each mixed-load run reconciles all 140 client samples with no unexplained records. All 36 formal load runs (four models x three workloads x three repeats) are completed and reconciled.

Each configuration contains `summary.csv`, `runs.csv`, `run-N.jtl`, `run-N.json`, `run-N.reconciliation.json` and `run-N.service_log_extract.jsonl`:

- [Gemma summary](../results/load/gemma2_2b/rate-250_search-450/summary.csv) and [runs](../results/load/gemma2_2b/rate-250_search-450/runs.csv).
- [Llama 3.2 summary](../results/load/llama3.2_3b/rate-250_search-450/summary.csv) and [runs](../results/load/llama3.2_3b/rate-250_search-450/runs.csv).
- [Qwen summary](../results/load/qwen2.5_7b/rate-250_search-450/summary.csv) and [runs](../results/load/qwen2.5_7b/rate-250_search-450/runs.csv).
- [Llama 3.1 summary](../results/load/llama3.1_8b/rate-250_search-450/summary.csv) and [runs](../results/load/llama3.1_8b/rate-250_search-450/runs.csv).

`results/load/summary_all.csv`, `summary_all.md` and `runs_all.csv` contain Gemma only in the verified checkout. Use per-configuration evidence above for four-model comparisons. No result artifacts were regenerated.

## Accuracy/performance trade-off

Qwen alone meets both R3 thresholds: 145 correct and all seven category counts at or above their minimums. Llama 3.1 has higher overall accuracy (152 correct) but only 9/17 correct Debt collection tickets. Llama 3.2 has the fastest measured sequential and mixed-load latency but only 109/180 correct. Gemma is less accurate than either medium model and misses R1. See [accuracy evidence](../results/accuracy/accuracy_summary.md) and [all category counts](prediction_vs_results.md).

No fully compliant production deployment is supported on this tested CPU-only configuration. Prioritise Qwen for subsequent hardware/optimisation evaluation because accuracy is the team's priority, then reassess all four requirements. Potential GPU acceleration is an untested future hypothesis. Qwen is just one ticket above the overall R3 minimum; 180 tickets do not establish population-wide accuracy.

The [75/h reconciliation](../results/stress/qwen2.5_7b/lower-rates/rate-75/run-1.reconciliation.json) and [250/h reconciliation](../results/stress/qwen2.5_7b/rate-250/run-1.reconciliation.json) support degradation evidence, not an established maximum sustainable rate. [Bottleneck analysis](bottleneck_analysis.md) distinguishes observations from inference. Runtime CPU utilisation, paging, prefill/decode timing and fresh PC1 model digests are unavailable; historical digests do not identify the benchmark's exact binaries. See [completion audit](completion_audit.md) for remaining provenance limitations.
