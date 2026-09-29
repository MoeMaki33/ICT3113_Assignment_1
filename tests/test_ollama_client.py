"""Ollama transport tests. Ollama is mocked with httpx.MockTransport; none is needed."""
import importlib
import json
import logging
from dataclasses import replace

import httpx
import pytest

from app import config
from app.config import Settings
from app.services import ollama_client
from app.services.ollama_client import (
    OllamaConfigurationError,
    OllamaError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
    OllamaUnavailableError,
    generate,
)


@pytest.fixture
def mock_ollama(monkeypatch):
    """Install a handler as the fake Ollama server; returns the list of parsed requests."""
    def install(handler, **settings_overrides):
        seen = []

        def recording(request):
            seen.append({"url": str(request.url), "json": json.loads(request.content)})
            return handler(request)

        monkeypatch.setattr(ollama_client, "settings",
                            Settings(ollama_url="http://ollama.test:11434/",
                                     ollama_model="test-model", **settings_overrides))
        real_client = httpx.Client
        monkeypatch.setattr(ollama_client.httpx, "Client", lambda **kw: real_client(
            transport=httpx.MockTransport(recording), **kw))
        return seen
    return install


def test_success_returns_response_text(mock_ollama):
    seen = mock_ollama(lambda r: httpx.Response(200, json={"response": "Mortgage", "done": True}))
    assert generate("prompt") == "Mortgage"
    body = seen[0]["json"]
    assert seen[0]["url"] == "http://ollama.test:11434/api/generate"
    assert body["model"] == "test-model"
    assert body["stream"] is False
    assert body["options"]["num_gpu"] == 0  # CPU-only


def test_missing_model_configuration(monkeypatch):
    monkeypatch.setattr(ollama_client, "settings", Settings(ollama_model="   "))
    with pytest.raises(OllamaConfigurationError, match="OLLAMA_MODEL"):
        generate("prompt")


def test_ollama_unavailable(mock_ollama):
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)
    mock_ollama(refuse)
    with pytest.raises(OllamaUnavailableError):
        generate("prompt")


def test_timeout(mock_ollama):
    def slow(request):
        raise httpx.ReadTimeout("timed out", request=request)
    mock_ollama(slow)
    with pytest.raises(OllamaTimeoutError):
        generate("prompt")


def test_configured_timeout_is_passed_to_http_client(monkeypatch):
    captured = {}
    real_client = httpx.Client

    def factory(**kw):
        captured.update(kw)
        return real_client(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"response": "Mortgage"})), **kw)

    monkeypatch.setattr(ollama_client, "settings", Settings(ollama_model="m", ollama_timeout=7.5))
    monkeypatch.setattr(ollama_client.httpx, "Client", factory)
    generate("prompt")
    assert captured["timeout"] == 7.5


def test_unknown_model(mock_ollama):
    mock_ollama(lambda r: httpx.Response(404, json={"error": "model 'test-model' not found"}))
    with pytest.raises(OllamaModelNotFoundError) as info:
        generate("prompt")
    assert "not found" in str(info.value) and "test-model" not in str(info.value)


def test_server_error_does_not_leak_body(mock_ollama):
    mock_ollama(lambda r: httpx.Response(500, json={"error": "UPSTREAM-DETAIL"}))
    with pytest.raises(OllamaResponseError) as info:
        generate("prompt")
    assert "UPSTREAM-DETAIL" not in str(info.value)


@pytest.mark.parametrize("response", [
    httpx.Response(200, content=b"<html>not json</html>"),
    httpx.Response(200, json=["response"]),
    httpx.Response(200, json={"done": True}),
    httpx.Response(200, json={"response": 42}),
    httpx.Response(200, json={"error": "model runner crashed"}),
])
def test_invalid_response_structure(mock_ollama, response):
    mock_ollama(lambda r: response)
    with pytest.raises(OllamaResponseError):
        generate("prompt")


def test_all_failures_share_one_base_class():
    for cls in (OllamaConfigurationError, OllamaUnavailableError, OllamaTimeoutError,
                OllamaModelNotFoundError, OllamaResponseError):
        assert issubclass(cls, OllamaError)  # Person 1's route catches OllamaError only


def test_each_call_sends_its_own_request_without_caching(mock_ollama):
    seen = mock_ollama(lambda r: httpx.Response(200, json={"response": "Mortgage"}))
    generate("same prompt")
    generate("same prompt")
    assert len(seen) == 2


def test_model_selection_follows_settings_without_code_change(mock_ollama, monkeypatch):
    seen = mock_ollama(lambda r: httpx.Response(200, json={"response": "Mortgage"}))
    for tag in ("gemma2:2b", "llama3.1:8b"):
        monkeypatch.setattr(ollama_client, "settings", replace(ollama_client.settings, ollama_model=tag))
        generate("prompt")
    assert [s["json"]["model"] for s in seen] == ["gemma2:2b", "llama3.1:8b"]


def test_environment_variables_configure_model_url_and_timeout(monkeypatch):
    with monkeypatch.context() as env:
        env.setenv("OLLAMA_MODEL", "qwen2.5:7b")
        env.setenv("OLLAMA_URL", "http://localhost:11434")
        env.setenv("OLLAMA_TIMEOUT_SECONDS", "45")
        reloaded = importlib.reload(config)
        assert reloaded.Settings().ollama_model == "qwen2.5:7b"
        assert reloaded.Settings().ollama_url == "http://localhost:11434"
        assert reloaded.Settings().ollama_timeout == 45.0
        env.setenv("OLLAMA_TIMEOUT_SECONDS", "not-a-number")
        assert importlib.reload(config).Settings().ollama_timeout == 120.0  # safe fallback
    importlib.reload(config)  # restore module state for the rest of the session


def test_logs_do_not_contain_prompt_or_model_output(mock_ollama, caplog):
    mock_ollama(lambda r: httpx.Response(200, json={"response": "ECHOED-PRIVATE-TEXT"}))
    with caplog.at_level(logging.DEBUG):
        generate("PRIVATE-PROMPT-TEXT")
    assert "PRIVATE-PROMPT-TEXT" not in caplog.text
    assert "ECHOED-PRIVATE-TEXT" not in caplog.text
    assert "test-model" in caplog.text  # useful, non-sensitive context is kept


@pytest.mark.parametrize("failure", [
    lambda r: (_ for _ in ()).throw(httpx.ConnectError("boom PRIVATE-PROMPT-TEXT", request=r)),
    lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("boom PRIVATE-PROMPT-TEXT", request=r)),
    lambda r: httpx.Response(404, json={"error": "PRIVATE-PROMPT-TEXT"}),
    lambda r: httpx.Response(200, content=b"PRIVATE-PROMPT-TEXT"),
])
def test_failure_logs_do_not_contain_sensitive_text(mock_ollama, caplog, failure):
    mock_ollama(failure)
    with caplog.at_level(logging.DEBUG), pytest.raises(OllamaError):
        generate("PRIVATE-PROMPT-TEXT")
    assert "PRIVATE-PROMPT-TEXT" not in caplog.text
    assert caplog.records  # a failure is logged, just without the text
