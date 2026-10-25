from app.services.discovery import _matches_explicit_intent
from app.services.scoring import score_candidate_fields


def test_rejects_generic_repository_for_github_mcp_query():
    assert not _matches_explicit_intent(
        query="Python MCP server for GitHub",
        name="donnemartin/system-design-primer",
        description="Learn how to design large-scale systems.",
        topics=["python", "system-design"],
        source="github",
    )


def test_accepts_repository_with_mcp_and_github_evidence():
    assert _matches_explicit_intent(
        query="Python MCP server for GitHub",
        name="example/github-mcp-server",
        description="Python MCP server for GitHub integration",
        topics=["mcp", "github"],
        source="github",
    )


def test_rejects_generic_repository_for_explicit_skill_query():
    assert not _matches_explicit_intent(
        query="stock-market agent skill for Claude Code",
        name="python-stock-analysis",
        description="Python library for analyzing stock market data",
        topics=["python", "finance"],
        source="github",
    )


def test_accepts_skill_with_matching_metadata():
    assert _matches_explicit_intent(
        query="stock-market agent skill for Claude Code",
        name="stock-market-agent-skill",
        description="A Claude Code skill for stock market research",
        topics=["agent-skill", "finance"],
        source="github",
    )


def test_requires_explicitly_requested_slack_integration():
    assert not _matches_explicit_intent(
        query="Python MCP server for Slack",
        name="python-mcp-server",
        description="An MCP server built with Python",
        topics=["mcp", "python"],
        source="github",
    )


def test_generic_python_query_still_accepts_relevant_repository():
    assert _matches_explicit_intent(
        query="Python automation tool",
        name="python-automation",
        description="Automate repetitive tasks with Python",
        source="github",
    )


def test_name_match_scores_higher_than_description_only_match():
    name_score, _ = score_candidate_fields(
        "python automation", "python-automation", "", []
    )
    description_score, _ = score_candidate_fields(
        "python automation", "task-helper",
        "Python automation tool", []
    )
    assert name_score > description_score


def test_rejects_mcp_registry_server_for_skill_request():
    assert not _matches_explicit_intent(
        query="stock-market agent skill for Claude Code",
        name="trade.coil/stock-market-scanner",
        description="Stock market trading signals",
        source="mcp_registry",
    )


def test_rejects_livestock_market_for_stock_market_query():
    assert not _matches_explicit_intent(
        query="stock-market agent skill for Claude Code",
        name="io.github.comndllc/livestock-market-prices",
        description="Cattle, sheep, and goat prices and market reports",
        source="github",
    )


def test_automation_query_requires_automation_evidence():
    assert not _matches_explicit_intent(
        query="Python automation tool",
        name="public-apis",
        description="A collective list of free APIs",
        source="github",
    )


def test_accepts_github_mcp_match_found_through_readme_search():
    assert _matches_explicit_intent(
        query="Python MCP server for GitHub",
        name="example/python-mcp",
        description="Python MCP server",
        source="github",
        search_queries=[
            "python in:name,description,readme",
            "mcp in:name,description,readme",
            "github in:name,description,readme",
        ],
    )

def test_python_query_rejects_non_python_automation_project():
    assert not _matches_explicit_intent(
        query="Python automation tool",
        name="n8n-io/n8n",
        description="Workflow automation platform with native AI",
        source="github",
    )


def test_python_query_accepts_python_metadata():
    assert _matches_explicit_intent(
        query="Python automation tool",
        name="example/task-automation",
        description="Automate repetitive tasks",
        topics=["automation", "python"],
        source="github",
    )


def test_registry_mcp_without_language_metadata_is_rejected():
    assert not _matches_explicit_intent(
        query="Python MCP server for GitHub",
        name="example/github-mcp",
        description="An MCP server for managing GitHub repositories",
        topics=["mcp", "github"],
        source="mcp_registry",
    )



def test_accepts_stock_skill_found_by_finance_search():
    assert _matches_explicit_intent(
        query="stock-market agent skill for Claude Code",
        name="example/market-research",
        description="A reusable research skill",
        topics=["agent-skill"],
        source="github",
        search_queries=["stock skill in:name,description,readme"],
    )
