# ICT3113 Assignment 1 — Financial Complaint Ticket Triage Service

**Module:** ICT3113 Performance Optimisation and Design  
**Team:** P2-7  
**Project:** CPU-based financial complaint classification and performance evaluation

## Project overview

This project investigates whether a financial services company can automatically route customer complaint tickets using a locally hosted language model. The client requires customer data to remain within its own infrastructure and has CPU-only servers, so the service uses Ollama locally rather than a public model API.

We developed a Python 3.12 web API with SQLite storage and Docker support. Each new ticket is classified synchronously: the request waits for the model's response before the ticket is stored and the assigned category returned. The Assignment 1 baseline deliberately does not use caching, queues, batching or background classification.

```text
Client / JMeter
      |
      v
Python API (POST /tickets)
      |
      v
Local Ollama model (CPU)
      |
      v
SQLite storage -> HTTP response

GET /search -> Search stored tickets
GET /stats  -> Counts by category
```

The seven supported categories are **Credit reporting, Debt collection, Mortgage, Credit card, Bank account or service, Consumer loan,** and **Money transfer or service**. Tickets enter the service only through `POST /tickets`; the assignment dataset is not directly imported into the database.

## Team members and contributions

| Member | Role | Main contributions |
|---|---|---|
| **Owen (Person 1)** | Backend and platform | Implemented the API endpoints, SQLite integration, Docker configuration, request logging, backend/integration tests and project structure. |
| **Alyssa (Person 2)** | Model and classification | Developed the Ollama client, classification prompt and output validation; configured model switching and documented candidate models and digests. |
| **Shaqeel (Person 3)** | Golden test set | Prepared the team dataset, labelling protocol, independent annotation sheets, agreement calculations, disagreement records and final golden set. |
| **Shamik (Person 4)** | Workload and requirements | Developed the workload estimates, performance and accuracy requirements, and pre-test prediction record. |
| **Daffa (Person 5)** | Performance testing | Prepared and executed the JMeter load/stress and accuracy testing workflows, processed results, reconciled logs and documented test procedures. |

The division of work is described further in [the team development plan](docs/team_development_plan.md).

## Project files

| Location | Purpose |
|---|---|
| `app/` | API routes, classification services, schemas and database |
| `tests/` | Automated API, classifier and integration tests |
| `scripts/` | Dataset preparation, accuracy evaluation, benchmarking and analysis |
| `data/` | Team dataset, labelling files, golden test set and local database |
| `jmeter/` | Open-loop JMeter test plan and inputs |
| `results/` | Accuracy, load, stress and supporting measurement evidence |
| `logs/` | Structured API request logs |
| `docs/` | Models, workload, requirements, predictions, playbook and recommendations |

## Setup instructions (Windows)

### 1. Prerequisites

Install **Python 3.12**, **Docker Desktop** and **Ollama**. Git is useful for cloning the repository. For formal performance testing, install **Apache JMeter 5.6.3** and Java on a **separate load-generator machine**; running JMeter on the service machine would interfere with CPU measurements.

Clone this repository and open PowerShell in its root directory:

```powershell
git clone https://github.com/MoeMaki33/ICT3113_Assignment_1.git
cd ICT3113_Assignment_1
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### 2. Install and start a local model

The candidate models evaluated in the project are `gemma2:2b`, `llama3.2:3b`, `qwen2.5:7b` and `llama3.1:8b`. For a simple demonstration, use one installed candidate, for example:

```powershell
ollama pull llama3.2:3b
ollama list
```

Make sure Ollama is running. On systems where it is not already running as a service, start it with `ollama serve`. The application requests CPU inference with `num_gpu: 0`; verify actual CPU execution with `ollama ps` during a request.

### 3. Configure the application

Open `.env` and set these values for a **local Python run**:

```dotenv
OLLAMA_MODEL=llama3.2:3b
OLLAMA_URL=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=120
```

For a **Docker run** with Ollama running on the host, change `OLLAMA_URL` to `http://host.docker.internal:11434`. Keep other settings from `.env.example` unless your environment requires changes.

### 4. Run the service

**Option A — Docker (recommended for reproducing the deployment):**

```powershell
docker compose up --build
```

**Option B — Python directly:**

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
```

Once started, open **http://localhost:8000/docs** for the interactive API documentation. A new database starts empty. Successful ticket submissions are stored and remain available after a restart.

Stop Docker with `docker compose down` (this does not delete the mounted data).

## Trying the API

Open a second PowerShell terminal while the service is running:

```powershell
$body = @{ narrative = 'I dispute a charge on my credit card.' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/tickets -ContentType application/json -Body $body
Invoke-RestMethod -Uri 'http://localhost:8000/search?q=charge'
Invoke-RestMethod -Uri http://localhost:8000/stats
```

| Endpoint | Purpose | Expected behaviour |
|---|---|---|
| `POST /tickets` | Classify and save a complaint | HTTP 201 with ticket ID and category |
| `GET /search?q=charge` | Find stored tickets containing a term | Matching stored ticket records |
| `GET /stats` | Summarise saved classifications | Counts for all seven categories, including zeros |

Invalid narratives or empty search terms return HTTP 400. Classification backend failures return HTTP 502 and do not save the ticket. Each request is recorded in `logs/service.log` with a request ID and timing information; full complaint narratives are excluded from logs.

## Running tests and reviewing evidence

Run automated tests without requiring a real Ollama model:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

To validate the golden test set and benchmark prerequisites without generating new test traffic:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_golden_set
.\.venv\Scripts\python.exe -m scripts.perf_common
```

For the full performance-testing procedure, machine configuration, open-loop arrival rates, repeat runs and commands, see [Test Playbook](docs/test_playbook.md). The load generator must run on a separate machine from the API and Ollama.

## Results and findings

We completed **36 formal JMeter load runs** (four models, three workloads and three repetitions), **four accuracy evaluations of 180 golden-set tickets each**, and **two Qwen stress-test steps**. The golden test set and prediction record were frozen before benchmarking.

### Measured model performance

The latency, throughput, error-rate and search figures below are from the **mixed-load configuration of 250 ticket arrivals/hour and 450 searches/hour**, with three runs per model. The measured window was 10 minutes after a two-minute warm-up. POST p95/p99 and search p95 are **means of the three individual-run percentiles**, not pooled percentiles. Achieved throughput and error rates are shown **per run** to make variations visible.

| Model | Accuracy (180 tickets) | Mean POST p95 / p99 | Successful classifications/hour (runs 1 / 2 / 3) | POST error rate (runs 1 / 2 / 3) | Mean search p95 |
|---|---:|---:|---:|---:|---:|
| Gemma 2B (`gemma2:2b`) | 67.2% (121/180) | 18.351 / 23.542 s | 258 / 234 / 270 | 0% / 0% / 0% | 0.055 s |
| Llama 3.2 3B (`llama3.2:3b`) | 60.6% (109/180) | 12.800 / 16.838 s | 258 / 240 / 270 | 0% / 0% / 0% | 0.111 s |
| Qwen 2.5 7B (`qwen2.5:7b`) | 80.6% (145/180) | 77.689 / 85.489 s | 228 / 240 / 240 | 0% / 0% / 2.174% | 0.076 s |
| Llama 3.1 8B (`llama3.1:8b`) | 84.4% (152/180) | 97.311 / 103.680 s | 210 / 234 / 240 | 6.667% / 0% / 0% | 0.063 s |

The accuracy percentages are based on the golden test set, **not** on the JMeter load-test tickets. The POST latency percentiles exclude failed requests, so they must be considered alongside the error rates.

### Evaluation against requirements

The team's frozen acceptance criteria are:

- **R1 — Response time:** mean POST p95 ≤ 15 seconds and mean POST p99 ≤ 30 seconds.
- **R2 — Throughput and reliability:** at least 245 successful classifications/hour and an error rate below 1% **in every run**.
- **R3 — Accuracy:** at least 80% correct overall and at least 70% recall for **each of the seven categories**.
- **R4 — Search performance:** mean GET /search p95 ≤ 1 second under mixed load.

R1, R2 and R4 are evaluated at the mixed-load configuration described above.

| Requirement | Gemma 2B | Llama 3.2 3B | Qwen 2.5 7B | Llama 3.1 8B |
|---|---|---|---|---|
| R1: POST latency | Fail | **Pass** | Fail | Fail |
| R2: Throughput and error rate in every run | Fail | Fail | Fail | Fail |
| R3: Overall and per-category accuracy | Fail | Fail | **Pass** | Fail |
| R4: Mixed-load search latency | **Pass** | **Pass** | **Pass** | **Pass** |

### Key findings and recommendation

- **Llama 3.2 3B** met the POST latency requirement and had the lowest measured mean POST p95, but its 60.6% classification accuracy did not meet R3.
- **Llama 3.1 8B** had the highest overall accuracy (84.4%), but it correctly classified only 9 of 17 Debt collection tickets (52.9% recall), below the 70% per-category minimum.
- **Qwen 2.5 7B** was the only model to meet both parts of R3: 145/180 correct overall (80.6%), with at least 70% recall in every category. However, it failed the latency and throughput requirements.
- **Gemma 2B** did not meet the latency or accuracy requirements. All four models met the mixed-load search latency requirement.

**Recommendation:** None of the four models is demonstrated to meet all requirements on the tested CPU-only configuration. Qwen 2.5 7B is the preferred candidate for **further optimisation or hardware evaluation** because it meets the classification accuracy criteria; it is **not** recommended as an already-compliant production deployment.

The second load-test run offered only 234 ticket arrivals/hour due to the Poisson arrival schedule. This contributed to R2 failures under the frozen absolute threshold, even for models with no errors; it does not by itself demonstrate insufficient processing capacity. The two Qwen stress steps showed degradation but did **not** establish a verified maximum sustainable throughput.

### Supporting evidence and limitations

Detailed results, methodology and traceable evidence are available in:

- [Measured results and recommendation](docs/recommendation.md)
- [Requirements evaluation](docs/requirements_evaluation.md)
- [Accuracy evidence](results/accuracy/accuracy_summary.md)
- [Per-model JMeter results](results/load/)
- [Stress-test results](results/stress/)
- [Predictions compared with results](docs/prediction_vs_results.md)
- [Bottleneck analysis](docs/bottleneck_analysis.md)
- [Test environment](docs/test_environment.md)
- [Completion audit and evidence limitations](docs/completion_audit.md)

All 36 formal load runs were reconciled against saved service-log extracts. The consolidated load index files cover Gemma only, so four-model comparisons should use the individual model result directories. Remaining limitations include unavailable runtime CPU/resource captures, unverified fresh model digests on the test machine, limited accuracy sample sizes, and a documented historical dataset source-hash discrepancy. These limitations restrict the conclusions that can be drawn from the measurements.

## Troubleshooting

| Problem | What to check or do |
|---|---|
| `py -3.12` is not recognised | Install Python 3.12 and ensure the Python launcher is available; check with `py --list`. |
| Dependencies fail to install | Check that the virtual environment uses Python 3.12, then rerun `python -m pip install -r requirements.txt` using the virtual environment interpreter. |
| Docker cannot connect to the daemon | Start Docker Desktop and wait until its engine is running; check `docker info`. |
| Port 8000 is already in use | Stop the existing process/container on port 8000 or adjust the port mapping and request URLs. |
| HTTP 502 when submitting a ticket | Check that Ollama is running, the selected model is installed, and `OLLAMA_URL` is reachable from the API. Review `logs/service.log` for the error type. |
| Model not found | Run `ollama list`, pull the exact model tag, and make `OLLAMA_MODEL` match it. Restart the API. |
| Ollama works on the host but not in Docker | Use `http://host.docker.internal:11434` for `OLLAMA_URL`. If needed, configure Ollama's listening address and restrict network access with the host firewall. |
| Classification times out | Confirm the model is loaded and the CPU has sufficient memory. Check `OLLAMA_TIMEOUT_SECONDS`; do not change benchmark settings when reproducing recorded results. |
| `/search` or `/stats` returns no tickets | A fresh database is intentionally empty. Submit a successful `POST /tickets` first. |
| Golden-set validator reports a source hash mismatch | Review [golden-set provenance](docs/golden_set_provenance.md). The historical discrepancy is documented; do not regenerate labels or silently overwrite evidence. |
| JMeter measurements differ from the report | Verify the exact model, test machine, arrival-rate configuration and raw `.jtl` files. Compare request IDs with the service logs and follow the test playbook. |

## Data handling and references

The project uses the course-provided extract of the [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/). Group 7 uses rows **7000–7999** for its assigned dataset. A manually adjudicated golden set of 180 complaints supports accuracy evaluation; raw consumer-selected labels are not treated as ground truth.

Model details, licence references and other sources are documented in [docs/models.md](docs/models.md) and [docs/references.md](docs/references.md).
