"""Select a reproducible golden-set sample and create independent blank sheets."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ANNOTATION_COLUMNS = ["row", "narrative", "assigned_category", "notes"]
MIN_TICKETS = 150
MAX_TICKETS = 200


def read_team_rows(source: Path, team_number: int) -> list[dict[str, str]]:
    if team_number < 0:
        raise ValueError("Team number must be nonnegative")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"row", "narrative"}.issubset(reader.fieldnames or []):
            raise ValueError("Team CSV must contain row and narrative columns")
        rows = list(reader)

    expected_rows = set(range(team_number * 1000, team_number * 1000 + 1000))
    by_row: dict[int, dict[str, str]] = {}
    for record in rows:
        try:
            row_number = int(record["row"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid original row number: {record.get('row')!r}") from exc
        if row_number in by_row:
            raise ValueError(f"Duplicate original row number: {row_number}")
        if not record.get("narrative", "").strip():
            raise ValueError(f"Missing narrative for original row {row_number}")
        by_row[row_number] = {"row": str(row_number), "narrative": record["narrative"]}

    if set(by_row) != expected_rows:
        raise ValueError("Team CSV must contain exactly the assigned 1000 original row numbers")
    return [by_row[row_number] for row_number in sorted(by_row)]


def select_rows(rows: list[dict[str, str]], count: int, seed: int) -> list[dict[str, str]]:
    if not MIN_TICKETS <= count <= MAX_TICKETS:
        raise ValueError(f"Golden-set size must be between {MIN_TICKETS} and {MAX_TICKETS}")
    if seed < 0:
        raise ValueError("Seed must be nonnegative")
    ranked = sorted(
        rows,
        key=lambda row: hashlib.sha256(
            json.dumps([seed, row["row"], row["narrative"]], ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")
        ).digest(),
    )
    return sorted(ranked[:count], key=lambda row: int(row["row"]))


def prepare(source: Path, output_dir: Path, team_number: int, count: int, seed: int) -> list[int]:
    rows = read_team_rows(source, team_number)
    selected = select_rows(rows, count, seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / "annotator_a.csv", output_dir / "annotator_b.csv", output_dir / "selection.json"]
    existing = [path for path in outputs if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing output: {existing[0]}")

    for path in outputs[:2]:
        with path.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=ANNOTATION_COLUMNS)
            writer.writeheader()
            writer.writerows({**row, "assigned_category": "", "notes": ""} for row in selected)

    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = {
        "team_number": team_number,
        "count": count,
        "seed": seed,
        "selection_method": "SHA-256 rank of seed, original row number, and narrative; selected rows sorted by original row number",
        "source_sha256": source_digest,
        "original_rows": [int(row["row"]) for row in selected],
    }
    with outputs[2].open("x", encoding="utf-8", newline="") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    return manifest["original_rows"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("team_csv", type=Path, help="Extracted CSV containing only the team's 1000 rows")
    parser.add_argument("--team-number", required=True, type=int)
    parser.add_argument("--count", type=int, default=180)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output-dir", type=Path, default=Path("data/labelling"))
    args = parser.parse_args()
    rows = prepare(args.team_csv, args.output_dir, args.team_number, args.count, args.seed)
    print(f"Created two blank annotation sheets for {len(rows)} selected tickets.")
    print(f"Selected row span: {rows[0]} through {rows[-1]} (selection.json has the exact row list).")


if __name__ == "__main__":
    main()
