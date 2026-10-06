"""Validate human resolutions and create a new, freeze-protected final golden CSV."""
import argparse
import csv
from pathlib import Path

from app.categories import CATEGORIES
from scripts.agreement import compare_annotations, read_annotations

MIN_TICKETS = 150
MAX_TICKETS = 200
REPORT_COLUMNS = {
    "row", "narrative", "annotator_a_label", "annotator_b_label",
    "final_resolved_label", "resolution_notes", "protocol_updated",
}
FINAL_COLUMNS = ["row", "narrative", "final_golden_category"]


def read_resolution_report(path: Path) -> dict[int, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not REPORT_COLUMNS.issubset(reader.fieldnames or []):
            raise ValueError("Disagreement report is missing required resolution columns")
        records = list(reader)
    resolutions = {}
    for record in records:
        try:
            row_number = int(record["row"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid row number in disagreement report: {record.get('row')!r}") from exc
        if row_number in resolutions:
            raise ValueError(f"Duplicate original row number {row_number} in disagreement report")
        resolutions[row_number] = record
    return resolutions


def finalize(annotator_a_path: Path, annotator_b_path: Path,
             disagreement_path: Path, output: Path) -> int:
    annotator_a = read_annotations(annotator_a_path)
    annotator_b = read_annotations(annotator_b_path)
    comparisons = compare_annotations(annotator_a, annotator_b)
    if not MIN_TICKETS <= len(comparisons) <= MAX_TICKETS:
        raise ValueError(f"Final golden set must contain {MIN_TICKETS}-{MAX_TICKETS} tickets")

    resolutions = read_resolution_report(disagreement_path)
    actual_disagreements = {
        row["row"]: (row, label_b)
        for row, label_b in comparisons if row["label"] != label_b
    }
    if set(resolutions) != {int(row_number) for row_number in actual_disagreements}:
        raise ValueError("Disagreement report rows do not exactly match annotator disagreements")

    final_labels = {}
    for row_number, (row_a, label_b) in actual_disagreements.items():
        report = resolutions[int(row_number)]
        if report["narrative"] != row_a["narrative"]:
            raise ValueError(f"Disagreement narrative changed for original row {row_number}")
        if report["annotator_a_label"] != row_a["label"] or report["annotator_b_label"] != label_b:
            raise ValueError(f"Disagreement labels changed for original row {row_number}")
        label = report["final_resolved_label"].strip()
        if not label:
            raise ValueError(f"Unresolved disagreement for original row {row_number}")
        if label not in CATEGORIES:
            raise ValueError(f"Invalid resolved category {label!r} for original row {row_number}")
        if not report["resolution_notes"].strip():
            raise ValueError(f"Missing resolution notes for original row {row_number}")
        if report["protocol_updated"].strip().casefold() not in {"yes", "no"}:
            raise ValueError(f"protocol_updated must be yes or no for original row {row_number}")
        final_labels[int(row_number)] = label

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINAL_COLUMNS)
        writer.writeheader()
        for row, label_b in comparisons:
            row_number = int(row["row"])
            writer.writerow({
                "row": row["row"],
                "narrative": row["narrative"],
                "final_golden_category": final_labels.get(row_number, row["label"]),
            })
    return len(comparisons)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotator_a", type=Path)
    parser.add_argument("annotator_b", type=Path)
    parser.add_argument("disagreements", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/golden_set_final.csv"))
    args = parser.parse_args()
    count = finalize(args.annotator_a, args.annotator_b, args.disagreements, args.output)
    print(f"Created final golden set with {count} manually labelled tickets: {args.output}")


if __name__ == "__main__":
    main()