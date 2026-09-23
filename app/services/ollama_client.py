import httpx

from app.config import settings


class OllamaError(RuntimeError):
    """Local model configuration, transport, or response failure."""


def generate(prompt: str) -> str:
    if not settings.ollama_model.strip():
        raise OllamaError("OLLAMA_MODEL must be configured before submitting tickets")
    try:
        # Blocking call: classification completes before storage and HTTP response.
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{settings.ollama_url.rstrip('/')}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_gpu": 0},
                },
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        # Do not expose upstream response bodies or complaint text in logs/errors.
        raise OllamaError("Local Ollama request failed") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("response"), str):
        raise OllamaError("Local Ollama returned an invalid response structure")
    return payload["response"]
