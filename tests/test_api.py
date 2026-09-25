import json

import pytest

from app.categories import CATEGORIES
from app.routes import tickets
from app.services.classifier import InvalidCategoryError


def test_application_starts_empty(client):
    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json() == dict.fromkeys(CATEGORIES, 0)


@pytest.mark.parametrize("payload", [{}, {"narrative": ""}, {"narrative": " \n "}, {"narrative": None}])
def test_rejects_empty_narrative(client, monkeypatch, payload):
    def unexpected_call(_):
        pytest.fail("Invalid input must not reach the classifier")
    monkeypatch.setattr(tickets, "classify_ticket", unexpected_call)
    assert client.post("/tickets", json=payload).status_code == 400


def test_submit_store_search_stats_and_log(client, monkeypatch, tmp_path):
    narrative = "Disputed card charge reference PRIVATE-COMPLAINT"
    calls = []

    def classify(text):
        calls.append(text)
        return "Credit card"

    monkeypatch.setattr(tickets, "classify_ticket", classify)
    response = client.post("/tickets", json={"narrative": narrative})
    assert response.status_code == 201
    assert calls == [narrative]
    assert response.json() == {"id": 1, "category": "Credit card"}
    stored = client.get("/search", params={"q": "PRIVATE-COMPLAINT"}).json()
    assert len(stored) == 1
    assert stored[0]["id"] == 1
    assert stored[0]["narrative"] == narrative
    assert "model" in stored[0] and stored[0]["created_at"]
    assert client.get("/search", params={"q": "%"}).json() == []
    expected = dict.fromkeys(CATEGORIES, 0)
    expected["Credit card"] = 1
    assert client.get("/stats").json() == expected
    content = (tmp_path / "service.log").read_text(encoding="utf-8")
    assert narrative not in content and "PRIVATE-COMPLAINT" not in content
    entries = [json.loads(line) for line in content.splitlines()]
    assert len(entries) == 4
    entry = entries[0]
    assert entry["request_id"] == response.headers["x-request-id"]
    assert entry["predicted_category"] == "Credit card"
    assert entry["status_code"] == 201
    assert entry["ticket_id"] == response.json()["id"]
    assert entry["duration_ms"] >= 0
    assert {"timestamp", "start_time", "end_time", "endpoint", "method", "model", "error"} <= entry.keys()


def test_invalid_model_output_is_not_stored(client, monkeypatch, tmp_path):
    def invalid(_):
        raise InvalidCategoryError("Model output is not one of the seven allowed categories")
    monkeypatch.setattr(tickets, "classify_ticket", invalid)
    assert client.post("/tickets", json={"narrative": "Complaint"}).status_code == 502
    assert sum(client.get("/stats").json().values()) == 0
    entry = json.loads((tmp_path / "service.log").read_text().splitlines()[0])
    assert entry["error"] == "InvalidCategoryError"


def test_validation_and_unknown_routes_are_logged(client, tmp_path):
    client.post("/tickets", json={"narrative": ""})
    client.get("/unknown-private-path", params={"q": "private-query"})
    content = (tmp_path / "service.log").read_text()
    assert "unknown-private-path" not in content and "private-query" not in content
    assert [json.loads(line)["status_code"] for line in content.splitlines()] == [400, 404]
