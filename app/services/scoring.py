import re
from collections.abc import Iterable

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "i", "in", "is", "it", "of", "on", "or", "the",
    "to", "with", "want", "need", "that", "this", "my", "me",
    "find", "best", "using", "use", "please", "search",
    "searching", "analyze", "analyzing", "analyse", "claude",
    "code", "agent", "agents", "tool", "tools", "server",
    "servers", "mcp", "skill", "skills", "build", "create",
    "make", "help", "them", "their",
}

ALIASES = {
    "stocks": "stock",
    "markets": "market",
    "financial": "finance",
    "equities": "equity",
    "trading": "trade",
    "investments": "investment",
    "investing": "investment",
    "brokers": "broker",
    "repositories": "repository",
}

NON_FINANCIAL_STOCK_PHRASES = (
    "stock photo",
    "stock photos",
    "stock image",
    "stock images",
    "stock photography",
)

FINANCE_CONTEXT = {
    "finance", "trade", "equity", "market", "investment",
    "portfolio", "securities", "brokerage",
}


def tokens(text: str) -> set[str]:
    result = set()

    # Split hyphenated names such as stock-market-research
    # into individual searchable terms.
    for token in re.findall(r"[a-zA-Z0-9+#]+", text.lower()):
        if len(token) <= 1 or token in STOP_WORDS:
            continue
        result.add(ALIASES.get(token, token))

    return result


def _is_nonfinancial_stock_photo(text: str) -> bool:
    lowered = text.lower()

    if not any(phrase in lowered for phrase in NON_FINANCIAL_STOCK_PHRASES):
        return False

    # "Stock" alone is not financial context. Look for additional
    # financial terminology before allowing a stock-photo match.
    return not (tokens(text) & FINANCE_CONTEXT)


def score_candidate(
    query: str, searchable_fields: Iterable[str]
) -> tuple[float, list[str]]:
    """Equal-weight lexical query-term coverage."""
    query_terms = tokens(query)
    if not query_terms:
        return 0.0, []

    text = " ".join(searchable_fields)

    if _is_nonfinancial_stock_photo(text):
        return 0.0, []

    matched = sorted(query_terms & tokens(text))
    return round(len(matched) / len(query_terms), 3), matched


def score_candidate_fields(
    query: str,
    name: str,
    description: str = "",
    topics: Iterable[str] = (),
) -> tuple[float, list[str]]:
    """
    Weighted query-term coverage:
    repository name: 1.00
    repository topics: 0.90
    description: 0.75

    Returns a relevance score, not an AI confidence estimate.
    """
    query_terms = tokens(query)
    if not query_terms:
        return 0.0, []

    topic_list = list(topics)
    all_text = " ".join([name, description, *topic_list])

    if _is_nonfinancial_stock_photo(all_text):
        return 0.0, []

    name_terms = tokens(name)
    topic_terms = tokens(" ".join(topic_list))
    description_terms = tokens(description)

    weights = []
    matched = []

    for term in sorted(query_terms):
        if term in name_terms:
            weight = 1.0
        elif term in topic_terms:
            weight = 0.9
        elif term in description_terms:
            weight = 0.75
        else:
            weight = 0.0

        weights.append(weight)

        if weight > 0:
            matched.append(term)

    score = round(sum(weights) / len(query_terms), 3)
    return score, matched
