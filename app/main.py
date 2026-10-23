from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import SearchRequest, SearchResponse
from app.services.discovery import discover

app = FastAPI(
    title="AgentScout API",
    description="Discover AI agents, MCP servers, and agent skills for a task.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "agentscout-api"}


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    return await discover(request.query, request.limit)
