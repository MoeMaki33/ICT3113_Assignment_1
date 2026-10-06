"""Calculate two-annotator agreement and create a blank disagreement-resolution file."""
import argparse
import csv
import json
from pathlib import Path

from app.categories import CATEGORIES

LABEL_COLUMN = "assigned_category"
REPORT_COLUMNS = [
    "row", "narrative", "annotator_a_label", "annotator_b_label",
    "final_resolved_label", "resolution_notes", "protocol_updated",
]


def read_annotations(path: Path) -> dict[int, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"row", "narrative", LABEL_COLUMN}.issubset(reader.fieldnames or []):
            raise ValueError(f"{path} must contain row, narrative, and {LABEL_COLUMN} columns")
        records = list(reader)
    if not records:
        raise ValueError(f"Annotation file is empty: {path}")

    annotations: dict[int, dict[str, str]] = {}
    for record in records:
        try:
            row_number = int(record["row"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid original row number in {path}: {record.get('row')!r}") from exc
        if row_number in annotations:
            raise ValueError(f"Duplicate original row number {row_number} in {path}")
        if not record.get("narrative", "").strip():
            raise ValueError(f"Missing narrative for original row {row_number} in {path}")
        label = record.get(LABEL_COLUMN, "").strip()
        if not label:
            raise ValueError(f"Missing label for original row {row_number} in {path}")
        if label not in CATEGORIES:
            raise ValueError(f"Invalid category {label!r} for original row {row_number} in {path}")
        annotations[row_number] = {
            "row": str(row_number), "narrative": record["narrative"], "label": label,
        }
    return annotations


def compare_annotations(annotator_a: dict[int, dict[str, str]],
                        annotator_b: dict[int, dict[str, str]]) -> list[tuple[dict[str, str], str]]:
    if annotator_a.keys() != annotator_b.keys():
        raise ValueError("Annotator files have mismatched original row numbers")
    comparisons = []
    for row_number in sorted(annotator_a):
        row_a, row_b = annotator_a[row_number], annotator_b[row_number]
        if row_a["narrative"] != row_b["narrative"]:
            raise ValueError(f"Annotator narratives differ for original row {row_number}")
        comparisons.append((row_a, row_b["label"]))
    return comparisons


def calculate_metrics(comparisons: list[tuple[dict[str, str], str]]) -> dict[str, int | float | None]:
    total = len(comparisons)
    if not total:
        raise ValueError("No paired annotations to compare")
    agreed = sum(row["label"] == label_b for row, label_b in comparisons)
    observed = agreed / total
    counts_a = {category: 0 for category in CATEGORIES}
    counts_b = {category: 0 for category in CATEGORIES}
    for row, label_b in comparisons:
        counts_a[row["label"]] += 1
        counts_b[label_b] += 1
    expected = sum(counts_a[c] * counts_b[c] for c in CATEGORIES) / (total * total)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else None
    return {
        "total_tickets": total,
        "agreed": agreed,
        "disagreed": total - agreed,
        "raw_percentage_agreement": 100 * observed,
        "cohens_kappa": kappa,
    }


def write_disagreements(path: Path, comparisons: list[tuple[dict[str, str], str]]) -> int:
    disagreements = [(row, label_b) for row, label_b in comparisons if row["label"] != label_b]
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        for row, label_b in disagreements:
            writer.writerow({
                "row": row["row"], "narrative": row["narrative"],
                "annotator_a_label": row["label"], "annotator_b_label": label_b,
                "final_resolved_label": "", "resolution_notes": "", "protocol_updated": "",
            })
    return len(disagreements)


def calculate_agreement(annotator_a_path: Path, annotator_b_path: Path) -> tuple[dict, list[tuple[dict[str, str], str]]]:
    annotator_a = read_annotations(annotator_a_path)
    annotator_b = read_annotations(annotator_b_path)
    comparisons = compare_annotations(annotator_a, annotator_b)
    return calculate_metrics(comparisons), comparisons


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotator_a", type=Path)
    parser.add_argument("annotator_b", type=Path)
    parser.add_argument("--disagreements", type=Path, default=Path("data/disagreements.csv"))
    args = parser.parse_args()
    metrics, comparisons = calculate_agreement(args.annotator_a, args.annotator_b)
    report_count = write_disagreements(args.disagreements, comparisons)
    print(json.dumps(metrics, indent=2))
    print(f"Blank disagreement-resolution rows written: {report_count}")
