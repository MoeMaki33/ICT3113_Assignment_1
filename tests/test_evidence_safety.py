"""Regression checks for admitting evidence; all measurements below are synthetic fixtures."""
import json
import subprocess

import httpx
import pytest

from app.routes import tickets
from scripts import accuracy_test, perf_common, run_load_test, run_stress_test
from scripts.process_jmeter_results import summarise_config
from scripts.reconcile_logs import reconcile_file
from scripts.validate_golden_set import golden_file_problems
from tests.test_testing_tools import golden_file, log_line, run_meta, steady_samples, write_jtl


def test_empty_golden_is_not_final(tmp_path):
    path = tmp_path / "golden.csv"
    path.write_text("row,narrative,final_golden_category\n")
    assert golden_file_problems(path)


def test_staged_files_are_not_committed(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "data").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "data/golden_set_final.csv").write_text("row,narrative,final_golden_category\n")
    (tmp_path / "docs/prediction_record.md").write_text("Status: FROZEN\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    problems = perf_common.freeze_gate_problems(tmp_path)
    assert sum("not committed" in p for p in problems) == 2


def test_final_status_does_not_replace_missing_predictions():
    problems = perf_common.prediction_problems("Status: FINAL\n")
    assert any("accuracy and latency" in p for p in problems)
    assert any("sign-off" in p for p in problems)


def test_official_run_requires_metadata_and_reconciliation(tmp_path):
    jtl = tmp_path / "run-1.jtl"
    write_jtl(jtl, steady_samples(120))
    assert summarise_config(tmp_path)["completed_runs"] == 0
    run_meta(jtl, official=True)
    summary = summarise_config(tmp_path)
    assert summary["completed_runs"] == 0 and not summary["official"]
    jtl.with_suffix(".reconciliation.json").write_text(json.dumps({"reconciled": True, "contaminated": False}))
    summary = summarise_config(tmp_path)
    assert summary["completed_runs"] == 1 and not summary["official"]  # still short of three runs


def test_load_input_validation_detects_tampering(tmp_path):
    import csv
    from scripts.prepare_jmeter_data import prepare

    (tmp_path / "data/labelling").mkdir(parents=True)
    source = tmp_path / "data/team.csv"
    with source.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["row", "narrative"])
        writer.writerows([i, f"Synthetic narrative {i}"] for i in range(1000))
    (tmp_path / "data/labelling/selection.json").write_text(json.dumps({"team_number": 0}))
    prepare(source, tmp_path / "jmeter/data")
    run_load_test.validate_load_inputs(tmp_path)
    with (tmp_path / "jmeter/data/team_narratives.tsv").open("a") as handle:
        handle.write('1000\t"unassigned synthetic row"\n')
    with pytest.raises(ValueError, match="hash differs"):
        run_load_test.validate_load_inputs(tmp_path)


def test_repeated_client_ids_and_unmatched_timeouts_fail_reconciliation(tmp_path):
    jtl = tmp_path / "run-1.jtl"
    run_meta(jtl)
    log = tmp_path / "service.log"
    log.write_text(log_line("a", 1) + "\n")
    write_jtl(jtl, [(1, 1000, "POST /tickets", "201", True, "a"),
                    (1, 1000, "POST /tickets", "201", True, "a")])
    report = reconcile_file(jtl, [log])
    assert not report["reconciled"] and report["duplicate_request_ids_in_client_count"] == 1
    write_jtl(jtl, [(1, 1000, "POST /tickets", "201", True, "a"),
                    (2, 1000, "POST /tickets", "ReadTimeout", False, None)])
    report = reconcile_file(jtl, [log])
    assert not report["reconciled"] and report["unmatched_no_response_count"] == 1


def test_accuracy_rejects_a_different_golden_file(tmp_path, monkeypatch):
    monkeypatch.setattr(accuracy_test, "ROOT", tmp_path)
    monkeypatch.setattr(accuracy_test, "freeze_gate_problems", lambda: [])
    frozen = golden_file(tmp_path)
    other = tmp_path / "other.csv"
    other.write_bytes(frozen.read_bytes() + b"\n")
    with pytest.raises(SystemExit, match="committed"):
        accuracy_test.evaluate(other, "http://unused", "m:1", tmp_path / "accuracy")


def test_accuracy_records_malformed_success_body_as_failure():
    for body in (b"invalid json", b"[]", b'{"category":"Credit card"}'):
        transport = httpx.MockTransport(lambda request: httpx.Response(201, content=body))
        with httpx.Client(base_url="http://unused", transport=transport) as client:
            result = accuracy_test.classify(client, "synthetic complaint")
        assert result["predicted_category"] == accuracy_test.FAILED and result["error"]


def test_orphaned_jmeter_log_reserves_run_number(tmp_path):
    (tmp_path / "run-1.jmeter.log").write_text("synthetic interrupted launch")
    assert perf_common.next_run_number(tmp_path) == 2


def test_stress_refuses_before_writing_a_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(run_stress_test, "freeze_gate_problems", lambda: ["draft record"])
    with pytest.raises(SystemExit, match="NOT allowed"):
        run_stress_test.stress("m:1", [250], 0, run_stress_test.DEFAULT_CRITERIA,
                              duration_s=720, warmup_s=120, cooldown_s=200, results_root=tmp_path)
    assert not (tmp_path / "stress").exists()


def test_unexpected_service_failure_has_request_id_and_stores_nothing(client, monkeypatch):
    def fail(_narrative):
        raise RuntimeError("sensitive internal message")
    monkeypatch.setattr(tickets, "classify_ticket", fail)
    response = client.post("/tickets", json={"narrative": "synthetic complaint"})
    assert response.status_code == 500 and response.headers["x-request-id"]
    assert response.json() == {"detail": "Internal server error"}
    assert sum(client.get("/stats").json().values()) == 0
