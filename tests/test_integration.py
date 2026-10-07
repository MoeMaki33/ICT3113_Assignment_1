import json
import os

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


@pytest.mark.skipif(os.getenv("RUN_OLLAMA_INTEGRATION") != "1",
                    reason="Opt in with RUN_OLLAMA_INTEGRATION=1 and a configured local Ollama model")
def test_real_ollama_integration(client):
    from app.config import settings
    from app.categories import CATEGORIES

    assert settings.ollama_model.strip(), "Set OLLAMA_MODEL to a pulled local tag before opting in"
    narrative = "I dispute an unauthorized purchase on my credit card account."
    before = client.get("/stats").json()
    response = client.post("/tickets", json={"narrative": narrative})
    assert response.status_code == 201
    assert response.headers["x-request-id"]
    ticket = response.json()
    assert ticket["category"] in CATEGORIES
    stored = next(t for t in client.get("/search", params={"q": narrative}).json() if t["id"] == ticket["id"])
    assert stored["category"] == ticket["category"] and stored["model"] == settings.ollama_model
    after = client.get("/stats").json()
    assert sum(after.values()) == sum(before.values()) + 1
