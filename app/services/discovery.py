import asyncio
import re
from typing import Any

import httpx

from app.models import Candidate, SearchResponse, SourceStatus
from app.services.scoring import score_candidate_fields
from app.services.sources import search_github, search_mcp_registry
from app.services.quality import assess_github_quality
from app.services.evidence import enrich_github_candidates


def _license_name(repo: dict[str, Any]) -> str | None:
    license_info = repo.get("license")
    if isinstance(license_info, dict):
        return license_info.get("spdx_id") or license_info.get("name")
    return None


def _matches_explicit_intent(
    query: str,
    name: str,
    description: str = "",
    topics: list[str] | None = None,
    source: str = "",
) -> bool:
    """Reject candidates missing explicitly requested integration evidence."""
    def words(value: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", value.lower()))

    query_words = words(query)
    candidate_words = words(
        " ".join([name, description, *(topics or [])])
    )

    # An explicit GitHub integration request needs metadata evidence.
    if "github" in query_words and "github" not in candidate_words:
        return False

    # For GitHub results, an explicit MCP request needs MCP evidence.
    mcp_requested = "mcp" in query_words or (
        {"model", "context", "protocol"} <= query_words
    )
    mcp_mentioned = "mcp" in candidate_words or (
        {"model", "context", "protocol"} <= candidate_words
    )
    if source == "github" and mcp_requested and not mcp_mentioned:
        return False

    return True


def _github_candidate(item: dict[str, Any], query: str) -> Candidate | None:
    url = item.get("html_url")
    name = item.get("full_name") or item.get("name")
    if not url or not name:
        return None

    description = item.get("description") or ""
    topics = item.get("topics") or []
    if not isinstance(topics, list):
        topics = []

    score, matched = score_candidate_fields(
        query, name, description, topics
    )
    quality_score, quality_signals = assess_github_quality(item)

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
        quality_score=quality_score,
        quality_signals=quality_signals,
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
        packages = server.get("packages") or []
        if packages and isinstance(packages[0], dict):
            url = packages[0].get("registryBaseUrl")
    if not url:
        url = "https://registry.modelcontextprotocol.io/"

    description = server.get("description") or ""
    score, matched = score_candidate_fields(query, name, description)

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
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True
    ) as client:
        github_task = search_github(
            client, f"{query} (agent OR MCP OR skill)", limit
        )
        mcp_task = search_mcp_registry(client, query, limit)
        github_items, mcp_items = await asyncio.gather(
            github_task, mcp_task
        )

    github_rows, github_error = github_items
    mcp_rows, mcp_error = mcp_items

    candidates: list[Candidate] = []
    for item in github_rows:
        topics = item.get("topics") or []
        if not isinstance(topics, list):
            topics = []

        if not _matches_explicit_intent(
            query=query,
            name=str(item.get("full_name") or item.get("name") or ""),
            description=str(item.get("description") or ""),
            topics=topics,
            source="github",
        ):
            continue

        candidate = _github_candidate(item, query)
        if candidate:
            candidates.append(candidate)

    for item in mcp_rows:
        server = item.get("server", item)
        if not isinstance(server, dict):
            continue

        server_name = str(server.get("name") or server.get("title") or "")
        server_description = str(server.get("description") or "")
        if not _matches_explicit_intent(
            query=query,
            name=server_name,
            description=server_description,
            source="mcp_registry",
        ):
            continue

        candidate = _mcp_candidate(item, query)
        if candidate:
            candidates.append(candidate)

    # Deduplicate URLs, keeping the candidate with the strongest score.
    unique: dict[str, Candidate] = {}
    for candidate in candidates:
        key = str(candidate.url).rstrip("/").lower()
        existing = unique.get(key)
        if existing is None or candidate.relevance_score > existing.relevance_score:
            unique[key] = candidate

    relevant_candidates = [
        item for item in unique.values()
        if item.relevance_score > 0
    ]

    results = sorted(
        relevant_candidates,
        key=lambda item: (item.relevance_score, item.stars or 0),
        reverse=True,
    )[:limit]

    # Add README/release evidence only to the highest-ranked GitHub results.
    # Evidence fetch failures are recorded as caveats and do not fail discovery.
    await enrich_github_candidates(results, max_candidates=3)

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
