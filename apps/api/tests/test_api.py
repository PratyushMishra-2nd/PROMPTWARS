"""API contract tests via TestClient. No real Gemini calls."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_contract_types():
    r = client.get("/api/v1/contract-types")
    body = r.json()["data"]
    assert "employment" in body["types"]
    assert "employee" in body["perspectives"]


def test_security_headers_present():
    r = client.get("/api/v1/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"


def test_404_unknown_analysis():
    r = client.get("/api/v1/analyses/does-not-exist")
    assert r.status_code == 404


def test_text_too_short_rejected():
    r = client.post("/api/v1/analyze/text", json={
        "text": "short", "perspective": "employee",
    })
    assert r.status_code == 400


def test_list_analyses_returns_list():
    r = client.get("/api/v1/analyses")
    assert r.status_code == 200
    assert isinstance(r.json()["data"]["analyses"], list)
