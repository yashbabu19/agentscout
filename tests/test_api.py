from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_rejects_too_short_query():
    response = client.post("/api/search", json={"query": "AI"})
    assert response.status_code == 422


def test_search_rejects_too_large_limit():
    response = client.post("/api/search", json={"query": "find an agent", "limit": 99})
    assert response.status_code == 422

def test_github_repository_is_not_automatically_labelled_mcp():
    from app.services.discovery import _github_candidate

    candidate = _github_candidate(
        {
            "id": 123,
            "full_name": "example/yfinance",
            "html_url": "https://github.com/example/yfinance",
            "description": "Download stock market data from a finance API",
            "topics": ["finance", "python"],
            "stargazers_count": 100,
        },
        "stock market data MCP servers",
    )

    assert candidate is not None
    assert candidate.resource_type == "github_repository"
