# Official test environment record

Owner: Person 5. Status: **BENCHMARK ARTIFACTS COMPLETE; RUNTIME RESOURCE EVIDENCE INCOMPLETE**.
The setup observations below were recorded before formal benchmarking.
As of the 2026-10-08 repository verification, 36 load runs, four completed
accuracy runs and two reconciled stress steps exist; see
[completion_audit.md](completion_audit.md). No new environment capture was
made during the final documentation analysis. `results/environment/`, CPU/memory
observations, Docker stats and per-model runtime processor captures are absent.
CPU-only remains configured rather than independently runtime-verified.

### PC1 environment update sign-off

The user approved this PC1 documentation update on 2026-10-07 with the
instruction "sign off". This records approval of the official i7-10510U
PC1 hardware and machine-role revision. PC2 hardware/software observations and
LAN connectivity were subsequently supplied by the user and recorded below.
The final prediction/requirements freeze is recorded in Git at
`2db5306d41a5b8dee9812cec005c4145dfd734fe`; remaining runtime evidence is separate.

## 1. Official machine roles

PC1 is the System Under Test: this laptop, configured to run Docker, FastAPI,
SQLite and host Ollama with CPU-only LLM inference. PC2 is a **different physical
desktop** that will run Apache JMeter over the local network. The user confirms
these are separate physical machines; verified PC2 details and session LAN
observations are recorded in sections 4 and 5. A VM/container on PC1 does not
fulfil the separate-machine role. The initial setup traffic was smoke/readiness testing. Subsequent formal
load and stress artifacts are now available under `results/`; no smoke-test
measurements are used in the final analysis.

## 2. Official PC1 hardware

These are the **user-supplied verified hardware observations** for the laptop.
They were collected using the CIM commands below, not inferred from historical
model provenance. Do not replace them with the former Ryzen draft assumptions
or the i7-10750H model-inspection machine.

| Item | Official PC1 value | Source |
|---|---|---|
| Role | System Under Test / Service + Ollama | User's pre-benchmark machine-role decision |
| CPU | Intel(R) Core(TM) i7-10510U CPU @ 1.80GHz | User-verified `Get-CimInstance Win32_Processor` |
| Physical CPU cores | 4 | Same |
| Logical processors | 8 | Same |
| Installed/usable RAM | 15.8 GB | User-verified `Get-CimInstance Win32_ComputerSystem` |
| Operating system | Microsoft Windows 11 Home | User-verified `Get-CimInstance Win32_OperatingSystem` |
| OS version | 10.0.26200 | Same |
| Architecture | 64-bit | Same |
| Intended workload | Docker + FastAPI + SQLite + Ollama | Baseline architecture; service runtime not verified in this update |
| Inference configuration | CPU only (`options.num_gpu: 0`) | `app/services/ollama_client.py`; runtime verification pending |
| Hostname | TO BE RECORDED | Future PC1 environment capture |

Hardware collection commands supplied by the user:

```powershell
Get-CimInstance Win32_Processor |
    Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
Get-CimInstance Win32_ComputerSystem |
    Select-Object @{Name="RAM_GB";Expression={[math]::Round($_.TotalPhysicalMemory/1GB,2)}}
Get-CimInstance Win32_OperatingSystem |
    Select-Object Caption, Version, OSArchitecture
```

## 3. PC1 software version checks

The following commands were executed in the current PC1 shell for this
pre-benchmark documentation update on 2026-10-07. These are CLI observations,
not proof that the service/container or Ollama is running.

| Command | Actual output / verification status |
|---|---|
| `docker --version` | `Docker version 29.4.3, build 055a478` |
| `docker compose version` | `Docker Compose version v5.1.3` |
| `ollama --version` | Unavailable/not verified: PowerShell did not recognise `ollama` on the current PATH; version TO BE RECORDED |
| `python --version` | `Python 3.7.6` (default PATH interpreter; not the project's Python 3.12 environment) |
| `.\.venv\Scripts\python.exe --version` | `Python 3.12.14` (project host virtual environment) |
| Container Python / installed packages | TO BE RECORDED; the Dockerfile targets Python 3.12, but the container version was not measured |

Both Docker version commands also emitted an access-denied warning for
`C:\Users\Owen\.docker\config.json` in the sandbox. Their version strings were
returned, but daemon availability, image build and container operation were not
verified by those commands. Use the project `.venv` interpreter for all scripts
and automated tests, rather than the default PATH Python 3.7.6.

| Remaining PC1 runtime item | Value / evidence needed |
|---|---|
| Ollama version / executable availability | TO BE RECORDED; restore/install or locate the actual executable before runtime checks |
| Candidate availability and actual PC1 digests | TO BE RECORDED; fresh `/api/tags` and `/api/show` capture compared with historical provenance |
| Runtime CPU-only verification | TO BE RECORDED for **each** of the four candidates; save `ollama ps` during inference |
| `OLLAMA_NUM_PARALLEL` | 1 per user-confirmed official PC1 configuration; server-process evidence to be captured |
| `OLLAMA_KEEP_ALIVE` | TO BE RECORDED from the actual server configuration |
| `OLLAMA_TIMEOUT_SECONDS` | Intended value 120 seconds from repository configuration; active runtime setting TO BE RECORDED |
| Docker resources / WSL 2 limits | TO BE RECORDED |
| Power plan / mains power | TO BE RECORDED |
| Other applications / background load | TO BE RECORDED |
| Model runtime memory and measured CPU utilisation | TO BE RECORDED; not measured in this documentation task |

The application sends `num_gpu: 0` for every blocking generation request.
`docker-compose.yml` has no GPU device/dependency configuration and mounts data
and logs persistently. This establishes **configured for CPU-only**, not
**runtime verified CPU-only**. Historical gemma2 CPU verification on the
provenance machine does not verify any candidate on PC1.

## 4. Official PC2 / separate physical load generator

PC2 is a different desktop. Do not assign PC1's i7-10510U specifications to PC2.
JMeter 5.6.3 was previously successfully tested on the i7-10510U laptop before
roles changed, according to the user. This is historical PC1 tooling information;
it did not establish an installed or verified JMeter version on PC2. The user
has now supplied the verified PC2 specifications below. These observations
were not independently remeasured by this documentation update.

| PC2 item | Value |
|---|---|
| Machine role | Separate physical desktop / Apache JMeter load generator |
| Hostname | TO BE RECORDED |
| CPU | AMD Ryzen 7 5800X3D (user-verified) |
| Physical cores / logical processors | 8 / 16 (user-verified) |
| RAM | 31.93 GB (user-verified) |
| OS / version / architecture | Windows 11 Home / 10.0.26300 / 64-bit (user-verified) |
| Java version | 1.8.0_333 (user-verified) |
| JMeter version | Apache JMeter 5.6.3 (user-verified) |
| JMeter distribution SHA-512 verification | TO BE RECORDED |
| Python version / packages | TO BE RECORDED |
| Network connection | TO BE RECORDED |
| Repository commit | TO BE RECORDED; must match PC1's tested revision |
| Prepared traffic hashes unchanged | TO BE RECORDED from `jmeter/data/manifest.json` and input validation |

## 5. Network and physical separation

| Item | Value |
|---|---|
| PC1 and PC2 are different physical machines | Confirmed by user: laptop PC1 and different desktop PC2 |
| Connection type (Ethernet / Wi-Fi) | TO BE RECORDED |
| Topology / router / switch | TO BE RECORDED |
| PC1 IP and active service port | Test-session LAN address `192.168.1.170`, TCP port 8000 (user observation) |
| PC2 IP | Test-session LAN address `192.168.1.240` (user observation) |
| Link speeds and limitations | TO BE RECORDED |
| PC2-to-PC1 connectivity | PC2 successfully reached PC1 TCP port 8000 (user-confirmed setup connectivity) |
| Round-trip time | TO BE RECORDED; smoke-test measurements are not formal results |
| Firewall rule scope | TO BE RECORDED |
| Clock synchronisation / offset | TO BE RECORDED |
| Hostname separation confirmation | TO BE RECORDED on both machines |

The addresses above apply to the observed setup session. They are not permanent
machine identifiers; record the current addresses again for the formal test session.

## 6. Historical provenance and remaining freeze actions

`docs/models.md` and `results/model_provenance.json` retain the original
2026-09-29 model capture: i7-10750H, approximately 32 GB RAM, Ollama 0.34.4.
That is the **historical model provenance machine**, not the official formal
benchmark PC1. The Ryzen 7 8845HS / 13.8 GB / Ollama 0.35.1 values are
**superseded draft prediction assumptions**, retained as revision context.

The prediction record is frozen and unchanged. The former source-hash blocker
has a committed [provenance review](golden_set_provenance.md): validation passes
with a historical byte-hash warning, while the unavailable original source
bytes and cause remain unknown. Benchmark commits and dirty-worktree flags
are recorded in run metadata; fresh PC1 model digests are absent.

Future environment evidence collection, on the indicated physical machines:

```powershell
# PC1 only, after completing its actual runtime setup:
.\.venv\Scripts\python.exe -m scripts.record_test_environment --role service
# PC2 only, after independently installing/verifying its tooling:
.\.venv\Scripts\python.exe -m scripts.record_test_environment --role loadgen
```

Capture exact container dependencies later with
`docker compose exec api python -m pip freeze`. Follow `test_playbook.md` for
setup, runtime CPU checks and subsequent formal testing only after all
prerequisites pass. No formal accuracy, JMeter load or stress run is authorised
by this documentation update.
