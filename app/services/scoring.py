import re
from collections.abc import Iterable

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "i", "in", "is", "it", "of", "on", "or", "the",
    "to", "with", "want", "need", "that", "this", "my", "me",
    "find", "best", "using", "use", "please", "search",
    "searching", "analyze", "analyzing", "analyse", "claude",
    "code", "agent", "agents", "tool", "tools", "server",
    "servers", "mcp", "skill", "skills",
}

ALIASES = {
    "stocks": "stock",
    "markets": "market",
    "financial": "finance",
    "equities": "equity",
    "trading": "trade",
}

NON_FINANCIAL_STOCK_PHRASES = (
    "stock photo",
    "stock photos",
    "stock image",
    "stock images",
    "stock photography",
)


def tokens(text: str) -> set[str]:
    result = set()
    for token in re.findall(r"[a-zA-Z0-9+#.-]+", text.lower()):
        if len(token) <= 1 or token in STOP_WORDS:
            continue
        result.add(ALIASES.get(token, token))
    return result


def score_candidate(
    query: str, searchable_fields: Iterable[str]
) -> tuple[float, list[str]]:
    query_terms = tokens(query)
    if not query_terms:
        return 0.0, []

    text = " ".join(searchable_fields).lower()

    if any(phrase in text for phrase in NON_FINANCIAL_STOCK_PHRASES):
        finance_context = {
            "finance", "financial", "trading", "trade", "equity",
            "market", "investment", "investing", "portfolio",
            "securities", "brokerage",
        }
        if not (tokens(text) & finance_context):
            return 0.0, []

    candidate_terms = tokens(text)
    matched = sorted(query_terms & candidate_terms)
    score = round(len(matched) / len(query_terms), 3)
    return score, matched
