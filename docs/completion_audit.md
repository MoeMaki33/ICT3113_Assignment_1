# Completion audit — 2026-10-07

**FORMAL TESTING NOT READY.** The committed prediction record remains DRAFT.
No formal accuracy, load or stress traffic was run in this audit. No benchmark
results, human labels, historical predictions, logs or model evidence were
invented, replaced or deleted. No commits were made.

## Pre-freeze PC1 environment revision

**PC1 environment update signed off by the user on 2026-10-07**, through the
instruction "sign off". This approves the PC1 documentation revision.
Numerical prediction review, team freeze, PC2/runtime evidence and source-hash
provenance remain outstanding. No benchmark or commit was performed for this
sign-off.

The user has now selected the **official PC1 / System Under Test**: Intel Core
i7-10510U @ 1.80 GHz laptop, 4 physical cores / 8 logical processors, 15.8 GB RAM,
Microsoft Windows 11 Home 64-bit, OS 10.0.26200. Hardware values are the user's
verified CIM observations. **PC2 is a separate physical desktop**, with hardware,
software and network details TO BE RECORDED. The following original audit table
is a historical snapshot before that role decision; `test_environment.md` is
the current official environment record.

PC1 version commands returned Docker CLI 29.4.3 (build 055a478), Docker Compose
v5.1.3, project `.venv` Python 3.12.14 and default PATH Python 3.7.6. Ollama was
not recognised on the current PATH, so its version is unavailable/not verified.
Docker emitted sandbox config-access warnings; container operation was not
verified by CLI version checks. JMeter 5.6.3 previously tested on the laptop
does not establish a verified installation on the new PC2.

Historical i7-10750H model provenance remains unchanged. The former Ryzen
environment is retained as superseded draft context in `prediction_record.md`.
Numerical predictions remain unchanged and require team review before freeze;
the DRAFT sign-off and separate selection-source hash discrepancy remain blockers.
R1-R4, workload values, all golden labels and existing raw evidence are unchanged.

Validation during this PC1 documentation revision:

- `.\.venv\Scripts\python.exe -m pytest -q`: **160 passed, 1 skipped**;
  installed Starlette emitted its existing TestClient deprecation warning.
- `.\.venv\Scripts\python.exe -m scripts.validate_golden_set`: exit 1,
  `selection.json source_sha256 differs from data/team.csv; review historical provenance`.
- `.\.venv\Scripts\python.exe -m scripts.perf_common`: exit 1,
  `docs/prediction_record.md has uncommitted changes` and
  `docs/prediction_record.md is still marked DRAFT`.
- `git diff --check`: passed. No formal benchmarks, commits or pushes ran.

Files updated for this revision: `docs/test_environment.md` (official PC1 and
pending PC2/runtime evidence), `docs/prediction_record.md` (hardware revision
and mandatory team review, numerical predictions retained), `docs/models.md`
(historical capture distinguished from PC1), `docs/test_playbook.md` (machine
roles and PC2 JMeter verification), `README.md` (current readiness context),
`docs/slide_data.md` (Slide 7 environment) and this audit (revision context/checks).

## Repository findings and assignment status

| Area | Status | Evidence / outstanding work |
|---|---|---|
| Three endpoints and seven categories | COMPLETE | Automated tests cover synchronous classification before storage/response, invalid output rejection, failure without insertion, substring search, all seven count keys and persistence |
| Unoptimised baseline | COMPLETE | Blocking Ollama call; no application cache, queue, batching, worker or parallel model calls introduced; fresh database empty, no dataset seeding |
| Request logging | COMPLETE | IDs, UTC times, method/route, status, duration, model, ticket/category and error; narratives excluded; unexpected pre-response errors now also carry an ID and generic 500 |
| Docker definition | COMPLETE (configuration); NEEDS HUMAN INPUT (execution) | Compose validates; Python 3.12 image, port 8000, data/log mounts, external configurable Ollama, `num_gpu=0`, no GPU dependency. Daemon was stopped: image build/runtime unverified |
| Golden rows and labels | COMPLETE (content); NEEDS HUMAN INPUT (provenance) | 180 rows from team 7's 7000-7999; narratives match course rows; deterministic seed 3113 selection reproduces; every human resolution matches final labels |
| Independent labelling evidence | COMPLETE (artifacts); NEEDS HUMAN INPUT (attestation) | Two completed sheets, 27 resolved disagreements, protocol v1.1. Real annotator names, independence and protocol approval cannot be established by software; approval remains pending in the protocol history |
| Agreement | COMPLETE | Recomputed 153/180 agreements, 85%, Cohen's kappa 0.8239066632849016; original annotator SHA-256 values match recorded evidence |
| Selection provenance | INCOMPLETE / NEEDS HUMAN INPUT | `selection.json` expects team hash `20e8ed8aeec33617a329c2785020b9a846ff33596ee5430883511ee87ca00d8c`; current committed team bytes hash to `3174ac682d4796ab44a32e809822c3d313cdd21429707def5aaed8b55ff1a99c`. Current selection reproduces exactly, but this does not explain the historical hash |
| Candidate set | COMPLETE (historical evidence); NEEDS HUMAN INPUT (actual test host) | Four tags unchanged: gemma2:2b, llama3.2:3b, qwen2.5:7b, llama3.1:8b; two size classes; four full digests in committed provenance; references/licences linked |
| Workload | COMPLETE (structure); NEEDS HUMAN INPUT (approval) | Volume/period, arrival/search estimates, peaks and lengths exist. FCA/CFPB figures checked against primary sources in `references.md`; estimated bank share, staffing and timing patterns clearly labelled |
| Requirements | COMPLETE (numeric draft); NEEDS HUMAN INPUT (approval) | R1-R4 have operations, numbers, load conditions and rationale; proposed decision-rule questions below remain for the team |
| Predictions | INCOMPLETE / NEEDS HUMAN INPUT | Bottleneck, per-model accuracy/latency and difficult-category predictions exist; status DRAFT and sign-off blank; original record preserved |
| Freeze gate | BLOCKED UNTIL PREREQUISITE | Both files exist in HEAD, clean individually. Golden first committed in `47f6f7b`; prediction record in `33b8b0c`. Draft status prevents testing; staged files alone no longer count as committed |
| Actual environment | MISSING / NEEDS HUMAN INPUT | Environment template unfilled, no separate-machine records; Intel/Ollama 0.34.4 historical provenance conflicts with Ryzen/Ollama 0.35.1 draft assumptions; actual test configuration must be chosen before freeze |
| Open-loop JMeter | COMPLETE (plan/tooling); NEEDS HUMAN INPUT (execution) | Two Open Model Thread Groups, Poisson schedules, configurable rates/seeds, JSON-escaped narratives from assigned rows, request-ID extraction. No JMeter executable available in this shell |
| Load evidence | BLOCKED UNTIL FORMAL TESTING | Three-rate, four-model, three-run procedure and processing prepared; raw official `.jtl` files absent |
| Accuracy evidence | BLOCKED UNTIL FORMAL TESTING | Sequential actual POST runner, raw predictions, overall/per-category recall and confusion matrix; no model-run predictions present |
| Stress limit and bottleneck | BLOCKED UNTIL FORMAL TESTING | Step/ramp/refinement/stopping criteria implemented; summaries provisional until reconciled; no measured limit claimed |
| Reconciliation | COMPLETE (tooling); BLOCKED UNTIL FORMAL TESTING (artifacts) | Rejects missing/duplicate IDs, status/route/model mismatch, unmatched timeouts and malformed log input; existing 18 development log lines retained |
| Outcome comparison/recommendation | BLOCKED UNTIL FORMAL TESTING | Separate templates added; no PASS/FAIL or winner claimed from missing results |
| Slide preparation/references | COMPLETE (structure); NEEDS HUMAN INPUT / FORMAL TESTING (content) | Twelve-slide evidence map and primary links added; member IDs/names and measured results remain TODO; no PowerPoint edited |
| Cleanliness | COMPLETE (tracked-path check) | No tracked `.env`, `.pyc`, SQLite database or cache paths found; existing local tool/cache directories ignored; intended course/team/golden datasets serve different roles and were retained. This is not a guarantee from a dedicated secret scanner |

## Validation executed

| Command | Outcome |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest -q` (before edits) | 149 passed, 1 skipped |
| `.\.venv\Scripts\python.exe -m pytest -q` (after code fixes) | 159 passed, 1 skipped; real Ollama test requires explicit opt-in |
| `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` (final code validation) | 160 passed, 1 skipped; cache provider disabled to avoid the observed cache permission warning |
| `docker compose config --quiet` | PASS after approval for access to Docker settings |
| `docker version --format '{{.Server.Version}}'` | No running daemon; Docker build/start was not performed |
| `.\.venv\Scripts\python.exe -m scripts.validate_golden_set` | Exit 1, intentionally: selection source-hash mismatch; remaining content/agreement checks pass |
| `.\.venv\Scripts\python.exe -m scripts.perf_common` | Exit 1, intentionally: prediction record DRAFT |
| `.\.venv\Scripts\python.exe -m scripts.prepare_jmeter_data data/team.csv`, then `validate_load_inputs()` | PASS: all 1,000 assigned narratives and manifest hashes match; restored Windows-converted search-term bytes to canonical LF |
| `git diff --check` | PASS: no whitespace errors |

Observed test warnings: installed Starlette deprecates its httpx TestClient
integration; one run also reported denied pytest cache writes. Neither changes
the test outcomes. Dependencies remain within the existing declared ranges;
record exact tested host/container versions before measuring.

## Questions to settle before the team freezes its requirements

Do not change thresholds in response to model results. These are pre-test
interpretation issues, not permission to adjust requirements after measurement.

- R1 says 95%/99% of requests meet latency targets, while the current processor
  uses successful requests only. Decide whether failures enter latency
  percentiles; report errors separately either way. R1 also describes each run
  but uses a mean-across-runs pass rule; agree which wording governs.
- With Poisson arrivals over 10 minutes, offered counts fluctuate. A fixed
  achieved-rate floor can fail even for a perfect service receiving fewer than
  245/h in that window. Record offered and achieved rates, discuss run length
  and the fixed versus offered-relative criterion before freezing. No team
  numbers were changed in this audit.
- R3's 85% annotator agreement is pairwise consistency, not a measured human
  accuracy ceiling against adjudicated truth. Treat it as a judgement anchor.
  The balanced course extract and assumed 25% bank share limit workload realism.

## Required human actions, in order

1. Inspect the selection-hash history and record an explanation or reviewed
   provenance correction while retaining the original hash. Do not relabel
   tickets or regenerate a different selection. Confirm annotator identities,
   independence, row convention and protocol approval. Run:

   ```powershell
   git log --oneline -- data/team.csv data/labelling/selection.json
   .\.venv\Scripts\python.exe -m scripts.validate_golden_set
   ```

2. Complete runtime recording on the now-selected i7-10510U laptop **PC1** and
   independently record the **separate physical desktop PC2** for JMeter.
   Complete remaining network/manual fields on the actual machines:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.record_test_environment --role service
   # On the separate load-generator machine:
   .\.venv\Scripts\python.exe -m scripts.record_test_environment --role loadgen
   ```

3. Approve workload/requirements and review predictions against the chosen
   hardware. Complete sign-off and mark predictions FROZEN/FINAL. Commit the
   reviewed evidence yourselves; Codex did not commit it. Verify clean state
   and the gate:

   ```powershell
   git log -1 -- data/golden_set_final.csv
   git log -1 -- docs/prediction_record.md
   git status --short -- data/golden_set_final.csv docs/prediction_record.md
   .\.venv\Scripts\python.exe -m scripts.perf_common
   ```

4. Install/start Docker and host Ollama on the service machine; install Java
   and JMeter 5.6.3 on the separate load generator. Follow `test_playbook.md`
   to set Ollama's environment before starting the correct server process.
   Pull the unchanged candidate set and capture fresh provenance to a new file:

   ```powershell
   ollama pull gemma2:2b
   ollama pull llama3.2:3b
   ollama pull qwen2.5:7b
   ollama pull llama3.1:8b
   .\.venv\Scripts\python.exe scripts\record_model_digests.py --json results\environment\model-provenance-before-tests.json
   docker compose up --build
   ```

   Configure `.env` first. Compare new digests with historical evidence, archive
   `ollama show <tag> --license`, and capture `ollama ps` showing 100% CPU during
   requests for every candidate. Record container dependencies and WSL limits.
   CPU options in code alone are not a CPU-execution observation.

5. Only after all checks pass, execute the full matrix in `test_playbook.md`:
   every candidate accuracy run, three runs at each load configuration, and at
   least one meaningful stress test. Run example commands from the **loadgen**:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.accuracy_test data\golden_set_final.csv --model <tag> --api-url http://<service-ip>:8000
   .\.venv\Scripts\python.exe -m scripts.run_load_test --model <tag> --rate 250 --search-rate 450 --host <service-ip> --run 1
   .\.venv\Scripts\python.exe -m scripts.run_stress_test --model qwen2.5:7b --host <service-ip>
   ```

   Repeat load runs 2 and 3 and the 125/h and 500/h configurations for every
   tag. Switch service models and use fresh, separately named databases as the
   playbook specifies. Keep aborted/failed runs and all raw logs.

6. Copy actual service logs to the load generator, reconcile every accuracy,
   load and stress run, then process load results. Complete outcome comparison,
   bottleneck and requirement decision tables only from verified raw evidence.

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.reconcile_logs <configuration-directory> --service-log <copied-service.log>
   .\.venv\Scripts\python.exe -m scripts.process_jmeter_results results\load
   .\.venv\Scripts\python.exe -m scripts.accuracy_test --summarise results\accuracy
   ```

## Files changed and purpose

| File | Change |
|---|---|
| `app/services/request_logger.py` | Correlate unexpected pre-response 500 errors without exposing internal text |
| `scripts/perf_common.py` | Prove files exist in HEAD, check completeness, preserve orphaned run numbers, expose read-only gate command |
| `scripts/validate_golden_set.py` | New read-only source/selection/annotation/adjudication/agreement validator |
| `scripts/accuracy_test.py` | Require frozen golden bytes, reject duplicate rows, retain malformed responses as failures, exclude first attempt consistently from warm latency |
| `scripts/run_load_test.py` | Preserve orphaned logs, validate arguments and exact assigned-team traffic/manifest hashes, record frozen-input hashes and launch failures |
| `scripts/process_jmeter_results.py` | Exclude missing metadata/unreconciled official runs and mixed configurations; incomplete repetitions cannot be marked official; record sample counts and observed duration definitions |
| `scripts/reconcile_logs.py` | Flag repeated client IDs, unmatched no-response samples, malformed logs and missing expected model |
| `scripts/run_stress_test.py` | Gate before plan creation/resume, preserve observation notes, mark unreconciled limits provisional |
| `scripts/record_model_digests.py` | Preserve existing provenance files, create output parents, return failure when candidates are missing |
| `scripts/record_test_environment.py` | Record package versions, reject failed version commands, restrict recorded Ollama environment fields |
| `tests/test_testing_tools.py` | Update fixtures to valid freeze evidence/canonical golden paths and explicit smoke stress runs; verify malformed-log rejection |
| `tests/test_evidence_safety.py` | New regressions for evidence admission and unexpected service failures |
| `tests/test_integration.py` | Implement opt-in real endpoint/Ollama smoke check using temporary storage |
| `README.md` | Correct current status and document integration/readiness commands and new evidence documents |
| `.gitattributes` | Preserve hashed JMeter search-term bytes across Windows checkouts; regenerated those inputs with the existing preparation script |
| `jmeter/data/search_terms.txt` | Restored local LF bytes to the existing HEAD/manifest content; no semantic change |
| `docs/models.md` | Correct digest status, preserve capture history and flag hardware/runtime conflict |
| `docs/test_environment.md` | Make every missing field an explicit TODO and distinguish intended settings from observations |
| `docs/test_playbook.md` | Document stronger gate and reconcile-before-processing order; use new provenance filename |
| `docs/references.md` | Primary dataset/workload/tool/model/licence references and source limitations |
| `docs/slide_data.md` | Twelve-slide evidence map and architecture diagram, with pending items explicit |
| `docs/prediction_vs_results.md` | Separate comparison template, pending measurements |
| `docs/recommendation.md` | Requirement decision table and evidence-based recommendation procedure, pending measurements |
| `docs/bottleneck_analysis.md` | Measurement/diagnosis worksheet and explicit interpretation limits |
| `docs/completion_audit.md` | This audit, test outcomes, blockers and exact human actions |
