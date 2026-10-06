"""Candidate Ollama models for the Assignment 1 classification comparison.

This module is data only; the application never imports it. The running service
uses whatever tag is in OLLAMA_MODEL. Exact digests are intentionally NOT stored
here: they must be read from the machine that pulled the model (see
scripts/record_model_digests.py and docs/models.md) and are never typed by hand.

All tags are official Ollama library tags that run on CPU (the client requests
num_gpu=0). ``licence`` is the upstream licence name as commonly published;
confirm it locally with ``ollama show <tag> --license``.
"""
from dataclasses import dataclass

SMALL = "Small (2-4B)"
MEDIUM = "Medium (7-9B)"


@dataclass(frozen=True)
class CandidateModel:
    name: str
    tag: str            # exact tag passed to `ollama pull` and to OLLAMA_MODEL
    size_class: str
    approx_params: str  # upstream figure; the exact value comes from `ollama show`
    licence: str
    rationale: str


CANDIDATE_MODELS: tuple[CandidateModel, ...] = (
    CandidateModel(
        name="Gemma 2 2B",
        tag="gemma2:2b",
        size_class=SMALL,
        approx_params="2.6B",
        licence="Gemma Terms of Use",
        rationale="Smallest candidate and the fastest CPU baseline; shows how far a ~2B model gets on "
                  "seven-way complaint classification.",
    ),
    CandidateModel(
        name="Llama 3.2 3B",
        tag="llama3.2:3b",
        size_class=SMALL,
        approx_params="3.2B",
        licence="Llama 3.2 Community License",
        rationale="Instruction-tuned ~3B model that follows 'reply with the label only' well; a "
                  "different family from Gemma at a similar size, so size and family can be compared.",
    ),
    CandidateModel(
        name="Qwen2.5 7B",
        tag="qwen2.5:7b",
        size_class=MEDIUM,
        approx_params="7.6B",
        licence="Apache-2.0",
        rationale="Strong instruction following and text classification for its size, with a permissive "
                  "licence; the main 7B-class candidate.",
    ),
    CandidateModel(
        name="Llama 3.1 8B",
        tag="llama3.1:8b",
        size_class=MEDIUM,
        approx_params="8.0B",
        licence="Llama 3.1 Community License",
        rationale="Widely used 8B reference model; pairs with Llama 3.2 3B to isolate the effect of "
                  "parameter count within one family.",
    ),
)
