"""Person 1 API contract tests; no live model or assignment data required."""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.categories import CATEGORIES
from app.database import db
from app.routes import tickets
from app.services import request_logger
from app.services.ollama_client import OllamaError


@pytest.mark.parametrize("value", [123, True, [], {}])
def test_rejects_non_string_narrative(client, monkeypatch, value):
    monkeypatch.setattr(tickets, "classify_ticket", lambda _: pytest.fail("Invalid input classified"))
    assert client.post("/tickets", json={"narrative": value}).status_code == 400
    assert sum(client.get("/stats").json().values()) == 0


def test_rejects_malformed_json_without_echoing_input(client):
    response = client.post("/tickets", content='{"narrative": "PRIVATE-TEXT",',
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert "PRIVATE-TEXT" not in response.text


@pytest.mark.parametrize("query", [None, "", "   ", "\n\t"])
def test_rejects_missing_or_blank_search(client, query):
    params = {} if query is None else {"q": query}
    assert client.get("/search", params=params).status_code == 400


def test_search_empty_database(client):
    response = client.get("/search", params={"q": "mortgage"})
    assert response.status_code == 200
    assert response.json() == []


def test_search_filters_stored_narratives_and_escapes_wildcards(client, monkeypatch):
    monkeypatch.setattr(tickets, "classify_ticket", lambda _: "Mortgage")
    for narrative in ["Mortgage interest 10% reference_A", "Unrelated card charge"]:
        assert client.post("/tickets", json={"narrative": narrative}).status_code == 201
    for query in [" Mortgage ", "10%", "reference_", "_"]:
        results = client.get("/search", params={"q": query}).json()
        assert [row["id"] for row in results] == [1]
    # Both tickets have category Mortgage, but search must use their narratives.
    assert [row["id"] for row in client.get("/search", params={"q": "card"}).json()] == [2]
    assert client.get("/search", params={"q": "' OR 1=1 --"}).json() == []


def test_counts_each_category_and_repeated_submissions(client, monkeypatch):
    for category in CATEGORIES:
        monkeypatch.setattr(tickets, "classify_ticket", lambda _, result=category: result)
        for _ in range(2):
            assert client.post("/tickets", json={"narrative": "Same complaint"}).status_code == 201
    assert client.get("/stats").json() == dict.fromkeys(CATEGORIES, 2)


def test_stored_model_and_request_log_match(client, monkeypatch, tmp_path):
    settings = replace(tickets.settings, ollama_model="mock-test-model")
    monkeypatch.setattr(tickets, "settings", settings)
    monkeypatch.setattr(request_logger, "settings", settings)
    monkeypatch.setattr(tickets, "classify_ticket", lambda _: "Credit card")
    response = client.post("/tickets", json={"narrative": "Disputed charge"})
    stored = client.get("/search", params={"q": "charge"}).json()[0]
    assert stored["model"] == "mock-test-model"
    assert stored["created_at"]
    log = json.loads((tmp_path / "service.log").read_text().splitlines()[0])
    assert log["model"] == stored["model"]
    assert log["ticket_id"] == stored["id"] == response.json()["id"]


@pytest.mark.parametrize("category", ["Unknown", "Credit card\nMortgage", "", None])
def test_backend_rejects_invalid_classifier_return(client, monkeypatch, category):
    monkeypatch.setattr(tickets, "classify_ticket", lambda _: category)
    assert client.post("/tickets", json={"narrative": "Complaint"}).status_code == 502
    assert sum(client.get("/stats").json().values()) == 0


def test_classifier_failure_is_safe_and_does_not_insert(client, monkeypatch, tmp_path):
    def fail(_):
        raise OllamaError("PRIVATE-COMPLAINT from upstream")
    monkeypatch.setattr(tickets, "classify_ticket", fail)
    response = client.post("/tickets", json={"narrative": "Complaint"})
    assert response.status_code == 502
    assert "PRIVATE-COMPLAINT" not in response.text
    assert "PRIVATE-COMPLAINT" not in (tmp_path / "service.log").read_text()
    assert sum(client.get("/stats").json().values()) == 0


def test_database_failure_rolls_back_and_returns_json(client, monkeypatch, tmp_path):
    monkeypatch.setattr(tickets, "classify_ticket", lambda _: "Mortgage")
    rollbacks = []
    original_rollback = Session.rollback

    def fail_commit(session):
        session.flush()  # Exercise rollback of an actual uncommitted insert.
        raise SQLAlchemyError("PRIVATE-DATABASE-DETAIL")

    def record_rollback(session):
        rollbacks.append(True)
        original_rollback(session)

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        patch.setattr(Session, "rollback", record_rollback)
        response = client.post("/tickets", json={"narrative": "Mortgage complaint"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Database operation failed"}
    assert response.headers["x-request-id"]
    assert rollbacks == [True]
    assert "PRIVATE-DATABASE-DETAIL" not in (tmp_path / "service.log").read_text()
    assert sum(client.get("/stats").json().values()) == 0
    assert client.post("/tickets", json={"narrative": "Retry complaint"}).status_code == 201


def test_classification_finishes_before_storage_and_response(client, monkeypatch):
    entered, release = Event(), Event()
    calls = []

    def classify(narrative):
        calls.append(narrative)
        entered.set()
        assert release.wait(timeout=10), "Test did not release classifier"
        return "Mortgage"

    monkeypatch.setattr(tickets, "classify_ticket", classify)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(client.post, "/tickets", json={"narrative": "Mortgage complaint"})
        try:
            assert entered.wait(timeout=10), "Classifier was not called"
            assert not future.done()
            assert sum(client.get("/stats").json().values()) == 0
        finally:
            release.set()
        assert future.result(timeout=10).status_code == 201
    # Repeated identical requests still call the classifier and store new tickets.
    assert client.post("/tickets", json={"narrative": "Mortgage complaint"}).status_code == 201
    assert calls == ["Mortgage complaint", "Mortgage complaint"]
    assert client.get("/stats").json()["Mortgage"] == 2


def test_startup_never_imports_csv_and_preserves_submissions(tmp_path, monkeypatch, request):
    monkeypatch.chdir(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "assignment.csv").write_text(
        'narrative,category\nCSV-ONLY-COMPLAINT,Mortgage\n', encoding="utf-8"
    )
    # Start only after the CSV exists, so this tests the real startup path.
    client = request.getfixturevalue("client")
    assert client.get("/stats").json() == dict.fromkeys(CATEGORIES, 0)
    assert client.get("/search", params={"q": "CSV-ONLY"}).json() == []
    monkeypatch.setattr(tickets, "classify_ticket", lambda _: "Mortgage")
    assert client.post("/tickets", json={"narrative": "API-ONLY-COMPLAINT"}).status_code == 201
    db.init_db()  # The same initialization used on a subsequent service startup.
    assert client.get("/stats").json()["Mortgage"] == 1
    assert client.get("/search", params={"q": "CSV-ONLY"}).json() == []
    assert len(client.get("/search", params={"q": "API-ONLY"}).json()) == 1
