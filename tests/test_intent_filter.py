from app.services.discovery import _matches_explicit_intent


def test_rejects_python_repository_for_explicit_github_mcp_query():
    assert not _matches_explicit_intent(
        query="Python MCP server for GitHub",
        name="donnemartin/system-design-primer",
        description="Learn how to design large-scale systems. Prep for system design interviews.",
        topics=["python", "system-design"],
        source="github",
    )


def test_accepts_github_mcp_repository_with_matching_metadata():
    assert _matches_explicit_intent(
        query="Python MCP server for GitHub",
        name="example/github-mcp-server",
        description="Python MCP server for GitHub integration",
        topics=["mcp", "github"],
        source="github",
    )


def test_rejects_registry_result_without_requested_github_integration():
    assert not _matches_explicit_intent(
        query="Python MCP server for GitHub",
        name="python-quickstart",
        description="A simple MCP server built with Python",
        source="mcp_registry",
    )


def test_rejects_registry_result_without_python_language_evidence():
    assert not _matches_explicit_intent(
        query="Python MCP server for GitHub",
        name="github-mcp",
        description="MCP server for GitHub repositories",
        source="mcp_registry",
    )


def test_generic_python_query_does_not_require_github_or_mcp():
    assert _matches_explicit_intent(
        query="Python automation tool",
        name="python-automation",
        description="Automate repetitive tasks with Python",
        source="github",
    )
