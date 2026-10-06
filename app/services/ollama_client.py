"""Blocking transport to a local Ollama server.

Assignment 1 baseline: one synchronous request per call. There is deliberately no
retry, cache, queue, batching, streaming or concurrency here.

Logging policy: never log the prompt, the complaint narrative, or the model's raw
output (it can echo the narrative). Only model tag, sizes and timings are logged.
"""
import logging
from time import perf_counter

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    """Local model configuration, transport, or response failure.

    Base class: the API layer catches this one type. Subclasses only make the
    failure mode identifiable in tests and in the request log's ``error`` field.
    """


class OllamaConfigurationError(OllamaError):
    """OLLAMA_MODEL is not set."""


class OllamaUnavailableError(OllamaError):
    """The Ollama server could not be reached (not running, wrong URL, network)."""


class OllamaTimeoutError(OllamaError):
    """Ollama did not answer within OLLAMA_TIMEOUT_SECONDS."""


class OllamaModelNotFoundError(OllamaError):
    """Ollama does not have the configured model (it has not been pulled)."""


class OllamaResponseError(OllamaError):
    """Ollama answered with an HTTP error or a body that is not a usable response."""


def generate(prompt: str) -> str:
    model = settings.ollama_model.strip()
    if not model:
        raise OllamaConfigurationError("OLLAMA_MODEL must be configured before submitting tickets")
    url = f"{settings.ollama_url.rstrip('/')}/api/generate"
    started = perf_counter()
    try:
        # Blocking call: classification completes before storage and HTTP response.
        with httpx.Client(timeout=settings.ollama_timeout) as client:
            response = client.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    # num_gpu=0 requests CPU-only inference; temperature 0 keeps
                    # classification as repeatable as the model allows.
                    "options": {"num_gpu": 0, "temperature": 0},
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        logger.warning("Ollama timed out (model=%s, timeout=%ss)", model, settings.ollama_timeout)
        raise OllamaTimeoutError("Local Ollama request timed out") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        # Response bodies are not logged or returned: keep upstream text out of errors.
        if status == 404:
            logger.error("Ollama does not have model %r; run: ollama pull %s", model, model)
            raise OllamaModelNotFoundError("Configured Ollama model was not found") from exc
        logger.error("Ollama returned HTTP %s (model=%s); check the Ollama server log", status, model)
        raise OllamaResponseError(f"Local Ollama returned HTTP {status}") from exc
    except httpx.TransportError as exc:
        logger.error("Ollama unreachable at %s (%s)", settings.ollama_url, type(exc).__name__)
        raise OllamaUnavailableError("Local Ollama server is unavailable") from exc
    except ValueError as exc:  # response.json() on a non-JSON body
        logger.error("Ollama returned a non-JSON body (model=%s)", model)
        raise OllamaResponseError("Local Ollama returned a non-JSON response") from exc
    except httpx.HTTPError as exc:  # any other httpx failure, e.g. invalid URL
        logger.error("Ollama request failed (%s)", type(exc).__name__)
        raise OllamaUnavailableError("Local Ollama request failed") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("response"), str):
        logger.error("Ollama response has an unexpected structure (model=%s)", model)
        raise OllamaResponseError("Local Ollama returned an invalid response structure")
    logger.info(
        "Ollama answered (model=%s, elapsed_ms=%.0f, response_chars=%d)",
        model, (perf_counter() - started) * 1000, len(payload["response"]),
    )
    return payload["response"]
