"""Describe narrative lengths in the team's rows (read-only; the dataset is never modified).

Reports count, min, max, mean, median and p50/p75/p90/p95/p99 of characters, words and
estimated tokens, plus a character-length histogram for the slides. Percentiles use the
nearest-rank method: the smallest value with at least p% of observations at or below it.
Estimated tokens = characters / 4, a common rule of thumb for English text with
Llama-family tokenizers; it is an estimate, not a tokenizer count.

    python scripts/ticket_lengths.py data/team.csv --json results/workload/ticket_lengths.json
    python scripts/ticket_lengths.py data/team.csv --subset data/golden_set_final.csv --json ...
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median

PERCENTILES = (50, 75, 90, 95, 99)
CHARS_PER_TOKEN = 4
HISTOGRAM_EDGES = (0, 250, 500, 1000, 2000, 4000, 8000)


def nearest_rank(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("No values to summarise")
    rank = max(1, math.ceil(percentile / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def describe(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    summary = {
        "count": len(ordered),
        "min": ordered[0],
        "max": ordered[-1],
        "mean": round(mean(ordered), 1),
        "median": median(ordered),
    }
    summary.update({f"p{p}": nearest_rank(ordered, p) for p in PERCENTILES})
    return summary


def histogram(char_counts: list[int]) -> list[dict[str, int | str]]:
    bins = []
    for low, high in zip(HISTOGRAM_EDGES, HISTOGRAM_EDGES[1:] + (None,)):
        label = f"{low}-{high - 1}" if high else f"{low}+"
        count = sum(1 for c in char_counts if c >= low and (high is None or c < high))
        bins.append({"chars": label, "tickets": count, "share_pct": round(100 * count / len(char_counts), 1)})
    return bins


def read_narratives(path: Path, rows: set[str] | None = None) -> list[str]:
    csv.field_size_limit(2**31 - 1)  # sys.maxsize overflows a C long on Windows
    with path.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    if not records or "narrative" not in records[0]:
        raise ValueError(f"{path} must contain a narrative column")
    if rows is not None:
        records = [r for r in records if r["row"] in rows]
    narratives = [r["narrative"] for r in records]
    if any(not n.strip() for n in narratives):
        raise ValueError(f"{path} contains blank narratives")
    return narratives


def analyse(narratives: list[str]) -> dict:
    chars = [len(n) for n in narratives]
    return {
        "characters": describe(chars),
        "words": describe([len(n.split()) for n in narratives]),
        "estimated_tokens": describe([math.ceil(c / CHARS_PER_TOKEN) for c in chars]),
        "character_histogram": histogram(chars),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("team_csv", type=Path)
    parser.add_argument("--subset", type=Path, help="CSV whose row numbers select a subset (e.g. the golden set)")
    parser.add_argument("--json", type=Path, help="Also write the result to this file")
    args = parser.parse_args()

    narratives = read_narratives(args.team_csv)
    record = {
        "source": args.team_csv.as_posix(),
        "source_sha256": hashlib.sha256(args.team_csv.read_bytes()).hexdigest(),
        "percentile_method": "nearest-rank",
        "token_estimate": f"characters / {CHARS_PER_TOKEN} (heuristic, not a tokenizer count)",
        "all_rows": analyse(narratives),
    }
    if args.subset:
        with args.subset.open(encoding="utf-8", newline="") as handle:
            subset_rows = {r["row"] for r in csv.DictReader(handle)}
        record["subset"] = {"source": args.subset.as_posix(), **analyse(read_narratives(args.team_csv, subset_rows))}

    text = json.dumps(record, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
