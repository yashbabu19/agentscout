
from datetime import datetime, timedelta, timezone

from app.services.quality import assess_github_quality


NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


def make_repo(**overrides):
    repo = {
        "pushed_at": (NOW - timedelta(days=10)).isoformat(),
        "stargazers_count": 150,
        "license": {"spdx_id": "MIT", "name": "MIT License"},
        "archived": False,
    }
    repo.update(overrides)
    return repo


def test_healthy_metadata_gets_high_quality_score():
    score, signals = assess_github_quality(make_repo(), now=NOW)

    assert score == 95
    assert any("Updated within the last 30 days" in s for s in signals)
    assert any("MIT" in s for s in signals)


def test_archived_repository_loses_active_status_points():
    score, signals = assess_github_quality(
        make_repo(archived=True),
        now=NOW,
    )

    assert score == 75
    assert any("archived" in s.lower() for s in signals)


def test_old_repository_gets_no_recent_maintenance_points():
    score, signals = assess_github_quality(
        make_repo(pushed_at=(NOW - timedelta(days=500)).isoformat()),
        now=NOW,
    )

    assert score == 60
    assert any("within the last year" in s for s in signals)


def test_missing_metadata_is_reported_without_crashing():
    score, signals = assess_github_quality({}, now=NOW)

    assert score == 0
    assert any("unknown" in s.lower() for s in signals)
    assert any("license" in s.lower() for s in signals)


def test_malformed_date_and_star_count_are_safe():
    score, signals = assess_github_quality(
        make_repo(pushed_at="not-a-date", stargazers_count="many"),
        now=NOW,
    )

    assert score == 45
    assert any("Maintenance history unknown" in s for s in signals)
    assert any("Popularity unknown" in s for s in signals)


def test_quality_score_never_exceeds_100():
    score, _ = assess_github_quality(make_repo(), now=NOW)

    assert 0 <= score <= 100
