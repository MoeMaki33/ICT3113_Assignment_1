"""Shared helpers for the Person 5 test tooling (load, stress, accuracy, reconciliation).

Nothing here sends traffic or produces measurements. It provides:

- the freeze gate that official benchmark runs must pass;
- result-directory naming (``results/<kind>/<model-dir>/rate-<X>/run-<N>.jtl``);
- reading JMeter ``.jtl`` CSV files and the nearest-rank percentile used everywhere.
"""
import csv
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_SET = Path("data/golden_set_final.csv")
PREDICTION_RECORD = Path("docs/prediction_record.md")
_DRAFT_RE = re.compile(r"Status:\s*\**\s*(DRAFT|PROPOSED)", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def model_dir(tag: str) -> str:
    """Directory-safe form of an exact Ollama tag (``qwen2.5:7b`` -> ``qwen2.5_7b``).

    Colons are not allowed in Windows paths; the exact tag is always kept in metadata.
    """
    if not tag or not tag.strip():
        raise ValueError("A model tag is required")
    return re.sub(r"[^A-Za-z0-9._-]", "_", tag.strip())


def rate_label(rate: float) -> str:
    return f"{rate:g}"


def config_dir_name(rate: float, search_rate: float = 0) -> str:
    name = f"rate-{rate_label(rate)}"
    return f"{name}_search-{rate_label(search_rate)}" if search_rate else name


def next_run_number(directory: Path) -> int:
    taken = [int(m.group(1)) for p in directory.glob("run-*.jtl")
             if (m := re.fullmatch(r"run-(\d+)\.jtl", p.name))]
    return max(taken, default=0) + 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(args: list[str], root: Path) -> str | None:
    try:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def git_info(root: Path = ROOT) -> dict:
    status = _git(["status", "--porcelain"], root)
    return {
        "commit": _git(["rev-parse", "HEAD"], root),
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"], root),
        "worktree_clean": status == "" if status is not None else None,
    }


def freeze_gate_problems(root: Path = ROOT) -> list[str]:
    """Reasons official benchmarking is NOT yet allowed (empty list = allowed).

    Official runs require the golden set and the prediction record to be committed,
    unmodified in the working tree, and the prediction record to be out of DRAFT/PROPOSED.
    """
    problems = []
    if _git(["rev-parse", "--git-dir"], root) is None:
        return ["Not a git repository (or git is unavailable): cannot prove the freeze commit"]
    for path in (GOLDEN_SET, PREDICTION_RECORD):
        if not (root / path).is_file():
            problems.append(f"{path.as_posix()} does not exist")
            continue
        if _git(["ls-files", "--error-unmatch", path.as_posix()], root) is None:
            problems.append(f"{path.as_posix()} is not committed to git")
        elif _git(["status", "--porcelain", "--", path.as_posix()], root):
            problems.append(f"{path.as_posix()} has uncommitted changes")
    record = root / PREDICTION_RECORD
    if record.is_file():
        match = _DRAFT_RE.search(record.read_text(encoding="utf-8"))
        if match:
            problems.append(f"{PREDICTION_RECORD.as_posix()} is still marked {match.group(1).upper()}")
    return problems


def nearest_rank(sorted_values: list[float], percentile: float) -> float:
    """Smallest value with at least ``percentile``% of observations at or below it.

    Same method as scripts/ticket_lengths.py, so every percentile in the report is computed
    the same way.
    """
    if not sorted_values:
        raise ValueError("No values to summarise")
    rank = max(1, math.ceil(percentile / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


JTL_REQUIRED = ("timeStamp", "elapsed", "label", "responseCode", "success")


def read_jtl(path: Path) -> list[dict]:
    """Read a JMeter CSV result file into normalised sample dicts (file is not modified)."""
    csv.field_size_limit(2**31 - 1)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in JTL_REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path} is not a JMeter CSV result file (missing columns: {missing})")
        samples = []
        for raw in reader:
            start = int(raw["timeStamp"])
            elapsed = int(raw["elapsed"])
            request_id = (raw.get("request_id") or "").strip()
            samples.append({
                "start_ms": start,
                "elapsed_ms": elapsed,
                "end_ms": start + elapsed,
                "label": raw["label"],
                "response_code": raw["responseCode"],
                "success": raw["success"].strip().lower() == "true",
                "failure_message": raw.get("failureMessage") or raw.get("responseMessage") or "",
                "request_id": request_id if request_id and request_id != "NO_REQUEST_ID" else None,
                "ticket_row": raw.get("ticket_row") or None,
            })
    return samples


def read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
