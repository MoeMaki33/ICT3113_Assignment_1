"""Tests for reproducible sampling and human-controlled golden-set validation."""
import csv
from pathlib import Path

import pytest

from app.categories import CATEGORIES
from scripts.agreement import calculate_agreement, calculate_metrics, write_disagreements
from scripts.create_golden_set import ANNOTATION_COLUMNS, prepare
from scripts.finalize_golden_set import finalize


def make_team_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row", "narrative"])
        writer.writeheader()
        writer.writerows({"row": row, "narrative": f"Synthetic fixture narrative {row}"}
                         for row in range(1000))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_selection_is_reproducible_and_creates_independent_blank_sheets(tmp_path):
    source = tmp_path / "team.csv"
    make_team_csv(source)
    first_dir, second_dir = tmp_path / "first", tmp_path / "second"

    selected = prepare(source, first_dir, team_number=0, count=150, seed=42)
    assert prepare(source, second_dir, team_number=0, count=150, seed=42) == selected
    first_a, first_b = read_csv(first_dir / "annotator_a.csv"), read_csv(first_dir / "annotator_b.csv")
    assert len(first_a) == 150
    assert first_a == first_b
    assert list(first_a[0]) == ANNOTATION_COLUMNS
    assert all(not row["assigned_category"] and not row["notes"] for row in first_a)
    assert selected == [int(row["row"]) for row in first_a]
    assert read_csv(first_dir / "annotator_a.csv") == read_csv(second_dir / "annotator_a.csv")


def test_selection_rejects_invalid_count_and_existing_outputs(tmp_path):
    source = tmp_path / "team.csv"
    make_team_csv(source)
    with pytest.raises(ValueError, match="between 150 and 200"):
        prepare(source, tmp_path / "invalid", team_number=0, count=149, seed=1)
    output_dir = tmp_path / "existing"
    prepare(source, output_dir, team_number=0, count=150, seed=1)
    with pytest.raises(FileExistsError):
        prepare(source, output_dir, team_number=0, count=150, seed=1)


def test_metrics_use_all_seven_category_slots_and_report_undefined_kappa():
    comparisons = [
        ({"label": CATEGORIES[0]}, CATEGORIES[0]),
        ({"label": CATEGORIES[0]}, CATEGORIES[0]),
    ]
    assert calculate_metrics(comparisons) == {
        "total_tickets": 2,
        "agreed": 2,
        "disagreed": 0,
        "raw_percentage_agreement": 100.0,
        "cohens_kappa": None,
    }


def test_metrics_calculate_finite_cohens_kappa():
    comparisons = [
        ({"label": CATEGORIES[0]}, CATEGORIES[0]),
        ({"label": CATEGORIES[1]}, CATEGORIES[2]),
    ]
    metrics = calculate_metrics(comparisons)
    assert metrics["total_tickets"] == 2
    assert metrics["agreed"] == 1
    assert metrics["disagreed"] == 1
    assert metrics["raw_percentage_agreement"] == 50.0
    assert metrics["cohens_kappa"] == pytest.approx(1 / 3)


def test_end_to_end_agreement_and_finalize_require_human_resolution(tmp_path):
    source = tmp_path / "team.csv"
    make_team_csv(source)
    annotation_dir = tmp_path / "annotations"
    prepare(source, annotation_dir, team_number=0, count=150, seed=19)
    path_a, path_b = annotation_dir / "annotator_a.csv", annotation_dir / "annotator_b.csv"
    records_a, records_b = read_csv(path_a), read_csv(path_b)
    for index, (row_a, row_b) in enumerate(zip(records_a, records_b)):
        label = CATEGORIES[index % len(CATEGORIES)]
        row_a["assigned_category"] = label
        row_b["assigned_category"] = label
    records_b[0]["assigned_category"] = CATEGORIES[(0 + 1) % len(CATEGORIES)]
    for path, records in ((path_a, records_a), (path_b, records_b)):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=ANNOTATION_COLUMNS)
            writer.writeheader()
            writer.writerows(records)

    metrics, comparisons = calculate_agreement(path_a, path_b)
    report = annotation_dir / "disagreements.csv"
    assert write_disagreements(report, comparisons) == 1
    assert metrics["total_tickets"] == 150
    report_rows = read_csv(report)
    assert len(report_rows) == 1
    assert report_rows[0]["final_resolved_label"] == ""
    assert report_rows[0]["resolution_notes"] == ""
    assert report_rows[0]["protocol_updated"] == ""

    output = tmp_path / "golden_set_final.csv"
    with pytest.raises(ValueError, match="Unresolved disagreement"):
        finalize(path_a, path_b, report, output)
    report_rows[0].update({
        "final_resolved_label": CATEGORIES[0],
        "resolution_notes": "Human resolution recorded in test fixture",
        "protocol_updated": "no",
    })
    with report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=report_rows[0].keys())
        writer.writeheader()
        writer.writerows(report_rows)

    assert finalize(path_a, path_b, report, output) == 150
    final_rows = read_csv(output)
    assert len(final_rows) == 150
    assert list(final_rows[0]) == ["row", "narrative", "final_golden_category"]
    assert final_rows[0]["final_golden_category"] == CATEGORIES[0]
    with pytest.raises(FileExistsError):
        finalize(path_a, path_b, report, output)


def test_agreement_rejects_mismatched_annotator_rows(tmp_path):
    path_a, path_b = tmp_path / "a.csv", tmp_path / "b.csv"
    for path, row_number in ((path_a, 10), (path_b, 11)):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=ANNOTATION_COLUMNS)
            writer.writeheader()
            writer.writerow({"row": row_number, "narrative": "Fixture",
                             "assigned_category": CATEGORIES[0], "notes": ""})
    with pytest.raises(ValueError, match="mismatched original row numbers"):
        calculate_agreement(path_a, path_b)