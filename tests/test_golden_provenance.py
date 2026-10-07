"""Provenance exceptions must never admit changed selection or human evidence."""
import csv
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.categories import CATEGORIES
from scripts.validate_golden_set import (
    REVIEWED_ARTIFACTS, selection_identity_sha256, validate,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def evidence_root(tmp_path):
    for name in (*REVIEWED_ARTIFACTS, "data/team.csv", "data/labelling/selection.json",
                 "docs/golden_set_provenance.md"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return tmp_path


def change_manifest(root, change):
    path = root / "data/labelling/selection.json"
    selection = json.loads(path.read_text(encoding="utf-8"))
    change(selection)
    path.write_text(json.dumps(selection), encoding="utf-8")


def test_documented_mismatch_passes_with_explicit_warning(evidence_root):
    report = validate(evidence_root)
    assert report["valid"] and not report["problems"]
    assert len(report["warnings"]) == 1
    assert report["checks"]["team_sha256"] != report["checks"]["selection_source_sha256"]


@pytest.mark.parametrize("field", [None, "original_source_sha256", "canonical_source_sha256",
                                  "selection_identity_sha256", "original_source_status",
                                  "inspected_source_commit", "artifacts_sha256", "documentation"])
def test_missing_review_metadata_is_fatal(evidence_root, field):
    def remove(selection):
        if field is None:
            del selection["source_provenance_review"]
        else:
            del selection["source_provenance_review"][field]
    change_manifest(evidence_root, remove)
    report = validate(evidence_root)
    assert not report["valid"] and report["problems"] and not report["warnings"]


@pytest.mark.parametrize("name", ["data/team.csv", *REVIEWED_ARTIFACTS])
def test_changed_raw_evidence_is_fatal(evidence_root, name):
    # Even byte changes ignored by a CSV reader require a new explicit review.
    with (evidence_root / name).open("ab") as handle:
        handle.write(b"\n")
    report = validate(evidence_root)
    assert not report["valid"] and report["problems"] and not report["warnings"]


@pytest.mark.parametrize("field,value", [("team_number", 8), ("seed", -1),
                                        ("seed", "3113"), ("count", 149), ("count", True)])
def test_invalid_selection_parameters_are_fatal(evidence_root, field, value):
    change_manifest(evidence_root, lambda selection: selection.update({field: value}))
    assert not validate(evidence_root)["valid"]


def test_repinning_changed_seed_does_not_bypass_deterministic_selection(evidence_root):
    def change(selection):
        selection["seed"] += 1
        selection["source_provenance_review"]["selection_identity_sha256"] = selection_identity_sha256(selection)
    change_manifest(evidence_root, change)
    report = validate(evidence_root)
    assert not report["valid"]
    assert "selection manifest cannot be reproduced from team rows and seed" in report["problems"]


@pytest.mark.parametrize("column", ["narrative", "final_golden_category"])
def test_repinning_golden_changes_does_not_bypass_content_or_human_checks(evidence_root, column):
    name = "data/golden_set_final.csv"
    path = evidence_root / name
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames, list(reader)
    rows[0][column] = (rows[0][column] + " changed" if column == "narrative" else
                       next(category for category in CATEGORIES if category != rows[0][column]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    def repin(selection):
        selection["source_provenance_review"]["artifacts_sha256"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    change_manifest(evidence_root, repin)
    report = validate(evidence_root)
    assert not report["valid"] and not report["warnings"]
    assert "golden labels differ from human agreement/adjudication records" in report["problems"]
