"""Extract a team's course CSV rows; never submit or seed service tickets."""
import argparse
import csv
from pathlib import Path


def extract(source: Path, output: Path, team_number: int, narrative_column: str) -> None:
    if team_number < 0:
        raise ValueError("Team number must be nonnegative")
    start = team_number * 1000
    end = start + 999
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if narrative_column not in (reader.fieldnames or []):
            raise ValueError(f"Missing narrative column: {narrative_column}")
        rows = []
        # Zero-based data rows, excluding the header. Confirm with the course.
        for index, record in enumerate(reader):
            if index > end:
                break
            if index >= start:
                rows.append({"row": index, "narrative": record[narrative_column]})
    if len(rows) != 1000:
        raise ValueError("Source does not contain the full assigned 1000-row range")
    with output.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row", "narrative"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--team-number", required=True, type=int)
    parser.add_argument("--narrative-column", required=True)
    args = parser.parse_args()
    extract(args.source, args.output, args.team_number, args.narrative_column)


if __name__ == "__main__":
    main()
