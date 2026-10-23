"""Fetch and summarize verifiable GitHub repository evidence."""
import asyncio
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from app.models import Candidate


INSTALL_PATTERNS = (
    re.compile(r"^\s*(?:\$ )?(?:pip install|pipx install|uv pip install|uv add)\b", re.I),
    re.compile(r"^\s*(?:\$ )?(?:npm install|npm i|pnpm add|yarn add|bun add)\b", re.I),
    re.compile(r"^\s*(?:\$ )?(?:npx|bunx|uvx)\b", re.I),
    re.compile(r"^\s*(?:\$ )?(?:docker pull|docker run|docker compose)\b", re.I),
    re.compile(r"^\s*(?:\$ )?(?:git clone|go install|cargo install)\b", re.I),
    re.compile(r"^\s*(?:\$ )?poetry add\b", re.I),
)


def extract_setup_hints(readme: str, max_items: int = 8) -> list[str]:
    """Return install/setup command lines literally present in README text."""
    found: list[str] = []
    seen: set[str] = set()

    for line in readme.splitlines():
        cleaned = line.strip().strip("`").strip()
        if not cleaned or len(cleaned) > 240:
            continue
        if any(pattern.search(cleaned) for pattern in INSTALL_PATTERNS):
            key = cleaned.lower()
            if key not in seen:
                seen.add(key)
                found.append(cleaned)
                if len(found) >= max_items:
                    break

    return found


def recommendation_reasons(candidate: Candidate) -> list[str]:
    reasons: list[str] = []

    if candidate.matched_terms:
        terms = ", ".join(candidate.matched_terms[:5])
        reasons.append(f"Matches your query through: {terms}.")
    if candidate.stars is not None:
        reasons.append(f"GitHub reports {candidate.stars} stars.")
    if candidate.quality_score is not None:
        reasons.append(
            f"Metadata-based quality heuristic: {candidate.quality_score}/100."
        )
    if candidate.license:
        reasons.append(f"GitHub reports license metadata: {candidate.license}.")

    if not reasons:
        reasons.append(
            "Included because it matched the discovery query; limited supporting metadata."
        )

    return reasons


async def _fetch_repo_evidence(
    client: httpx.AsyncClient, candidate: Candidate
) -> None:
    """Enrich one GitHub candidate; enrichment failures never fail discovery."""
    parsed = urlparse(str(candidate.url))
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return

    owner, repo = parts[0], parts[1].removesuffix(".git")
    api_base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github+json"}

    candidate.evidence.append({
        "label": "Repository page",
        "url": str(candidate.url),
        "status": "verified",
    })

    try:
        readme_response = await client.get(f"{api_base}/readme", headers=headers)
        if readme_response.status_code == 200:
            readme_meta: dict[str, Any] = readme_response.json()
            download_url = readme_meta.get("download_url")
            html_url = readme_meta.get("html_url")

            if html_url:
                candidate.evidence.append({
                    "label": "README",
                    "url": html_url,
                    "status": "available",
                })

            if download_url:
                raw_response = await client.get(download_url)
                if raw_response.status_code == 200:
                    hints = extract_setup_hints(raw_response.text)
                    candidate.setup_instructions = hints
                    if not hints:
                        candidate.caveats.append(
                            "README was found, but no supported install-command pattern was extracted."
                        )
        elif readme_response.status_code == 404:
            candidate.caveats.append("GitHub did not report a README for this repository.")
        else:
            candidate.caveats.append(
                f"README evidence unavailable (GitHub HTTP {readme_response.status_code})."
            )
    except (httpx.HTTPError, ValueError, TypeError):
        candidate.caveats.append("README evidence could not be fetched.")

    try:
        release_response = await client.get(f"{api_base}/releases/latest", headers=headers)
        if release_response.status_code == 200:
            release = release_response.json()
            release_url = release.get("html_url")
            if release_url:
                candidate.release_url = release_url
                candidate.evidence.append({
                    "label": "Latest GitHub release",
                    "url": release_url,
                    "status": "available",
                })
        elif release_response.status_code == 404:
            candidate.caveats.append(
                "No latest GitHub release was reported; this does not prove the project is unmaintained."
            )
        else:
            candidate.caveats.append(
                f"Release evidence unavailable (GitHub HTTP {release_response.status_code})."
            )
    except (httpx.HTTPError, ValueError, TypeError):
        candidate.caveats.append("Release evidence could not be fetched.")

    candidate.recommendation_reasons = recommendation_reasons(candidate)


async def enrich_github_candidates(
    candidates: list[Candidate], max_candidates: int = 3
) -> None:
    """Enrich only the highest-ranked GitHub results, with bounded concurrency."""
    selected = [
        candidate for candidate in candidates
        if candidate.source == "github"
    ][:max_candidates]

    if not selected:
        return

    timeout = httpx.Timeout(8.0, connect=3.0)
    limits = httpx.Limits(max_connections=3, max_keepalive_connections=3)

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        follow_redirects=True,
        headers={"User-Agent": "AgentScout/0.1"},
    ) as client:
        await asyncio.gather(
            *(_fetch_repo_evidence(client, candidate) for candidate in selected)
        )

    # Include reasons for candidates not selected for README/release enrichment.
    for candidate in candidates:
        if not candidate.recommendation_reasons:
            candidate.recommendation_reasons = recommendation_reasons(candidate)
