# References and evidence sources

Links checked on 2026-10-07. These are source references, not measurements of
our service. Archive the exact model licence text and runtime versions on the
formal test machine; library tags and upstream pages can change.

| Subject | Primary source | Repository use |
|---|---|---|
| Consumer Complaint Database | [CFPB database](https://www.consumerfinance.gov/data-research/consumer-complaints/) | Origin of complaint narratives; the course extract is a separate artifact |
| Course extract | `data/ict3113_tickets.csv` | Team 7 rows 7000-7999; TODO: record the exact xSiTe release/file identifier and course row-allocation instructions |
| Workload volume, 2024 H2 | [FCA aggregate complaints data](https://www.fca.org.uk/data/complaints-data/aggregate-complaints-data-2024-h2) | Banking/credit-card volume used in `workload_model.md`; published 29 April 2025, page updated 13 January 2026 |
| Submission channel and complaint mix | [CFPB 2024 Consumer Response report](https://files.consumerfinance.gov/f/documents/cfpb_cr-annual-report_2025-05.pdf) | Context for arrival assumptions; PDF pages 5 and 3 respectively |
| Ollama generation API | [Ollama API](https://docs.ollama.com/api/generate) | Blocking `/api/generate` call, options and response format |
| Ollama runtime/source | [Ollama repository](https://github.com/ollama/ollama) | TODO: record release/commit and host runtime used for formal testing |
| Gemma 2 | [Ollama model library](https://ollama.com/library/gemma2) | Exact candidate `gemma2:2b` |
| Gemma licence | [Google Gemma Terms of Use](https://ai.google.dev/gemma/terms) | Confirm against `ollama show gemma2:2b --license` |
| Llama 3.2 | [Ollama model library](https://ollama.com/library/llama3.2) | Exact candidate `llama3.2:3b` |
| Llama 3.2 licence | [Meta licence](https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE) | Confirm against the pulled model's licence |
| Qwen2.5 | [Ollama model library](https://ollama.com/library/qwen2.5) | Exact candidate `qwen2.5:7b` |
| Qwen2.5 7B licence | [Official Qwen model licence](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/blob/main/LICENSE) | Apache-2.0 for this candidate; do not generalise to every Qwen variant |
| Llama 3.1 | [Ollama model library](https://ollama.com/library/llama3.1) | Exact candidate `llama3.1:8b` |
| Llama 3.1 licence | [Meta licence](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE) | Confirm against the pulled model's licence |
| Open-loop JMeter traffic | [Apache component reference](https://jmeter.apache.org/usermanual/component_reference.html#Open_Model_Thread_Group) | Open Model Thread Group schedules and seeded random arrivals |
| JMeter installation | [Apache downloads](https://jmeter.apache.org/download_jmeter.cgi) | TODO: archive actual distribution filename, version and verified SHA-512 |

The FCA figure and CFPB submission statistics cited in the workload document
were checked against these sources during the completion audit. The estimates
in section 3 of that document remain team assumptions, including market share,
daily patterns, staffing and search rates. No public source validates them.

Agreement is reproduced by `scripts.validate_golden_set` from the two human
sheets; it is not model accuracy. Token lengths use a characters/4 heuristic,
not an observed tokenizer count. Model speed and accuracy claims remain
predictions until the team's own measurements exist.
