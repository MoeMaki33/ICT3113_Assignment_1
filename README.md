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
- `scripts/`: dataset preparation and future evaluation entry points
- `tests/`: isolated SQLite and mocked Ollama tests
- `data/`: dataset workspace and runtime SQLite database
- `jmeter/`: future open-loop testing instructions
- `results/{accuracy,load,stress}/`: empty evidence directories
- `logs/`: structured request logs
- `docs/`: assignment placeholders and preserved original team development plan

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
no real Ollama model is needed. The real integration test is explicitly skipped
until the team defines it. Tests do not populate the service database.

## API examples

After configuring a local model, these PowerShell requests exercise the API:

```powershell
$ticketBody = @{ narrative = 'I dispute a charge on my credit card.' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/tickets -ContentType application/json -Body $ticketBody
Invoke-RestMethod -Uri 'http://localhost:8000/search?q=charge'
Invoke-RestMethod -Uri http://localhost:8000/stats
```

`POST /tickets` returns HTTP 201 with `id` and `category`; empty/whitespace-only
narratives return 422. `GET /search?q=...` returns matching stored ticket records,
including narrative, model, and creation timestamp. Search is a literal substring
match using the database's collation. `GET /stats` returns counts for all seven
categories, including zeros.

Every request writes a JSON line to `logs/service.log`, with request ID, UTC
timestamps, endpoint, method, model, duration, status, predicted category, and
error where applicable. Responses carry `X-Request-ID` for JMeter correlation.
Full narratives, query strings, and raw model errors are excluded from these
logs. Uvicorn access logging is disabled to avoid logging search queries.
`LOG_LEVEL` controls general application logging; request audit records are
always retained. Service logs and `.jtl` evidence are not ignored by Git.

## Team responsibilities

| Person | Responsibility |
|---|---|
| Person 1 | Backend/API |
| Person 2 | Ollama/Classification |
| Person 3 | Dataset/Accuracy |
| Person 4 | JMeter/Performance |
| Person 5 | DevOps/Logging/Integration |

Person 1 calls `classify_ticket(narrative: str) -> str`; Person 2 maintains that
interface and rejects invalid model output. See `data/README.md` for preparation
commands and `jmeter/README.md` for future performance test requirements.
Extraction and blank annotation preparation are usable helpers; agreement,
accuracy evaluation, and JMeter processing are deliberately unimplemented CLI
scaffolds. They exit with a TODO message and produce no results.

## Before formal evaluation

**DO NOT RUN FORMAL BENCHMARKS UNTIL:**
- golden test set is frozen
- labelling work is complete
- prediction record is complete
- golden set and prediction record have been committed to Git

TODO: Confirm the actual team number, course CSV narrative column, and row-index
convention; complete independent labelling/adjudication and agreement rules;
select local model tags and digests; complete prediction/workload documents;
implement evaluation/result-processing scripts and the real integration test;
define arrival rates, repetitions, and stress stopping criteria. Resolve and
record exact dependency/runtime versions before formal runs.

The original README is preserved at `docs/team_development_plan.md` as planning
material. No benchmarks, accuracy measurements, or candidate-model results have
been generated by this scaffold.
