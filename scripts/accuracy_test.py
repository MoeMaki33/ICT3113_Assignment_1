"""Accuracy test: send every frozen golden-set ticket through POST /tickets and score it.

Per candidate model (the service machine sets OLLAMA_MODEL and restarts the API first):

    python -m scripts.accuracy_test data/golden_set_final.csv --model qwen2.5:7b --api-url http://<service>:8000

- Tickets are sent ONE AT A TIME (no concurrency), in golden-set row order, so the recorded
  latencies are single-request latencies with no other load.
- Every prediction is appended to ``predictions.csv`` as soon as it arrives (raw evidence;
  a crash keeps everything so far). Narratives are not copied, only the golden row number.
- After the first successful ticket, the stored record is looked up through GET /search and
  its ``model`` must equal ``--model``; otherwise the run stops (wrong model configured).
- A ticket that fails to classify (502, timeout, ...) counts as INCORRECT (docs/requirements.md R3).
- The golden set is only read; its SHA-256 is recorded so the exact file is traceable.

Outputs in ``results/accuracy/<model-dir>/run-<N>/`` (never overwritten): metadata.json,
predictions.csv, metrics.json, per_category.csv, confusion_matrix.csv, summary.md.
``--summarise results/accuracy`` builds accuracy_summary.csv/.md across all model runs.

Official runs require the freeze gate. ``--smoke`` (optionally with ``--limit``) is a tooling
check that writes under results/smoke/accuracy/ and is never evidence.
"""
import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.categories import CATEGORIES
from scripts.perf_common import (
    ROOT, GOLDEN_SET, freeze_gate_problems, git_info, model_dir, nearest_rank, read_json, sha256_file, utc_now,
    write_json,
)

FAILED = "FAILED"
PREDICTION_COLUMNS = ("row", "golden_category", "predicted_category", "correct", "status_code", "error",
                      "ticket_id", "request_id", "start_epoch_ms", "elapsed_ms")


def read_golden(path: Path) -> list[dict]:
    csv.field_size_limit(2**31 - 1)
    with path.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    if not records or not {"row", "narrative", "final_golden_category"} <= set(records[0]):
        raise ValueError(f"{path} must have columns row,narrative,final_golden_category")
    for record in records:
        if record["final_golden_category"] not in CATEGORIES:
            raise ValueError(f"Row {record['row']}: invalid golden category {record['final_golden_category']!r}")
        if not record["narrative"].strip():
            raise ValueError(f"Row {record['row']}: empty narrative")
    ids = [int(r["row"]) for r in records]
    if len(set(ids)) != len(ids) or any(i < 0 for i in ids):
        raise ValueError("Golden source rows must be unique nonnegative integers")
    return records


def next_run_dir(base: Path) -> Path:
    numbers = [int(p.name[4:]) for p in base.glob("run-*") if p.name[4:].isdigit()]
    return base / f"run-{max(numbers, default=0) + 1}"


def classify(client: httpx.Client, narrative: str) -> dict:
    start_ms = int(time.time() * 1000)
    timer = time.perf_counter()
    try:
        response = client.post("/tickets", json={"narrative": narrative})
    except httpx.HTTPError as exc:
        return {"status_code": "", "error": type(exc).__name__, "request_id": "", "ticket_id": "",
                "predicted_category": FAILED, "start_epoch_ms": start_ms,
                "elapsed_ms": round((time.perf_counter() - timer) * 1000)}
    elapsed = round((time.perf_counter() - timer) * 1000)
    result = {"status_code": response.status_code, "request_id": response.headers.get("x-request-id", ""),
              "start_epoch_ms": start_ms, "elapsed_ms": elapsed, "error": "", "ticket_id": "",
              "predicted_category": FAILED}
    if response.status_code == 201:
        try:
            body = response.json()
        except ValueError:
            result["error"] = "InvalidJSONResponse"
            return result
        if not isinstance(body, dict) or not isinstance(body.get("id"), int) or isinstance(body.get("id"), bool) or body["id"] <= 0:
            result["error"] = "InvalidTicketResponse"
            return result
        result.update(ticket_id=body.get("id", ""), predicted_category=body.get("category", FAILED))
        if result["predicted_category"] not in CATEGORIES:
            result.update(error="CategoryOutsideSeven", predicted_category=FAILED)
    else:
        result["error"] = f"HTTP {response.status_code}"
    return result


def stored_model(client: httpx.Client, narrative: str, ticket_id: int) -> tuple[str | None, str | None]:
    """Model recorded by the service for ``ticket_id`` (looked up by a narrative substring).

    Also returns the look-up's X-Request-ID, so log reconciliation can account for it.
    """
    probe = narrative.strip()[:60]
    response = client.get("/search", params={"q": probe})
    request_id = response.headers.get("x-request-id")
    if response.status_code != 200:
        return None, request_id
    return next((t.get("model") for t in response.json() if t.get("id") == ticket_id), None), request_id


def compute_metrics(predictions: list[dict]) -> dict:
    total = len(predictions)
    correct = sum(1 for p in predictions if p["correct"])
    matrix = {g: Counter() for g in CATEGORIES}
    for p in predictions:
        matrix[p["golden_category"]][p["predicted_category"]] += 1
    predicted_totals = Counter(p["predicted_category"] for p in predictions)
    per_category = []
    for category in CATEGORIES:
        golden = sum(matrix[category].values())
        hits = matrix[category][category]
        per_category.append({
            "category": category, "golden_tickets": golden, "correct": hits,
            "accuracy_recall": round(hits / golden, 4) if golden else None,
            "predicted_as_category": predicted_totals[category],
            "precision": round(hits / predicted_totals[category], 4) if predicted_totals[category] else None,
            "failed": matrix[category][FAILED],
        })
    ok = [p for p in predictions if p["predicted_category"] != FAILED]
    latencies = sorted(int(p["elapsed_ms"]) for p in ok)
    warm = sorted(int(p["elapsed_ms"]) for p in predictions[1:] if p["predicted_category"] != FAILED)

    def lat(values: list[int]) -> dict:
        if not values:
            return {"n": 0}
        return {"n": len(values), **{f"p{q}_s": round(nearest_rank(values, q) / 1000, 3) for q in (50, 95, 99)},
                "mean_s": round(sum(values) / len(values) / 1000, 3), "max_s": round(values[-1] / 1000, 3)}

    return {
        "total": total, "correct": correct, "incorrect": total - correct,
        "failed_requests": sum(1 for p in predictions if p["predicted_category"] == FAILED),
        "failures_by_type": dict(Counter(p["error"] for p in predictions if p["error"])),
        "overall_accuracy": round(correct / total, 4) if total else None,
        "lowest_category_accuracy": min((c["accuracy_recall"] for c in per_category
                                         if c["accuracy_recall"] is not None), default=None),
        "per_category": per_category,
        "confusion_matrix": {g: {p: matrix[g][p] for p in (*CATEGORIES, FAILED)} for g in CATEGORIES},
        "single_request_latency_all": lat(latencies),
        "single_request_latency_excluding_first": lat(warm),
        "method": {"accuracy": "correct / all golden tickets (failed requests count as incorrect)",
                   "per_category": "recall: correct / golden tickets of that category",
                   "latency": "client-measured POST /tickets time, sequential requests, nearest-rank"},
    }


def write_outputs(out: Path, metrics: dict, metadata: dict) -> None:
    write_json(out / "metrics.json", metrics)
    with (out / "per_category.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics["per_category"][0]))
        writer.writeheader()
        writer.writerows(metrics["per_category"])
    with (out / "confusion_matrix.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["golden \\ predicted", *CATEGORIES, FAILED])
        for golden, row in metrics["confusion_matrix"].items():
            writer.writerow([golden, *row.values()])
    pct = lambda v: f"{v:.1%}" if v is not None else "-"
    lines = [f"# Accuracy: `{metadata['model']}` ({out.name})", ""]
    if not metadata["official"]:
        lines += ["**NOT OFFICIAL EVIDENCE** (smoke run or freeze gate not met).", ""]
    lat = metrics["single_request_latency_excluding_first"]
    lines += [f"Golden set `{metadata['golden_set']}` (sha256 `{metadata['golden_sha256'][:12]}…`), "
              f"{metrics['total']} tickets, status `{metadata['status']}`.", "",
              f"- Overall accuracy: **{pct(metrics['overall_accuracy'])}** ({metrics['correct']}/{metrics['total']})",
              f"- Lowest per-category accuracy: **{pct(metrics['lowest_category_accuracy'])}**",
              f"- Failed requests (counted incorrect): {metrics['failed_requests']} {metrics['failures_by_type'] or ''}",
              f"- Single-request latency excl. first: p50 {lat.get('p50_s', '-')} s, p95 {lat.get('p95_s', '-')} s, "
              f"p99 {lat.get('p99_s', '-')} s (n={lat['n']})", "",
              "| Category | Golden | Correct | Accuracy (recall) | Predicted as | Precision | Failed |",
              "|---|---|---|---|---|---|---|"]
    lines += [f"| {c['category']} | {c['golden_tickets']} | {c['correct']} | {pct(c['accuracy_recall'])} | "
              f"{c['predicted_as_category']} | {pct(c['precision'])} | {c['failed']} |" for c in metrics["per_category"]]
    lines += ["", "Confusion matrix (rows = golden, columns = predicted):", "",
              "| golden \\ predicted | " + " | ".join((*CATEGORIES, FAILED)) + " |",
              "|---" * (len(CATEGORIES) + 2) + "|"]
    lines += [f"| {g} | " + " | ".join(str(v) for v in row.values()) + " |"
              for g, row in metrics["confusion_matrix"].items()]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate(golden_set: Path, api_url: str, model: str, output: Path, smoke: bool = False,
             limit: int | None = None, timeout: float = 180.0, transport: httpx.BaseTransport | None = None) -> Path:
    problems = freeze_gate_problems()
    if problems and not smoke:
        raise SystemExit("Official accuracy testing is NOT allowed yet:\n  - " + "\n  - ".join(problems)
                         + "\nUse --smoke for a tooling check (results go to results/smoke/accuracy/).")
    if limit is not None and not smoke:
        raise SystemExit("--limit is only allowed with --smoke: official runs score every golden ticket")
    if limit is not None and limit <= 0:
        raise ValueError("--limit must be positive")
    if not smoke and sha256_file(golden_set) != sha256_file(ROOT / GOLDEN_SET):
        raise SystemExit("Official accuracy testing must use the committed data/golden_set_final.csv bytes")
    golden = read_golden(golden_set)[:limit]
    base = (output.parent / "smoke" / output.name if smoke else output) / model_dir(model)
    out = next_run_dir(base)
    out.mkdir(parents=True)
    metadata = {"model": model, "official": not smoke, "freeze_gate_problems": problems, "api_url": api_url,
                "golden_set": golden_set.as_posix(), "golden_sha256": sha256_file(golden_set),
                "tickets": len(golden), "concurrency": 1, "timeout_s": timeout, "git": git_info(),
                "started_utc": utc_now(), "status": "running"}
    write_json(out / "metadata.json", metadata)
    predictions = []
    with httpx.Client(base_url=api_url, timeout=timeout, transport=transport) as client, \
            (out / "predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREDICTION_COLUMNS)
        writer.writeheader()
        verified = False
        for index, ticket in enumerate(golden, 1):
            result = classify(client, ticket["narrative"])
            row = {"row": ticket["row"], "golden_category": ticket["final_golden_category"], **result}
            row["correct"] = row["predicted_category"] == row["golden_category"]
            writer.writerow(row)
            handle.flush()
            predictions.append(row)
            print(f"[{index}/{len(golden)}] row {row['row']}: {row['predicted_category']} "
                  f"({'ok' if row['correct'] else 'wrong'}, {row['elapsed_ms']} ms)", flush=True)
            if not verified and row["ticket_id"] != "":
                seen, lookup_id = stored_model(client, ticket["narrative"], row["ticket_id"])
                metadata.update(model_verified_via_search=seen, auxiliary_request_ids=[lookup_id] if lookup_id else [])
                if seen != model:
                    metadata.update(status="aborted_model_mismatch", finished_utc=utc_now())
                    write_json(out / "metadata.json", metadata)
                    raise SystemExit(f"Service stored model {seen!r}, expected {model!r}. Stopped; "
                                     f"partial predictions kept in {out}")
                verified = True
    metadata.update(status="completed", finished_utc=utc_now())
    write_json(out / "metadata.json", metadata)
    write_outputs(out, compute_metrics(predictions), metadata)
    return out


def summarise_all(root: Path) -> Path:
    rows = []
    for metrics_path in sorted(root.rglob("metrics.json")):
        metrics, metadata = read_json(metrics_path), read_json(metrics_path.parent / "metadata.json") or {}
        lat = metrics["single_request_latency_excluding_first"]
        row = {"model": metadata.get("model"), "run": metrics_path.parent.name, "official": metadata.get("official"),
               "status": metadata.get("status"), "tickets": metrics["total"], "correct": metrics["correct"],
               "overall_accuracy": metrics["overall_accuracy"],
               "lowest_category_accuracy": metrics["lowest_category_accuracy"],
               "failed_requests": metrics["failed_requests"],
               "latency_p50_s": lat.get("p50_s"), "latency_p95_s": lat.get("p95_s"), "latency_p99_s": lat.get("p99_s")}
        row.update({f"acc_{c['category']}": c["accuracy_recall"] for c in metrics["per_category"]})
        rows.append(row)
    if not rows:
        raise SystemExit(f"No metrics.json under {root}; no accuracy results exist yet.")
    columns = list(dict.fromkeys(k for row in rows for k in row))
    target = root / "accuracy_summary.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    fmt = lambda v: f"{v:.1%}" if isinstance(v, float) and v <= 1 else ("-" if v is None else str(v))
    md = ["| Model | Run | Official | Overall | Lowest category | " + " | ".join(CATEGORIES)
          + " | Failed | p50 s | p95 s |", "|---" * (len(CATEGORIES) + 8) + "|"]
    md += [f"| {r['model']} | {r['run']} | {r['official']} | {fmt(r['overall_accuracy'])} | "
           f"{fmt(r['lowest_category_accuracy'])} | " + " | ".join(fmt(r.get(f'acc_{c}')) for c in CATEGORIES)
           + f" | {r['failed_requests']} | {r['latency_p50_s']} | {r['latency_p95_s']} |" for r in rows]
    (root / "accuracy_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("golden_set", type=Path, nargs="?", default=Path("data/golden_set_final.csv"))
    parser.add_argument("--model", help="Exact Ollama tag configured on the service")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "accuracy")
    parser.add_argument("--timeout", type=float, default=180.0, help="Per-request seconds (> Ollama's 120 s)")
    parser.add_argument("--smoke", action="store_true", help="Tooling check only; not evidence")
    parser.add_argument("--limit", type=int, help="Only the first N tickets (smoke only)")
    parser.add_argument("--summarise", type=Path, metavar="ROOT", help="Only build accuracy_summary.csv under ROOT")
    args = parser.parse_args()
    if args.summarise:
        print(summarise_all(args.summarise))
    else:
        if not args.model:
            parser.error("--model is required")
        print(evaluate(args.golden_set, args.api_url, args.model, args.output, args.smoke, args.limit, args.timeout))
