from fastapi.testclient import TestClient

from qp_api.main import app
from qp_api.sse import sse

client = TestClient(app)  # no `with`: startup (DB pool, graph) is not run


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_rejects_empty_question() -> None:
    assert client.post("/api/ask", json={"question": ""}).status_code == 422


def test_ask_rejects_overlong_question() -> None:
    assert client.post("/api/ask", json={"question": "x" * 501}).status_code == 422


def test_sse_format() -> None:
    assert sse("step", {"node": "route"}) == 'event: step\ndata: {"node": "route"}\n\n'
