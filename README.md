# AgentScout

Find AI agents, MCP servers, and agent skills for a task you describe.

**Current milestone:** first backend vertical slice — natural-language query in, candidate tools from GitHub and the official MCP Registry out.

## What works in this starter

- `GET /health` health check
- `POST /api/search` searches GitHub repositories and the official MCP Registry
- Normalises both sources into one candidate shape
- Applies a transparent baseline relevance score (not an LLM score)
- Returns source URLs and available metadata
- Handles upstream timeouts/errors without failing the whole request
- Includes tests for ranking and API behaviour

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- HTTPX
- Pytest

No database, embeddings, or LLM calls yet. We'll add those only after we validate the first discovery workflow.

## Run locally (macOS)

```bash
cd agentscout-starter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

Try a search:

```bash
curl -s http://127.0.0.1:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"research Indian stocks with Claude Code","limit":5}' | python -m json.tool
```

GitHub search has stricter rate limits than many ordinary API endpoints. Set `GITHUB_TOKEN` in your shell if you want authenticated requests:

```bash
export GITHUB_TOKEN="your_github_token"
```

Never commit tokens to Git.

## Run tests

```bash
pytest -q
```

## API shape

`POST /api/search`

```json
{
  "query": "research Indian stocks with Claude Code",
  "limit": 10
}
```

Returns `query`, `count`, `results`, and `source_status`. Each result includes the source, URL, description, available maintenance metadata, a baseline score, and an explanation of matched query terms.

## Current limitations

- The baseline scorer is lexical; it does not yet understand intent deeply.
- GitHub repository search is not a complete index of skills or agents.
- The official MCP Registry's name search is substring-based, so it can miss relevant servers.
- A repository's stars/activity are signals, not proof of quality or security.
- No install commands are executed. Search results and repository content must be treated as untrusted.
