# Stress test: `qwen2.5:7b`

**PROVISIONAL: service-log reconciliation is required for every step. Already unsustainable at the first step (250/h): the limit is below it. Start a new test (--label) with lower rates.**

Stopping criteria (fixed before the first step): error rate > 5%; achieved/offered < 0.9; continuously growing latency; p95 > 120.0 s. Each step: 720 s schedule, first 120 s excluded, 200 s cool-down between steps.

| # | Rate set /h | Offered /h | Achieved /h | Achieved/offered | Error rate | p50 s | p95 s | p99 s | Trend ratio | Verdict | Reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 250 | 270.0 | 138.0 | 0.511 | 53.3% | 45.954 | 94.447 | 99.394 | 2.25 | UNSUSTAINABLE | error rate 53.3% > 5%; achieved/offered 0.51 < 0.9; latency kept growing (last/first third median x2.25) |

Observations (fill in from the service machine: CPU %, `ollama ps`, memory, log errors):

