from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=10, ge=1, le=25)


class Candidate(BaseModel):
    id: str
    name: str
    source: Literal["github", "mcp_registry"]
    url: HttpUrl
    description: str = ""
    resource_type: str
    stars: int | None = None
    updated_at: str | None = None
    language: str | None = None
    license: str | None = None
    relevance_score: float
    quality_score: int | None = None
    quality_signals: list[str] = Field(default_factory=list)
    evidence: list[dict[str, str]] = Field(default_factory=list)
    setup_instructions: list[str] = Field(default_factory=list)
    release_url: str | None = None
    recommendation_reasons: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class SourceStatus(BaseModel):
    ok: bool
    message: str


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[Candidate]
    source_status: dict[str, SourceStatus]
