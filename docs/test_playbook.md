# Test playbook

Owner: Person 5 (Testing Lead). This playbook is meant to let another competent tester repeat
every official test (load, accuracy, stress) without asking the team anything. Commands are
for PowerShell on Windows, the team's machines. On macOS/Linux, replace `.\.venv\Scripts\python.exe`
with `.venv/bin/python` and use `/` in paths.

## 0. Rules that apply to every test

1. **Freeze gate.** No official accuracy, load or stress run before the golden set
   (`data/golden_set_final.csv`) and the prediction record (`docs/prediction_record.md`) are
   committed, unmodified, and the record is no longer marked DRAFT/PROPOSED. Every script enforces
   this (`scripts/perf_common.py:freeze_gate_problems`) and refuses official runs otherwise.
   The gate also rejects incomplete/invalid golden CSVs, staged-but-uncommitted
   files, missing per-model numeric predictions and unfinished prediction sign-off.
   Run `python -m scripts.validate_golden_set` separately and resolve every
   provenance problem; passing the freeze gate alone does not prove machine readiness.
   `--smoke` exists only to check the tooling. Smoke output goes to `results/smoke/`, is labelled
   *NOT OFFICIAL EVIDENCE*, and must never be reported.
2. **Baseline protection.** Test the service exactly as committed. Do not add caching, queues,
   batching, concurrency or prompt changes, do not tune Ollama between runs, and do not change
   `OLLAMA_TIMEOUT_SECONDS`. If a bottleneck is found, **document it** (section 7.6). Fixing it is Assignment 2.
3. **Raw evidence is never deleted or edited.** This covers `.jtl` files, their `.json` metadata
   and `.jmeter.log` files, copies of `logs/service.log`, and accuracy `predictions.csv`/`metadata.json`.
   The scripts refuse to overwrite them. A failed or contaminated run is kept and marked, then
   repeated with the next run number.
4. **No invented numbers.** Every reported figure must come from a processed raw file under `results/`.
   A missing run is reported as missing.
5. **The load generator is a separate machine** from the service + Ollama machine.
6. **Open-loop traffic only.** The JMeter plan uses Open Model Thread Groups with random (Poisson)
   arrivals. Never use a classic (closed-loop) Thread Group for evidence.

## 1. Machines

| Role | Machine | Runs |
|---|---|---|
| Service machine | AMD Ryzen 7 8845HS laptop, Windows 11 (as assumed in `docs/prediction_record.md`) | Docker Desktop (API container) and Ollama on the host, CPU only |
| Load generator | A **different** laptop on the same network | JMeter 5.6.3, Java 17+, Python 3.12, this repository |
| Network | Same LAN; wired Ethernet preferred (Wi-Fi only if recorded) | Service port 8000 reachable from the load generator |

Record both machines and the network in `docs/test_environment.md` (section 2.4) **before** the
first official run. If the service machine differs from the one in the prediction record, the
predictions must be updated *before* the freeze commit, not afterwards.

## 2. One-time setup

### 2.1 Service machine

```powershell
git clone https://github.com/MoeMaki33/ICT3113_Assignment_1.git
cd ICT3113_Assignment_1
git checkout <freeze-commit-or-later-main>
Copy-Item .env.example .env        # then edit .env (below)
```

`.env` for Docker:

```text
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=<exact tag of the model under test>
OLLAMA_TIMEOUT_SECONDS=120
DATABASE_URL=sqlite:///./data/tickets.db
LOG_LEVEL=INFO
```

Ollama (host). Set these **before** starting it and record them:

```powershell
$env:OLLAMA_NUM_PARALLEL = "1"         # one inference at a time (assumed in the prediction record)
$env:OLLAMA_HOST = "0.0.0.0:11434"     # only if the container cannot reach host Ollama; firewall it to the local machine
ollama serve
# second terminal
ollama pull gemma2:2b; ollama pull llama3.2:3b; ollama pull qwen2.5:7b; ollama pull llama3.1:8b
.\.venv\Scripts\python.exe scripts\record_model_digests.py --json results\environment\model-provenance-before-tests.json
```

Check that the digests match `docs/models.md`. Keep `OLLAMA_KEEP_ALIVE` at its default and record it.
The 2-minute warm-up that is excluded from every measured window covers loading the model.

Allow inbound TCP 8000 from the load generator's IP only (Windows Defender Firewall → Inbound
rule → Port 8000 → scope: remote IP = load generator).

Python venv (used for the environment record):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.record_test_environment --role service
```

### 2.2 Load generator

1. Install Java 17 or newer (`java -version`).
2. Download Apache JMeter **5.6.3** from https://jmeter.apache.org/download_jmeter.cgi, verify the
   SHA-512 against the published `.sha512`, and unzip it, e.g. to `C:\tools\apache-jmeter-5.6.3`.
3. Tell the scripts where JMeter is: `$env:JMETER_BIN = "C:\tools\apache-jmeter-5.6.3\bin\jmeter.bat"`.
4. Clone the repository at the same commit as the service machine, then:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.prepare_jmeter_data data\team.csv    # regenerates jmeter\data\
git status jmeter\data     # must show NO changes: the committed inputs are byte-identical
.\.venv\Scripts\python.exe -m scripts.record_test_environment --role loadgen
.\.venv\Scripts\python.exe -m pytest -q                                     # tooling self-test
```

5. Check that the load generator reaches the service: `curl.exe http://<service-ip>:8000/stats`.
6. Check that the clocks of both machines are synchronised: Settings → Time → *Sync now* on both.
   Reconciliation reports the remaining offset.

### 2.3 Tooling smoke check (allowed before the freeze; not evidence)

With the service running any model, check the toolchain end to end once:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_load_test --smoke --model <tag> --rate 250 --duration-s 120 --warmup-s 30 --host <service-ip>
.\.venv\Scripts\python.exe -m scripts.process_jmeter_results results\smoke\load
```

Smoke traffic goes into the service log too. Note the time window in your test notes so it is
never confused with official runs. Reconciliation of later official runs only looks at each
run's own window.

## 3. JMeter configuration (reference)

Plan: `jmeter/ticket_load_test.jmx`. Result format: `jmeter/results.properties`. Data:
`jmeter/data/` (made by `scripts/prepare_jmeter_data.py`; SHA-256 values in `jmeter/data/manifest.json`).

| Element | Setting |
|---|---|
| Thread groups | 2 × **Open Model Thread Group**: `Tickets` and `Searches` (no closed-loop groups) |
| Tickets schedule | `rate(${rate}/hour) random_arrivals(${duration_s} s) pause(${drain_s} s)`: Poisson arrivals at the given rate, then a no-arrival drain so in-flight requests complete |
| Searches schedule | `rate(<search_rate>/hour)random_arrivals(<duration_s>s)pause(<drain_s>s)` (built by the wrapper, passed as `-Jsearch_schedule`), or `pause(1s)` when searches are off |
| Ticket data | CSV Data Set Config on `team_narratives.tsv`: 1,000 team rows (7000–7999), tab-delimited, narrative **pre-encoded as a JSON string**, shared by all threads, recycled in row order |
| Ticket request | `POST /tickets`, `Content-Type: application/json`, body `{"narrative": ${narrative_json}}` |
| Search request | `GET /search?q=${search_term}` (URL-encoded), 20 fixed terms from `search_terms.txt` |
| Assertions | `/tickets` must return **201**, `/search` must return **200**; anything else is an error |
| Request id | Regular Expression Extractor on response headers → `${request_id}` → `.jtl` column via `sample_variables` |
| Timeouts | connect 10 s; response 180 s (> the service's 120 s Ollama timeout, so service 502s are observed rather than client timeouts) |
| Drain | `drain_s = timeout + 10 s = 190 s` |
| Seed | ticket arrivals `311300 + run number`, searches `+50`; recorded in metadata |
| `.jtl` | CSV; `timeStamp` = request **start** (epoch ms), `elapsed` = to last byte; plus `request_id`, `ticket_row` |

Properties are passed with `-J` by `scripts/run_load_test.py`, so new rates need no plan edits.
The raw command, if the wrapper cannot be used, is printed in each run's `.json` (`jmeter_command`).

Known JMeter behaviour: after the drain, the JMeter process takes about 60 s to exit while its
arrival-starter threads shut down. This happens after the test has ended and does not affect results.

## 4. Load test

### 4.1 Arrival rates, duration, repetitions

From `docs/workload_model.md` (design peak 250 tickets/h, peak search rate 450/h):

| Configuration | Tickets/h | Searches/h | Purpose | Runs |
|---|---|---|---|---|
| `rate-125` | 125 | 0 | 0.5× design peak (non-peak behaviour) | 3 |
| `rate-250_search-450` | 250 | 450 | **Design peak hour, mixed traffic: R1, R2, R4** | 3 |
| `rate-500` | 500 | 0 | 2× design peak (headroom) | 3 |

- **Every candidate model** runs all three configurations. Priority if time is short:
  `rate-250_search-450` for all four models first, then `rate-500`, then `rate-125`.
- R1/R2 are evaluated at the design peak *with* the peak search traffic, because that is the peak
  hour the workload model describes. It is also the stricter condition.
- **Run length:** 720 s of arrivals. The first **120 s are warm-up** (excluded); the measured window
  is the remaining **10 minutes**. Then a 190 s drain.
- **Three runs per configuration**, back-to-back, numbered `run-1..3`. The drain empties the queue
  between runs. Each run ≈ 12 + 3 + 1 min.
- **Database state:** before each model's series, stop the API, set `DATABASE_URL=sqlite:///./data/bench-<model-dir>.db`
  (a new file; keep the old ones), and start it again. Every model then starts from an empty
  database, and search load sees the same growth pattern. Each run's metadata records the
  ticket count before the run (`tickets_in_database_before`).

### 4.2 Procedure (per model)

On the **service machine**:

```powershell
# 1. set OLLAMA_MODEL=<tag> and DATABASE_URL in .env, then
docker compose up --build -d
docker compose logs api --tail 5          # started, no errors
ollama ps                                 # after the first request: PROCESSOR shows 100% CPU
```

On the **load generator** (no other traffic to the service during runs):

```powershell
$m = "qwen2.5:7b"; $h = "<service-ip>"
foreach ($run in 1..3) {
  .\.venv\Scripts\python.exe -m scripts.run_load_test --model $m --rate 250 --search-rate 450 --host $h --run $run
}
foreach ($run in 1..3) { .\.venv\Scripts\python.exe -m scripts.run_load_test --model $m --rate 500 --host $h --run $run }
foreach ($run in 1..3) { .\.venv\Scripts\python.exe -m scripts.run_load_test --model $m --rate 125 --host $h --run $run }
```

Leave `--run` out to use the next free number. The wrapper refuses to overwrite an existing run.
If a run fails or is contaminated, keep it, note why (`--notes "..."` on the repeat run), and repeat
it as run-4 (the processing reports all completed runs, and the extra run is explained in the report).

### 4.3 After each model's series

1. Copy the service log from the service machine. It is not on the load generator. Copy the whole
   file, unchanged, into the configuration folders, one copy per run:

   ```powershell
   # on the service machine (or over a share / USB)
   Copy-Item logs\service.log \\<loadgen>\share\service-<model-dir>-<yyyymmdd-hhmm>.log
   # on the load generator, for every run of the series
   Copy-Item <copied log> results\load\<model-dir>\rate-250_search-450\run-1.service.log
   ```
   (Or keep a single copy and pass it with `--service-log` in the next step.)
2. Reconcile first, then process (section 6). Official unreconciled runs are excluded.
3. Commit the raw files and the summaries on your branch (`git add results/load/<model-dir>`).

## 5. Accuracy test

| Item | Value |
|---|---|
| Prerequisites | Freeze gate passed; service running `OLLAMA_MODEL=<tag>`; no other traffic |
| Golden set | `data/golden_set_final.csv`: 180 tickets, columns `row,narrative,final_golden_category`; read-only; its SHA-256 is recorded per run |
| Model selection | Set `OLLAMA_MODEL` on the service machine and restart the API (`docker compose up -d`); `--model` must name the same tag. The script checks the stored ticket's model through `GET /search` after the first ticket and stops on a mismatch |
| Execution | Sequential (one request at a time), golden-set row order, 180 s client timeout |
| Scoring | Overall accuracy = correct / 180; per-category accuracy = recall (correct / golden tickets of that category); a failed request (502, timeout) counts as incorrect; confusion matrix rows = golden, columns = predicted + FAILED |
| Repetitions | One run per model (temperature 0). Repeat a run only if it was aborted, and keep the aborted one |
| Output | `results/accuracy/<model-dir>/run-N/`: `metadata.json`, `predictions.csv` (raw, written per ticket), `metrics.json`, `per_category.csv`, `confusion_matrix.csv`, `summary.md` |

```powershell
.\.venv\Scripts\python.exe -m scripts.accuracy_test data\golden_set_final.csv --model qwen2.5:7b --api-url http://<service-ip>:8000
# after all models:
.\.venv\Scripts\python.exe -m scripts.accuracy_test --summarise results\accuracy
.\.venv\Scripts\python.exe -m scripts.reconcile_logs results\accuracy\qwen2.5_7b\run-1\predictions.csv --service-log <copied service.log>
```

Run accuracy tests **separately from** load tests: never at the same time, because they share the
service. Their sequential latencies are the "single-request latency" that the prediction record
predicts: `single_request_latency_excluding_first` in `metrics.json`.

## 6. Processing results and reconciling with logs

```powershell
.\.venv\Scripts\python.exe -m scripts.reconcile_logs results\load\qwen2.5_7b\rate-250_search-450 --service-log <copied service.log>
.\.venv\Scripts\python.exe -m scripts.process_jmeter_results results\load       # after reconciling every configuration
```

### 6.1 Metric definitions (identical for every run)

| Metric | Definition |
|---|---|
| Measured window | `[t0 + 120 s, t0 + 720 s)`; t0 = moment JMeter started the schedules (from `.jmeter.log`) |
| Offered rate | samples **started** in the window ÷ window hours |
| Achieved throughput | **successful** samples **completed** in the window ÷ window hours |
| Error rate | unsuccessful samples ÷ samples started in the window (wrong status, 502, timeouts, connection errors) |
| p50 / p95 / p99 | JMeter `elapsed` of successful samples started in the window, nearest-rank method, seconds |
| Latency trend | median of last third ÷ median of first third of the window; least-squares slope; *growing* if ratio ≥ 1.5 and slope > 0 |
| Across 3 runs | mean, sample SD, min, max of each per-run metric; plus p50/p95/p99 pooled over all three runs' samples (≈ 125 samples at 250/h, so the pooled p99 is more meaningful than a per-run p99 from ≈ 42) |

### 6.2 Outputs (machine-readable and presentation-ready)

| File | Content | Use |
|---|---|---|
| `<config>/runs.csv` | one row per run × endpoint | spread charts, appendix |
| `<config>/summary.csv`, `summary.json` | mean/SD/min/max + pooled percentiles per endpoint | requirement comparison |
| `<config>/summary.md` | Markdown table | paste into slides/report |
| `results/load/summary_all.csv`, `runs_all.csv`, `summary_all.md` | every configuration, every model | latency-vs-rate and throughput-vs-rate graphs |
| `results/accuracy/accuracy_summary.csv`/`.md` | overall + per-category accuracy, failures, latency for all models | accuracy table/graph |
| `results/stress/<model>/stress_steps.csv`, `stress_summary.md` | one row per step | stress graph (offered vs achieved, p95 vs rate) |
| `*.reconciliation.json`, `reconciliation.csv` | log reconciliation per run | evidence of traceability |

### 6.3 How reconciliation works

Each `/tickets` or `/search` response carries `X-Request-ID`. The service writes the same id, with
status, model and `duration_ms`, to `logs/service.log`. JMeter writes it to the `request_id`
column; the accuracy test writes it to `predictions.csv`. `scripts/reconcile_logs.py` then:

1. matches every client sample to exactly one log line by id, and compares endpoint, status code and model;
2. lists client samples without an id: either *no HTTP response* (client timeout/connection error)
   or *a response without the id*, which must never happen;
3. lists log lines in the run's window that no client sample explains. The wrapper's preflight
   `GET /stats` (its id is in the run metadata) and requests the client gave up on are explained.
   Anything else is **unexplained** and marks the run **contaminated**;
4. reports client elapsed minus server `duration_ms` (time outside the application: network and
   the HTTP server's own queue) and the clock offset between the machines;
5. writes `run-N.reconciliation.json` and `run-N.service_log_extract.jsonl` (exactly the log lines
   used) next to the `.jtl`, without changing the original log.

A run is valid evidence only if `reconciled = true` and `contaminated = false`. The command exits
non-zero otherwise. A failing run is repeated, not deleted. Every reported number can then be
traced: summary → `runs.csv` row → `.jtl` sample → `request_id` → service-log line.

Malformed log lines, repeated client IDs, absent expected model and client
timeouts without a corresponding possible service-log line now fail
reconciliation. Same-endpoint lines attributed to abandoned clients remain
possible matches; inspect timestamps/errors and retain that uncertainty.

Official load aggregation excludes missing metadata, missing schedule start,
missing/failed reconciliation and differing model/workload/window configurations.
It is marked official only after at least three valid official runs exist.
Per-run JSON also records sample count, observed first-start-to-last-end span,
wrapper elapsed time when available, and the configured measured window; these
are distinct duration definitions.

## 7. Stress test

### 7.1 Goal and model

Find the **maximum sustainable ticket arrival rate** of the baseline: the highest open-loop rate at
which latency stays bounded and errors stay acceptable. Model: **`qwen2.5:7b`**, the candidate
the prediction record expects to come closest to meeting the requirements, and so the most likely
recommendation. Repeat for other models if time allows, with the same criteria.

### 7.2 Starting load and increment strategy

| Item | Value |
|---|---|
| Starting load | 250 tickets/h (design peak), ticket-only traffic |
| Steps | 250 → 500 → 750 → 1000 → 1500 → 2000 → 3000 tickets/h, in order |
| Refinement | after the first unsustainable step, **2 bisection steps** between the last sustainable and first unsustainable rate, rounded to 25/h |
| Per step | one run of 720 s (120 s warm-up excluded, 10-min window) + 190 s drain |
| Between steps | 200 s cool-down (> the 120 s Ollama timeout) so each step starts from an idle service |
| Stop | at the first unsustainable step (plus refinement). Never push past it "to see more" |

If the first step is already unsustainable, start a new test with lower rates (`--label lower --rates 50,100,150,200`).
If no step fails, extend the rates and resume. In both cases no limit is claimed until one is measured.

### 7.3 Stopping criteria (fixed before the first step)

A step is **unsustainable** if any of these holds in its measured window:

1. error rate > **5%**;
2. achieved throughput < **90%** of the offered rate (a backlog is building);
3. latency **grows continuously**: last-third median ≥ 1.5 × first-third median, with a positive slope;
4. p95 > **120 s** (the Ollama timeout, beyond which requests fail).

These values are written to `results/stress/<model-dir>/stress_plan.json` when the test starts. The
script refuses to resume with different values. A change needs a new `--label` and a written reason.

### 7.4 Commands

```powershell
.\.venv\Scripts\python.exe -m scripts.run_stress_test --model qwen2.5:7b --host <service-ip>
# resumable: the same command reuses completed steps and never re-runs or overwrites them
.\.venv\Scripts\python.exe -m scripts.reconcile_logs results\stress\qwen2.5_7b\rate-750 --service-log <copied log>
```

Expected duration: up to about 9 steps × ~20 min ≈ 3 h.

### 7.5 Recorded metrics

Per step, in `stress_steps.csv`/`stress_summary.md`: rate setting, offered rate, achieved
throughput, achieved/offered, error rate (with error types), p50/p95/p99, trend ratio and slope,
verdict, reasons, and an `observations` column. The conclusion states the **highest measured
sustainable rate** and the **lowest measured unsustainable rate**, and says the limit lies between
them. Only measured steps appear.

Observations on the **service machine** during every step, saved under `results/stress/<model-dir>/observations/`:

```powershell
# CPU and memory every 10 s for the length of a step (run in a separate PowerShell window)
Get-Counter '\Processor(_Total)\% Processor Time','\Memory\Available MBytes' -SampleInterval 10 -MaxSamples 90 |
  Export-Counter -Path results\stress\qwen2.5_7b\observations\rate-750-counters.csv -FileFormat CSV
ollama ps                       > results\stress\qwen2.5_7b\observations\rate-750-ollama-ps.txt
docker stats --no-stream        > results\stress\qwen2.5_7b\observations\rate-750-docker-stats.txt
```

Write a short note per step into the `observations` column of `stress_steps.csv` (CPU ≈ %,
`ollama ps` processor split, container CPU, available memory, error types from the service log).

### 7.6 Documenting the bottleneck (do not fix it)

From the stress and load evidence, record in the final report:
- where time is spent: server `duration_ms` vs client elapsed (reconciliation), and the Ollama vs service CPU share;
- how latency behaves as the rate approaches the limit (queueing: does p95 grow faster than p50?);
- the error types at the limit (e.g. `OllamaTimeoutError` 502 in the service log, or client timeouts);
- comparison with the prediction record's bottleneck prediction (section 1 there).

## 8. Troubleshooting

| Symptom | Action |
|---|---|
| `Official benchmarking is NOT allowed yet` | The freeze gate is not met. Do not work around it. The listed reasons say what is missing |
| `JMeter not found` | Set `JMETER_BIN` or pass `--jmeter` |
| `Service not reachable` | Check `docker compose ps`, the firewall rule, and the IP |
| Accuracy test stops with a model mismatch | `OLLAMA_MODEL` on the service is not the tag passed; fix `.env`, restart, re-run (the aborted run is kept) |
| `contaminated = true` | Someone else used the service during the run. Keep the run, record it, repeat with the next run number |
| Many `SocketTimeoutException` errors | Requests took > 180 s (beyond the service's own 120 s timeout): record it, it is part of the finding |
| Run status `failed` | Keep the files, read `run-N.jmeter.log`, repeat as the next run |
