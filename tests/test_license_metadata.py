from app.services.discovery import _license_name


def test_returns_confirmed_spdx_license():
    assert _license_name({
        "license": {"spdx_id": "MIT", "name": "MIT License"}
    }) == "MIT"


def test_noassertion_is_not_a_confirmed_license():
    assert _license_name({
        "license": {"spdx_id": "NOASSERTION", "name": "Other"}
    }) is None


def test_missing_or_malformed_license_is_unknown():
    assert _license_name({"license": None}) is None
    assert _license_name({"license": "MIT"}) is None
    assert _license_name({}) is None


def test_uses_name_when_spdx_id_is_unavailable():
    assert _license_name({
        "license": {
            "spdx_id": "NOASSERTION",
            "name": "Apache License 2.0",
        }
    }) == "Apache License 2.0"
