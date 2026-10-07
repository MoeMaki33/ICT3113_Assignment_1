"""Stress test: raise the open-loop ticket arrival rate in steps until the service stops coping.

Goal: the MAXIMUM SUSTAINABLE TICKET ARRIVAL RATE of the baseline for one model, found only
from measurements. Each step is one JMeter run (scripts/run_load_test.py, kind "stress") at a
fixed rate, starting from an idle service. After each step the ticket metrics of the measured
window are checked against the stopping criteria, which are fixed BEFORE the first step and
saved in ``stress_plan.json`` (a resumed test must use the identical plan):

A step is UNSUSTAINABLE if any of these holds (defaults in brackets):
  1. error rate > max_error_rate                                   [5%]
  2. achieved throughput < min_throughput_ratio x offered rate      [0.90]
  3. latency grows continuously over the window (trend ratio >= 1.5 and positive slope)
  4. p95 latency > max_p95_s                                        [120 s, the Ollama timeout]

The test stops at the first unsustainable step. With ``--refine N`` it then bisects N times
between the last sustainable and the first unsustainable rate (rounded to 25/h). The result is
"highest measured sustainable rate" and "lowest measured unsustainable rate": the limit lies
between them. If every step is sustainable, no limit is claimed (raise --rates and continue).

Outputs in results/stress/<model-dir>/: stress_plan.json, rate-<X>/run-1.{jtl,json,jmeter.log},
stress_steps.csv, stress_summary.json, stress_summary.md. Completed steps are reused on resume,
never re-run or overwritten.

    python -m scripts.run_stress_test --model qwen2.5:7b --host <service-ip>
    python -m scripts.run_stress_test --model qwen2.5:7b --host <service-ip> --rates 250,500,750,1000 --refine 2
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.perf_common import ROOT, config_dir_name, model_dir, read_json, utc_now, write_json
from scripts.process_jmeter_results import summarise_run
from scripts.run_load_test import DEFAULT_DURATION_S, DEFAULT_WARMUP_S, run_once

TICKETS = "POST /tickets"
DEFAULT_RATES = (250, 500, 750, 1000, 1500, 2000, 3000)
DEFAULT_CRITERIA = {"max_error_rate": 0.05, "min_throughput_ratio": 0.90, "stop_on_growing_latency": True,
                    "max_p95_s": 120.0}
STEP_COLUMNS = ("order", "rate_setting_per_hour", "offered_per_hour", "achieved_per_hour", "throughput_ratio",
                "error_rate", "latency_p50_s", "latency_p95_s", "latency_p99_s", "trend_ratio",
                "trend_slope_s_per_min", "growing", "errors_by_type", "verdict", "reasons", "official",
                "jtl", "observations")


def evaluate_step(metrics: dict, criteria: dict) -> tuple[bool, list[str]]:
    reasons = []
    error_rate = metrics.get("error_rate")
    if error_rate is None:
        reasons.append("no samples in the measured window")
    elif error_rate > criteria["max_error_rate"]:
        reasons.append(f"error rate {error_rate:.1%} > {criteria['max_error_rate']:.0%}")
    offered = metrics.get("offered_per_hour") or 0
    ratio = metrics["achieved_per_hour"] / offered if offered else 0
    if ratio < criteria["min_throughput_ratio"]:
        reasons.append(f"achieved/offered {ratio:.2f} < {criteria['min_throughput_ratio']}")
    if criteria["stop_on_growing_latency"] and metrics.get("growing"):
        reasons.append(f"latency kept growing (last/first third median x{metrics['trend_ratio']})")
    p95 = metrics.get("latency_p95_s")
    if p95 is not None and p95 > criteria["max_p95_s"]:
        reasons.append(f"p95 {p95} s > {criteria['max_p95_s']} s")
    return not reasons, reasons


def load_or_create_plan(path: Path, plan: dict) -> dict:
    existing = read_json(path)
    if existing is None:
        write_json(path, {**plan, "created_utc": utc_now()})
        return plan
    fixed = {k: v for k, v in existing.items() if k != "created_utc"}
    if fixed != plan:
        raise SystemExit(f"{path} already fixes a different plan:\n{json.dumps(fixed, indent=2)}\n"
                         "Criteria must not change after the stress test started. Resume with the same "
                         "arguments, or document the reason and start a new test with a different --label.")
    return existing


def stress(model: str, rates: list[float], refine: int, criteria: dict, *, duration_s: int, warmup_s: int,
           cooldown_s: int, label: str = "", smoke: bool = False, results_root: Path = ROOT / "results",
           run_kwargs: dict | None = None, sleep=time.sleep) -> dict:
    run_kwargs = run_kwargs or {}
    base = (results_root / "smoke" / "stress" if smoke else results_root / "stress") / model_dir(model)
    if label:
        base = base / label
    plan = {"model": model, "rates_per_hour": rates, "refine_steps": refine, "criteria": criteria,
            "duration_s": duration_s, "warmup_s": warmup_s, "cooldown_s": cooldown_s,
            "timeout_ms": run_kwargs.get("timeout_ms", 180_000),
            "increment_strategy": "listed rates in order until the first unsustainable step, then "
                                  f"{refine} bisection step(s) rounded to 25/h", "official": not smoke}
    base.mkdir(parents=True, exist_ok=True)
    load_or_create_plan(base / "stress_plan.json", plan)
    steps: list[dict] = []
    need_cooldown = False

    def step(rate: float) -> dict:
        nonlocal need_cooldown
        directory = base / config_dir_name(rate)
        meta = read_json(directory / "run-1.json")
        if not (meta and meta.get("status") == "completed"):
            if meta:
                raise SystemExit(f"{directory}/run-1 exists with status {meta.get('status')!r}; inspect it "
                                 "(raw files are never overwritten) and record it before continuing.")
            if need_cooldown:
                print(f"Cooling down {cooldown_s} s so queued requests finish before the next step")
                sleep(cooldown_s)
            run_once(model=model, rate=rate, duration_s=duration_s, warmup_s=warmup_s, kind="stress", run=1,
                     smoke=smoke, results_root=results_root, out_dir=directory, **run_kwargs)
            need_cooldown = True
            meta = read_json(directory / "run-1.json")
            if not meta or meta.get("status") != "completed":
                raise SystemExit(f"JMeter run for {rate:g}/h did not complete; see {directory}")
        summary = summarise_run(directory / "run-1.jtl", meta)
        metrics = summary["labels"].get(TICKETS, {})
        sustainable, reasons = evaluate_step(metrics, criteria) if metrics else (False, ["no ticket samples"])
        offered = metrics.get("offered_per_hour") or 0
        row = {"order": len(steps) + 1, "rate_setting_per_hour": rate, "official": meta.get("official"),
               "jtl": (directory / "run-1.jtl").as_posix(),
               "throughput_ratio": round(metrics.get("achieved_per_hour", 0) / offered, 3) if offered else None,
               **{k: metrics.get(k) for k in STEP_COLUMNS if k in metrics},
               "errors_by_type": json.dumps(metrics.get("errors_by_type", {}), sort_keys=True),
               "verdict": "sustainable" if sustainable else "UNSUSTAINABLE", "reasons": "; ".join(reasons),
               "observations": ""}
        steps.append(row)
        print(f"Step {row['order']}: {rate:g}/h -> {row['verdict']} {row['reasons']}")
        return row

    last_ok, first_bad = None, None
    for rate in rates:
        if step(rate)["verdict"] == "sustainable":
            last_ok = rate
        else:
            first_bad = rate
            break
    if last_ok is not None and first_bad is not None:
        for _ in range(refine):
            mid = round((last_ok + first_bad) / 2 / 25) * 25
            if mid <= last_ok or mid >= first_bad:
                break
            if step(mid)["verdict"] == "sustainable":
                last_ok = mid
            else:
                first_bad = mid
    return write_summary(base, plan, steps, last_ok, first_bad)


def write_summary(base: Path, plan: dict, steps: list[dict], last_ok, first_bad) -> dict:
    with (base / "stress_steps.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STEP_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(steps)
    if first_bad is None:
        conclusion = (f"No unsustainable step up to {max(s['rate_setting_per_hour'] for s in steps):g}/h: "
                      "no limit found yet. Extend --rates and resume.") if steps else "No steps run."
    elif last_ok is None:
        conclusion = (f"Already unsustainable at the first step ({first_bad:g}/h): the limit is below it. "
                      "Start a new test (--label) with lower rates.")
    else:
        conclusion = (f"Highest measured sustainable rate: {last_ok:g} tickets/h. Lowest measured unsustainable "
                      f"rate: {first_bad:g} tickets/h. The limit lies between them.")
    summary = {"plan": plan, "steps": steps, "highest_sustainable_per_hour": last_ok,
               "lowest_unsustainable_per_hour": first_bad, "conclusion": conclusion, "generated_utc": utc_now()}
    write_json(base / "stress_summary.json", summary)
    fmt = lambda v: "-" if v is None else str(v)
    lines = [f"# Stress test: `{plan['model']}`", ""]
    if not plan["official"]:
        lines += ["**NOT OFFICIAL EVIDENCE** (smoke run).", ""]
    lines += [f"**{conclusion}**", "", "Stopping criteria (fixed before the first step): "
              f"error rate > {plan['criteria']['max_error_rate']:.0%}; achieved/offered < "
              f"{plan['criteria']['min_throughput_ratio']}; continuously growing latency; p95 > "
              f"{plan['criteria']['max_p95_s']} s. Each step: {plan['duration_s']} s schedule, first "
              f"{plan['warmup_s']} s excluded, {plan['cooldown_s']} s cool-down between steps.", "",
              "| # | Rate set /h | Offered /h | Achieved /h | Achieved/offered | Error rate | p50 s | p95 s | p99 s "
              "| Trend ratio | Verdict | Reasons |", "|---" * 12 + "|"]
    for s in steps:
        err = s.get("error_rate")
        lines.append(f"| {s['order']} | {s['rate_setting_per_hour']:g} | {fmt(s.get('offered_per_hour'))} | "
                     f"{fmt(s.get('achieved_per_hour'))} | {fmt(s.get('throughput_ratio'))} | "
                     f"{'-' if err is None else f'{err:.1%}'} | {fmt(s.get('latency_p50_s'))} | "
                     f"{fmt(s.get('latency_p95_s'))} | {fmt(s.get('latency_p99_s'))} | {fmt(s.get('trend_ratio'))} | "
                     f"{s['verdict']} | {s['reasons'] or '-'} |")
    lines += ["", "Observations (fill in from the service machine: CPU %, `ollama ps`, memory, log errors):", ""]
    (base / "stress_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(conclusion)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", required=True)
    parser.add_argument("--rates", default=",".join(str(r) for r in DEFAULT_RATES),
                        help="Comma-separated tickets/h, increasing")
    parser.add_argument("--refine", type=int, default=2, help="Bisection steps after the first failure")
    parser.add_argument("--duration-s", type=int, default=DEFAULT_DURATION_S)
    parser.add_argument("--warmup-s", type=int, default=DEFAULT_WARMUP_S)
    parser.add_argument("--cooldown-s", type=int, default=200, help="Idle wait between steps (> Ollama timeout)")
    parser.add_argument("--max-error-rate", type=float, default=DEFAULT_CRITERIA["max_error_rate"])
    parser.add_argument("--min-throughput-ratio", type=float, default=DEFAULT_CRITERIA["min_throughput_ratio"])
    parser.add_argument("--max-p95-s", type=float, default=DEFAULT_CRITERIA["max_p95_s"])
    parser.add_argument("--ignore-latency-trend", action="store_true")
    parser.add_argument("--label", default="", help="Sub-folder for a separate stress test of the same model")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout-ms", type=int, default=180_000, help="HTTP timeout; drain = timeout + 10 s")
    parser.add_argument("--jmeter")
    parser.add_argument("--results-root", type=Path, default=ROOT / "results")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    rates = [float(r) for r in args.rates.split(",") if r.strip()]
    if rates != sorted(rates) or len(set(rates)) != len(rates) or min(rates) <= 0:
        parser.error("--rates must be strictly increasing positive numbers")
    criteria = {"max_error_rate": args.max_error_rate, "min_throughput_ratio": args.min_throughput_ratio,
                "stop_on_growing_latency": not args.ignore_latency_trend, "max_p95_s": args.max_p95_s}
    stress(args.model, rates, args.refine, criteria, duration_s=args.duration_s, warmup_s=args.warmup_s,
           cooldown_s=args.cooldown_s, label=args.label, smoke=args.smoke, results_root=args.results_root,
           run_kwargs={"host": args.host, "port": args.port, "jmeter": args.jmeter,
                       "timeout_ms": args.timeout_ms})


if __name__ == "__main__":
    main()
