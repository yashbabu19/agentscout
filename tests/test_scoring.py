from app.services.scoring import score_candidate, tokens


def test_tokens_remove_common_words():
    assert tokens("I want an AI agent for GitHub") == {"ai", "github"}


def test_score_is_query_term_coverage():
    score, matched = score_candidate(
        "Indian stock research",
        ["Indian market research agent"],
    )
    assert score == 0.667
    assert matched == ["indian", "research"]


def test_no_query_terms_scores_zero():
    assert score_candidate("the and for", ["anything"]) == (0.0, [])

def test_stock_photo_repository_is_not_a_finance_match():
    score, matched = score_candidate(
        "stock market data",
        ["Design resources for developers", "Stock photos and web templates"],
    )
    assert score == 0.0
    assert matched == []
