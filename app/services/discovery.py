import asyncio
from typing import Any

import httpx

from app.models import Candidate, SearchResponse, SourceStatus
from app.services.scoring import score_candidate
from app.services.sources import search_github, search_mcp_registry


def _license_name(repo: dict[str, Any]) -> str | None:
    license_info = repo.get("license")
    if isinstance(license_info, dict):
        return license_info.get("spdx_id") or license_info.get("name")
    return None


def _github_candidate(item: dict[str, Any], query: str) -> Candidate | None:
    url = item.get("html_url")
    name = item.get("full_name") or item.get("name")
    if not url or not name:
        return None

    description = item.get("description") or ""
    score, matched = score_candidate(
        query,
        [name, description, item.get("topics") and " ".join(item["topics"]) or ""],
    )
    caveats = ["Repository metadata is not a security audit."]
    if item.get("archived"):
        caveats.append("Repository is archived.")
    if not item.get("license"):
        caveats.append("No license detected in repository metadata.")

    return Candidate(
        id=f"github:{item.get('id', name)}",
        name=name,
        source="github",
        url=url,
        description=description,
        resource_type="github_repository",
        stars=item.get("stargazers_count"),
        updated_at=item.get("pushed_at") or item.get("updated_at"),
        language=item.get("language"),
        license=_license_name(item),
        relevance_score=score,
        matched_terms=matched,
        caveats=caveats,
    )


def _mcp_candidate(item: dict[str, Any], query: str) -> Candidate | None:
    server = item.get("server", item)
    if not isinstance(server, dict):
        return None

    name = server.get("name") or server.get("title")
    if not name:
        return None

    repo = server.get("repository") or {}
    url = repo.get("url") if isinstance(repo, dict) else None
    if not url:
        # Some registry records have package details but no source URL.
        packages = server.get("packages") or []
        if packages and isinstance(packages[0], dict):
            url = packages[0].get("registryBaseUrl")
    if not url:
        url = "https://registry.modelcontextprotocol.io/"

    description = server.get("description") or ""
    score, matched = score_candidate(query, [name, description])
    return Candidate(
        id=f"mcp:{name}",
        name=name,
        source="mcp_registry",
        url=url,
        description=description,
        resource_type="mcp_server",
        relevance_score=score,
        matched_terms=matched,
        caveats=["Registry presence does not establish security or quality."],
    )


async def discover(query: str, limit: int) -> SearchResponse:
    timeout = httpx.Timeout(15.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        github_task = search_github(client, f"{query} (agent OR MCP OR skill)", limit)
        mcp_task = search_mcp_registry(client, query, limit)
        github_items, mcp_items = await asyncio.gather(github_task, mcp_task)

    github_rows, github_error = github_items
    mcp_rows, mcp_error = mcp_items

    candidates: list[Candidate] = []
    for item in github_rows:
        candidate = _github_candidate(item, query)
        if candidate:
            candidates.append(candidate)
    for item in mcp_rows:
        candidate = _mcp_candidate(item, query)
        if candidate:
            candidates.append(candidate)

    # Deduplicate by normalised URL; keep the candidate with the strongest baseline score.
    unique: dict[str, Candidate] = {}
    for candidate in candidates:
        key = str(candidate.url).rstrip("/").lower()
        if key not in unique or candidate.relevance_score > unique[key].relevance_score:
            unique[key] = candidate

    # Never recommend candidates that matched no meaningful query terms.
    relevant_candidates = [
        item for item in unique.values()
        if item.relevance_score > 0
    ]

    results = sorted(
        relevant_candidates,
        key=lambda item: (item.relevance_score, item.stars or 0),
        reverse=True,
    )[:limit]

    return SearchResponse(
        query=query,
        count=len(results),
        results=results,
        source_status={
            "github": SourceStatus(
                ok=github_error is None,
                message=github_error or f"Returned {len(github_rows)} repositories.",
            ),
            "mcp_registry": SourceStatus(
                ok=mcp_error is None,
                message=mcp_error or f"Returned {len(mcp_rows)} registry entries.",
            ),
        },
    )
