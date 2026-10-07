# Prediction record

**THIS DOCUMENT MUST BE COMPLETED AND COMMITTED BEFORE THE FIRST BENCHMARK RUN.**
**Once committed, the predictions below are never edited.** Results are compared against them
afterwards, and differences are explained in the final report.

Owner: Person 4. Status: **DRAFT (2026-10-07)**: the team reviews every value below, changes
any it disagrees with, fills in the sign-off, and commits it in the freeze commit. Every number
is a prediction; none is a measurement.

## 0. Basis for the predictions

### Information available when predicting

- No accuracy, load or stress benchmark has been run. No candidate model has classified any
  golden-set ticket.
- **Disclosure:** during environment setup on 2026-10-06, two hand-written sentences (not from
  our dataset) were sent once each to `llama3.2:3b` inside the running service. They returned
  correct categories in 8.1 s (first request, including model load) and 0.4 s (second request,
  very short text). The team saw these two timings before writing this record. No other model
  output or timing was seen.
- Golden-set annotator disagreements (`data/labelling/disagreements.csv`) were used for the
  category predictions in section 3. They are human labels, not model output.

### Assumed test environment

| Item | Value |
|---|---|
| Official PC1: service + Ollama | Intel(R) Core(TM) i7-10510U CPU @ 1.80GHz; 4 physical cores / 8 logical processors; 15.8 GB RAM |
| PC1 operating system | Microsoft Windows 11 Home, version 10.0.26200, 64-bit |
| Inference | Ollama version: TO BE RECORDED (command unavailable on the current shell's PATH); configured CPU only (`num_gpu: 0`), `temperature: 0`; `OLLAMA_NUM_PARALLEL=1` intended, server setting TO BE RECORDED |
| Service | Docker / synchronous FastAPI / SQLite; Docker CLI 29.4.3 (build 055a478), Compose v5.1.3 verified by version commands; container runtime and WSL resource limits TO BE RECORDED |
| Python | Project host `.venv`: 3.12.14; container version TO BE RECORDED; default PATH `python`: 3.7.6 (use the project `.venv` for scripts) |
| Official PC2: load generator | Separate physical desktop; CPU, cores/threads, RAM, OS, Java, JMeter and Python versions TO BE RECORDED |
| Network | Local network between PC1 and PC2; connection type, topology, IPs and link speeds TO BE RECORDED |
| Prompt | About 330 tokens of fixed instructions, then the narrative, then a 1-line suffix |
| Narratives | Golden-set median ≈ 218 tokens, p95 ≈ 448 tokens (characters / 4 estimate) |

If the team runs the benchmarks on a different machine, these predictions must be updated
**before** the freeze commit.

### Environment revision before formal benchmarking (2026-10-07)

The official service/Ollama machine was changed to the Intel Core i7-10510U
laptop (4 physical cores / 8 logical processors, 15.8 GB RAM) before this
record was frozen and before any formal accuracy, load or stress benchmark.
Hardware and OS values above are the user's verified CIM observations.
PC2 is a different physical desktop; its specifications remain TO BE RECORDED.

**TEAM REVIEW REQUIRED BEFORE FREEZE.** The former draft assumed an AMD Ryzen
7 8845HS (8 cores / 16 threads, 13.8 GB usable RAM) and Ollama 0.35.1. Those
are historical draft assumptions, not the official PC1 or a verified PC1 runtime.
All existing numerical accuracy, latency, sustainable-rate and resource
predictions below are retained unchanged pending team review. The assumed
prefill/generation speeds in section 2 and predicted PASS/FAIL outcomes also
need review against the new CPU. Changing the CPU alone does not justify
changing accuracy predictions. No formal measurements informed this revision,
and this note does not claim the team has already approved the predictions.

The setup timings disclosed above remain historical observations; their
machine attribution is TO BE RECORDED. They are not new PC1 benchmark results.
Configured CPU-only requests are not proof of runtime CPU-only execution:
every candidate still needs a PC1 `ollama ps` capture during inference.

## 1. Bottleneck prediction

**We predict Ollama CPU inference will be the bottleneck, specifically prompt processing
(prefill) of the narrative. The API, SQLite and the network will not be.**

- Each classification needs the model to process about 200–500 narrative tokens on PC1's 4 physical CPU cores.
  We predict this takes seconds, while the API and SQLite work takes milliseconds.
- `OLLAMA_NUM_PARALLEL=1` means Ollama processes **one request at a time**. FastAPI's thread pool
  accepts concurrent requests, but they wait in Ollama's queue. The system behaves as a
  single-server queue whose capacity ≈ 3600 / mean classification time.
- **Predicted symptom at overload:** once the arrival rate exceeds that capacity, latency grows
  steadily for the whole run. When a request waits more than 120 s (`OLLAMA_TIMEOUT_SECONDS`), the
  service returns 502 with `OllamaTimeoutError` in `logs/service.log`. We predict errors at
  overload will be timeouts, not crashes or HTTP 5xx from Ollama itself.
- **Predicted resource picture during load:** CPU utilisation near 100% of the cores Ollama uses;
  service-container CPU below 10%.
- **Memory risk (medium models):** PC1's 15.8 GB of RAM must hold Windows, Docker's WSL 2 VM and a
  ~5 GB model. We predict the 7–8B models fit, but if memory pressure causes paging, their
  latency will be markedly higher and more variable between runs than the small models'.

## 2. Per-model predictions

Single-request latency = time for one `POST /tickets` with no other traffic, model already loaded,
over golden-set narratives. It is based on assumed CPU speeds for quantised models of each size
(not measured): prefill ≈ 150, 120, 50 and 45 tokens/s and generation ≈ 25, 20, 9 and 8 tokens/s
for the four models in table order, with the fixed instruction prefix reused between requests.

| Model (exact tag) | Size class | Expected golden-set accuracy | Expected single-request latency, median | Expected single-request latency, p95 | Expected max sustainable rate |
|---|---|---|---|---|---|
| `gemma2:2b` | Small | **70%** | **1.8 s** | 3.5 s | ≈ 1,800 tickets/h |
| `llama3.2:3b` | Small | **72%** | **2.2 s** | 4.2 s | ≈ 1,500 tickets/h |
| `qwen2.5:7b` | Medium | **82%** | **5.0 s** | 9.5 s | ≈ 650 tickets/h |
| `llama3.1:8b` | Medium | **80%** | **5.5 s** | 10.5 s | ≈ 600 tickets/h |

Expected first request after the model is loaded from disk: 5–15 s longer than the above.

### Predicted outcome against the requirements (`docs/requirements.md`)

| Model | R1 latency at 250/h | R2 throughput at 250/h | R3 overall ≥ 80% | R3 every category ≥ 70% |
|---|---|---|---|---|
| `gemma2:2b` | Pass | Pass | **Fail** | **Fail** |
| `llama3.2:3b` | Pass | Pass | **Fail** | **Fail** |
| `qwen2.5:7b` | Pass | Pass | Pass | **Fail** (Debt collection) |
| `llama3.1:8b` | Pass | Pass | Pass (borderline) | **Fail** (Debt collection) |

We therefore predict that **no candidate meets every requirement** at the baseline. The small
models fail on accuracy, and the medium models meet overall accuracy but miss the per-category
floor on Debt collection. We predict `qwen2.5:7b` comes closest.

At **500 tickets/h** (2× design peak) we predict all four models still keep up, but the medium
models' p95 rises above 15 s because of queueing. Their stress-test limit is between 550 and
700 tickets/h.

Other predictions:

- Invalid-output failures (502 `InvalidCategoryError`): ≤ 2% of golden tickets for `gemma2:2b`
  and `llama3.2:3b`, ≤ 1% for the medium models.
- Run-to-run spread of p95 at 250/h: within ±15% of the mean for the small models; larger for
  the medium models.

## 3. Difficult categories

Ranked from hardest:

1. **Debt collection.** Hardest for every model. Lowest per-category accuracy for all four;
   below 70% for all four.
   - Collection accounts appear on credit reports, and many narratives are written as credit-report
     disputes about a collection debt. Our annotators disagreed most on exactly this pair:
     **11 of 27** disagreements were Credit reporting vs Debt collection.
   - Debt collection appears in 17 disagreements while only 17 golden tickets carry it as their
     final label.
   - We predict most errors on golden Debt collection tickets will be predicted as Credit reporting.
2. **Consumer loan.** Below 75% for the small models. It is confused with Debt collection (a loan
   in default and being collected; 6 annotator disagreements) and with Credit reporting (3).
3. **Money transfer or service vs Bank account or service.** Some confusion for small models,
   because transfers are made from bank accounts and the narrative often describes both.

Easiest: **Mortgage**. We predict at least 90% accuracy for all four models: its vocabulary
(escrow, servicer, foreclosure, loan modification) is distinctive, and annotators had **no**
disagreements involving Mortgage.

## 4. Sign-off

PC1 environment revision approved by the user on 2026-10-07 (instruction:
"sign off"). This approval covers the environment documentation update;
the numerical prediction review and team freeze fields below remain pending.

| | |
|---|---|
| Reviewed by (names) | |
| Values changed from the draft | |
| Committed in (commit hash) | |
| Date committed | |
