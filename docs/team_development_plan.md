# ICT3113 Assignment 1 – Team Development Plan

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

The seven possible categories are:

```text
Credit reporting
Debt collection
Mortgage
Credit card
Bank account or service
Consumer loan
Money transfer or service
```

---

# 2. Team Split

| Member   | Main Responsibility                 | Coding Responsibility                                   |
| -------- | ----------------------------------- | ------------------------------------------------------- |
| Person 1 | Backend / API Lead                  | `/tickets`, `/search`, `/stats`, database               |
| Person 2 | Ollama / Classification Lead        | Ollama integration, prompts, model switching            |
| Person 3 | Dataset / Accuracy Lead             | Dataset scripts, golden-set tools, accuracy testing     |
| Person 4 | Performance Testing Lead            | JMeter, load testing, stress testing, result processing |
| Person 5 | DevOps / Logging / Integration Lead | Docker, logging, configuration, integration scripts     |

Everyone should understand the complete system even though each person owns a particular area.

---

# 3. Person 1 – Backend / API Lead

## Main Goal

Build the actual Ticket Triage web service.

## Required Coding

Create the application structure, for example:

```text
app/
├── main.py
├── routes/
│   ├── tickets.py
│   ├── search.py
│   └── stats.py
├── services/
├── database/
│   └── db.py
└── models/
```

### Task 1 – Implement `POST /tickets`

Example request:

```json
{
  "narrative": "I found an incorrect account on my credit report..."
}
```

Required flow:

```text
Receive ticket
      ↓
Validate narrative
      ↓
Call Person 2's classifier
      ↓
Receive category
      ↓
Store ticket + category
      ↓
Return category
```

Example response:

```json
{
  "category": "Credit reporting"
}
```

IMPORTANT:

Classification must be **synchronous**.

The endpoint must wait for Ollama to finish classification before returning the response.

Do NOT implement:

```text
Caching
Queues
Async background classification
Pre-computed classifications
```

This assignment requires a straightforward baseline.

### Task 2 – Implement `GET /search`

Example:

```text
GET /search?q=mortgage
```

Search stored ticket narratives.

Example response:

```json
[
  {
    "id": 12,
    "narrative": "...mortgage...",
    "category": "Mortgage"
  }
]
```

### Task 3 – Implement `GET /stats`

Return ticket counts grouped by category.

Example:

```json
{
  "Credit reporting": 25,
  "Debt collection": 19,
  "Mortgage": 11,
  "Credit card": 17,
  "Bank account or service": 15,
  "Consumer loan": 8,
  "Money transfer or service": 5
}
```

### Task 4 – Database

Create storage for submitted tickets.

Minimum fields:

```text
id
narrative
category
model
created_at
```

Remember:

**DO NOT import the CSV directly into the service.**

Tickets must enter through:

```text
POST /tickets
```

### Person 1 Deliverables

```text
app/main.py
app/routes/tickets.py
app/routes/search.py
app/routes/stats.py
app/database/db.py
```

Person 1 must prove:

* POST `/tickets` works
* GET `/search` works
* GET `/stats` works
* tickets are stored correctly
* service starts with an empty database

---

# 4. Person 2 – Ollama / Classification Lead

## Main Goal

Implement all interaction between the application and Ollama.

Person 1 should NOT write model-specific code inside `/tickets`.

Instead:

```text
POST /tickets
      ↓
classifier.py
      ↓
Ollama
      ↓
Category
```

## Task 1 – Ollama Client

Create:

```text
app/services/classifier.py
```

Example interface:

```python
def classify_ticket(narrative):
    ...
    return category
```

The function should send the ticket to Ollama and return exactly one valid category.

## Task 2 – Classification Prompt

Create a prompt instructing the model to choose exactly one of:

```text
Credit reporting
Debt collection
Mortgage
Credit card
Bank account or service
Consumer loan
Money transfer or service
```

The model should NOT return explanations.

Preferred response:

```text
Mortgage
```

Not:

```text
I believe this complaint belongs to the Mortgage category because...
```

## Task 3 – Output Validation

Validate the model output.

For example:

```python
VALID_CATEGORIES = [
    "Credit reporting",
    "Debt collection",
    "Mortgage",
    "Credit card",
    "Bank account or service",
    "Consumer loan",
    "Money transfer or service"
]
```

If Ollama returns something unexpected, record it as an error rather than silently pretending it is valid.

## Task 4 – Candidate Models

Team must eventually test **3–5 Ollama models spanning at least two parameter-size classes**.

Person 2 is responsible for making model selection configurable.

For example:

```text
OLLAMA_MODEL=model-name:tag
```

Do NOT hardcode the model throughout the application.

## Task 5 – Model Identification

For every candidate model record:

```text
Model name
Exact Ollama tag
Digest
Parameter size/class
```

These exact model versions must be preserved for testing.

### Person 2 Deliverables

```text
app/services/classifier.py
app/services/ollama_client.py
config/model_config.py
docs/models.md
```

Person 2 must prove:

```text
Narrative
   ↓
Ollama
   ↓
Exactly one valid category
```

---

# 5. Person 3 – Dataset / Golden Set / Accuracy Lead

## Main Goal

Build scripts for handling the team's assigned dataset and evaluating classification accuracy.

The provided CSV contains:

```text
row
source_label
narrative
```

IMPORTANT:

`source_label` is NOT automatically the correct answer.

The assignment specifically requires the team to create a manually labelled **golden test set of 150–200 tickets**.

## Task 1 – Extract Team Rows

Create:

```text
scripts/extract_team_data.py
```

The script should select the team's required 1,000 rows.

Rule:

```text
Start = team_number × 1000
End   = team_number × 1000 + 999
```

Example:

```text
Team 4

Rows:
4000 → 4999
```

Save as something like:

```text
data/team_tickets.csv
```

## Task 2 – Golden Set Preparation

Create a script to select/export the tickets that will be manually labelled.

Example:

```text
scripts/create_golden_set.py
```

Output:

```text
data/golden_set.csv
```

Suggested columns:

```text
row
narrative
annotator_1
annotator_2
final_label
notes
```

IMPORTANT:

At least TWO members must independently label every golden-set ticket.

Do not automatically copy `source_label` into `final_label`.

## Task 3 – Agreement Calculation

Create:

```text
scripts/agreement.py
```

The script should compare the two independent annotators and calculate the selected inter-annotator agreement statistic.

Also identify disagreements.

Example output:

```text
Total tickets: 180
Agreements: ...
Disagreements: ...
Agreement statistic: ...
```

## Task 4 – Accuracy Testing

Create:

```text
scripts/accuracy_test.py
```

For every candidate model:

```text
Golden ticket
      ↓
POST /tickets
      ↓
Model prediction
      ↓
Compare with final_label
```

Calculate:

```text
Overall accuracy
Per-category accuracy
Confusion matrix
```

Example output directory:

```text
results/accuracy/
├── model_1.csv
├── model_2.csv
├── model_3.csv
└── summary.csv
```

### Person 3 Deliverables

```text
scripts/extract_team_data.py
scripts/create_golden_set.py
scripts/agreement.py
scripts/accuracy_test.py

data/team_tickets.csv
data/golden_set.csv

results/accuracy/
```

---

# 6. Person 4 – Performance / JMeter Lead

## Main Goal

Build and execute all performance tests.

Apache JMeter MUST be used for the required load testing.

## Task 1 – Create JMeter Test Plan

Create:

```text
jmeter/ticket_load_test.jmx
```

JMeter should read ticket narratives from the team's dataset.

Flow:

```text
CSV Data Set Config
        ↓
Select narrative
        ↓
POST /tickets
        ↓
Record response
```

## Task 2 – Open-Loop Traffic

IMPORTANT:

Testing must use **open-loop traffic**.

Use something such as:

```text
Open Model Thread Group

OR

Precise Throughput Timer
```

Do NOT use a normal closed-loop setup as the evidence for the latency/throughput requirements.

## Task 3 – Test Different Arrival Rates

The final rates depend on the team's workload model.

Example structure:

```text
Low load
Medium load
Expected peak load
Above peak load
```

For EACH configuration run:

```text
Run 1
Run 2
Run 3
```

Three runs are required.

## Task 4 – Capture Metrics

For every arrival rate record:

```text
p50 latency
p95 latency
p99 latency
achieved throughput
error rate
```

## Task 5 – Stress Test

Create at least ONE stress test designed to find a meaningful system limit.

Example:

```text
Increase ticket arrival rate
        ↓
Monitor latency
        ↓
Continue increasing
        ↓
Find point where system cannot keep up
```

Possible limits:

```text
Maximum sustainable arrival rate

OR

Concurrency where Ollama/service begins failing
```

## Task 6 – Result Processing

Create:

```text
scripts/process_jmeter_results.py
```

Input:

```text
.jtl files
```

Output:

```text
p50
p95
p99
throughput
error rate
```

### Person 4 Deliverables

```text
jmeter/ticket_load_test.jmx
jmeter/stress_test.jmx

scripts/process_jmeter_results.py

results/load/
results/stress/
```

NEVER delete the raw `.jtl` files.

---

# 7. Person 5 – DevOps / Logging / Integration Lead

## Main Goal

Make sure everybody's work runs together and every reported result can be traced back to evidence.

## Task 1 – Docker

Create:

```text
Dockerfile
docker-compose.yml
```

The environment should include at minimum:

```text
Ticket Triage Service
Database/storage
Ollama connection/configuration
```

The application should be reproducible using something similar to:

```bash
docker compose up --build
```

## Task 2 – Configuration

Create environment configuration.

Example:

```text
.env.example
```

Possible settings:

```text
OLLAMA_URL=
OLLAMA_MODEL=
DATABASE_URL=
LOG_LEVEL=
```

Do NOT commit passwords or secrets.

## Task 3 – Request Logging

Every request handled by the service must be logged.

Create:

```text
app/services/logger.py
```

Logs should contain enough information to reconcile JMeter results with service activity.

Suggested fields:

```text
request_id
timestamp
endpoint
model
ticket_row
start_time
end_time
duration_ms
status_code
predicted_category
error
```

Example:

```json
{
  "request_id": "abc123",
  "endpoint": "/tickets",
  "model": "model-name:tag",
  "duration_ms": 2814,
  "status_code": 200,
  "predicted_category": "Mortgage"
}
```

## Task 4 – Integration Test

Create:

```text
tests/test_api.py
tests/test_integration.py
```

Verify:

```text
Application starts
POST /tickets works
Ollama can be reached
Ticket gets stored
/search finds ticket
/stats updates
Logs are generated
```

## Task 5 – Repository Organisation

Person 5 owns the final repository structure.

Target:

```text
ICT3113-Assignment-1/
│
├── app/
│   ├── main.py
│   │
│   ├── routes/
│   │   ├── tickets.py
│   │   ├── search.py
│   │   └── stats.py
│   │
│   ├── services/
│   │   ├── classifier.py
│   │   ├── ollama_client.py
│   │   └── logger.py
│   │
│   └── database/
│       └── db.py
│
├── scripts/
│   ├── extract_team_data.py
│   ├── create_golden_set.py
│   ├── agreement.py
│   ├── accuracy_test.py
│   └── process_jmeter_results.py
│
├── tests/
│   ├── test_api.py
│   └── test_integration.py
│
├── jmeter/
│   ├── ticket_load_test.jmx
│   └── stress_test.jmx
│
├── data/
│   ├── team_tickets.csv
│   └── golden_set.csv
│
├── results/
│   ├── accuracy/
│   ├── load/
│   └── stress/
│
├── logs/
│
├── docs/
│   ├── labelling_protocol.md
│   ├── prediction_record.md
│   ├── workload_model.md
│   └── models.md
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# 8. Shared Team Tasks

Some assignment requirements CANNOT belong to only one person.

## Golden Set Labelling

At least TWO people must independently label every golden-set ticket.

Recommended:

```text
Person 1 → Annotator A
Person 3 → Annotator B
```

They must label independently first.

Afterwards, disagreements are discussed by the team.

Keep:

```text
annotator_1.csv
annotator_2.csv
disagreement_resolutions.csv
labelling_protocol.md
```

---

# 9. Workload Model

Recommended owners:

```text
Person 4 + Person 5
```

Research and estimate:

```text
Ticket volume
Tickets/hour
Search frequency
Peak period
Non-peak period
Ticket length distribution
```

Every external number needs a source.

If no source exists:

```text
State that it is an estimate
+
Explain how the estimate was obtained
```

Output:

```text
docs/workload_model.md
```

---

# 10. Performance Requirements

The whole team should agree on the requirements BEFORE benchmarking.

Requirements must include:

### Response Time

Example FORMAT ONLY:

```text
At the expected peak arrival rate,
95% of POST /tickets requests must complete
within X seconds.
```

### Throughput

Example FORMAT ONLY:

```text
The service must sustain at least
X classifications per hour.
```

### Accuracy

Example FORMAT ONLY:

```text
Overall classification accuracy >= X%

AND

Each category accuracy >= Y%
```

Do NOT blindly use these example numbers.

The team's actual numbers must come from the workload model and justification.

---

# 11. Prediction Record – MUST BE DONE BEFORE BENCHMARKING

Create:

```text
docs/prediction_record.md
```

Record BEFORE running benchmarks:

### Predicted Bottleneck

Example:

```text
We predict Ollama CPU inference will be the primary
bottleneck because...
```

### Model Predictions

For every candidate:

```text
Expected accuracy
Expected single-request latency
```

### Difficult Categories

Predict which categories will be hardest to classify and explain why.

IMPORTANT:

The prediction record must be committed BEFORE the first benchmark.

Do NOT edit the predictions after seeing the benchmark results.

---

# 12. Git Workflow

Everyone should work on their own branch.

Example:

```text
main

├── feature/backend-api
├── feature/ollama
├── feature/dataset-accuracy
├── feature/jmeter
└── feature/devops-logging
```

Person assignments:

```text
Person 1:
feature/backend-api

Person 2:
feature/ollama

Person 3:
feature/dataset-accuracy

Person 4:
feature/jmeter

Person 5:
feature/devops-logging
```

Do NOT have all five people directly editing `main`.

Typical workflow:

```bash
git checkout -b feature/backend-api

git add .
git commit -m "Implement POST tickets endpoint"

git push origin feature/backend-api
```

Then merge through Pull Request.

---

# 13. IMPORTANT Git Checkpoint

Before the FIRST benchmark, the repository MUST already contain:

```text
Golden test set
Prediction record
Labelling protocol
Independent labels
Agreement calculation/results
```

Create a clearly identifiable commit.

Example:

```text
Freeze golden set and prediction record before benchmarking
```

Only after that commit should performance/accuracy benchmark runs begin.

---

# 14. Testing Order

Follow this order:

```text
1. Extract team's 1,000 rows

2. Write labelling protocol

3. Create + independently label golden set

4. Build baseline API

5. Connect Ollama

6. Verify /tickets, /search and /stats

7. Select and pin candidate models

8. Complete workload model

9. Define requirements

10. Write prediction record

11. COMMIT GOLDEN SET + PREDICTIONS

==============================
DO NOT BENCHMARK BEFORE THIS
==============================

12. Run accuracy tests

13. Run JMeter load tests

14. Run each configuration THREE times

15. Run stress test

16. Process results

17. Compare results against requirements

18. Diagnose bottleneck

19. Make final model recommendation

20. Prepare slides
```

---

# 15. Definition of Done for Each Member

## Person 1

```text
[ ] POST /tickets implemented
[ ] GET /search implemented
[ ] GET /stats implemented
[ ] Database implemented
[ ] Input validation implemented
[ ] API tested
```

## Person 2

```text
[ ] Ollama connection implemented
[ ] Classification prompt implemented
[ ] Seven-category validation implemented
[ ] Model can be changed through configuration
[ ] Candidate model tags recorded
[ ] Candidate model digests recorded
```

## Person 3

```text
[ ] Team's 1,000 rows extracted
[ ] Golden-set preparation completed
[ ] Independent labels preserved
[ ] Agreement calculated
[ ] Accuracy test automated
[ ] Per-category accuracy generated
[ ] Confusion matrix generated
```

## Person 4

```text
[ ] JMeter test plan created
[ ] CSV Data Set Config working
[ ] Open-loop traffic configured
[ ] Multiple arrival rates configured
[ ] Three runs per configuration completed
[ ] p50/p95/p99 calculated
[ ] Throughput calculated
[ ] Error rate calculated
[ ] Stress test completed
[ ] Raw JTL files preserved
```

## Person 5

```text
[ ] Dockerfile working
[ ] docker-compose.yml working
[ ] Environment configuration working
[ ] Request logging implemented
[ ] Integration tests implemented
[ ] Logs preserved
[ ] Repository organised
[ ] Full system reproducible
```

---

# 16. Integration Contract

To prevent people from writing incompatible code, agree on these interfaces BEFORE coding.

## Classifier

Person 2 provides:

```python
classify_ticket(narrative: str) -> str
```

Person 1 calls it.

---

## POST `/tickets`

Person 1 provides:

```text
POST /tickets
```

Person 3 uses it for accuracy testing.

Person 4 uses it for JMeter testing.

---

## Logs

Person 5 provides a consistent logging format.

Person 4 uses the logs to verify performance measurements.

---

# 17. What NOT To Do

```text
❌ Do not use OpenAI/Claude/Gemini/public model APIs for classification.

❌ Do not use GPU inference.

❌ Do not directly import all CSV tickets into the service.

❌ Do not trust source_label as the golden truth.

❌ Do not let only one person label the golden set.

❌ Do not optimise the baseline.

❌ Do not add caching.

❌ Do not add queues.

❌ Do not run only one JMeter test.

❌ Do not use closed-loop JMeter results as the required
   latency/throughput evidence.

❌ Do not delete raw JMeter files.

❌ Do not delete service logs.

❌ Do not benchmark before freezing the golden set.

❌ Do not benchmark before committing the prediction record.

❌ Do not change predictions after seeing results.

❌ Do not fabricate measurements.
```

---

# 18. Final Responsibility Matrix

| Work               | P1      | P2      | P3       | P4      | P5      |
| ------------------ | ------- | ------- | -------- | ------- | ------- |
| API                | LEAD    | Support | Test     | Test    | Test    |
| Database           | LEAD    |         |          |         | Support |
| Ollama             | Support | LEAD    | Test     | Test    | Support |
| Prompt             |         | LEAD    | Evaluate |         |         |
| Dataset Extraction |         |         | LEAD     |         |         |
| Golden Set Tools   |         |         | LEAD     |         |         |
| Manual Labelling   | ✓       |         | ✓        |         |         |
| Agreement          |         |         | LEAD     |         |         |
| Accuracy Testing   |         | Support | LEAD     |         |         |
| JMeter             |         |         |          | LEAD    | Support |
| Stress Testing     |         | Support |          | LEAD    | Support |
| Docker             | Support | Support |          |         | LEAD    |
| Logging            | Support |         |          | Support | LEAD    |
| Integration Tests  | Support | Support | Support  | Support | LEAD    |
| Workload Model     |         |         |          | LEAD    | LEAD    |
| Requirements       | ✓       | ✓       | ✓        | ✓       | ✓       |
| Predictions        | ✓       | ✓       | ✓        | ✓       | ✓       |
| Final Analysis     | ✓       | ✓       | ✓        | ✓       | ✓       |
| Slides             | ✓       | ✓       | ✓        | ✓       | ✓       |

---

# 19. Immediate Next Tasks

Before anyone starts independently coding, complete these first:

```text
1. Confirm team number.

2. Person 3 extracts the correct 1,000 CSV rows.

3. Team agrees on repository structure.

4. Person 5 creates the GitHub repository.

5. Create five development branches.

6. Person 1 creates API skeleton.

7. Person 2 installs/tests Ollama and starts classifier module.

8. Person 3 prepares golden-set labelling files.

9. Person 4 installs JMeter and creates initial test plan.

10. Person 5 creates Docker + logging skeleton.

11. Agree on the API/classifier/logging interfaces.

12. Begin implementation in parallel.
```

# Critical Assignment Rule

**The golden test set and prediction record must be committed to Git before the first benchmark run.**

Keep the commit history, raw JMeter `.jtl` files, and service logs as evidence.

Every performance number eventually placed in the presentation must be traceable back to the retained test evidence.
