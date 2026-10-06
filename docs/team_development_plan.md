# ICT3113 Assignment 1 – Team Development Plan

Revised 2026-10-07 to match the team's actual division of work. The original
plan split DevOps/logging into a separate role and gave accuracy testing to the
dataset lead; the team instead works as follows:

- **Person 1** built the whole service platform (API, database, Docker, configuration, logging, integration tests, repository layout).
- **Person 2** owns the Ollama backend, classifier and candidate models.
- **Person 3** owns the golden test set, labelling workflow and agreement.
- **Person 4** owns the workload model, requirements and prediction record.
- **Person 5** owns all testing: JMeter load and stress tests, accuracy tests, result processing, log reconciliation and the test playbook.

## 1. Project Overview

This project builds a **Ticket Triage Service** for automatically classifying financial complaint tickets.

The system must run locally using **Docker** and **Ollama on CPU only**.

The system must provide:

```text
POST /tickets
GET /search
GET /stats
```

`POST /tickets` receives a ticket narrative, sends it to the selected Ollama model for classification, stores the ticket and classification result, and returns the assigned category.

`GET /search` searches previously stored tickets.

`GET /stats` returns the number of stored tickets in each category.

The seven possible categories are (`app/categories.py`):

```text
Credit reporting
Debt collection
Mortgage
Credit card
Bank account or service
Consumer loan
Money transfer or service
```

Team number: **7** — the team's rows are **7000–7999** of `data/ict3113_tickets.csv`.

---

# 2. Team Split

| Member   | Main Responsibility                              | Owns                                                                                   |
| -------- | ------------------------------------------------ | -------------------------------------------------------------------------------------- |
| Person 1 | Backend / Platform Lead                          | `/tickets`, `/search`, `/stats`, database, Docker, configuration, request logging, integration tests, repository layout |
| Person 2 | Ollama / Classification Lead                     | Ollama client, prompt, output parsing, model switching, candidate models and digests   |
| Person 3 | Golden Set Lead                                  | Team rows, golden-set selection, labelling protocol, annotator sheets, agreement, disagreement resolution, final golden set |
| Person 4 | Workload / Requirements / Predictions Lead       | Workload model, ticket-length analysis, arrival-rate calculations, requirements, prediction record |
| Person 5 | Testing Lead                                     | Test environment record, JMeter load and stress tests, accuracy tests, result processing, log reconciliation, test playbook |

Everyone should understand the complete system even though each person owns a particular area.

---

# 3. Person 1 – Backend / Platform Lead

## Main Goal

Build the Ticket Triage web service and the platform it runs on, so that it can be rebuilt and run with `docker compose`.

## Task 1 – `POST /tickets`

```text
Receive ticket → validate narrative → call Person 2's classify_ticket()
→ receive category → store ticket + category + model → return 201 {id, category}
```

Classification is **synchronous**: the endpoint waits for Ollama before responding.
Do NOT implement caching, queues, async background classification, or pre-computed classifications.
Classification failure returns 502 and stores nothing.

## Task 2 – `GET /search`

`GET /search?q=<text>` returns stored tickets whose narrative contains the query.

## Task 3 – `GET /stats`

Returns ticket counts for all seven categories, including zeros.

## Task 4 – Database

Minimum fields: `id`, `narrative`, `category`, `model`, `created_at`.
The service starts empty. **Tickets enter only through `POST /tickets`; the CSV is never imported.**

## Task 5 – Docker and Configuration

`Dockerfile`, `docker-compose.yml` and `.env.example` (`OLLAMA_URL`, `OLLAMA_MODEL`,
`OLLAMA_TIMEOUT_SECONDS`, `DATABASE_URL`, `LOG_LEVEL`). Ollama runs on the host; the container
reaches it through `host.docker.internal`. No secrets are committed.

## Task 6 – Request Logging

Every request writes one JSON line to `logs/service.log`: request ID, timestamps, endpoint,
method, model, duration, status, ticket ID, predicted category, error. Every response carries
`X-Request-ID` so Person 5 can reconcile JMeter samples with log lines. Narratives and query
strings are never logged.

## Task 7 – Tests and Repository Layout

API, backend and integration tests under `tests/`, using temporary SQLite databases and mocked
classification. Person 1 keeps the repository layout in section 13 consistent.

### Person 1 Deliverables

```text
app/main.py, app/config.py, app/categories.py
app/routes/{tickets,search,stats}.py
app/database/{db,models}.py
app/schemas/tickets.py
app/services/request_logger.py
Dockerfile, docker-compose.yml, .env.example, requirements.txt
tests/test_api.py, tests/test_backend.py, tests/test_integration.py
```

---

# 4. Person 2 – Ollama / Classification Lead

## Main Goal

Implement all interaction between the application and Ollama. Person 1 does not write
model-specific code inside `/tickets`.

```text
POST /tickets → classifier.py → ollama_client.py → Ollama → category
```

## Tasks

1. **Ollama client** (`app/services/ollama_client.py`): one blocking `/api/generate` call per ticket
   with `num_gpu: 0` (CPU only) and `temperature: 0`; distinct errors for unavailable, timeout,
   unknown model, invalid response and missing configuration.
2. **Prompt** (`app/services/classifier.py`): the model must choose exactly one of the seven
   categories and reply with the name only; the complaint is delimited and treated as data.
3. **Output validation**: accept a category only as a whole first line; reject prose, unknown
   values and output naming more than one category.
4. **Model switching**: `OLLAMA_MODEL=<exact tag>`; no tag is hardcoded in `app/`.
5. **Candidate models**: 3–5 models across at least two size classes, each pinned by exact tag
   and digest, with licence and selection rationale.

### Person 2 Deliverables

```text
app/services/classifier.py
app/services/ollama_client.py
app/candidate_models.py
docs/models.md
scripts/record_model_digests.py
results/model_provenance.json
tests/test_classifier.py, tests/test_ollama_client.py, tests/test_candidate_models.py
```

Digests must be recorded on the machine that runs the benchmarks, with
`python scripts/record_model_digests.py --json results/model_provenance.json`.

---

# 5. Person 3 – Golden Set Lead

## Main Goal

Build a manually labelled **golden test set of 150–200 tickets** from the team's 1,000 rows,
frozen before any model sees it. `source_label` in the course CSV is NOT the correct answer.

## Tasks

1. **Extract team rows**: `scripts/extract_team_data.py` → `data/team.csv` (rows 7000–7999,
   columns `row,narrative`). The course CSV is never modified.
2. **Reproducible selection**: `scripts/create_golden_set.py` ranks tickets by SHA-256 of seed,
   row and narrative and writes `data/labelling/selection.json` plus two blank, separate sheets.
3. **Labelling protocol**: `docs/labelling_protocol.md` — definitions, include/exclude rules,
   indicators and edge cases per category; rules for multiple, ambiguous and none-of-seven
   tickets; disagreement resolution; revision history.
4. **Independent labelling**: Annotator A and Annotator B label their own sheet without conferring.
5. **Agreement**: `scripts/agreement.py` — total, agreed, disagreed, raw agreement and unweighted
   Cohen's kappa; result kept in `results/accuracy/agreement.json`.
6. **Disagreement resolution**: every disagreement resolved by discussion and recorded in
   `data/labelling/disagreements.csv`; the protocol is revised where a gap is found.
7. **Final golden set**: `scripts/finalize_golden_set.py` → `data/golden_set_final.csv`
   (`row,narrative,final_golden_category`); refuses to overwrite.

### Person 3 Deliverables

```text
scripts/extract_team_data.py, scripts/create_golden_set.py
scripts/agreement.py, scripts/finalize_golden_set.py
data/team.csv
data/labelling/{selection.json,annotator_a.csv,annotator_b.csv,disagreements.csv}
data/golden_set_final.csv
docs/labelling_protocol.md
results/accuracy/agreement.json
tests/test_golden_workflow.py
```

---

# 6. Person 4 – Workload / Requirements / Predictions Lead

## Main Goal

Turn the client scenario into numbers the tests can be judged against, and record the team's
predictions before any benchmark runs. This work happens BEFORE benchmarking and never uses
measured results.

## Task 1 – Workload Model (`docs/workload_model.md`)

Estimate ticket volume, tickets per day and hour, agent-side search rate, peak and non-peak
periods, and the narrative-length distribution. Keep two clearly separate tables:

- **Source-derived figures**: source, URL, publication date, exact figure, how it is used.
- **Our estimates / assumptions**: the value and exactly how it was derived.

## Task 2 – Ticket-Length Analysis

A read-only script over `data/team.csv` reporting count, min, max, mean, median, p50, p95 and p99
of characters and words. Its output is saved under `results/` so the figures are traceable.

## Task 3 – Arrival-Rate Calculations

A script that computes the average arrival rate, peak arrival rate, test arrival rates and search
rate from the workload inputs, showing every formula.

## Task 4 – Requirements (`docs/requirements.md`)

Testable requirements, each with a number, a percentile where relevant, and the load condition:

- **Response time** — endpoint, threshold, percentile, load condition (must cover the peak).
- **Throughput** — classifications per time unit under sustained load.
- **Accuracy** — minimum overall and minimum per-category accuracy on the golden set.

Each requirement is justified from the workload model, usability, capacity or the cost of
misrouted tickets. The whole team agrees them before benchmarking.

## Task 5 – Prediction Record (`docs/prediction_record.md`)

Specific enough to be proven wrong:

- Where the bottleneck will be under load, and why.
- For every candidate tag in `docs/models.md`: expected golden-set accuracy and expected
  single-request latency on the test hardware.
- Which categories will be hardest to classify, and why.

Any measurement the team had seen before writing the predictions (for example setup smoke
tests) is disclosed in the record. **The prediction record is committed before the first
benchmark and never edited afterwards.**

### Person 4 Deliverables

```text
docs/workload_model.md
docs/requirements.md
docs/prediction_record.md
scripts/ticket_lengths.py
scripts/workload_calc.py
results/workload/
tests/test_workload.py
```

---

# 7. Person 5 – Testing Lead

## Main Goal

Run every official test, process the results, and make every reported number traceable to raw
evidence. Official benchmarks must NOT start until all of these are true:

```text
1. Golden test set complete
2. Golden test set committed
3. Prediction record complete
4. Prediction record committed
5. Baseline service working
6. Ollama candidate models configured (pulled, digests recorded on the test machine)
```

Person 5 never modifies the frozen golden labels or the prediction record, and never optimises
the baseline. A bottleneck that is found is diagnosed and documented, not fixed (that is Assignment 2).

## Task 1 – Test Environment Record

A template/script recording, for each machine: CPU, RAM, OS and relevant software.

```text
Service machine     CPU, RAM, OS, Docker, Python
Ollama machine      CPU, RAM, OS, Ollama version
Load generator      CPU, RAM, OS, JMeter and Java versions
Network             Connection type, addresses, link speed
```

**The load generator MUST run on a separate machine from the service and Ollama.**

## Task 2 – JMeter Load Test

`jmeter/ticket_load_test.jmx`: reads narratives from the team's rows (CSV Data Set Config) and
sends each one as JSON to `POST /tickets`, escaping narratives correctly. The CSV is never
imported into the service.

Traffic is **open-loop**, using the Open Model Thread Group or the Precise Throughput Timer.
Closed-loop results are not accepted as evidence.

## Task 3 – Configurable Arrival Rates

The arrival rate, duration, target host and output path are JMeter properties (`-J...`), so new
rates need no plan edits. The test rates come from Person 4's `docs/workload_model.md`.

## Task 4 – Three Runs per Configuration

Raw results are never overwritten:

```text
results/load/<model-tag>/rate-<X>/run-1.jtl
results/load/<model-tag>/rate-<X>/run-2.jtl
results/load/<model-tag>/rate-<X>/run-3.jtl
```

## Task 5 – Result Processing

`scripts/process_jmeter_results.py` computes for every run: p50, p95, p99 latency, achieved
throughput and error rate; and across the three runs: mean and spread. Missing runs are reported
as missing, never filled in. Output is machine-readable CSV/JSON plus presentation-ready tables.

## Task 6 – Accuracy Testing

`scripts/accuracy_test.py`, per candidate model:

```text
Configure OLLAMA_MODEL → read data/golden_set_final.csv → POST /tickets for every ticket
→ record predicted category → compare with final_golden_category
```

Reports overall accuracy, per-category accuracy and a confusion matrix, and keeps the raw
per-ticket predictions under `results/accuracy/<model-tag>/`. The golden labels are never modified.

## Task 7 – Stress Test

One stress test on at least one candidate model that finds a real limit — for example the highest
arrival rate before latency grows without bound or errors become unacceptable. Load increases in
defined steps with stopping criteria written down before the run. Record offered rate, achieved
throughput, p50/p95/p99, error rate and observations. The limit comes only from measurements.

## Task 8 – Log Reconciliation

A check that matches every JMeter sample to its service-log line through `X-Request-ID` and
compares counts, status codes and timings. `.jtl` files, service logs and raw accuracy outputs
are never deleted. Development traffic is kept out of benchmark logs.

## Task 9 – Test Playbook

A playbook detailed enough for another tester to repeat every test without asking the team:

- **Load test**: prerequisites, machines, commands, model, arrival rates, duration, JMeter configuration, repetitions, output locations.
- **Accuracy test**: prerequisites, golden-set location, model selection, execution, output.
- **Stress test**: starting load, increment strategy, stopping criteria, recorded metrics.

### Person 5 Deliverables

```text
jmeter/ticket_load_test.jmx
jmeter/stress_test.jmx (or the load plan with stress properties)
scripts/process_jmeter_results.py
scripts/accuracy_test.py
scripts/reconcile_logs.py
docs/test_environment.md
docs/test_playbook.md
results/load/, results/stress/, results/accuracy/
```

---

# 8. Shared Team Tasks

## Golden Set Labelling

At least TWO people independently label every golden-set ticket (Annotator A and Annotator B),
without conferring. Disagreements are then resolved by discussion and recorded.

## Requirements and Predictions

Person 4 drafts them; the whole team reviews and agrees them before the freeze commit.

## Final Analysis and Slides

Everyone contributes to comparing results with requirements, diagnosing the bottleneck, the
model recommendation and the 12 slides.

---

# 9. IMPORTANT Git Checkpoint

Before the FIRST benchmark, the repository MUST already contain:

```text
Golden test set
Labelling protocol and revisions
Independent label sheets
Agreement calculation/results
Prediction record
```

Create a clearly identifiable commit, for example:

```text
Freeze golden set and prediction record before benchmarking
```

Only after that commit may accuracy, load or stress benchmark runs begin.

---

# 10. Git Workflow

Everyone works on their own branch and merges through Pull Requests. Do not edit `main` directly.

```bash
git checkout -b <your-branch>
git add <files>
git commit -m "Describe the change"
git push origin <your-branch>
```

---

# 11. Testing Order

```text
1.  Extract team's 1,000 rows                        (Person 3)
2.  Write labelling protocol                         (Person 3)
3.  Create + independently label golden set          (Person 3 + annotators)
4.  Build baseline API, Docker and logging           (Person 1)
5.  Connect Ollama                                   (Person 2)
6.  Verify /tickets, /search and /stats              (Person 1)
7.  Select and pin candidate models                  (Person 2)
8.  Complete workload model                          (Person 4)
9.  Define requirements                              (Person 4, team agrees)
10. Write prediction record                          (Person 4, team agrees)
11. COMMIT GOLDEN SET + PREDICTIONS

==============================
DO NOT BENCHMARK BEFORE THIS
==============================

12. Record test environment                          (Person 5)
13. Run accuracy tests                               (Person 5)
14. Run JMeter load tests, THREE runs each           (Person 5)
15. Run stress test                                  (Person 5)
16. Process results and reconcile with logs          (Person 5)
17. Compare results against requirements             (team)
18. Diagnose bottleneck                              (team)
19. Make final model recommendation                  (team)
20. Prepare slides                                   (team)
```

---

# 12. Definition of Done for Each Member

## Person 1

```text
[ ] POST /tickets implemented
[ ] GET /search implemented
[ ] GET /stats implemented
[ ] Database implemented
[ ] Input validation implemented
[ ] Dockerfile and docker-compose.yml working
[ ] Environment configuration working
[ ] Request logging implemented
[ ] API and integration tests implemented
[ ] Full system reproducible with docker compose
```

## Person 2

```text
[ ] Ollama connection implemented
[ ] Classification prompt implemented
[ ] Seven-category validation implemented
[ ] Model can be changed through configuration
[ ] Candidate model tags recorded
[ ] Candidate model digests recorded on the test machine
[ ] CPU-only inference confirmed for every candidate
```

## Person 3

```text
[ ] Team's 1,000 rows extracted
[ ] Reproducible golden-set selection
[ ] Labelling protocol written and approved
[ ] Independent labels preserved
[ ] Agreement calculated and recorded
[ ] Disagreements resolved and recorded
[ ] Final golden set generated and committed
```

## Person 4

```text
[ ] Workload model with sourced figures and labelled estimates
[ ] Ticket-length analysis
[ ] Average, peak and test arrival rates calculated
[ ] Response-time, throughput and accuracy requirements agreed
[ ] Prediction record completed and committed before benchmarking
```

## Person 5

```text
[ ] Test environment recorded
[ ] JMeter test plan created with CSV Data Set Config
[ ] Open-loop traffic configured
[ ] Arrival rates configurable
[ ] Three runs per configuration completed
[ ] p50/p95/p99, throughput and error rate calculated
[ ] Accuracy tests run for every candidate
[ ] Stress test completed
[ ] JMeter results reconciled with service logs
[ ] Test playbook written
[ ] Raw JTL files, service logs and raw accuracy outputs preserved
```

---

# 13. Repository Layout

```text
ICT3113_Assignment_1/
├── app/
│   ├── main.py, config.py, categories.py, candidate_models.py
│   ├── routes/      tickets.py, search.py, stats.py
│   ├── services/    classifier.py, ollama_client.py, request_logger.py
│   ├── database/    db.py, models.py
│   └── schemas/     tickets.py
├── scripts/         extract_team_data.py, create_golden_set.py, agreement.py,
│                    finalize_golden_set.py, record_model_digests.py,
│                    ticket_lengths.py, workload_calc.py,
│                    accuracy_test.py, process_jmeter_results.py, reconcile_logs.py
├── tests/
├── jmeter/
├── data/            ict3113_tickets.csv, team.csv, golden_set_final.csv, labelling/
├── results/         accuracy/, load/, stress/, workload/, model_provenance.json
├── logs/
├── docs/            labelling_protocol.md, models.md, workload_model.md, requirements.md,
│                    prediction_record.md, test_environment.md, test_playbook.md
├── Dockerfile, docker-compose.yml, requirements.txt, .env.example, .gitattributes
└── README.md
```

---

# 14. Integration Contract

| Interface | Provider | Used by |
|---|---|---|
| `classify_ticket(narrative: str) -> str` | Person 2 | Person 1 (`POST /tickets`) |
| `POST /tickets` → `201 {id, category}` | Person 1 | Person 5 (JMeter, accuracy tests) |
| JSON request log + `X-Request-ID` header | Person 1 | Person 5 (reconciliation) |
| `data/golden_set_final.csv` | Person 3 | Person 5 (accuracy tests) |
| Candidate tags and digests (`docs/models.md`) | Person 2 | Person 4 (predictions), Person 5 (test runs) |
| Test arrival rates and requirements | Person 4 | Person 5 (test configuration and pass/fail) |

---

# 15. What NOT To Do

```text
❌ Do not use OpenAI/Claude/Gemini/public model APIs for classification.
❌ Do not use GPU inference.
❌ Do not directly import CSV tickets into the service.
❌ Do not trust source_label as the golden truth.
❌ Do not let only one person label the golden set.
❌ Do not optimise the baseline. No caching, no queues.
❌ Do not run the load generator on the system-under-test machine.
❌ Do not run only one JMeter test per configuration.
❌ Do not use closed-loop JMeter results as latency/throughput evidence.
❌ Do not delete raw JMeter files, service logs or raw accuracy outputs.
❌ Do not benchmark before freezing the golden set and committing the prediction record.
❌ Do not change predictions after seeing results.
❌ Do not fabricate measurements.
```

---

# 16. Final Responsibility Matrix

| Work                  | P1      | P2      | P3       | P4      | P5      |
| --------------------- | ------- | ------- | -------- | ------- | ------- |
| API                   | LEAD    | Support |          |         | Test    |
| Database              | LEAD    |         |          |         |         |
| Docker / Config       | LEAD    | Support |          |         | Support |
| Logging               | LEAD    |         |          |         | Support |
| Integration Tests     | LEAD    | Support |          |         | Support |
| Ollama / Prompt       | Support | LEAD    |          |         | Test    |
| Candidate Models      |         | LEAD    |          | Support | Support |
| Dataset Extraction    |         |         | LEAD     |         |         |
| Golden Set Tools      |         |         | LEAD     |         |         |
| Manual Labelling      | A/B     | A/B     | A/B      | A/B     | A/B     |
| Agreement             |         |         | LEAD     |         |         |
| Workload Model        |         |         |          | LEAD    | Support |
| Requirements          | ✓       | ✓       | ✓        | LEAD    | ✓       |
| Predictions           | ✓       | ✓       | ✓        | LEAD    | ✓       |
| Accuracy Testing      |         | Support | Support  |         | LEAD    |
| JMeter Load Testing   |         |         |          | Support | LEAD    |
| Stress Testing        |         | Support |          | Support | LEAD    |
| Result Processing     |         |         |          |         | LEAD    |
| Log Reconciliation    | Support |         |          |         | LEAD    |
| Final Analysis        | ✓       | ✓       | ✓        | ✓       | ✓       |
| Slides                | ✓       | ✓       | ✓        | ✓       | ✓       |

Manual labelling: at least two members act as Annotator A and Annotator B; record who they
were in `docs/labelling_protocol.md`.

---

# Critical Assignment Rule

**The golden test set and prediction record must be committed to Git before the first benchmark run.**

Keep the commit history, raw JMeter `.jtl` files, and service logs as evidence.

Every performance number eventually placed in the presentation must be traceable back to the retained test evidence.
