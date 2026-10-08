# Requirements evaluation (R1-R4)

Status: **COMPLETE - evidence checked on 2026-10-08**.
The frozen [requirements](requirements.md) govern this evaluation. R1 and R4 use means of three per-run percentiles; R2 must pass in **every** run; R3 uses raw golden-set counts, including failed requests as incorrect.

| Requirement | Gemma 2 2B | Llama 3.2 3B | Qwen 2.5 7B | Llama 3.1 8B |
|---|---|---|---|---|
| R1: mean POST p95 <=15 s and mean p99 <=30 s | FAIL | PASS | FAIL | FAIL |
| R2: each run >=245 successful/h and errors <1% | FAIL | FAIL | FAIL | FAIL |
| R3: overall >=80% and every category >=70% recall | FAIL | FAIL | PASS | FAIL |
| R4: mean search p95 <=1 s at mixed peak | PASS | PASS | PASS | PASS |

The earlier Gemma and Llama 3.2 R2 passes relied on means (254/h and 256/h). Their second runs achieved 234/h and 240/h, so both fail the authoritative per-run rule. That run offered only 234/h due to random arrivals; this explains why the absolute threshold can fail even with zero errors. It does not justify changing the criterion or claiming a processing-capacity limit.

[recommendation.md](recommendation.md) contains measured R1 p95/p99, R2 individual rates/errors and raw counts, R3 category minima, R4 search percentiles and exact per-model evidence links. All 36 load runs were verified against raw JTLs and saved reconciled service extracts. Consolidated load indexes contain Gemma only; use per-model files.

Qwen's separate stress steps reconcile 15/15 and 50/50 requests. The configured 75/h step fails solely on a 2.096x latency trend (12 measured starts, no errors); the configured 250/h step fails on 53.3% errors, 0.511 achieved/offered and a 2.25x trend. These sessions do not replace formal three-repeat mixed-load results and establish no maximum sustainable rate. See [bottleneck analysis](bottleneck_analysis.md).

No candidate passes all four requirements. Qwen is the quality-focused candidate for future hardware/optimisation evaluation, not an already-compliant production deployment. Resource attribution and the benchmark's exact model digests remain unverified; see [completion audit](completion_audit.md).
