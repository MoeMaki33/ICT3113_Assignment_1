"""Record real provenance (digest, quantisation, licence) of pulled candidate models.

Queries a running Ollama server; nothing is invented. A candidate that has not been
pulled is reported as NOT PULLED. Run after `ollama pull <tag>` for each candidate:

    python scripts/record_model_digests.py                 # table on stdout
    python scripts/record_model_digests.py --json out.json # also save raw record
    python scripts/record_model_digests.py --url http://localhost:11434 gemma2:2b

The digest is the full sha256 from Ollama's /api/tags (the ID column of
`ollama list` is its first 12 characters).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.candidate_models import CANDIDATE_MODELS  # noqa: E402


def collect(client: httpx.Client, base_url: str, tags: list[str]) -> dict:
    """Return {'ollama_version', 'recorded_at', 'models': [...]} from a live server."""
    base = base_url.rstrip("/")
    version = client.get(f"{base}/api/version").raise_for_status().json().get("version")
    installed = {
        m.get("name"): m for m in client.get(f"{base}/api/tags").raise_for_status().json().get("models", [])
    }
    records = []
    for tag in tags:
        entry = installed.get(tag)
        if entry is None:
            records.append({"tag": tag, "status": "NOT PULLED"})
            continue
        show = client.post(f"{base}/api/show", json={"model": tag}).raise_for_status().json()
        details = show.get("details") or entry.get("details") or {}
        licence_text = show.get("license") or ""
        records.append({
            "tag": tag,
            "status": "pulled",
            "digest": "sha256:" + entry["digest"] if entry.get("digest") and not entry["digest"].startswith("sha256:")
            else entry.get("digest"),
            "parameter_size": details.get("parameter_size"),
            "quantization": details.get("quantization_level"),
            "family": details.get("family"),
            "size_bytes": entry.get("size"),
            # First line of the licence text only, as an identifier to check by eye.
            "licence_first_line": licence_text.strip().splitlines()[0] if licence_text.strip() else None,
        })
    return {
        "ollama_version": version,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "models": records,
    }


def to_markdown(record: dict) -> str:
    rows = ["| Tag | Status | Digest | Parameter size | Quantisation | Licence (first line) |", "|---|---|---|---|---|---|"]
    for m in record["models"]:
        rows.append("| `{tag}` | {status} | {digest} | {p} | {q} | {lic} |".format(
            tag=m["tag"], status=m["status"], digest=m.get("digest") or "-",
            p=m.get("parameter_size") or "-", q=m.get("quantization") or "-",
            lic=m.get("licence_first_line") or "-",
        ))
    return f"Ollama version: {record['ollama_version']}  (recorded {record['recorded_at']})\n\n" + "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tags", nargs="*", help="Tags to record (default: all candidates)")
    parser.add_argument("--url", default=os.getenv("OLLAMA_URL_LOCAL", "http://localhost:11434"))
    parser.add_argument("--json", type=Path, help="Also write the raw record to this file")
    args = parser.parse_args()
    tags = args.tags or [m.tag for m in CANDIDATE_MODELS]
    try:
        with httpx.Client(timeout=30.0) as client:
            record = collect(client, args.url, tags)
    except httpx.HTTPError as exc:
        print(f"Could not query Ollama at {args.url}: {type(exc).__name__}. Is `ollama serve` running?", file=sys.stderr)
        return 1
    print(to_markdown(record))
    if args.json:
        args.json.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
