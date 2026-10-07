"""Read-only validation of the golden set and its human annotation provenance.

Run: python -m scripts.validate_golden_set
No labels, manifests or evidence are changed. A raw source hash mismatch requires
an explicit provenance review and successful independent content checks.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.categories import CATEGORIES
from scripts.agreement import calculate_agreement
from scripts.create_golden_set import read_team_rows, select_rows
from scripts.finalize_golden_set import finalize

ROOT = Path(__file__).resolve().parents[1]
REVIEWED_ARTIFACTS = (
    "data/ict3113_tickets.csv", "data/golden_set_final.csv",
    "data/labelling/annotator_a.csv", "data/labelling/annotator_b.csv",
    "data/labelling/disagreements.csv", "results/accuracy/agreement.json",
)


def selection_identity_sha256(selection: dict) -> str:
    """Bind the review to the original selection, without hashing its added metadata."""
    identity = {key: selection[key] for key in
                ("team_number", "count", "seed", "selection_method", "original_rows")}
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def provenance_review_problems(root: Path, selection: dict, actual_hash: str) -> list[str]:
    review = selection.get("source_provenance_review")
    if not isinstance(review, dict):
        return ["selection.json source_sha256 differs from data/team.csv; review historical provenance"]
    problems = []
    expected = {
        "original_source_sha256": selection["source_sha256"],
        "canonical_source_sha256": actual_hash,
        "selection_identity_sha256": selection_identity_sha256(selection),
        "original_source_status": "not_located_in_available_git_history",
        "documentation": "docs/golden_set_provenance.md",
    }
    for key, value in expected.items():
        if review.get(key) != value:
            problems.append(f"source provenance review missing or inconsistent: {key}")
    commit = review.get("inspected_source_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        problems.append("source provenance review missing or inconsistent: inspected_source_commit")
    evidence = review.get("artifacts_sha256")
    if not isinstance(evidence, dict) or set(evidence) != set(REVIEWED_ARTIFACTS):
        problems.append("source provenance review must pin all required evidence files")
    else:
        for name in REVIEWED_ARTIFACTS:
            if evidence[name] != hashlib.sha256((root / name).read_bytes()).hexdigest():
                problems.append(f"source provenance reviewed evidence hash differs: {name}")
    documentation = (root / "docs/golden_set_provenance.md").read_text(encoding="utf-8")
    for value in (selection["source_sha256"], actual_hash, commit):
        if not isinstance(value, str) or value not in documentation:
            problems.append("source provenance documentation does not match review hashes/commit")
            break
    return problems


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def golden_file_problems(path: Path) -> list[str]:
    try:
        rows = read_csv(path)
        if not 150 <= len(rows) <= 200:
            return ["golden set must contain 150-200 tickets"]
        if not {"row", "narrative", "final_golden_category"} <= set(rows[0]):
            return ["golden set is missing required columns"]
        ids = [int(r["row"]) for r in rows]
        if len(set(ids)) != len(ids) or any(i < 0 for i in ids):
            return ["golden set has duplicate or negative source row identifiers"]
        if any(not (r.get("narrative") or "").strip() or r.get("final_golden_category") not in CATEGORIES
               for r in rows):
            return ["golden set has missing narratives or invalid/incomplete human labels"]
    except (OSError, ValueError, TypeError, csv.Error) as exc:
        return [f"cannot validate golden set: {type(exc).__name__}"]
    return []


def validate(root: Path = ROOT) -> dict:
    problems = golden_file_problems(root / "data/golden_set_final.csv")
    checks = {}
    warnings = []
    reviewed_mismatch = False
    try:
        selection = json.loads((root / "data/labelling/selection.json").read_text(encoding="utf-8"))
        for key in ("team_number", "count", "seed"):
            if type(selection[key]) is not int:
                raise ValueError(f"selection {key} must be an integer")
        team_path = root / "data/team.csv"
        team = read_team_rows(team_path, selection["team_number"])
        actual_hash = hashlib.sha256(team_path.read_bytes()).hexdigest()
        checks["team_sha256"] = actual_hash
        checks["selection_source_sha256"] = selection["source_sha256"]
        mismatch = actual_hash != selection["source_sha256"]
        if mismatch or "source_provenance_review" in selection:
            review_problems = provenance_review_problems(root, selection, actual_hash)
            problems.extend(review_problems)
            reviewed_mismatch = mismatch and not review_problems
        selected = select_rows(team, selection["count"], selection["seed"])
        if [int(r["row"]) for r in selected] != selection["original_rows"]:
            problems.append("selection manifest cannot be reproduced from team rows and seed")
        golden = read_csv(root / "data/golden_set_final.csv")
        if [{"row": r.get("row"), "narrative": r.get("narrative")} for r in golden] != selected:
            problems.append("golden rows/narratives differ from deterministic team selection")
        # Stream the original course extract; do not copy or relabel its narratives.
        expected = {r["row"]: r["narrative"] for r in team}
        seen = set()
        with (root / "data/ict3113_tickets.csv").open(encoding="utf-8-sig", newline="") as handle:
            for index, row in enumerate(csv.DictReader(handle)):
                if str(index) in expected:
                    if row.get("row") != str(index) or row.get("narrative") != expected[str(index)]:
                        problems.append(f"course source mismatch at assigned row {index}")
                    seen.add(str(index))
        if seen != set(expected):
            problems.append("course extract does not contain every assigned team row")
        a, b = (root / f"data/labelling/annotator_{name}.csv" for name in ("a", "b"))
        metrics, _ = calculate_agreement(a, b)
        checks["agreement"] = metrics
        recorded = json.loads((root / "results/accuracy/agreement.json").read_text(encoding="utf-8"))
        for key, value in metrics.items():
            stored = recorded.get(key)
            if (value is None and stored is not None) or (value is not None and
                    (stored is None or not math.isclose(value, stored, abs_tol=1e-12))):
                problems.append(f"recorded agreement metric differs: {key}")
        for name, path in (("a", a), ("b", b)):
            if recorded.get("inputs", {}).get(f"data/labelling/annotator_{name}.csv") != hashlib.sha256(path.read_bytes()).hexdigest():
                problems.append(f"annotator {name} hash differs from agreement evidence")
        with tempfile.TemporaryDirectory() as directory:
            regenerated = Path(directory) / "golden.csv"
            finalize(a, b, root / "data/labelling/disagreements.csv", regenerated)
            if read_csv(regenerated) != golden:
                problems.append("golden labels differ from human agreement/adjudication records")
        checks["golden_tickets"] = len(golden)
        checks["team_number"] = selection["team_number"]
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as exc:
        problems.append(f"annotation/source evidence validation failed: {exc}")
    if reviewed_mismatch and not problems:
        warnings.append("historical selection source raw-byte hash differs from current canonical "
                        "team.csv; documented provenance review, deterministic selection, course "
                        "content and human annotation/adjudication integrity verified")
    return {"valid": not problems, "checks": checks, "warnings": warnings, "problems": problems}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    report = validate(args.root)
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
