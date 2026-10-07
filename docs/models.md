# Candidate models

All candidates are official Ollama library tags, run locally through Ollama, and are
used with `options.num_gpu = 0` (CPU-only). GPU availability is not assumed. Two
parameter-size classes are covered: **Small (2-4B)** and **Medium (7-9B)**.

**All four digests are recorded** in `results/model_provenance.json` from the
2026-09-29 capture below. They identify those pulled artifacts, not proof that
the models are available on the eventual test machine. Recheck there using
[Recording digests](#recording-digests); preserve earlier captures.

| Model | Ollama Tag | Digest | Parameter Class | Licence (upstream, confirm locally) | Reason Selected |
|---|---|---|---|---|---|
| Gemma 2 2B | `gemma2:2b` | `sha256:8ccf136fdd5298f3ffe2d69862750ea7fb56555fa4d5b18c04e3fa4d82ee09d7` | Small, 2.6B (Q4_0) | Gemma Terms of Use | Smallest candidate and fastest CPU baseline; shows how far a ~2B model gets on seven-way complaint classification. |
| Llama 3.2 3B | `llama3.2:3b` | `sha256:a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` | Small, 3.2B (Q4_K_M) | Llama 3.2 Community License | Instruction-tuned ~3B model that follows "reply with the label only"; a different family from Gemma at a similar size. |
| Qwen2.5 7B | `qwen2.5:7b` | `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` | Medium, 7.6B (Q4_K_M) | Apache-2.0 | Strong instruction following for its size with a permissive licence; the main 7B-class candidate. |
| Llama 3.1 8B | `llama3.1:8b` | `sha256:46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e` | Medium, 8.0B (Q4_K_M) | Llama 3.1 Community License | Widely used 8B reference; pairs with Llama 3.2 3B to isolate parameter count within one family. |

Parameter figures are the upstream values; the exact value on your machine appears in
`ollama show <tag>` (and in the script output below). Licences are the upstream names as
commonly published and **must be confirmed** with `ollama show <tag> --license` before
they are quoted in the report. The machine-readable candidate list is
`app/candidate_models.py`; `tests/test_candidate_models.py` checks it matches this table.

## Selection and CPU compatibility

- **Local and CPU-only.** Every tag is a quantised GGUF model served by Ollama. The
  client sends `num_gpu: 0` on every request, so results do not depend on a GPU.
- **Two size classes** (small 2-4B, medium 7-9B) allow a size-versus-accuracy-versus-latency
  comparison. Two families appear in each class or across classes (Gemma, Llama, Qwen), so
  size and family are not fully confounded.
- **Suitable for classification.** All are general instruction-tuned chat models, which is
  what a prompt-only, no-fine-tuning classifier needs. None is a reasoning ("thinking")
  model, so answers are short and latency is not inflated by hidden reasoning tokens.
- **Memory.** Ollama's own guidance is at least 8 GB of RAM for 7B models. The published
  download sizes for `llama3.2:3b` (2.0 GB), `llama3.1:8b` (4.7 GB) and `gemma2:2b` (1.6 GB)
  are on the Ollama library. Check `ollama list` for the sizes on your machine. The 7-8B
  models will be noticeably slower on CPU.
- **Not evaluated yet.** No accuracy, latency or throughput has been measured. Nothing here
  is a benchmark result. Selection is by size class, family and licence, not by performance.

## Exact model and runtime provenance

### Recording digests

With Ollama running and each candidate pulled (`ollama pull <tag>`):

```text
python scripts/record_model_digests.py --json results/environment/model-provenance-before-tests.json
```

This reads the full `sha256` digest, quantisation, parameter size and licence line from
Ollama's `/api/tags` and `/api/show`, and marks any unpulled tag `NOT PULLED`. Equivalent
manual commands, per model:

```text
ollama list                      # ID column = first 12 hex chars of the digest
ollama show <tag>                # architecture, parameters, quantization
ollama show <tag> --license      # licence text
curl http://localhost:11434/api/tags   # full digest for every pulled model
```

Paste the full digest into the table above (format `sha256:` plus 64 hex characters) and
fill in the run record below. Re-record after any re-pull: a tag can be updated upstream
while its name stays the same, which is why the digest is what identifies the model.
The script refuses to overwrite an existing provenance file. Use a new dated
filename for subsequent captures. Missing candidates produce a nonzero exit.

Official model and licence links are in [references.md](references.md). Statements
about speed and instruction following above are selection hypotheses, pending our
own tests; the 2B candidate has not been measured as the fastest.

**TODO before freezing:** this historical capture uses an Intel i7-10750H and
Ollama 0.34.4, while `prediction_record.md` assumes a Ryzen 7 8845HS and Ollama
0.35.1. The team must select and record the actual test machine/runtime, recheck
digests and confirm CPU inference for every candidate. Preserve this historical
capture and the setup observations already disclosed in the prediction record.

### Run record (to be filled in on the test machine)

| Field | Value |
|---|---|
| Ollama version (`ollama --version`) | 0.34.4 |
| OS and version | Windows 11 Home |
| CPU model and core count | Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz, 6 physical cores / 12 logical processors |
| RAM | 32,514 MB (~32 GB) |
| Date models were pulled | 2026-09-29 (all four candidates pulled) |
| CPU-only confirmed (`ollama ps` shows `100% CPU` during a request) | CONFIRMED for `gemma2:2b`. A direct `/api/generate` request with `"options": {"num_gpu": 0}` (the same request our client sends) showed `ollama ps` reporting `100% CPU` while running, on a machine that otherwise defaults to `100% GPU` (seen with the GPU-default `ollama run gemma2:2b`). Not yet independently re-checked for the other three candidates, but they use the same client code path and the same `num_gpu: 0` option. |
