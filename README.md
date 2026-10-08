# ICT3113 Assignment 1 — Ticket Triage Service

An unoptimised Python 3.12 baseline for classifying financial complaints with a
local Ollama model on CPU. The seven categories live in `app/categories.py`.

`Client -> POST /tickets -> synchronous Ollama classification -> SQLite -> response`

A fresh database is empty. Successful submissions persist across restarts.
Classification failure returns HTTP 502 and does not store a ticket. The API can
start with no model configured; submissions require a team-selected local model.
There is no CSV import endpoint, cache, queue, batching, or background classification.

## Directory structure

- `app/routes/`: POST /tickets, GET /search, GET /stats
- `app/services/`: classifier interface, blocking Ollama client, JSON request logging
- `app/database/`: SQLAlchemy models, sessions, and database operations
- `app/schemas/`: request and response validation
- `scripts/`: dataset preparation and evaluation tooling
- `tests/`: isolated SQLite and mocked Ollama tests
- `data/`: dataset workspace and runtime SQLite database
- `jmeter/`: open-loop JMeter plan, result-format properties and prepared input data
- `results/{accuracy,load,stress}/`: completed accuracy, load and reconciled stress evidence
- `logs/`: structured request logs
- `docs/`: requirements, completed analysis and preserved team development plan

## Install and run locally

Install Python **3.12** and Ollama first. From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On macOS/Linux use `python3.12 -m venv .venv`, `.venv/bin/python`, and
`cp .env.example .env` instead. Edit `.env`: set `OLLAMA_MODEL` to the exact
team-selected local tag and, for a host-run API, set
`OLLAMA_URL=http://localhost:11434`. No final model has been selected.

Start Ollama if it is not already running, then pull the selected local model
in another terminal (replace the placeholder; do not use a cloud model tag):

```text
ollama serve
ollama pull <TEAM_SELECTED_LOCAL_MODEL_TAG>
```

The client sends `options: {"num_gpu": 0}` on every generation request to request
CPU inference. Before later formal tests, verify CPU execution on the host with
`ollama ps` during inference and record the runtime version. The request format
follows the [official Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md).

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
```

Open `http://localhost:8000/docs`. SQLite tables are created at startup, without
seed data. Database access is isolated under `app/database/`; `DATABASE_URL`
configures the backend (another backend will also need its driver).

## Ollama model backend (candidate models)

Candidates, exact tags and how to record their digests are in `docs/models.md`. The
model is chosen only by environment variable, so switching needs no code change:

```text
OLLAMA_MODEL=llama3.2:3b     # exact tag; one of gemma2:2b, llama3.2:3b, qwen2.5:7b, llama3.1:8b
OLLAMA_URL=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=120
```

Set it in `.env` (or the shell / `docker compose`), pull the tag with `ollama pull`, and
restart the API. Each stored ticket and every request-log line records the model used.
Failures return a generic 502 and store nothing; the request log's `error` field names the
cause (`OllamaUnavailableError`, `OllamaTimeoutError`, `OllamaModelNotFoundError`,
`OllamaResponseError`, `InvalidCategoryError`). Narratives and raw model output are never
logged. Record digests on the test machine with `python scripts/record_model_digests.py`.

## Docker

Start Docker Desktop/Engine and host Ollama. Set `.env` to use
`OLLAMA_URL=http://host.docker.internal:11434` and the selected model tag.
If host Ollama is inaccessible from Docker, configure its listening address
(e.g. `OLLAMA_HOST=0.0.0.0:11434` before starting it) and restrict access to the
local machine/Docker network through the host firewall.

```text
docker compose up --build
```

The container uses Python 3.12, exposes port 8000, and mounts `data/` and `logs/`
for persistence. Ollama runs externally; no GPU configuration is included.
`docker compose down` stops the service and keeps the mounted data.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Or use `docker compose run --rm api python -m pytest -q` after building.
Tests use temporary SQLite databases and mocked classification/HTTP responses;
no real Ollama model is needed. The real integration check is opt-in and uses a
temporary test database and one handwritten complaint (no benchmark metrics):

```powershell
$env:RUN_OLLAMA_INTEGRATION = '1'
$env:OLLAMA_URL = 'http://localhost:11434'
$env:OLLAMA_MODEL = '<pulled-local-tag>'
.\.venv\Scripts\python.exe -m pytest -q tests/test_integration.py
Remove-Item Env:RUN_OLLAMA_INTEGRATION
```

Tests do not populate the service database.

## API examples

After configuring a local model, these PowerShell requests exercise the API:

```powershell
$ticketBody = @{ narrative = 'I dispute a charge on my credit card.' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/tickets -ContentType application/json -Body $ticketBody
Invoke-RestMethod -Uri 'http://localhost:8000/search?q=charge'
Invoke-RestMethod -Uri http://localhost:8000/stats
```

`POST /tickets` returns HTTP 201 with `id` and `category`; empty/whitespace-only
narratives return 400. Missing/null/non-string narratives and malformed JSON also
return 400. Missing, empty, or whitespace-only search queries return 400. `GET /search?q=...` returns matching stored ticket records,
including narrative, model, and creation timestamp. Search is a literal substring
match using the database's collation. `GET /stats` returns counts for all seven
categories, including zeros.

Every request writes a JSON line to `logs/service.log`, with request ID, UTC
timestamps, endpoint, method, model, duration, status, ticket ID, predicted category, and
error where applicable. Responses carry `X-Request-ID` for JMeter correlation.
Full narratives, query strings, and raw model errors are excluded from these
logs. Uvicorn access logging is disabled to avoid logging search queries.
`LOG_LEVEL` controls general application logging; request audit records are
always retained. Service logs and `.jtl` evidence are not ignored by Git.

## Team responsibilities

| Person | Responsibility |
|---|---|
| Person 1 | Backend/API, database, Docker, configuration, logging, integration tests |
| Person 2 | Ollama/Classification, candidate models |
| Person 3 | Golden test set, labelling protocol, agreement |
| Person 4 | Workload model, requirements, prediction record |
| Person 5 | JMeter load/stress tests, accuracy tests, result processing, log reconciliation |

The full division of work is in `docs/team_development_plan.md`.

Person 1 calls `classify_ticket(narrative: str) -> str`; Person 2 maintains that
interface and rejects invalid model output. See `data/README.md` for preparation
commands and `jmeter/README.md` for future performance test requirements.
Team-row extraction, deterministic golden-set selection, separate blank
annotator sheets, agreement calculation, disagreement reporting, and
freeze-protected golden-set finalization are implemented. The accuracy test,
JMeter load/stress tooling, result processing and log reconciliation are
implemented (see "Testing (Person 5)" below). See `data/README.md`
and `docs/labelling_protocol.md` for the human workflow. Labels are never
generated automatically; agreement is calculated only from completed human
annotation sheets.

## Testing (Person 5)

All official tests follow [`docs/test_playbook.md`](docs/test_playbook.md): machines, setup,
JMeter configuration, arrival rates, repetitions, stress-test steps and stopping criteria,
metric definitions and output locations. Every runner refuses official runs until the freeze
gate is met (golden set and prediction record committed, record no longer DRAFT); `--smoke`
checks the tooling only and writes to `results/smoke/`.

| Step | Command (`python -m ...`) | Output |
|---|---|---|
| Prepare JMeter data | `scripts.prepare_jmeter_data data/team.csv` | `jmeter/data/` |
| Record a machine | `scripts.record_test_environment --role service\|loadgen` | `results/environment/` |
| One load run | `scripts.run_load_test --model <tag> --rate 250 --search-rate 450 --host <ip>` | `results/load/<model>/rate-250_search-450/run-N.jtl` |
| Stress test | `scripts.run_stress_test --model <tag> --host <ip>` | `results/stress/<model>/` |
| Accuracy test | `scripts.accuracy_test data/golden_set_final.csv --model <tag> --api-url http://<ip>:8000` | `results/accuracy/<model>/run-N/` |
| Process results | `scripts.process_jmeter_results results/load` | `summary.csv/.json/.md`, `summary_all.csv` |
| Reconcile with log | `scripts.reconcile_logs <config-dir> --service-log <copy of logs/service.log>` | `run-N.reconciliation.json` |

## Completed benchmark and analysis

The repository includes 36 formal load runs, four 180-ticket accuracy runs, and two Qwen stress steps. The prediction record and requirements were frozen before benchmarking.

| Requirement | Gemma | Llama 3.2 | Qwen | Llama 3.1 |
|---|---|---|---|---|
| R1 POST latency | FAIL | PASS | FAIL | FAIL |
| R2 throughput/errors in every run | FAIL | FAIL | FAIL | FAIL |
| R3 overall and category accuracy | FAIL | FAIL | PASS | FAIL |
| R4 mixed-load search latency | PASS | PASS | PASS | PASS |

No candidate is fully compliant on the tested configuration. Qwen is the
quality-focused candidate for future hardware/optimisation evaluation.
The small models' R2 failures reflect below-threshold completions in the
second Poisson arrival window, despite means above 245/h. The consolidated
load indexes contain Gemma only; use each model's configuration summaries.

- [Requirement decisions and per-run evidence](docs/recommendation.md)
- [Requirements evaluation](docs/requirements_evaluation.md)
- [Frozen predictions versus results](docs/prediction_vs_results.md)
- [Bottleneck observations and limitations](docs/bottleneck_analysis.md)
- [Completion audit and evidence gaps](docs/completion_audit.md)
- [Environment](docs/test_environment.md), [slide evidence](docs/slide_data.md)
  and [references](docs/references.md)

The historical selection-source byte hash remains unexplained, with verified
selection/label integrity documented in [provenance review](docs/golden_set_provenance.md).
Runtime CPU/resource captures and fresh PC1 model digests remain unavailable.
The Qwen stress evidence establishes no maximum sustainable throughput.

Read-only validation (no benchmark traffic):

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_golden_set
.\.venv\Scripts\python.exe -m scripts.perf_common
```

