# Performance and accuracy requirements

Owner: Person 4. Status: **FINAL (2026-10-07)**: the whole team agrees these before the freeze
commit. They are requirements, not results; nothing here has been measured.

Load figures come from `docs/workload_model.md`: design peak **250 tickets/h** and peak search
rate **450 searches/h**.

## Team position: accuracy before speed

A misrouted ticket costs an agent's time to recognise and re-route it, and delays the
customer's resolution by hours. A slower classification costs seconds, because a human agent
picks the ticket up minutes or hours later in any case. The requirements are therefore strict
on accuracy and comparatively generous on latency. Latency is still bounded so the intake keeps
up with the peak and a submission does not appear to hang.

## R1 – Response time of `POST /tickets`

> At an open-loop arrival rate of **250 tickets/h** (design peak), using narratives from our team's
> rows, **95% of `POST /tickets` requests complete within 15 s** and **99% within 30 s**, measured
> over the steady-state window of each run.

- **Workload:** at 250/h a ticket arrives on average every 14.4 s. If most classifications take
  longer than about one arrival gap, requests queue and latency keeps growing. A 15 s p95 keeps the
  service close to that bound.
- **Usability:** `POST /tickets` is synchronous, so the intake system waits for it. 15 s is our
  estimate of the longest wait an intake form can show before it looks broken.
- **Capacity:** 30 s p99 stays well below the service's 120 s Ollama timeout, beyond which
  requests fail with 502.
- **Pass:** p95 ≤ 15 s and p99 ≤ 30 s, taking the mean across the three runs.

## R2 – Throughput

> At an offered open-loop rate of **250 tickets/h**, sustained for the measured window, the service
> **completes at least 245 successful classifications per hour** (≥ 98% of the offered rate)
> with an **error rate below 1%**.

- **Workload:** 250/h is the design peak (estimated peak 177/h × 1.25 headroom).
- **Capacity:** if achieved throughput falls below the offered rate, a backlog builds during the
  busiest hour and tickets wait unrouted.
- **Pass:** in every one of the three runs, achieved throughput ≥ 245/h and error rate < 1%.
  Errors are non-2xx responses, including 502 classification failures.

## R3 – Classification accuracy (golden set)

> On the frozen golden set (`data/golden_set_final.csv`, 180 tickets), each ticket sent through
> `POST /tickets`: **overall accuracy ≥ 80%** and **accuracy ≥ 70% in every one of the seven
> categories**. Per-category accuracy = correct predictions / golden tickets of that category
> (recall).

- **Cost of misrouting:** every misrouted ticket costs agent time and delays the customer, so this
  is the requirement the team weights most.
- **Anchor:** our two trained human annotators agreed on 85.0% of tickets
  (`results/accuracy/agreement.json`). Requiring a model to match humans would be unrealistic;
  80% means "nearly as consistent as a trained human".
- **Per category:** a 70% floor stops a model from passing overall while failing one team (for
  example, routing most debt-collection tickets elsewhere).
- **Small samples:** the number of correct tickets needed in each category is:

| Category | Golden tickets | Correct needed (≥ 70%) |
|---|---|---|
| Credit reporting | 38 | 27 |
| Mortgage | 32 | 23 |
| Bank account or service | 29 | 21 |
| Credit card | 26 | 19 |
| Consumer loan | 20 | 14 |
| Money transfer or service | 18 | 13 |
| Debt collection | 17 | 12 |
| **Overall (≥ 80%)** | **180** | **144** |

- A ticket that fails to classify (502) counts as incorrect.

## R4 – Search response time under mixed load

> While `POST /tickets` receives **250 tickets/h** open-loop, `GET /search` receiving **450 searches/h**
> open-loop completes **95% of requests within 1 s**.

- **Workload:** 45 agents × 10 searches/h at peak.
- **Usability:** agents search interactively while handling tickets; a lookup slower than about 1 s
  interrupts their work.
- **Pass:** p95 ≤ 1 s for `GET /search`, taking the mean across the three runs.

## How each requirement is tested

| Requirement | Test (Person 5) | Evidence |
|---|---|---|
| R1, R2 | JMeter open-loop load test at 250/h, three runs | `.jtl` files reconciled with `logs/service.log` |
| R3 | Accuracy test over all 180 golden tickets for each candidate | Raw per-ticket predictions under `results/accuracy/` |
| R4 | JMeter mixed load (tickets + searches), three runs | `.jtl` files and service logs |
