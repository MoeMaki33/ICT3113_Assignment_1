# Test environment record

Owner: Person 5. Status: **TEMPLATE: not yet filled in.** No official test has been run.

Fill this in **before the first official benchmark**, on the machines that will actually run the
tests. Hardware and software values come from `scripts/record_test_environment.py`, run on each
machine. Its JSON output under `results/environment/` is the raw evidence, and this page summarises
it. Network and manual items are filled in by hand. Leave a field blank rather than guessing.

```powershell
.\.venv\Scripts\python.exe -m scripts.record_test_environment --role service   # on the service + Ollama machine
.\.venv\Scripts\python.exe -m scripts.record_test_environment --role loadgen   # on the JMeter machine
```

## 1. Summary

| Machine | CPU | Cores / threads | RAM | OS | Software |
|---|---|---|---|---|---|
| Service machine (API in Docker) | | | | | Docker: · Compose: · Python (container): 3.12 |
| Ollama machine (same as service) | | | | | Ollama: · `OLLAMA_NUM_PARALLEL`: · `OLLAMA_KEEP_ALIVE`: |
| Load generator | | | | | JMeter: 5.6.3 · Java: · Python: |
| Network | Connection type: · Service IP: · Load generator IP: · Link speed: | | | | Clock sync method: |

## 2. Details

### 2.1 Service machine

| Item | Value | Source |
|---|---|---|
| Hostname | | `results/environment/service-<host>.json` |
| CPU model | | same |
| Physical cores / logical CPUs | | same |
| RAM (GB) | | same |
| OS and build | | same |
| Docker / Docker Compose | | same |
| Docker resources (Settings → Resources / WSL 2 limits) | | manual |
| Power plan / plugged in | | manual (use "Best performance", on mains power) |
| Other running applications | | manual (close everything non-essential) |

### 2.2 Ollama (on the service machine)

| Item | Value | Source |
|---|---|---|
| Ollama version | | `ollama --version` (in the JSON) |
| Models and digests | | `results/model_provenance.json`; must match `docs/models.md` |
| CPU-only confirmed | | `ollama ps` during inference shows `100% CPU` (screenshot or text under `results/environment/`) |
| `OLLAMA_NUM_PARALLEL` | | environment of `ollama serve` |
| `OLLAMA_KEEP_ALIVE` | | default unless recorded otherwise |
| Service timeout `OLLAMA_TIMEOUT_SECONDS` | 120 | `.env` |

### 2.3 Load generator

| Item | Value | Source |
|---|---|---|
| Hostname | | `results/environment/loadgen-<host>.json` |
| CPU / cores / RAM / OS | | same |
| Java version | | same |
| JMeter version and SHA-512 verified | 5.6.3 / yes-no | same + manual |
| Repository commit | | `git rev-parse HEAD` (in the JSON) |
| `jmeter/data/manifest.json` hashes unchanged | yes-no | `git status jmeter/data` |

### 2.4 Network

| Item | Value |
|---|---|
| Connection (Ethernet / Wi-Fi, switch/router) | |
| Service machine IP : port | `:8000` |
| Load generator IP | |
| Link speed (both ends) | |
| Round-trip time (`ping` from load generator, 20 pings, avg) | |
| Firewall rule (port 8000, scope) | |
| Clock synchronisation (method, offset before testing) | |

## 3. Confirmation that the load generator is separate

| Check | Value |
|---|---|
| Load generator hostname ≠ service hostname | |
| JMeter `--host` used in runs | (the service IP, never `localhost`) |
