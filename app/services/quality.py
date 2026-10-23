
from datetime import datetime, timezone
from typing import Any


def assess_github_quality(
    repo: dict[str, Any],
    now: datetime | None = None,
) -> tuple[int, list[str]]:
    """Estimate repository quality from observable metadata.

    This is a heuristic metadata score, not a security assessment.
    Missing or malformed metadata is treated as unknown.
    """
    now = now or datetime.now(timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    score = 0
    signals: list[str] = []

    # Maintenance: up to 35 points.
    pushed_at = repo.get("pushed_at") or repo.get("updated_at")
    pushed_date = None

    if isinstance(pushed_at, str):
        try:
            pushed_date = datetime.fromisoformat(
                pushed_at.replace("Z", "+00:00")
            )
            if pushed_date.tzinfo is None:
                pushed_date = pushed_date.replace(tzinfo=timezone.utc)
        except ValueError:
            pushed_date = None

    if pushed_date is None:
        signals.append("Maintenance history unknown: no valid update date.")
    else:
        age_days = max(0, (now - pushed_date).days)

        if age_days <= 30:
            score += 35
            signals.append("Updated within the last 30 days.")
        elif age_days <= 90:
            score += 25
            signals.append("Updated within the last 90 days.")
        elif age_days <= 180:
            score += 15
            signals.append("Updated within the last 6 months.")
        elif age_days <= 365:
            score += 8
            signals.append("Updated within the last year.")
        else:
            signals.append("No update recorded within the last year.")

    # Popularity: up to 20 points.
    stars = repo.get("stargazers_count")

    if isinstance(stars, int) and not isinstance(stars, bool) and stars >= 0:
        if stars >= 1000:
            score += 20
        elif stars >= 100:
            score += 15
        elif stars >= 10:
            score += 10
        elif stars > 0:
            score += 5

        signals.append(f"GitHub popularity: {stars} stars.")
    else:
        signals.append("Popularity unknown: no valid star count.")

    # Licensing: up to 25 points.
    license_info = repo.get("license")

    if isinstance(license_info, dict):
        spdx_id = license_info.get("spdx_id")
        license_name = license_info.get("name")

        if spdx_id and spdx_id != "NOASSERTION":
            score += 25
            signals.append(f"License detected: {spdx_id}.")
        elif license_name:
            score += 18
            signals.append(f"License name reported: {license_name}; verify its terms.")
        else:
            signals.append("License unclear: verify the repository's license.")
    else:
        signals.append("No license detected in repository metadata.")

    # Archive status: up to 20 points.
    archived = repo.get("archived")

    if archived is True:
        signals.append("Repository is archived.")
    elif archived is False:
        score += 20
        signals.append("Repository is not marked as archived.")
    else:
        signals.append("Archive status unknown.")

    return min(score, 100), signals
