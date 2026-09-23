"""Prepare blank manual annotation columns; source labels are not ground truth."""
import argparse
import csv
from pathlib import Path

COLUMNS = ["row", "narrative", "annotator_1", "annotator_2", "final_label", "notes"]


def prepare(source: Path, output: Path) -> None:
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"row", "narrative"}.issubset(reader.fieldnames or []):
            raise ValueError("Input must contain row and narrative columns")
        rows = [{"row": row["row"], "narrative": row["narrative"]} for row in reader]
    with output.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)


if __name__ == "__main__":
    main()
