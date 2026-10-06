"""Tests for the ticket-length analysis and workload calculations (no dataset changes, no measurements)."""
import csv
import json
from datetime import date
from pathlib import Path

import pytest

from scripts import workload_calc
from scripts.ticket_lengths import analyse, describe, nearest_rank, read_narratives

ROOT = Path(__file__).resolve().parents[1]


def test_nearest_rank_percentiles():
    values = list(range(1, 101))
    assert nearest_rank(values, 50) == 50
    assert nearest_rank(values, 95) == 95
    assert nearest_rank(values, 99) == 99
    assert nearest_rank([7], 99) == 7
    with pytest.raises(ValueError):
        nearest_rank([], 50)


def test_describe_reports_all_required_statistics():
    summary = describe([10, 20, 30, 40])
    assert summary["count"] == 4 and summary["min"] == 10 and summary["max"] == 40
    assert summary["mean"] == 25 and summary["median"] == 25
    assert {"p50", "p95", "p99"} <= set(summary)


def test_analyse_counts_characters_words_and_estimated_tokens():
    result = analyse(["one two three", "a" * 400])
    assert result["characters"]["max"] == 400
    assert result["words"]["min"] == 1 and result["words"]["max"] == 3
    assert result["estimated_tokens"]["max"] == 100
    assert sum(b["tickets"] for b in result["character_histogram"]) == 2


def test_read_narratives_is_read_only_and_filters_subset(tmp_path):
    path = tmp_path / "team.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row", "narrative"])
        writer.writeheader()
        writer.writerows([{"row": "7000", "narrative": "first"}, {"row": "7001", "narrative": "second one"}])
    before = path.read_bytes()
    assert read_narratives(path, {"7001"}) == ["second one"]
    assert path.read_bytes() == before


def test_read_narratives_rejects_blank_narratives(tmp_path):
    path = tmp_path / "team.csv"
    path.write_text("row,narrative\n7000,\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_narratives(path)


def test_every_workload_input_is_labelled_source_or_estimate():
    for name, entry in workload_calc.INPUTS.items():
        assert entry["kind"] in {"SOURCE", "ESTIMATE"}, name
        assert entry["note"], name


def test_count_days_for_2024_h2():
    assert workload_calc.count_days(date(2024, 7, 1), date(2024, 12, 31)) == (132, 52)


def test_rates_follow_the_documented_formulas():
    results = workload_calc.calculate()
    inputs = {name: entry["value"] for name, entry in workload_calc.INPUTS.items()}
    weekday_daily = results["weekday_tickets_per_day"]["value"]
    assert results["average_daytime_rate"]["per_hour"] == pytest.approx(
        weekday_daily * inputs["daytime_share"] / inputs["daytime_hours"], abs=0.1)
    peak = results["estimated_peak_rate"]["per_hour"]
    design = results["design_peak_rate"]["per_hour"]
    assert design >= peak * inputs["growth_headroom"] - 0.1
    assert design % inputs["design_rate_step"] == 0
    assert [r["per_hour"] for r in results["test_arrival_rates"]] == [
        design * m for m in inputs["test_rate_multipliers"]]


def test_committed_workload_results_match_the_script():
    path = ROOT / "results" / "workload" / "workload_calc.json"
    if not path.exists():  # results/ is excluded from the Docker image by .dockerignore
        pytest.skip("results/workload/workload_calc.json is not present")
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps({"inputs": workload_calc.INPUTS, "results": workload_calc.calculate()}))
