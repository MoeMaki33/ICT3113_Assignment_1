import json

import httpx
import pytest

from app.config import Settings
from app.services import classifier, ollama_client


@pytest.mark.parametrize("output", ["Unknown", "Credit card\nMortgage", "This is a Credit card complaint"])
def test_classifier_rejects_invalid_output(monkeypatch, output):
    monkeypatch.setattr(classifier, "generate", lambda _: output)
    with pytest.raises(classifier.InvalidCategoryError):
        classifier.classify_ticket("Complaint")


def test_mocked_ollama_cpu_request(monkeypatch):
    monkeypatch.setattr(ollama_client, "settings", Settings(ollama_model="test-only-model"))

    def handle(request):
        payload = json.loads(request.content)
        assert request.url.path == "/api/generate"
        assert payload["stream"] is False
        assert payload["options"] == {"num_gpu": 0, "temperature": 0}
        assert "Complaint" in payload["prompt"]
        return httpx.Response(200, json={"response": "Credit card\n"})

    client_class = httpx.Client
    monkeypatch.setattr(ollama_client.httpx, "Client", lambda **kw: client_class(
        transport=httpx.MockTransport(handle), **kw
    ))
    assert classifier.classify_ticket("Complaint") == "Credit card"


def test_model_configuration_required(monkeypatch):
    monkeypatch.setattr(ollama_client, "settings", Settings(ollama_model=""))
    with pytest.raises(ollama_client.OllamaError, match="OLLAMA_MODEL"):
        ollama_client.generate("Complaint")


@pytest.mark.skip(reason="TODO: team selects a local model and defines an opt-in real integration test")
def test_real_ollama_integration():
    pass
