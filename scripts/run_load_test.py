"""Run ONE open-loop JMeter load test against the Ticket Triage Service.

Run this on the LOAD-GENERATOR machine (never on the service/Ollama machine). Every run
writes, and never overwrites:

    results/load/<model-dir>/rate-<X>[_search-<Y>]/run-<N>.jtl    raw JMeter samples
    results/load/<model-dir>/rate-<X>[_search-<Y>]/run-<N>.json   run metadata
    results/load/<model-dir>/rate-<X>[_search-<Y>]/run-<N>.jmeter.log

Official runs require the freeze gate (golden set + prediction record committed and the
record no longer DRAFT). ``--smoke`` skips the gate for tooling checks only and writes under
``results/smoke/`` instead, so smoke traffic can never be mistaken for evidence.

The service's model is set by OLLAMA_MODEL on the service machine; ``--model`` must name the
same exact tag. scripts/reconcile_logs.py verifies it against the service log afterwards.

    python -m scripts.run_load_test --model qwen2.5:7b --rate 250 --host 192.168.1.20
    python -m scripts.run_load_test --model qwen2.5:7b --rate 250 --search-rate 450 --host ...
"""
import argparse
import math
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from scripts.perf_common import (
    ROOT, config_dir_name, freeze_gate_problems, git_info, model_dir, next_run_number,
    read_jtl, read_json, sha256_file, utc_now, write_json,
)

PLAN = ROOT / "jmeter" / "ticket_load_test.jmx"
PROPERTIES = ROOT / "jmeter" / "results.properties"
NARRATIVES = ROOT / "jmeter" / "data" / "team_narratives.tsv"
SEARCH_TERMS = ROOT / "jmeter" / "data" / "search_terms.txt"
DEFAULT_DURATION_S = 720   # 2 min warm-up + 10 min measured window
DEFAULT_WARMUP_S = 120
DEFAULT_TIMEOUT_MS = 180_000


def find_jmeter(explicit: str | None) -> str:
    candidate = explicit or os.getenv("JMETER_BIN") or "jmeter"
    found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
    if not found:
        raise SystemExit(f"JMeter not found ({candidate}). Install JMeter 5.6+ or pass --jmeter / set JMETER_BIN.")
    return found


def output_dir(results_root: Path, kind: str, model: str, rate: float, search_rate: float, smoke: bool) -> Path:
    base = results_root / "smoke" / kind if smoke else results_root / kind
    return base / model_dir(model) / config_dir_name(rate, search_rate)


def search_schedule(search_rate: float, duration_s: int, drain_s: int) -> str:
    # No spaces, so the -J argument needs no quoting through jmeter.bat on Windows.
    if search_rate <= 0:
        return "pause(1s)"  # rate(0/hour) would make JMeter wait forever for an arrival
    return f"rate({search_rate:g}/hour)random_arrivals({duration_s}s)pause({drain_s}s)"


def build_command(jmeter: str, jtl: Path, log: Path, props: dict[str, object]) -> list[str]:
    command = [jmeter, "-n", "-t", str(PLAN), "-q", str(PROPERTIES), "-l", str(jtl), "-j", str(log)]
    command += [f"-J{key}={value}" for key, value in props.items()]
    return command


def preflight(base_url: str) -> tuple[str | None, dict]:
    """One GET /stats so a dead service is caught before a long run.

    Returns the response's X-Request-ID (the service logs this request too; reconciliation
    accounts for it through the run metadata) and the per-category ticket counts, because
    GET /search latency depends on how many tickets are already stored.
    """
    try:
        response = httpx.get(f"{base_url}/stats", timeout=10)
    except httpx.HTTPError as exc:
        raise SystemExit(f"Service not reachable at {base_url}: {type(exc).__name__}") from exc
    if response.status_code != 200:
        raise SystemExit(f"Service preflight GET /stats returned HTTP {response.status_code}")
    return response.headers.get("x-request-id"), response.json()


_STARTED_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}) .*All thread groups have been started", re.M)


def schedule_start_ms(jmeter_log: Path) -> int | None:
    """Epoch ms at which JMeter started the arrival schedules (jmeter.log is in local time)."""
    if not jmeter_log.is_file():
        return None
    match = _STARTED_RE.search(jmeter_log.read_text(encoding="utf-8", errors="replace"))
    if not match:
        return None
    return int(datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f").timestamp() * 1000)


def run_once(*, model: str, rate: float, duration_s: int = DEFAULT_DURATION_S,
             warmup_s: int = DEFAULT_WARMUP_S, search_rate: float = 0, kind: str = "load",
             run: int | None = None, host: str = "localhost", port: int = 8000,
             protocol: str = "http", seed: int | None = None, timeout_ms: int = DEFAULT_TIMEOUT_MS,
             jmeter: str | None = None, smoke: bool = False, results_root: Path = ROOT / "results",
             skip_preflight: bool = False, notes: str = "", out_dir: Path | None = None) -> Path:
    """Run JMeter once and return the path of the run metadata JSON."""
    if rate <= 0 or duration_s <= 0 or not 0 <= warmup_s < duration_s or search_rate < 0:
        raise ValueError("Need rate > 0, duration > 0, 0 <= warm-up < duration and search rate >= 0")
    problems = freeze_gate_problems()
    if problems and not smoke:
        raise SystemExit("Official benchmarking is NOT allowed yet:\n  - " + "\n  - ".join(problems)
                         + "\nUse --smoke for a tooling check (results go to results/smoke/).")
    for required in (PLAN, PROPERTIES, NARRATIVES, SEARCH_TERMS):
        if not required.is_file():
            raise SystemExit(f"Missing {required}; run: python -m scripts.prepare_jmeter_data")
    jmeter_bin = find_jmeter(jmeter)
    directory = out_dir or output_dir(results_root, kind, model, rate, search_rate, smoke)
    directory.mkdir(parents=True, exist_ok=True)
    run = run or next_run_number(directory)
    jtl, log, meta_path = (directory / f"run-{run}{ext}" for ext in (".jtl", ".jmeter.log", ".json"))
    if jtl.exists() or meta_path.exists():
        raise SystemExit(f"{jtl} already exists; raw results are never overwritten. Use another --run.")
    seed = seed if seed is not None else 3113 * 100 + run
    drain_s = math.ceil(timeout_ms / 1000) + 10
    props = {
        "host": host, "port": port, "protocol": protocol, "rate": f"{rate:g}",
        "duration_s": duration_s, "drain_s": drain_s, "search_schedule": search_schedule(search_rate, duration_s, drain_s),
        "seed": seed,
        "search_seed": seed + 50, "data_file": NARRATIVES, "search_file": SEARCH_TERMS,
        "timeout_ms": timeout_ms,
    }
    base_url = f"{protocol}://{host}:{port}"
    preflight_id, stored = (None, {}) if skip_preflight else preflight(base_url)
    command = build_command(jmeter_bin, jtl, log, props)
    metadata = {
        "kind": kind, "official": not smoke, "freeze_gate_problems": problems,
        "model": model, "model_dir": model_dir(model), "target": base_url,
        "rate_per_hour": rate, "search_rate_per_hour": search_rate,
        "duration_s": duration_s, "warmup_s": warmup_s, "drain_s": drain_s, "run": run, "seed": seed,
        "preflight_request_id": preflight_id, "stats_before": stored,
        "tickets_in_database_before": sum(stored.values()) if stored else None,
        "timeout_ms": timeout_ms, "arrivals": "open model, random (Poisson) arrivals",
        "jmeter_command": [str(c) for c in command],
        "plan_sha256": sha256_file(PLAN), "properties_sha256": sha256_file(PROPERTIES),
        "narratives_sha256": sha256_file(NARRATIVES), "search_terms_sha256": sha256_file(SEARCH_TERMS),
        "git": git_info(), "notes": notes, "status": "running",
        "started_utc": utc_now(), "started_epoch_ms": int(time.time() * 1000),
        "jtl": jtl.name, "jmeter_log": log.name,
    }
    write_json(meta_path, metadata)
    print(f"[{metadata['started_utc']}] {kind} run {run}: {model} at {rate:g}/h"
          + (f" + {search_rate:g} searches/h" if search_rate else "") + f" for {duration_s} s -> {jtl}")
    try:
        exit_code = subprocess.run(command).returncode
    except KeyboardInterrupt:
        metadata.update(status="interrupted", finished_utc=utc_now(), schedule_start_epoch_ms=schedule_start_ms(log))
        write_json(meta_path, metadata)
        raise SystemExit(f"Interrupted; partial results kept and marked in {meta_path}")
    metadata.update(finished_utc=utc_now(), finished_epoch_ms=int(time.time() * 1000), exit_code=exit_code,
                    schedule_start_epoch_ms=schedule_start_ms(log))
    if exit_code == 0 and jtl.is_file():
        samples = read_jtl(jtl)
        metadata.update(status="completed", samples=len(samples),
                        samples_without_request_id=sum(1 for s in samples if not s["request_id"]))
    else:
        metadata["status"] = "failed"
    write_json(meta_path, metadata)
    print(f"Run {metadata['status']} (exit {exit_code}); metadata: {meta_path}")
    return meta_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", required=True, help="Exact Ollama tag the service is running")
    parser.add_argument("--rate", type=float, required=True, help="POST /tickets arrivals per hour")
    parser.add_argument("--search-rate", type=float, default=0, help="GET /search arrivals per hour (0 = off)")
    parser.add_argument("--duration-s", type=int, default=DEFAULT_DURATION_S)
    parser.add_argument("--warmup-s", type=int, default=DEFAULT_WARMUP_S,
                        help="Excluded from the measured window when processing")
    parser.add_argument("--run", type=int, help="Run number (default: next free number)")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--protocol", default="http")
    parser.add_argument("--seed", type=int, help="Arrival seed (default 311300 + run)")
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)
    parser.add_argument("--jmeter", help="Path to the jmeter executable (or set JMETER_BIN)")
    parser.add_argument("--results-root", type=Path, default=ROOT / "results")
    parser.add_argument("--smoke", action="store_true", help="Tooling check only; not evidence")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    meta = run_once(model=args.model, rate=args.rate, duration_s=args.duration_s, warmup_s=args.warmup_s,
                    search_rate=args.search_rate, run=args.run, host=args.host, port=args.port,
                    protocol=args.protocol, seed=args.seed, timeout_ms=args.timeout_ms,
                    jmeter=args.jmeter, smoke=args.smoke, results_root=args.results_root,
                    skip_preflight=args.skip_preflight, notes=args.notes)
    if read_json(meta)["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
