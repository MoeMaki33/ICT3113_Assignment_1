"""Reconcile client-side results with the service's request log (inputs are never modified).

Every response from the service carries ``X-Request-ID``; the service writes the same id to
``logs/service.log`` (one JSON line per request, Person 1). JMeter saves the id in the
``request_id`` column of each .jtl; scripts/accuracy_test.py saves it in predictions.csv.

For one run this check reports:

- matched: client samples whose request id has exactly one service-log line;
- status / endpoint / model mismatches between the client record and the log line;
- client samples with NO request id, split into "no HTTP response" (timeout, refused
  connection: the service may still log the request later) and "HTTP response without id"
  (should never happen);
- request ids missing from the log, and duplicate ids in the log;
- extra log lines inside the run's time window that no client sample accounts for. They are
  split into "preflight" (the tools' own requests whose ids are stored in the run metadata:
  the load wrapper's GET /stats, the accuracy test's GET /search model look-up),
  "abandoned by client" (log lines for the endpoint of client samples that got no HTTP
  response, up to that number) and UNEXPLAINED (e.g. development traffic). A run with any
  unexplained line is flagged ``contaminated``: benchmark windows must contain only test traffic;
- timing: client elapsed minus server duration_ms (network + queueing outside the app; a
  negative value beyond 5 ms is flagged), and the clock offset between the two machines.

``reconciled`` is true only if every client sample with an HTTP response matched one log line
with the same endpoint, status and model. The command exits non-zero if any run is not
reconciled or is contaminated. Outputs, next to the client file:

    run-N.reconciliation.json         the report
    run-N.service_log_extract.jsonl   raw log lines for this run (matched + in-window extras)

The service log must be copied from the SERVICE machine (it is not on the load generator);
by default it is looked for as ``run-N.service.log`` next to the .jtl, or pass --service-log.

    python -m scripts.reconcile_logs results/load/qwen2.5_7b/rate-250 --service-log copies/service.log
    python -m scripts.reconcile_logs results/accuracy/qwen2.5_7b/run-1/predictions.csv --service-log ...
"""
import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.perf_common import nearest_rank, read_jtl, read_json, utc_now, write_json

LABEL_ROUTES = {"POST /tickets": ("POST", "/tickets"), "GET /search": ("GET", "/search"),
                "GET /stats": ("GET", "/stats")}
WINDOW_MARGIN_MS = 5_000
NEGATIVE_TOLERANCE_MS = 5


def _epoch_ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


def read_client_samples(path: Path) -> tuple[list[dict], str]:
    """Load a JMeter .jtl or an accuracy predictions.csv into one sample format."""
    with path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle), [])
    if "timeStamp" in header:
        return read_jtl(path), "jmeter"
    if {"request_id", "status_code", "elapsed_ms", "start_epoch_ms"} <= set(header):
        samples = []
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                start, elapsed = int(row["start_epoch_ms"]), int(float(row["elapsed_ms"]))
                samples.append({
                    "start_ms": start, "elapsed_ms": elapsed, "end_ms": start + elapsed,
                    "label": "POST /tickets", "response_code": row["status_code"] or row.get("error", ""),
                    "success": row["status_code"] == "201", "failure_message": row.get("error", ""),
                    "request_id": row["request_id"] or None,
                })
        return samples, "accuracy"
    raise ValueError(f"{path} is neither a JMeter .jtl nor an accuracy predictions.csv")


def read_service_log(paths: list[Path]) -> tuple[list[dict], int]:
    records, malformed = [], 0
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    record["_start_ms"] = _epoch_ms(record["start_time"])
                    record["_raw"] = line.rstrip("\n")
                except (ValueError, KeyError, TypeError):
                    malformed += 1
                    continue
                records.append(record)
    return records, malformed


def _pct(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {"n": len(ordered), "min": round(ordered[0], 1), "p50": round(nearest_rank(ordered, 50), 1),
            "p95": round(nearest_rank(ordered, 95), 1), "max": round(ordered[-1], 1)}


def reconcile(samples: list[dict], log: list[dict], expected_model: str | None,
              preflight_ids: set[str] | frozenset = frozenset()) -> tuple[dict, list[str]]:
    by_id: dict[str, list[dict]] = {}
    for record in log:
        by_id.setdefault(record.get("request_id"), []).append(record)
    matched, overhead, offsets = [], [], []
    no_response, response_without_id, missing_in_log = Counter(), 0, []
    no_response_routes = Counter()
    status_mismatch, endpoint_mismatch, model_mismatch, duplicates = [], [], [], []
    for sample in samples:
        rid = sample["request_id"]
        if not rid:
            if sample["response_code"].isdigit():
                response_without_id += 1
            else:
                no_response[sample["response_code"][:80] or "no response"] += 1
                no_response_routes[LABEL_ROUTES.get(sample["label"])] += 1
            continue
        lines = by_id.get(rid, [])
        if not lines:
            missing_in_log.append(rid)
            continue
        if len(lines) > 1:
            duplicates.append(rid)
        line = lines[0]
        matched.append((sample, line))
        expected_route = LABEL_ROUTES.get(sample["label"])
        if expected_route and (line.get("method"), line.get("endpoint")) != expected_route:
            endpoint_mismatch.append(rid)
        if str(line.get("status_code")) != sample["response_code"]:
            status_mismatch.append({"request_id": rid, "client": sample["response_code"],
                                    "service": line.get("status_code")})
        if expected_model is not None and line.get("model") != expected_model:
            model_mismatch.append({"request_id": rid, "service_model": line.get("model")})
        overhead.append(sample["elapsed_ms"] - float(line.get("duration_ms") or 0))
        offsets.append(sample["start_ms"] - line["_start_ms"])

    offset = statistics.median(offsets) if offsets else 0
    matched_ids = {line["request_id"] for _, line in matched}
    extras = []
    if samples:
        low = min(s["start_ms"] for s in samples) - offset - WINDOW_MARGIN_MS
        high = max(s["end_ms"] for s in samples) - offset + WINDOW_MARGIN_MS
        extras = [r for r in log if low <= r["_start_ms"] <= high and r.get("request_id") not in matched_ids]
    describe = lambda r: (f"{r.get('method')} {r.get('endpoint')} -> {r.get('status_code')}"
                          + (f" ({r['error']})" if r.get("error") else ""))
    extra_types = Counter(describe(r) for r in extras)
    preflight = [r for r in extras if r.get("request_id") in preflight_ids]
    abandoned, unexplained, budget = [], [], Counter(no_response_routes)
    for r in extras:
        if r in preflight:
            continue
        route = (r.get("method"), r.get("endpoint"))
        if budget[route] > 0:
            budget[route] -= 1
            abandoned.append(r)
        else:
            unexplained.append(r)
    with_response = sum(1 for s in samples if s["request_id"] or s["response_code"].isdigit())
    client_ok = sum(1 for s in samples if s["success"])
    service_2xx = sum(1 for _, line in matched if 200 <= int(line.get("status_code", 0)) < 300)
    report = {
        "client_samples": len(samples),
        "client_samples_with_http_response": with_response,
        "client_successful": client_ok,
        "matched": len(matched),
        "matched_service_2xx": service_2xx,
        "client_no_http_response": dict(no_response),
        "client_http_response_without_request_id": response_without_id,
        "request_ids_missing_from_log": missing_in_log[:50],
        "request_ids_missing_from_log_count": len(missing_in_log),
        "duplicate_request_ids_in_log": duplicates[:50],
        "status_mismatches": status_mismatch[:50], "status_mismatch_count": len(status_mismatch),
        "endpoint_mismatch_count": len(endpoint_mismatch),
        "expected_model": expected_model,
        "model_mismatches": model_mismatch[:50], "model_mismatch_count": len(model_mismatch),
        "models_seen_in_matched_lines": dict(Counter(line.get("model") for _, line in matched)),
        "extra_log_lines_in_window": len(extras),
        "extra_log_lines_by_type": dict(extra_types),
        "extra_preflight": len(preflight),
        "extra_abandoned_by_client": len(abandoned),
        "extra_unexplained": len(unexplained),
        "extra_unexplained_by_type": dict(Counter(describe(r) for r in unexplained)),
        "client_minus_service_ms": _pct(overhead),
        "client_faster_than_service_count": sum(1 for v in overhead if v < -NEGATIVE_TOLERANCE_MS),
        "clock_offset_client_minus_service_ms": _pct(offsets),
    }
    report["reconciled"] = bool(
        samples and len(matched) == with_response and not missing_in_log and not response_without_id
        and not status_mismatch and not endpoint_mismatch and not model_mismatch and not duplicates)
    report["contaminated"] = bool(unexplained)
    notes = []
    if no_response:
        notes.append(f"{sum(no_response.values())} client samples got no HTTP response (see client_no_http_response); "
                     "the service may have logged them later, they appear among the extra in-window lines.")
    if unexplained:
        notes.append(f"{len(unexplained)} in-window log lines are not test traffic (see extra_unexplained_by_type): "
                     "the run is contaminated; find the source, record it, and repeat the run.")
    report["notes"] = notes
    extract = [line["_raw"] for _, line in matched] + [r["_raw"] for r in extras]
    return report, extract


def reconcile_file(client_file: Path, service_logs: list[Path], expected_model: str | None = None) -> dict:
    samples, source = read_client_samples(client_file)
    metadata = read_json(client_file.with_suffix(".json")) or read_json(client_file.parent / "metadata.json") or {}
    expected_model = expected_model or metadata.get("model")
    log, malformed = read_service_log(service_logs)
    # The test tools' own requests: load-test preflight GET /stats, accuracy-test model look-up.
    preflight_ids = {metadata["preflight_request_id"]} if metadata.get("preflight_request_id") else set()
    preflight_ids |= set(metadata.get("auxiliary_request_ids") or [])
    report, extract = reconcile(samples, log, expected_model, preflight_ids)
    report = {"client_file": client_file.as_posix(), "client_format": source,
              "service_logs": [p.as_posix() for p in service_logs], "service_log_lines": len(log),
              "service_log_malformed_lines": malformed, "generated_utc": utc_now(), **report}
    stem = client_file.with_suffix("") if source == "jmeter" else client_file.parent / client_file.stem
    write_json(stem.parent / f"{stem.name}.reconciliation.json", report)
    (stem.parent / f"{stem.name}.service_log_extract.jsonl").write_text(
        "".join(line + "\n" for line in extract), encoding="utf-8")
    return report


def _logs_for(client_file: Path, explicit: list[Path] | None) -> list[Path]:
    if explicit:
        return explicit
    for candidate in (client_file.with_suffix(".service.log"), client_file.parent / "service.log"):
        if candidate.is_file():
            return [candidate]
    raise SystemExit(f"No service log for {client_file}: copy the service machine's logs/service.log to "
                     f"{client_file.with_suffix('.service.log')} or pass --service-log")


SUMMARY_COLUMNS = ("client_file", "reconciled", "contaminated", "client_samples", "matched", "client_successful",
                   "matched_service_2xx", "status_mismatch_count", "model_mismatch_count",
                   "request_ids_missing_from_log_count", "extra_log_lines_in_window", "extra_preflight",
                   "extra_abandoned_by_client", "extra_unexplained")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", type=Path, help="run-N.jtl, predictions.csv, or a folder of run-*.jtl")
    parser.add_argument("--service-log", type=Path, action="append",
                        help="Copy of the service machine's logs/service.log (repeatable)")
    parser.add_argument("--model", help="Expected exact model tag (default: from run metadata)")
    args = parser.parse_args(argv)
    files = sorted(args.target.glob("run-*.jtl")) if args.target.is_dir() else [args.target]
    if not files:
        raise SystemExit(f"No run-*.jtl files in {args.target}")
    reports = [reconcile_file(f, _logs_for(f, args.service_log), args.model) for f in files]
    if args.target.is_dir():
        with (args.target / "reconciliation.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(reports)
    for report in reports:
        print(f"{report['client_file']}: reconciled={report['reconciled']} matched={report['matched']}/"
              f"{report['client_samples']} status_mismatch={report['status_mismatch_count']} "
              f"model_mismatch={report['model_mismatch_count']} extra_in_window={report['extra_log_lines_in_window']} "
              f"(preflight {report['extra_preflight']}, abandoned {report['extra_abandoned_by_client']}, "
              f"UNEXPLAINED {report['extra_unexplained']})")
    if not all(r["reconciled"] and not r["contaminated"] for r in reports):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
