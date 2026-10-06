"""Candidate model list, documentation consistency and the digest recording script."""
import importlib.util
import re
from pathlib import Path

import httpx
import pytest

from app.candidate_models import CANDIDATE_MODELS

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "models.md").read_text(encoding="utf-8")


def load_script():
    spec = importlib.util.spec_from_file_location("record_model_digests", ROOT / "scripts" / "record_model_digests.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_three_to_five_candidates_with_unique_tags():
    tags = [m.tag for m in CANDIDATE_MODELS]
    assert 3 <= len(tags) <= 5
    assert len(set(tags)) == len(tags)
    assert all(re.fullmatch(r"[a-z0-9._-]+:[a-z0-9._-]+", t) for t in tags), "tags must be explicit name:tag"


def test_at_least_two_parameter_size_classes():
    assert len({m.size_class for m in CANDIDATE_MODELS}) >= 2


def test_every_candidate_is_documented_with_its_fields():
    for m in CANDIDATE_MODELS:
        row = next((line for line in DOC.splitlines() if f"`{m.tag}`" in line and line.startswith("|")), None)
        assert row, f"{m.tag} missing from docs/models.md table"
        assert m.name in row and m.licence in row


def test_docs_contain_no_fabricated_digests():
    # A digest, if present, must be a well-formed sha256 of 64 hex characters; a placeholder is fine.
    for match in re.findall(r"sha256:\S*", DOC):
        cleaned = match.strip("|`.,")
        assert cleaned == "sha256:" or re.fullmatch(r"sha256:[0-9a-f]{64}", cleaned), cleaned
    tags = {m.tag for m in CANDIDATE_MODELS}
    table_rows = [line for line in DOC.splitlines()
                  if line.startswith("|") and line.split("|")[2].strip().strip("`") in tags]
    assert len(table_rows) == len(CANDIDATE_MODELS)
    for row in table_rows:
        digest_cell = row.split("|")[3].strip()
        assert digest_cell == "NOT RECORDED" or re.fullmatch(r"`?sha256:[0-9a-f]{64}`?", digest_cell)


def test_application_code_does_not_hardcode_a_candidate_tag():
    for path in (ROOT / "app").rglob("*.py"):
        if path.name == "candidate_models.py":
            continue
        source = path.read_text(encoding="utf-8")
        for m in CANDIDATE_MODELS:
            assert m.tag not in source, f"{m.tag} hardcoded in {path.relative_to(ROOT)}"


def test_digest_script_reports_only_what_ollama_returns_and_marks_missing_models():
    script = load_script()
    digest = "a" * 64

    def handler(request):
        path = request.url.path
        if path == "/api/version":
            return httpx.Response(200, json={"version": "9.9.9-test"})
        if path == "/api/tags":
            return httpx.Response(200, json={"models": [
                {"name": "gemma2:2b", "digest": digest, "size": 1, "details": {"parameter_size": "2.6B"}}]})
        if path == "/api/show":
            return httpx.Response(200, json={"license": "Test Licence\nmore text",
                                             "details": {"parameter_size": "2.6B", "quantization_level": "Q4_0"}})
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        record = script.collect(client, "http://ollama.test", ["gemma2:2b", "llama3.2:3b"])
    pulled, missing = record["models"]
    assert record["ollama_version"] == "9.9.9-test"
    assert pulled["digest"] == "sha256:" + digest
    assert pulled["quantization"] == "Q4_0" and pulled["licence_first_line"] == "Test Licence"
    assert missing == {"tag": "llama3.2:3b", "status": "NOT PULLED"}  # no digest invented
    table = script.to_markdown(record)
    assert "NOT PULLED" in table and "sha256:" + digest in table
