"""Prepare JMeter input files from the team's rows (read-only on the source data).

JMeter's CSV Data Set Config cannot safely carry narratives that contain quotes, commas
or line breaks into a JSON body. This script writes each narrative already JSON-encoded
(``json.dumps``), so the request body is simply ``{"narrative": ${narrative_json}}``:

- ``jmeter/data/team_narratives.tsv``: ``row<TAB>narrative_json`` for every team row, in
  row order. JSON encoding escapes tabs and newlines, so each record is one line.
- ``jmeter/data/search_terms.txt``: fixed search terms for the mixed load test (R4).

The CSV is never imported into the service: tickets only enter through POST /tickets.

    python -m scripts.prepare_jmeter_data data/team.csv
"""
import argparse
import csv
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.perf_common import sha256_file, write_json

# Short literal terms a complaints agent might look up. Fixed and versioned so every search
# run uses the same queries. They are test inputs chosen by Person 5, not dataset statistics.
SEARCH_TERMS = (
    "credit report", "collection", "mortgage", "escrow", "foreclosure", "credit card",
    "late fee", "interest", "overdraft", "checking account", "savings", "deposit",
    "wire transfer", "money order", "loan", "payment", "dispute", "fraud", "refund", "bank",
)


def prepare(team_csv: Path, out_dir: Path) -> dict:
    csv.field_size_limit(2**31 - 1)
    with team_csv.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    if not records or not {"row", "narrative"} <= set(records[0]):
        raise ValueError(f"{team_csv} must have columns row,narrative")
    out_dir.mkdir(parents=True, exist_ok=True)
    narratives = out_dir / "team_narratives.tsv"
    with narratives.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            if not record["narrative"].strip():
                raise ValueError(f"Row {record['row']} has an empty narrative")
            encoded = json.dumps(record["narrative"], ensure_ascii=True)
            assert "\t" not in encoded and "\n" not in encoded
            handle.write(f"{int(record['row'])}\t{encoded}\n")
    terms = out_dir / "search_terms.txt"
    terms.write_text("\n".join(SEARCH_TERMS) + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "source": team_csv.as_posix(),
        "source_sha256": sha256_file(team_csv),
        "narratives_file": narratives.as_posix(),
        "narratives_sha256": sha256_file(narratives),
        "narrative_count": len(records),
        "search_terms_file": terms.as_posix(),
        "search_terms_sha256": sha256_file(terms),
        "search_term_count": len(SEARCH_TERMS),
    }
    write_json(out_dir / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("team_csv", type=Path, nargs="?", default=Path("data/team.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("jmeter/data"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.team_csv, args.out_dir), indent=2))
