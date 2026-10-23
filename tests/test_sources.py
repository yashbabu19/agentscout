from app.services.sources import _github_queries, _registry_queries


def test_finance_search_includes_readme_content():
    queries = _github_queries("research Indian stocks with Claude Code")

    assert len(queries) == 5
    assert all("in:name,description,readme" in query for query in queries)
    assert any("stock" in query for query in queries)


def test_finance_registry_search_uses_multiple_terms():
    queries = _registry_queries("find stock market MCP servers")

    assert queries == ["stock", "finance", "market", "trading"]


def test_generic_search_ignores_client_and_filler_words():
    queries = _github_queries("Find the best Python MCP server for Claude Code")

    assert queries == ["python in:name,description,readme"]


def test_generic_search_deduplicates_terms():
    queries = _github_queries("Python python automation automation tool")

    assert queries == [
        "python in:name,description,readme",
        "automation in:name,description,readme",
    ]


def test_finance_detection_uses_whole_words():
    # "marketplace" alone should not trigger the finance-specific search.
    queries = _github_queries("build a marketplace tool")

    assert queries == ["marketplace in:name,description,readme"]
