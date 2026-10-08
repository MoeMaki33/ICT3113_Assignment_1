# Prediction versus results

Status: **COMPLETE - verified against repository evidence on 2026-10-08**.
The [frozen record](prediction_record.md) remains unchanged.

## Freeze and evidence identity

Git history identifies `2db5306d41a5b8dee9812cec005c4145dfd734fe`
(Finalise reviewed pre-benchmark freeze) as the final prediction/requirements
freeze. `87e839f2452e5c42572575516ce17c23d8ab91b3` is the earlier freeze;
`99cf39b02fdfeedbc80e592e7a621b05ba60adad` changed golden-set provenance and
validation, not predictions. The frozen record's embedded hash field still says
pending; this separate analysis supplies the verified hash without amending it.

- Prediction working-file SHA-256 (CRLF, also recorded in load metadata):
  `c0e933fe2b3aba05918dd8be2d42bd03ef05ea8428900db1353654fcdf472497`.
- Prediction Git-blob SHA-256 (LF at the final freeze):
  `9f0ee1d190bead176077cbb06edbaf2f3ba772ec260eb76f9019d39b464c9e1c`.
  Content is identical after normalising CRLF/LF; this is a byte-format difference.
- Frozen golden-set SHA-256, matching all completed accuracy metadata:
  `54ae476fc87e20de9356b55fd741392857bd274c6f48c0f475d1229343a46c2e`.

Official completed accuracy evidence, each containing `metrics.json`,
`metadata.json`, `predictions.csv`, `per_category.csv` and `confusion_matrix.csv`:

| Model | Metrics | Recorded execution commit |
|---|---|---|
| Gemma | [run-2](../results/accuracy/gemma2_2b/run-2/metrics.json) | `1bc38e2ff2a5a73de21829b9b153f0658d730158` |
| Llama 3.2 | [run-1](../results/accuracy/llama3.2_3b/run-1/metrics.json) | `9559e90d575cb3faca58aa8ee850c9b38fe290bd` |
| Qwen | [run-1](../results/accuracy/qwen2.5_7b/run-1/metrics.json) | `9559e90d575cb3faca58aa8ee850c9b38fe290bd` |
| Llama 3.1 | [run-1](../results/accuracy/llama3.1_8b/run-1/metrics.json) | `a6eb0adc587a04102756c221a3700c6c5fc8213a` |

Gemma run-1 is incomplete (`status: running`) and is excluded. Gemma run-2
and Qwen metadata record dirty worktrees; the commit alone cannot identify all
execution-time files. [Environment](test_environment.md) records official PC1
i7-10510U, 4 cores/8 logical processors, 15.8 GB RAM, and separate PC2 Ryzen
5800X3D. CPU-only is configured, with no per-model runtime processor capture.
[Historical digests](models.md) exist in
[model provenance](../results/model_provenance.json), but fresh PC1 digests
are unavailable: the benchmark's exact model binaries are **not verified**.

## Accuracy and sequential latency

Actual accuracy uses correct/all 180 tickets, counting failed attempts incorrect.
Percentage-point differences below use raw counts, rounded to three decimals.
Actual latency uses `single_request_latency_excluding_first`: client-measured,
sequential successful POSTs, nearest-rank p50/p95, excluding the **first attempt**
even if failed. Samples are 179 for each model except Qwen (177 due to two HTTP
502 failures). This approximates the prediction's warm single-request condition
but does not independently verify residency or absence of background work.

| Model | Predicted accuracy | Actual correct / accuracy | Actual minus prediction (pp) | Predicted median / p95 (s) | Actual p50 / p95 (s) |
|---|---:|---|---:|---|---|
| `gemma2:2b` | 70% | 121/180; 67.222% | -2.778 | 1.8 / 3.5 | 7.081 / 12.937 |
| `llama3.2:3b` | 72% | 109/180; 60.556% | -11.444 | 2.2 / 4.2 | 5.218 / 11.141 |
| `qwen2.5:7b` | 82% | 145/180; 80.556% | -1.444 | 5.0 / 9.5 | 11.237 / 23.960 |
| `llama3.1:8b` | 80% | 152/180; 84.444% | +4.444 | 5.5 / 10.5 | 11.004 / 24.092 |

| Model | Median increase (s); actual/predicted | p95 increase (s); actual/predicted |
|---|---|---|
| Gemma | +5.281; 3.934x | +9.437; 3.696x |
| Llama 3.2 | +3.018; 2.372x | +6.941; 2.653x |
| Qwen | +6.237; 2.247x | +14.460; 2.522x |
| Llama 3.1 | +5.504; 2.001x | +13.592; 2.294x |

All latency predictions were optimistic. The assumed prefill/generation speeds
and prefix reuse were unmeasured. CPU-only inference and queueing plausibly
explain slow POSTs, but no Ollama timing split verifies prefill dominance.
Latency differences under load are separate from sequential timing; see
[bottleneck analysis](bottleneck_analysis.md).

## Requirement predictions versus decisions

Apply the unchanged [requirements](requirements.md), with measured values and
per-run counts in [recommendation.md](recommendation.md). R3 is split here to
match the frozen prediction table.

| Model | R1 predicted / actual | R2 predicted / actual | R3 overall predicted / actual | R3 category floors predicted / actual | R4 actual |
|---|---|---|---|---|---|
| Gemma | PASS / FAIL | PASS / FAIL | FAIL / FAIL | FAIL / FAIL | PASS |
| Llama 3.2 | PASS / PASS | PASS / FAIL | FAIL / FAIL | FAIL / FAIL | PASS |
| Qwen | PASS / FAIL | PASS / FAIL | PASS / PASS | FAIL / PASS | PASS |
| Llama 3.1 | PASS / FAIL | PASS / FAIL | PASS / PASS | FAIL / FAIL | PASS |

The record predicted search would not be the bottleneck but did not give an
explicit per-model R4 verdict. All measured R4 means pass. R2 failures for the
small models arise in the low-arrival second run; they are formal acceptance
failures, not a measured capacity ceiling. The predicted conclusion that no
candidate passes everything holds, but Qwen meets all quality floors and fails
performance rather than the predicted Debt collection floor.

## Category hypotheses

Raw correct/category totals below come from each completed run's per-category
metrics and confusion matrix. They also support exact R3 threshold comparisons.

| Category | Gemma | Llama 3.2 | Qwen | Llama 3.1 |
|---|---|---|---|---|
| Credit reporting | 33/38 (86.8%) | 33/38 (86.8%) | 33/38 (86.8%) | 35/38 (92.1%) |
| Debt collection | 9/17 (52.9%) | 8/17 (47.1%) | 13/17 (76.5%) | 9/17 (52.9%) |
| Mortgage | 30/32 (93.8%) | 26/32 (81.2%) | 25/32 (78.1%) | 30/32 (93.8%) |
| Credit card | 16/26 (61.5%) | 11/26 (42.3%) | 19/26 (73.1%) | 19/26 (73.1%) |
| Bank account or service | 21/29 (72.4%) | 21/29 (72.4%) | 25/29 (86.2%) | 25/29 (86.2%) |
| Consumer loan | 3/20 (15.0%) | 4/20 (20.0%) | 15/20 (75.0%) | 17/20 (85.0%) |
| Money transfer or service | 9/18 (50.0%) | 6/18 (33.3%) | 15/18 (83.3%) | 17/18 (94.4%) |

Debt collection was weakest only for Llama 3.1. Consumer loan was weakest for
both small models; Credit card was weakest for Qwen. Qwen passed all seven
floors, including 13/17 Debt collection. Mortgage was not at least 90% for
Llama 3.2 or Qwen. Human disagreement patterns suggested useful hypotheses
but did not determine model performance. Two Qwen failures were HTTP 502 and
count as incorrect; an HTTP status alone does not identify invalid output.

## Sustainable-rate predictions versus available tests

| Model | Frozen predicted maximum (tickets/h) | Actual evidence and limitation |
|---|---:|---|
| Gemma | about 1800 | At configured 500/h, mean achieved 456/h; all three runs show growing latency, run 3 has 10/92 errors. No stepped stress maximum. |
| Llama 3.2 | about 1500 | At configured 500/h, achieved 306 / 492 / 552 per hour; run 1 has 34/88 errors and runs 1/3 show growth. No stepped stress maximum. |
| Qwen | about 650 | Dedicated 75/h and 250/h steps fail stopping rules; no successful step establishes a sustainable bracket. |
| Llama 3.1 | about 600 | At configured 500/h, achieved 204 / 192 / 174 per hour and 63.6-67.1% errors. No stepped stress maximum. |

Evidence: each model's `results/load/<model>/rate-500/summary.csv` and
`runs.csv`; Qwen [250/h stress steps](../results/stress/qwen2.5_7b/stress_steps.csv)
and [75/h steps](../results/stress/qwen2.5_7b/lower-rates/stress_steps.csv).
The prediction that all models keep up at 500/h is unsupported by these runs.
Formal 125/h observations are short lower-load measurements, not established
long-term sustainable limits.

The 75/h step had only 12 measured starts (15 total), zero errors, measured
offered 72/h and achieved 78/h, but a 2.096x trend triggered stopping. The
250/h step offered 270/h, achieved 138/h, had 53.3% errors and a 2.25x trend.
These are distinct stress sessions, not the baseline mixed-load averages.
The generated stress conclusion says the limit is below the first step; that
is a stopping-rule interpretation, **not** an empirically established capacity
maximum or proof that Qwen cannot process 75/h. No measured maximum can be
substituted for any frozen sustainable-rate prediction.
