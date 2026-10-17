"""Fork-owned tests: ``tui_gateway/session_model_pin.py``.

The resume/persist integration cases live in
``tests/tui_gateway/test_session_model_source.py``; these pin the module's
rules directly, with the config readers injected.
"""

import pytest

from tui_gateway import session_model_pin as pin


def _cfg(default="cfg-model", provider="custom", base_url="https://llm.example/v1"):
    return lambda: {"model": {"default": default, "provider": provider, "base_url": base_url}}


def _boom():
    raise AssertionError("config must not be read for a row with model_source")


@pytest.mark.parametrize(("override", "expected"), [
    ({"model": "picked"}, "user"),
    ({"model": "  "}, "default"),
    ({}, "default"),
])
def test_row_model_source(override, expected):
    assert pin.row_model_source(override) == expected


@pytest.mark.parametrize(("provider", "expected"), [
    ("custom", "custom"),
    ("custom:box", "custom"),
    (" Custom:Box ", "custom"),
    ("openrouter", "openrouter"),
    ("", ""),
    (None, ""),
])
def test_provider_class(provider, expected):
    assert pin.provider_class(provider) == expected


def test_explicit_source_is_authoritative_without_reading_config():
    assert pin.stored_model_is_pinned({"model_source": "user"}, "m", "", "", load_cfg=_boom) is True
    assert pin.stored_model_is_pinned({"model_source": "default"}, "m", "", "", load_cfg=_boom) is False


def test_legacy_same_model_is_harmless_pin():
    assert pin.stored_model_is_pinned({}, "cfg-model", "custom", "", load_cfg=_cfg()) is True


def test_legacy_rename_on_same_endpoint_follows_config():
    assert pin.stored_model_is_pinned(
        {}, "old-name", "custom", "https://llm.example/v1/", load_cfg=_cfg()
    ) is False


def test_legacy_different_endpoint_stays_pinned():
    assert pin.stored_model_is_pinned(
        {}, "other", "custom", "https://other.example/v1", load_cfg=_cfg()
    ) is True


def test_legacy_provider_class_decides_without_urls():
    load = _cfg(base_url="")
    assert pin.stored_model_is_pinned({}, "other", "custom:box", "", load_cfg=load) is False
    assert pin.stored_model_is_pinned({}, "other", "openrouter", "", load_cfg=load) is True


def test_legacy_without_endpoint_evidence_follows_config():
    load = lambda: {"model": "cfg-model"}  # noqa: E731
    assert pin.stored_model_is_pinned({}, "other", "", "", load_cfg=load) is False


def test_adoption_notice():
    target = lambda: ("new-model", "custom")  # noqa: E731
    note = pin.adoption_notice({"model": "old-model"}, {}, config_model_target=target)
    assert note and "old-model" in note and "new-model" in note
    assert pin.adoption_notice({"model": "new-model"}, {}, config_model_target=target) is None
    assert pin.adoption_notice({"model": "old"}, {"model_override": {"model": "old"}},
                               config_model_target=target) is None
    assert pin.adoption_notice(None, {}, config_model_target=target) is None
    assert pin.adoption_notice({"model": ""}, {}, config_model_target=target) is None


def test_server_wrappers_pass_the_server_config_readers(monkeypatch):
    from tui_gateway import server

    monkeypatch.setattr(server, "_load_cfg", lambda: {"model": {"default": "cfg-model"}})
    assert server._stored_model_is_pinned({}, "other", "", "") is False
    monkeypatch.setattr(server, "_config_model_target", lambda: ("cfg-model", ""))
    assert "cfg-model" in server._stored_model_adoption_notice({"model": "other"}, {})
