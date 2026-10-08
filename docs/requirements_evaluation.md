\# Requirements Evaluation (R1–R4)



\## 1. Evaluation Overview



Four locally deployed Ollama models were evaluated using Apache JMeter and a frozen 180-ticket golden dataset. Performance requirements were assessed using three repeated runs at the target workload of 250 ticket submissions per hour and 450 search requests per hour.



\## 2. Requirements Compliance



| Requirement | Gemma2 2B | Llama 3.2 3B | Qwen 2.5 7B | Llama 3.1 8B |

|---|---|---|---|---|

| R1: POST p95 ≤15s and p99 ≤30s | Fail | Pass | Fail | Fail |

| R2: ≥245 successful tickets/h and errors <1% | Pass | Pass | Fail | Fail |

| R3: Overall accuracy ≥80% and category recall ≥70% | Fail | Fail | Pass | Fail |

| R4: Search p95 ≤1s | Pass | Pass | Pass | Pass |



\*The table reflects consolidated three-run measurements. Individual-run results should also be reviewed when discussing consistency.\*



\## 3. Performance Results



| Model | POST p95 | Achieved tickets/h | Overall accuracy | Lowest category recall |

|---|---:|---:|---:|---:|

| Gemma2 2B | 18.351s | 254 | 67.2% | 15.0% |

| Llama 3.2 3B | 12.800s | 256 | 60.6% | 20.0% |

| Qwen 2.5 7B | 77.689s | 236 | 80.6% | 73.1% |

| Llama 3.1 8B | 97.311s | 228 | 84.4% | 52.9% |



\## 4. Stress-Test Findings



Qwen 2.5 7B was subjected to additional stress testing.



At a configured rate of 75 tickets/hour, no request errors occurred, but the latency trend increased by approximately 2.096 times, triggering the predefined unsustainable criterion.



At 250 tickets/hour, the measured error rate reached 53.3%, achieved/offered throughput was 0.511, and latency increased by approximately 2.25 times.



Both runs were successfully reconciled against the service logs, with 15/15 and 50/50 requests matched respectively. The tests demonstrated performance degradation but did not establish a precise maximum sustainable throughput.



\## 5. Overall Evaluation and Recommendation



None of the four models satisfied all requirements on the tested CPU-only deployment.



Qwen 2.5 7B was the only model satisfying R3, achieving 80.6% overall accuracy and at least 73.1% recall in every category. However, it failed the required throughput and response-time targets.



Llama 3.2 3B satisfied the consolidated R1, R2 and R4 performance targets, but its 60.6% overall classification accuracy was below the required threshold.



Therefore, no model is recommended for fully compliant production deployment on the existing hardware. Qwen 2.5 7B is the preferred candidate for further performance optimization, potentially through GPU acceleration, followed by repeated benchmarking against all four requirements.



\## 6. Supporting Evidence



\- `results/load/` — Three-run JMeter performance results

\- `results/accuracy/` — Golden-set classification evaluation

\- `results/stress/qwen2.5\_7b/` — Stress-test results and service-log reconciliation

\- `data/` — Golden dataset and associated evidence



