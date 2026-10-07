"""Tests for the Person 5 test tooling. Synthetic .jtl/log files and a mocked HTTP service only:
no JMeter, Ollama or network is needed, and no benchmark results are produced."""
import csv
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import pytest

from app.categories import CATEGORIES
from scripts import accuracy_test, perf_common, run_stress_test
from scripts.prepare_jmeter_data import prepare
from scripts.process_jmeter_results import process, summarise_config, summarise_run
from scripts.reconcile_logs import reconcile_file

ROOT = Path(__file__).resolve().parents[1]
JTL_HEADER = ["timeStamp", "elapsed", "label", "responseCode", "responseMessage", "success",
              "failureMessage", "request_id", "ticket_row"]
T0 = 1_800_000_000_000  # arbitrary epoch ms


def write_jtl(path: Path, samples: list[tuple]) -> None:
    """samples: (offset_s, elapsed_ms, label, code, success, request_id)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(JTL_HEADER)
        for offset, elapsed, label, code, success, rid in samples:
            writer.writerow([T0 + int(offset * 1000), elapsed, label, code, "", str(success).lower(), "",
                             rid or "NO_REQUEST_ID", 7000])


def run_meta(path: Path, **extra) -> None:
    meta = {"status": "completed", "run": int(path.stem.split("-")[1]), "model": "m:1", "official": False,
            "kind": "load", "rate_per_hour": 360, "search_rate_per_hour": 0, "warmup_s": 10,
            "duration_s": 110, "schedule_start_epoch_ms": T0, **extra}
    path.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")


def steady_samples(n=100, elapsed=1000, start=0, gap=1.0, code="201", rid_prefix="r"):
    return [(start + i * gap, elapsed, "POST /tickets", code, code == "201", f"{rid_prefix}{i}")
            for i in range(n)]


# --- shared helpers -------------------------------------------------------------------------

def test_model_dir_and_config_names_are_path_safe():
    assert perf_common.model_dir("qwen2.5:7b") == "qwen2.5_7b"
    assert perf_common.config_dir_name(250) == "rate-250"
    assert perf_common.config_dir_name(250, 450) == "rate-250_search-450"
    with pytest.raises(ValueError):
        perf_common.model_dir(" ")


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_freeze_gate_requires_committed_unmodified_non_draft_record(tmp_path):
    git = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "data").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "data/golden_set_final.csv").write_text("row,narrative,final_golden_category\n")
    record = tmp_path / "docs/prediction_record.md"
    record.write_text("Owner: Person 4. Status: **DRAFT (2026-10-07)**\n")
    problems = perf_common.freeze_gate_problems(tmp_path)
    assert any("not committed" in p for p in problems) and any("DRAFT" in p for p in problems)
    git("add", ".")
    git("commit", "-qm", "draft")
    assert perf_common.freeze_gate_problems(tmp_path) == ["docs/prediction_record.md is still marked DRAFT"]
    record.write_text("Owner: Person 4. Status: **FROZEN (2026-10-08)**\n")
    assert perf_common.freeze_gate_problems(tmp_path) == ["docs/prediction_record.md has uncommitted changes"]
    git("commit", "-qam", "Freeze golden set and prediction record before benchmarking")
    assert perf_common.freeze_gate_problems(tmp_path) == []


# --- JMeter inputs --------------------------------------------------------------------------

def test_prepared_narratives_survive_quotes_commas_tabs_and_newlines(tmp_path):
    team = tmp_path / "team.csv"
    tricky = 'He said "stop", then\nleft.\tTab, comma, ${notavar} \\ backslash, café'
    with team.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows([["row", "narrative"], [7000, tricky], [7001, "plain"]])
    manifest = prepare(team, tmp_path / "out")
    lines = (tmp_path / "out/team_narratives.tsv").read_text(encoding="utf-8").splitlines()
    assert manifest["narrative_count"] == 2 and len(lines) == 2
    row, encoded = lines[0].split("\t")
    assert row == "7000" and json.loads(encoded) == tricky
    assert json.loads('{"narrative": ' + encoded + "}")["narrative"] == tricky


@pytest.mark.skipif(not (ROOT / "jmeter/ticket_load_test.jmx").is_file(), reason="jmeter/ not in image")
def test_jmeter_plan_is_open_loop_configurable_and_captures_request_id():
    tree = ET.parse(ROOT / "jmeter/ticket_load_test.jmx")
    groups = tree.findall(".//OpenModelThreadGroup")
    assert len(groups) == 2 and not tree.findall(".//ThreadGroup")  # no closed-loop thread groups
    schedules = [g.find("stringProp[@name='OpenModelThreadGroup.schedule']").text for g in groups]
    assert "rate(${__P(rate)}/hour)" in schedules[0] and "random_arrivals(${__P(duration_s)} s)" in schedules[0]
    assert "pause(${__P(drain_s,190)} s)" in schedules[0]
    assert schedules[1] == "${__P(search_schedule,pause(1 s))}"
    extractor = tree.find(".//RegexExtractor")
    assert extractor.find("stringProp[@name='RegexExtractor.refname']").text == "request_id"
    props = (ROOT / "jmeter/results.properties").read_text()
    assert "sample_variables=request_id,ticket_row" in props
    assert "sampleresult.timestamp.start=true" in props


def test_search_schedule_never_uses_a_zero_rate():
    from scripts.run_load_test import search_schedule
    assert search_schedule(0, 720, 190) == "pause(1s)"
    assert search_schedule(450, 720, 190) == "rate(450/hour)random_arrivals(720s)pause(190s)"
    assert " " not in search_schedule(450, 720, 190)


# --- result processing ----------------------------------------------------------------------

def test_run_summary_uses_window_and_documented_definitions(tmp_path):
    jtl = tmp_path / "rate-360/run-1.jtl"
    # one sample per second from t=0..119 s; 2 failures inside the window
    samples = steady_samples(120, elapsed=1000)
    samples[50] = (50, 400, "POST /tickets", "502", False, "r50")
    samples[60] = (60, 180000, "POST /tickets", "Non HTTP response code: java.net.SocketTimeoutException",
                   False, None)
    write_jtl(jtl, samples)
    run_meta(jtl)
    tickets = summarise_run(jtl)["labels"]["POST /tickets"]
    assert tickets["samples_in_window"] == 100              # starts in [10 s, 110 s)
    assert tickets["failed_in_window"] == 2 and tickets["error_rate"] == 0.02
    assert tickets["offered_per_hour"] == 3600.0            # 100 per 100 s
    # successful completions with end in window: ends at 10..109 s => starts 9..108, minus 2 failures
    assert tickets["achieved_per_hour"] == pytest.approx(98 * 36, rel=1e-6)
    assert tickets["latency_p50_s"] == tickets["latency_p99_s"] == 1.0
    assert tickets["errors_by_type"] == {"HTTP 502": 1, "SocketTimeoutException": 1}
    assert tickets["growing"] is False


def test_growing_latency_is_detected(tmp_path):
    jtl = tmp_path / "rate-360/run-1.jtl"
    write_jtl(jtl, [(i, 1000 + i * 500, "POST /tickets", "201", True, f"r{i}") for i in range(120)])
    run_meta(jtl)
    tickets = summarise_run(jtl)["labels"]["POST /tickets"]
    assert tickets["growing"] is True and tickets["trend_ratio"] > 1.5


def test_config_summary_reports_missing_and_failed_runs_without_filling_them(tmp_path):
    config = tmp_path / "m_1/rate-360"
    write_jtl(config / "run-1.jtl", steady_samples(120))
    run_meta(config / "run-1.jtl")
    write_jtl(config / "run-2.jtl", steady_samples(120))
    run_meta(config / "run-2.jtl", status="failed")
    summary = summarise_config(config)
    assert summary["completed_runs"] == 1
    assert summary["missing_runs"] == ["run-2", "run-3"]
    assert any("run-2" in p and "failed" in p for p in summary["problems"])
    assert summary["aggregate"]["POST /tickets"]["latency_p95_s"]["n"] == 1


def test_contaminated_runs_are_excluded_and_replacements_count(tmp_path):
    config = tmp_path / "m_1/rate-360"
    for run in (1, 2, 3, 4):
        write_jtl(config / f"run-{run}.jtl", steady_samples(120))
        run_meta(config / f"run-{run}.jtl")
        bad = run == 2
        (config / f"run-{run}.reconciliation.json").write_text(json.dumps(
            {"reconciled": True, "contaminated": bad}))
    summary = summarise_config(config)
    assert summary["completed_runs"] == 3 and summary["missing_runs"] == []
    assert any("run-2" in p and "contaminated=True" in p for p in summary["problems"])
    (config / "run-4.reconciliation.json").write_text(json.dumps({"reconciled": False, "contaminated": False}))
    assert summarise_config(config)["missing_runs"] == ["run-2"]  # only 2 valid runs: 1 and 3


def test_process_root_writes_machine_readable_and_markdown_outputs(tmp_path):
    for run in (1, 2, 3):
        jtl = tmp_path / f"m_1/rate-360/run-{run}.jtl"
        write_jtl(jtl, steady_samples(120, elapsed=1000 * run))
        run_meta(jtl)
    process(tmp_path)
    config = tmp_path / "m_1/rate-360"
    for name in ("summary.json", "summary.csv", "runs.csv", "summary.md"):
        assert (config / name).is_file()
    rows = list(csv.DictReader((tmp_path / "summary_all.csv").open()))
    assert len(rows) == 1 and rows[0]["completed_runs"] == "3" and rows[0]["missing_runs"] == ""
    assert float(rows[0]["latency_p95_s_mean"]) == 2.0 and float(rows[0]["pooled_p99_s"]) == 3.0
    assert len(list(csv.DictReader((tmp_path / "runs_all.csv").open()))) == 3
    assert "NOT OFFICIAL EVIDENCE" in (config / "summary.md").read_text()


def test_process_refuses_when_there_are_no_results(tmp_path):
    with pytest.raises(SystemExit, match="nothing to process"):
        process(tmp_path)


# --- log reconciliation ---------------------------------------------------------------------

def log_line(rid, start_s, status=201, endpoint="/tickets", method="POST", model="m:1", duration=900.0):
    start = perf_common.datetime.fromtimestamp((T0 + start_s * 1000) / 1000, perf_common.timezone.utc)
    return json.dumps({"request_id": rid, "start_time": start.isoformat(), "endpoint": endpoint,
                       "method": method, "model": model, "duration_ms": duration, "status_code": status,
                       "error": None if status < 400 else f"HTTP {status}"})


def test_reconciliation_matches_ids_and_classifies_extra_lines(tmp_path):
    jtl = tmp_path / "run-1.jtl"
    write_jtl(jtl, [(1, 1000, "POST /tickets", "201", True, "a"), (2, 1000, "POST /tickets", "201", True, "b"),
                    (3, 180000, "POST /tickets", "Non HTTP response code: java.net.SocketTimeoutException",
                     False, None)])
    run_meta(jtl, preflight_request_id="pre")
    log = tmp_path / "service.log"
    log.write_text("\n".join([log_line("pre", 0, 200, "/stats", "GET"), log_line("a", 1), log_line("b", 2),
                              log_line("late", 3), "not json"]) + "\n")
    report = reconcile_file(jtl, [log])
    assert report["reconciled"] and not report["contaminated"]
    assert report["matched"] == 2 and report["service_log_malformed_lines"] == 1
    assert (report["extra_preflight"], report["extra_abandoned_by_client"], report["extra_unexplained"]) == (1, 1, 0)
    assert report["client_minus_service_ms"]["p50"] == 100.0
    extract = (tmp_path / "run-1.service_log_extract.jsonl").read_text().splitlines()
    assert len(extract) == 4 and (tmp_path / "run-1.reconciliation.json").is_file()


def test_reconciliation_flags_mismatches_and_contamination(tmp_path):
    jtl = tmp_path / "run-1.jtl"
    write_jtl(jtl, [(1, 1000, "POST /tickets", "201", True, "a"), (2, 1000, "POST /tickets", "201", True, "b"),
                    (3, 1000, "POST /tickets", "201", True, "c")])
    run_meta(jtl)
    log = tmp_path / "service.log"
    log.write_text("\n".join([log_line("a", 1, status=502), log_line("b", 2, model="other:1"),
                              log_line("dev", 2.5, 200, "/search", "GET")]) + "\n")
    report = reconcile_file(jtl, [log])
    assert not report["reconciled"] and report["contaminated"]
    assert report["status_mismatch_count"] == 1 and report["model_mismatch_count"] == 1
    assert report["request_ids_missing_from_log"] == ["c"]
    assert report["extra_unexplained_by_type"] == {"GET /search -> 200": 1}


# --- accuracy test --------------------------------------------------------------------------

def golden_file(tmp_path: Path, n_per_category: int = 2) -> Path:
    path = tmp_path / "golden.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["row", "narrative", "final_golden_category"])
        row = 7000
        for category in CATEGORIES:
            for i in range(n_per_category):
                writer.writerow([row, f"Complaint {row} about {category} number {i}", category])
                row += 1
    return path


def fake_service(model="m:1", wrong_rows=(), failing_rows=()):
    store = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            narrative = json.loads(request.content)["narrative"]
            row = int(narrative.split()[1])
            rid = f"req-{row}"
            if row in failing_rows:
                return httpx.Response(502, json={"detail": "Ticket classification failed"},
                                      headers={"x-request-id": rid})
            category = narrative.split(" about ")[1].rsplit(" number", 1)[0]
            if row in wrong_rows:
                category = "Mortgage" if category != "Mortgage" else "Credit card"
            ticket_id = len(store) + 1
            store[ticket_id] = {"id": ticket_id, "narrative": narrative, "model": model, "category": category}
            return httpx.Response(201, json={"id": ticket_id, "category": category}, headers={"x-request-id": rid})
        query = request.url.params["q"]
        return httpx.Response(200, json=[t for t in store.values() if query in t["narrative"]],
                              headers={"x-request-id": "lookup"})

    return httpx.MockTransport(handler)


def test_accuracy_refuses_official_run_before_freeze(tmp_path, monkeypatch):
    monkeypatch.setattr(accuracy_test, "freeze_gate_problems", lambda: ["prediction record is DRAFT"])
    with pytest.raises(SystemExit, match="NOT allowed"):
        accuracy_test.evaluate(golden_file(tmp_path), "http://svc", "m:1", tmp_path / "accuracy")
    with pytest.raises(SystemExit, match="--limit"):
        monkeypatch.setattr(accuracy_test, "freeze_gate_problems", lambda: [])
        accuracy_test.evaluate(golden_file(tmp_path), "http://svc", "m:1", tmp_path / "accuracy", limit=3)


def test_accuracy_scores_every_ticket_and_counts_failures_as_incorrect(tmp_path, monkeypatch):
    monkeypatch.setattr(accuracy_test, "freeze_gate_problems", lambda: [])
    out = accuracy_test.evaluate(golden_file(tmp_path), "http://svc", "m:1", tmp_path / "accuracy",
                                 transport=fake_service(wrong_rows={7002}, failing_rows={7004}))
    assert out == tmp_path / "accuracy/m_1/run-1"
    metrics = json.loads((out / "metrics.json").read_text())
    assert metrics["total"] == 14 and metrics["correct"] == 12 and metrics["failed_requests"] == 1
    assert metrics["overall_accuracy"] == round(12 / 14, 4)
    per = {c["category"]: c for c in metrics["per_category"]}
    # row 7002 (Debt collection) is misclassified as Mortgage; row 7004 (Mortgage) fails with 502
    assert per["Debt collection"]["accuracy_recall"] == 0.5 and per["Mortgage"]["accuracy_recall"] == 0.5
    assert per["Credit reporting"]["accuracy_recall"] == 1.0 and metrics["lowest_category_accuracy"] == 0.5
    assert metrics["confusion_matrix"]["Debt collection"]["Mortgage"] == 1
    assert metrics["confusion_matrix"]["Mortgage"]["FAILED"] == 1
    predictions = list(csv.DictReader((out / "predictions.csv").open()))
    assert len(predictions) == 14 and predictions[0]["request_id"] == "req-7000"
    assert "narrative" not in predictions[0]
    metadata = json.loads((out / "metadata.json").read_text())
    assert metadata["status"] == "completed" and metadata["model_verified_via_search"] == "m:1"
    assert metadata["auxiliary_request_ids"] == ["lookup"]
    for name in ("per_category.csv", "confusion_matrix.csv", "summary.md"):
        assert (out / name).is_file()
    second = accuracy_test.evaluate(golden_file(tmp_path), "http://svc", "m:1", tmp_path / "accuracy",
                                    transport=fake_service())
    assert second.name == "run-2"  # never overwrites
    summary = accuracy_test.summarise_all(tmp_path / "accuracy")
    assert len(list(csv.DictReader(summary.open()))) == 2


def test_accuracy_stops_when_service_runs_a_different_model(tmp_path, monkeypatch):
    monkeypatch.setattr(accuracy_test, "freeze_gate_problems", lambda: [])
    with pytest.raises(SystemExit, match="expected 'm:1'"):
        accuracy_test.evaluate(golden_file(tmp_path), "http://svc", "m:1", tmp_path / "accuracy",
                               transport=fake_service(model="other:7b"))
    metadata = json.loads((tmp_path / "accuracy/m_1/run-1/metadata.json").read_text())
    assert metadata["status"] == "aborted_model_mismatch"


def test_accuracy_predictions_reconcile_with_service_log(tmp_path, monkeypatch):
    monkeypatch.setattr(accuracy_test, "freeze_gate_problems", lambda: [])
    out = accuracy_test.evaluate(golden_file(tmp_path, 1), "http://svc", "m:1", tmp_path / "accuracy",
                                 transport=fake_service())
    rows = list(csv.DictReader((out / "predictions.csv").open()))
    log = tmp_path / "service.log"
    lookup_time = int(rows[0]["start_epoch_ms"]) / 1000
    log.write_text(json.dumps({"request_id": "lookup", "start_time": perf_common.datetime.fromtimestamp(
        lookup_time, perf_common.timezone.utc).isoformat(), "endpoint": "/search", "method": "GET",
        "model": "m:1", "duration_ms": 1.0, "status_code": 200}) + "\n" + "".join(json.dumps({
        "request_id": r["request_id"], "start_time": perf_common.datetime.fromtimestamp(
            int(r["start_epoch_ms"]) / 1000, perf_common.timezone.utc).isoformat(),
        "endpoint": "/tickets", "method": "POST", "model": "m:1", "duration_ms": 0.0,
        "status_code": int(r["status_code"])}) + "\n" for r in rows))
    report = reconcile_file(out / "predictions.csv", [log])
    assert report["client_format"] == "accuracy" and report["matched"] == 7
    # the model look-up GET /search is the tool's own request: explained, not contamination
    assert report["extra_preflight"] == 1 and report["extra_unexplained"] == 0
    assert report["reconciled"] and not report["contaminated"]


# --- stress test ----------------------------------------------------------------------------

CRITERIA = dict(run_stress_test.DEFAULT_CRITERIA)


def test_step_evaluation_applies_each_stopping_criterion():
    ok = {"error_rate": 0.0, "offered_per_hour": 100, "achieved_per_hour": 99, "growing": False,
          "trend_ratio": 1.0, "latency_p95_s": 5}
    assert run_stress_test.evaluate_step(ok, CRITERIA) == (True, [])
    assert not run_stress_test.evaluate_step({**ok, "error_rate": 0.06}, CRITERIA)[0]
    assert not run_stress_test.evaluate_step({**ok, "achieved_per_hour": 80}, CRITERIA)[0]
    assert not run_stress_test.evaluate_step({**ok, "growing": True, "trend_ratio": 2.0}, CRITERIA)[0]
    assert not run_stress_test.evaluate_step({**ok, "latency_p95_s": 121}, CRITERIA)[0]


def fake_run_once(capacity_per_hour: float):
    """Stand-in for JMeter: below capacity flat latency, above it latency grows."""
    def run(*, rate, out_dir, duration_s, warmup_s, **_kw):
        gap = 3600 / rate
        n = int(duration_s / gap)
        overloaded = rate > capacity_per_hour
        samples = [(i * gap, 1000 + (i * 400 if overloaded else 0), "POST /tickets", "201", True, f"r{i}")
                   for i in range(n)]
        write_jtl(out_dir / "run-1.jtl", samples)
        run_meta(out_dir / "run-1.jtl", duration_s=duration_s, warmup_s=warmup_s, rate_per_hour=rate)
        return out_dir / "run-1.json"
    return run


def test_stress_finds_limit_with_bisection_and_locks_its_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(run_stress_test, "run_once", fake_run_once(capacity_per_hour=800))
    kwargs = dict(duration_s=600, warmup_s=60, cooldown_s=1, results_root=tmp_path, sleep=lambda _s: None)
    summary = run_stress_test.stress("m:1", [250, 500, 1000, 2000], 2, CRITERIA, **kwargs)
    rates = [s["rate_setting_per_hour"] for s in summary["steps"]]
    assert rates == [250, 500, 1000, 750, 875]  # stops at 1000, then bisects 500..1000
    assert summary["highest_sustainable_per_hour"] == 750
    assert summary["lowest_unsustainable_per_hour"] == 875
    base = tmp_path / "stress/m_1"
    assert (base / "stress_steps.csv").is_file() and "limit lies between" in (base / "stress_summary.md").read_text()
    # resuming reuses completed steps and refuses changed criteria
    again = run_stress_test.stress("m:1", [250, 500, 1000, 2000], 2, CRITERIA, **kwargs)
    assert again["highest_sustainable_per_hour"] == 750
    with pytest.raises(SystemExit, match="must not change"):
        run_stress_test.stress("m:1", [250, 500, 1000, 2000], 2, {**CRITERIA, "max_error_rate": 0.5}, **kwargs)


def test_stress_does_not_claim_a_limit_it_did_not_reach(tmp_path, monkeypatch):
    monkeypatch.setattr(run_stress_test, "run_once", fake_run_once(capacity_per_hour=10_000))
    summary = run_stress_test.stress("m:1", [250, 500], 2, CRITERIA, duration_s=600, warmup_s=60, cooldown_s=1,
                                     results_root=tmp_path, sleep=lambda _s: None)
    assert summary["lowest_unsustainable_per_hour"] is None
    assert "no limit found" in summary["conclusion"]
