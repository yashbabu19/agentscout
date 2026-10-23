from app.models import Candidate
from app.services.evidence import extract_setup_hints, recommendation_reasons


def test_extracts_only_supported_install_commands():
    readme = """
# Setup
Install the package:
pip install example-agent
npm install @example/mcp
npx example-server
docker run example/image
This is just explanatory prose, not a command.
"""
    hints = extract_setup_hints(readme)

    assert "pip install example-agent" in hints
    assert "npm install @example/mcp" in hints
    assert "npx example-server" in hints
    assert "docker run example/image" in hints
    assert not any("explanatory prose" in hint for hint in hints)


def test_setup_hints_are_deduplicated():
    readme = "pip install example\npip install example\n"
    assert extract_setup_hints(readme) == ["pip install example"]


def test_setup_hints_are_bounded():
    readme = "\n".join(f"pip install package-{i}" for i in range(20))
    assert len(extract_setup_hints(readme, max_items=5)) == 5


def test_recommendation_reasons_explain_matching_and_metadata():
    candidate = Candidate(
        id="github:example/repo",
        name="example/repo",
        source="github",
        url="https://github.com/example/repo",
        resource_type="github_repository",
        relevance_score=0.9,
        matched_terms=["mcp", "python"],
        stars=123,
        quality_score=80,
        license="MIT",
    )

    reasons = recommendation_reasons(candidate)

    assert any("mcp" in reason for reason in reasons)
    assert any("123 stars" in reason for reason in reasons)
    assert any("80/100" in reason for reason in reasons)
    assert any("MIT" in reason for reason in reasons)


def test_reasons_do_not_claim_security():
    candidate = Candidate(
        id="github:example/repo",
        name="example/repo",
        source="github",
        url="https://github.com/example/repo",
        resource_type="github_repository",
        relevance_score=0.5,
    )

    reasons = recommendation_reasons(candidate)

    assert reasons
    assert not any("secure" in reason.lower() or "safe" in reason.lower() for reason in reasons)
