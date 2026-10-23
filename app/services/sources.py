import asyncio
import os
import re
from typing import Any

import httpx

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
MCP_REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"

IGNORED_QUERY_WORDS = {
    "find", "best", "github", "search", "searching", "analyzing",
    "analyse", "analyze", "using", "use", "for", "with", "from",
    "that", "this", "want", "need", "please", "the", "and", "are",
    "mcp", "server", "servers", "agent", "agents", "claude", "code",
    "skill", "skills", "tool", "tools",
}


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AgentScout/0.1",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_queries(query: str) -> list[str]:
    text = query.lower()

    if any(word in text for word in (
        "stock", "market", "finance", "financial",
        "trading", "equity", "equities", "nse", "bse",
    )):
        return [
            "stock in:name,description",
            "finance in:name,description",
            "financial data in:name,description",
            "trading in:name,description",
            "market data in:name,description",
        ]

    words = [
        word for word in re.findall(r"[a-zA-Z0-9+#.-]+", text)
        if len(word) > 2 and word not in IGNORED_QUERY_WORDS
    ]

    return [
        f"{word} in:name,description"
        for word in words[:3]
    ]


def _registry_queries(query: str) -> list[str]:
    text = query.lower()

    if any(word in text for word in (
        "stock", "market", "finance", "financial",
        "trading", "equity", "equities", "nse", "bse",
    )):
        return ["stock", "finance", "market", "trading"]

    words = [
        word for word in re.findall(r"[a-zA-Z0-9+#.-]+", text)
        if len(word) > 2 and word not in IGNORED_QUERY_WORDS
    ]
    return words[:3]


async def search_github(
    client: httpx.AsyncClient, query: str, limit: int
) -> tuple[list[dict[str, Any]], str | None]:
    queries = _github_queries(query)
    if not queries:
        return [], None

    async def fetch(search_query: str):
        response = await client.get(
            GITHUB_SEARCH_URL,
            params={
                "q": search_query,
                "sort": "stars",
                "order": "desc",
                "per_page": limit,
            },
            headers=_github_headers(),
        )
        response.raise_for_status()
        return response.json().get("items", [])

    responses = await asyncio.gather(
        *(fetch(q) for q in queries),
        return_exceptions=True,
    )

    rows: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for result in responses:
        if isinstance(result, Exception):
            errors.append(type(result).__name__)
            continue
        for item in result:
            key = str(item.get("id") or item.get("html_url") or "")
            if key:
                rows[key] = item

    if not rows and errors:
        return [], f"GitHub search failed: {', '.join(sorted(set(errors)))}"

    error = (
        f"Some GitHub searches failed: {', '.join(sorted(set(errors)))}"
        if errors else None
    )
    return list(rows.values()), error


async def search_mcp_registry(
    client: httpx.AsyncClient, query: str, limit: int
) -> tuple[list[dict[str, Any]], str | None]:
    search_terms = _registry_queries(query)
    if not search_terms:
        return [], None

    async def fetch(term: str):
        response = await client.get(
            MCP_REGISTRY_URL,
            params={"search": term, "version": "latest", "limit": limit},
            headers={
                "Accept": "application/json",
                "User-Agent": "AgentScout/0.1",
            },
        )
        response.raise_for_status()
        payload = response.json()
        servers = payload.get("servers", [])
        return servers if isinstance(servers, list) else []

    responses = await asyncio.gather(
        *(fetch(term) for term in search_terms),
        return_exceptions=True,
    )

    rows: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for result in responses:
        if isinstance(result, Exception):
            errors.append(type(result).__name__)
            continue
        for item in result:
            server = item.get("server", item)
            if isinstance(server, dict):
                name = server.get("name") or server.get("title")
                if name:
                    rows[name.lower()] = item

    if not rows and errors:
        return [], f"MCP Registry search failed: {', '.join(sorted(set(errors)))}"

    error = (
        f"Some registry searches failed: {', '.join(sorted(set(errors)))}"
        if errors else None
    )
    return list(rows.values()), error
