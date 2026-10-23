from app.services.scoring import (
    score_candidate,
    score_candidate_fields,
    tokens,
)


def test_tokens_remove_common_words():
    assert tokens("I want an AI agent for GitHub") == {"ai", "github"}


def test_hyphenated_names_split_into_terms():
    assert tokens("stock-market-research") == {
        "stock", "market", "research"
    }


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


def test_repository_name_match_outranks_description_match():
    name_score, _ = score_candidate_fields(
        "stock market research",
        "stock-market-research",
        "Research tools",
    )
    description_score, _ = score_candidate_fields(
        "stock market research",
        "general-data-tools",
        "Tools for stock market research",
    )

    assert name_score == 1.0
    assert description_score == 0.75
    assert name_score > description_score


def test_topic_match_outranks_description_match():
    topic_score, _ = score_candidate_fields(
        "financial",
        "data-tool",
        "Useful developer software",
        ["financial"],
    )
    description_score, _ = score_candidate_fields(
        "financial",
        "data-tool",
        "Financial software",
    )

    assert topic_score == 0.9
    assert description_score == 0.75
    assert topic_score > description_score


def test_weighted_score_reports_matched_terms():
    score, matched = score_candidate_fields(
        "Indian stock research",
        "stock-research",
        "Indian market information",
    )

    assert score == 0.917
    assert matched == ["indian", "research", "stock"]


def test_unrelated_repository_scores_zero():
    assert score_candidate_fields(
        "stock market data",
        "weather-dashboard",
        "Weather forecasts and climate charts",
    ) == (0.0, [])
