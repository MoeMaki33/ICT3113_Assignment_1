"""Turn raw JMeter .jtl files into latency / throughput / error metrics (raw files never modified).

Definitions (identical for every run, written to every summary):

- Measured window: [t0 + warm-up, t0 + duration), where t0 is the moment JMeter started the
  arrival schedule (``schedule_start_epoch_ms``, read from jmeter.log by scripts/run_load_test.py),
  else the wrapper's launch time, else the first sample's start when metadata is missing.
  After the schedule, JMeter waits ``drain_s`` with no new arrivals so requests still in flight
  complete instead of being cut off. Warm-up and duration come from the run metadata (defaults 120 s / 720 s).
- Offered rate: samples STARTED in the window / window hours.
- Achieved throughput: SUCCESSFUL samples that COMPLETED in the window / window hours.
- Error rate: failed samples / samples started in the window. A failure is any sample JMeter
  marked unsuccessful: non-201 (/tickets) or non-200 (/search), timeouts, connection errors.
- Latency p50/p95/p99: JMeter ``elapsed`` (send to last byte) of SUCCESSFUL samples started in
  the window, nearest-rank method (same as scripts/ticket_lengths.py), reported in seconds.
- Latency trend: median latency of the last third of the window divided by that of the first
  third, and the least-squares slope of latency against start time. ``growing`` is true when
  the ratio >= 1.5 and the slope is positive: latency did not settle, it kept rising.

Across the runs of one configuration: mean, sample standard deviation, min and max of every
per-run metric, plus p50/p95/p99 pooled over all runs' windowed samples. Runs that did not
complete, or whose ``run-N.reconciliation.json`` (scripts/reconcile_logs.py) says not reconciled
or contaminated, are excluded and listed under problems. Fewer valid runs than expected are
reported as missing; nothing is filled in.

    python -m scripts.process_jmeter_results results/load                     # every configuration
    python -m scripts.process_jmeter_results results/load/qwen2.5_7b/rate-250 # one configuration
    python -m scripts.process_jmeter_results results/load/qwen2.5_7b/rate-250/run-1.jtl
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median, stdev

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.perf_common import nearest_rank, read_jtl, read_json, utc_now, write_json

DEFAULT_WARMUP_S = 120
DEFAULT_DURATION_S = 720
EXPECTED_RUNS = 3
TREND_RATIO = 1.5
METHOD = {
    "window": "[t0 + warmup_s, t0 + duration_s); t0 = JMeter schedule start (jmeter.log)",
    "offered_rate": "samples started in window / window hours",
    "achieved_throughput": "successful samples completed in window / window hours",
    "error_rate": "unsuccessful samples / samples started in window",
    "latency": "JMeter elapsed of successful samples started in window; nearest-rank percentiles; seconds",
    "trend": f"growing = (median last third / median first third >= {TREND_RATIO}) and slope > 0",
}
RUN_METRICS = ("offered_per_hour", "achieved_per_hour", "error_rate", "latency_p50_s", "latency_p95_s",
               "latency_p99_s", "latency_mean_s", "latency_max_s", "trend_ratio")


def _seconds(ms: float) -> float:
    return round(ms / 1000, 3)


def latency_trend(samples: list[dict]) -> dict:
    ordered = sorted(samples, key=lambda s: s["start_ms"])
    if len(ordered) < 6:
        return {"trend_ratio": None, "trend_slope_s_per_min": None, "growing": None}
    third = len(ordered) // 3
    first = median(s["elapsed_ms"] for s in ordered[:third])
    last = median(s["elapsed_ms"] for s in ordered[-third:])
    xs = [(s["start_ms"] - ordered[0]["start_ms"]) / 1000 for s in ordered]
    ys = [s["elapsed_ms"] / 1000 for s in ordered]
    x_bar, y_bar = mean(xs), mean(ys)
    spread = sum((x - x_bar) ** 2 for x in xs)
    slope = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys)) / spread if spread else 0.0
    ratio = last / first if first else None
    return {
        "trend_ratio": round(ratio, 3) if ratio is not None else None,
        "trend_slope_s_per_min": round(slope * 60, 3),
        "growing": bool(ratio is not None and ratio >= TREND_RATIO and slope > 0),
    }


def _error_key(sample: dict) -> str:
    code = sample["response_code"]
    match = re.search(r"([A-Za-z]+(?:Exception|Error))", code + " " + sample["failure_message"])
    if code.isdigit():
        return f"HTTP {code}"
    return match.group(1) if match else (code or "unknown")


def summarise_label(samples: list[dict], window_start: int, window_end: int) -> dict:
    window_h = (window_end - window_start) / 3_600_000
    started = [s for s in samples if window_start <= s["start_ms"] < window_end]
    ok = [s for s in started if s["success"]]
    failed = [s for s in started if not s["success"]]
    completed_ok = [s for s in samples if s["success"] and window_start <= s["end_ms"] < window_end]
    result = {
        "samples_total": len(samples),
        "samples_in_window": len(started),
        "successful_in_window": len(ok),
        "failed_in_window": len(failed),
        "offered_per_hour": round(len(started) / window_h, 2),
        "achieved_per_hour": round(len(completed_ok) / window_h, 2),
        "error_rate": round(len(failed) / len(started), 4) if started else None,
        "errors_by_type": dict(Counter(_error_key(s) for s in failed)),
    }
    if ok:
        values = sorted(s["elapsed_ms"] for s in ok)
        result.update({
            "latency_p50_s": _seconds(nearest_rank(values, 50)),
            "latency_p95_s": _seconds(nearest_rank(values, 95)),
            "latency_p99_s": _seconds(nearest_rank(values, 99)),
            "latency_mean_s": _seconds(mean(values)),
            "latency_max_s": _seconds(values[-1]),
        })
    else:
        result.update(dict.fromkeys(("latency_p50_s", "latency_p95_s", "latency_p99_s",
                                     "latency_mean_s", "latency_max_s")))
    result.update(latency_trend(ok))
    return result


def summarise_run(jtl: Path, metadata: dict | None = None) -> dict:
    metadata = metadata if metadata is not None else (read_json(jtl.with_suffix(".json")) or {})
    samples = read_jtl(jtl)
    if not samples:
        raise ValueError(f"{jtl} contains no samples")
    warmup = int(metadata.get("warmup_s", DEFAULT_WARMUP_S))
    duration = int(metadata.get("duration_s", DEFAULT_DURATION_S))
    t0 = int(metadata.get("schedule_start_epoch_ms") or metadata.get("started_epoch_ms")
             or min(s["start_ms"] for s in samples))
    window_start, window_end = t0 + warmup * 1000, t0 + duration * 1000
    labels = {}
    for label in sorted({s["label"] for s in samples}):
        labels[label] = summarise_label([s for s in samples if s["label"] == label], window_start, window_end)
    return {
        "jtl": jtl.as_posix(),
        "run": metadata.get("run"),
        "model": metadata.get("model"),
        "official": metadata.get("official"),
        "kind": metadata.get("kind"),
        "offered_rate_setting_per_hour": metadata.get("rate_per_hour"),
        "search_rate_setting_per_hour": metadata.get("search_rate_per_hour"),
        "status": metadata.get("status", "unknown (no metadata)"),
        "warmup_s": warmup, "duration_s": duration,
        "window_start_epoch_ms": window_start, "window_end_epoch_ms": window_end,
        "window_minutes": round((window_end - window_start) / 60000, 2),
        "labels": labels,
    }


def _stats(values: list[float]) -> dict:
    values = [v for v in values if v is not None]
    if not values:
        return {"mean": None, "sd": None, "min": None, "max": None, "n": 0}
    return {"mean": round(mean(values), 4), "sd": round(stdev(values), 4) if len(values) > 1 else None,
            "min": min(values), "max": max(values), "n": len(values)}


def summarise_config(directory: Path, expected_runs: int = EXPECTED_RUNS) -> dict:
    runs, problems, used = [], [], set()
    found = {int(m.group(1)) for p in directory.glob("run-*.jtl") if (m := re.fullmatch(r"run-(\d+)\.jtl", p.name))}
    for number in sorted(found):
        jtl = directory / f"run-{number}.jtl"
        metadata = read_json(jtl.with_suffix(".json"))
        if metadata is None:
            problems.append(f"run-{number}: metadata JSON missing (window falls back to first sample)")
        elif metadata.get("status") != "completed":
            problems.append(f"run-{number}: status {metadata.get('status')!r}; excluded")
            continue
        reconciliation = read_json(directory / f"run-{number}.reconciliation.json")
        if reconciliation is None:
            problems.append(f"run-{number}: not reconciled with the service log yet")
        elif not reconciliation.get("reconciled") or reconciliation.get("contaminated"):
            problems.append(f"run-{number}: reconciliation failed (reconciled={reconciliation.get('reconciled')}, "
                            f"contaminated={reconciliation.get('contaminated')}); excluded, kept as evidence")
            continue
        try:
            runs.append(summarise_run(jtl, metadata))
            used.add(number)
        except ValueError as exc:
            problems.append(f"run-{number}: {exc}; excluded")
    # A replacement run (e.g. run-4 after a contaminated run-2) counts towards the expected number.
    shortfall = max(0, expected_runs - len(used))
    missing = [f"run-{n}" for n in range(1, expected_runs + len(found) + 1) if n not in used][:shortfall]
    aggregate = {}
    for label in sorted({label for r in runs for label in r["labels"]}):
        per_run = [r["labels"][label] for r in runs if label in r["labels"]]
        aggregate[label] = {metric: _stats([p.get(metric) for p in per_run]) for metric in RUN_METRICS}
        aggregate[label]["runs_with_growing_latency"] = sum(1 for p in per_run if p.get("growing"))
        pooled = []
        for r in runs:
            jtl_samples = [s for s in read_jtl(Path(r["jtl"])) if s["label"] == label and s["success"]
                           and r["window_start_epoch_ms"] <= s["start_ms"] < r["window_end_epoch_ms"]]
            pooled += [s["elapsed_ms"] for s in jtl_samples]
        pooled.sort()
        aggregate[label]["pooled"] = {
            "samples": len(pooled),
            **({f"latency_p{p}_s": _seconds(nearest_rank(pooled, p)) for p in (50, 95, 99)} if pooled else {}),
        }
    first = runs[0] if runs else {}
    return {
        "configuration": directory.as_posix(),
        "model": first.get("model"), "kind": first.get("kind"),
        "official": all(r.get("official") for r in runs) if runs else None,
        "rate_per_hour": first.get("offered_rate_setting_per_hour"),
        "search_rate_per_hour": first.get("search_rate_setting_per_hour"),
        "expected_runs": expected_runs, "completed_runs": len(runs),
        "missing_runs": missing, "problems": problems,
        "generated_utc": utc_now(), "method": METHOD,
        "runs": runs, "aggregate": aggregate,
    }


def _fmt(value) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


RUN_COLUMNS = ("model", "official", "rate_setting_per_hour", "search_setting_per_hour", "run", "label",
               "samples_in_window", "offered_per_hour", "achieved_per_hour", "error_rate",
               "latency_p50_s", "latency_p95_s", "latency_p99_s", "latency_mean_s", "latency_max_s",
               "trend_ratio", "trend_slope_s_per_min", "growing", "errors_by_type", "jtl")
SUMMARY_COLUMNS = ("model", "official", "rate_setting_per_hour", "search_setting_per_hour", "label",
                   "completed_runs", "missing_runs",
                   *(f"{m}_{s}" for m in ("offered_per_hour", "achieved_per_hour", "error_rate",
                                          "latency_p50_s", "latency_p95_s", "latency_p99_s")
                     for s in ("mean", "sd", "min", "max")),
                   "pooled_samples", "pooled_p50_s", "pooled_p95_s", "pooled_p99_s",
                   "runs_with_growing_latency", "configuration")


def run_rows(summary: dict) -> list[dict]:
    rows = []
    for run in summary["runs"]:
        for label, metrics in run["labels"].items():
            rows.append({
                "model": run["model"], "official": run["official"],
                "rate_setting_per_hour": run["offered_rate_setting_per_hour"],
                "search_setting_per_hour": run["search_rate_setting_per_hour"],
                "run": run["run"], "label": label, "jtl": run["jtl"],
                **{c: metrics.get(c) for c in RUN_COLUMNS if c in metrics},
                "errors_by_type": json.dumps(metrics["errors_by_type"], sort_keys=True),
            })
    return rows


def summary_rows(summary: dict) -> list[dict]:
    rows = []
    for label, agg in summary["aggregate"].items():
        row = {"model": summary["model"], "official": summary["official"],
               "rate_setting_per_hour": summary["rate_per_hour"],
               "search_setting_per_hour": summary["search_rate_per_hour"], "label": label,
               "completed_runs": summary["completed_runs"],
               "missing_runs": " ".join(summary["missing_runs"]),
               "pooled_samples": agg["pooled"]["samples"],
               "pooled_p50_s": agg["pooled"].get("latency_p50_s"),
               "pooled_p95_s": agg["pooled"].get("latency_p95_s"),
               "pooled_p99_s": agg["pooled"].get("latency_p99_s"),
               "runs_with_growing_latency": agg["runs_with_growing_latency"],
               "configuration": summary["configuration"]}
        for metric in ("offered_per_hour", "achieved_per_hour", "error_rate",
                       "latency_p50_s", "latency_p95_s", "latency_p99_s"):
            for stat in ("mean", "sd", "min", "max"):
                row[f"{metric}_{stat}"] = agg[metric][stat]
        rows.append(row)
    if not rows:  # still show the configuration, with its missing runs
        rows.append({"model": summary["model"], "rate_setting_per_hour": summary["rate_per_hour"],
                     "completed_runs": 0, "missing_runs": " ".join(summary["missing_runs"]),
                     "configuration": summary["configuration"]})
    return rows


def write_csv(path: Path, rows: list[dict], columns: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict]) -> str:
    lines = ["| Model | Official | Tickets/h set | Searches/h set | Endpoint | Runs | Missing | Offered/h (mean) "
             "| Achieved/h (mean ± sd) | Error rate (mean) | p50 s (mean) | p95 s (mean ± sd) | p99 s (mean) "
             "| p99 s pooled | Growing-latency runs |",
             "|" + "---|" * 15]
    for r in rows:
        sd = lambda m: f" ± {_fmt(r.get(m + '_sd'))}" if r.get(m + "_sd") is not None else ""
        error = r.get("error_rate_mean")
        lines.append(" | ".join([
            "", str(r.get("model")), _fmt(r.get("official")), _fmt(r.get("rate_setting_per_hour")),
            _fmt(r.get("search_setting_per_hour")), str(r.get("label", "-")), _fmt(r.get("completed_runs")),
            r.get("missing_runs") or "none", _fmt(r.get("offered_per_hour_mean")),
            _fmt(r.get("achieved_per_hour_mean")) + sd("achieved_per_hour"),
            f"{error:.2%}" if error is not None else "-", _fmt(r.get("latency_p50_s_mean")),
            _fmt(r.get("latency_p95_s_mean")) + sd("latency_p95_s"), _fmt(r.get("latency_p99_s_mean")),
            _fmt(r.get("pooled_p99_s")), _fmt(r.get("runs_with_growing_latency")), "",
        ]).strip())
    return "\n".join(lines) + "\n"


def write_config_outputs(summary: dict, directory: Path) -> None:
    write_json(directory / "summary.json", summary)
    write_csv(directory / "runs.csv", run_rows(summary), RUN_COLUMNS)
    write_csv(directory / "summary.csv", summary_rows(summary), SUMMARY_COLUMNS)
    note = "" if summary["official"] else "\n**NOT OFFICIAL EVIDENCE** (smoke run or freeze gate not met).\n"
    problems = "".join(f"- {p}\n" for p in summary["problems"]) or "- none\n"
    (directory / "summary.md").write_text(
        f"# {summary['configuration']}\n{note}\nGenerated {summary['generated_utc']} by "
        f"scripts/process_jmeter_results.py from the raw .jtl files in this folder.\n\n"
        + markdown_table(summary_rows(summary)) + f"\nProblems:\n{problems}", encoding="utf-8")


def config_dirs(root: Path) -> list[Path]:
    return sorted({p.parent for p in root.rglob("run-*.jtl")})


def process(target: Path, expected_runs: int = EXPECTED_RUNS) -> dict:
    if target.is_file():
        return summarise_run(target)
    dirs = [target] if any(target.glob("run-*.jtl")) else config_dirs(target)
    if not dirs:
        raise SystemExit(f"No run-*.jtl files under {target}; nothing to process (no results invented).")
    summaries = []
    for directory in dirs:
        summary = summarise_config(directory, expected_runs)
        write_config_outputs(summary, directory)
        summaries.append(summary)
    if len(dirs) > 1 or target not in dirs:
        rows = [row for s in summaries for row in summary_rows(s)]
        write_csv(target / "summary_all.csv", rows, SUMMARY_COLUMNS)
        write_csv(target / "runs_all.csv", [row for s in summaries for row in run_rows(s)], RUN_COLUMNS)
        (target / "summary_all.md").write_text(
            f"# All configurations under {target.as_posix()}\n\nGenerated {utc_now()} from raw .jtl files. "
            "Rows marked Official = False are not evidence.\n\n" + markdown_table(rows), encoding="utf-8")
    return {"configurations": [s["configuration"] for s in summaries]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", type=Path, help="A run-N.jtl, a configuration folder, or a results root")
    parser.add_argument("--expected-runs", type=int, default=EXPECTED_RUNS)
    args = parser.parse_args()
    print(json.dumps(process(args.target, args.expected_runs), indent=2))
