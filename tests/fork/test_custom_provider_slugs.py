"""Fork-owned tests: ``hermes_cli/custom_provider_slugs.py`` helpers.

``canonicalize_provider_slug`` and the web-server integration are covered in
``tests/hermes_cli/test_custom_provider_slug_canonicalization.py``; these pin
the helpers the upstream call sites delegate to.
"""

import logging

import pytest

from hermes_cli import custom_provider_slugs as slugs

_log = logging.getLogger("test.custom_provider_slugs")


@pytest.mark.parametrize(("provider", "expected"), [
    ("custom", True), ("custom:box", True), (" CUSTOM:x ", True),
    ("customproxy", False), ("openrouter", False), ("", False), (None, False),
])
def test_is_custom_class(provider, expected):
    assert slugs.is_custom_class(provider) is expected


class TestCollapseUnresolvedCustomSlug:
    def test_bare_row_slug_always_collapses(self):
        assert slugs.collapse_unresolved_custom_slug("custom:custom", "custom:custom", {}, _log) == "custom"

    def test_named_slug_collapses_when_bare_endpoint_is_routable(self, caplog):
        cfg = {"model": {"provider": "custom", "base_url": "https://llm.example/v1"}}
        with caplog.at_level(logging.WARNING, logger=_log.name):
            got = slugs.collapse_unresolved_custom_slug("custom:gone", "custom:gone", cfg, _log)
        assert got == "custom"
        assert "custom:gone" in caplog.text

    def test_named_slug_falls_through_without_base_url(self):
        assert slugs.collapse_unresolved_custom_slug("custom:gone", "custom:gone", {"model": {}}, _log) is None

    def test_non_custom_falls_through(self):
        assert slugs.collapse_unresolved_custom_slug("openrouter", "openrouter", {}, _log) is None


class TestSameCustomEndpoint:
    def test_bare_to_named_on_same_url(self):
        assert slugs.same_custom_endpoint("custom", "custom:box", "https://x/v1", "https://x/v1/") is True

    def test_empty_new_url_keeps_the_stored_one(self):
        assert slugs.same_custom_endpoint("custom:box", "custom", "https://x/v1", "") is True

    def test_different_url_is_a_switch(self):
        assert slugs.same_custom_endpoint("custom", "custom:box", "https://x/v1", "https://y/v1") is False

    def test_non_custom_side_is_a_switch(self):
        assert slugs.same_custom_endpoint("openrouter", "custom", "https://x/v1", "") is False

    def test_no_stored_url_is_a_switch(self):
        assert slugs.same_custom_endpoint("custom", "custom:box", "", "https://x/v1") is False


def test_user_provider_entry_accepts_the_namespaced_slug():
    providers = {"box": {"base_url": "https://box/v1"}}
    assert slugs.user_provider_entry(providers, "box") == providers["box"]
    assert slugs.user_provider_entry(providers, "custom:box") == providers["box"]
    assert slugs.user_provider_entry(providers, "custom:none") is None
    assert slugs.user_provider_entry(None, "custom:box") is None


def test_canonicalize_or_keep_survives_a_failing_config_read():
    def boom():
        raise RuntimeError("no config")

    assert slugs.canonicalize_provider_slug_or_keep("custom:custom", boom, _log) == "custom:custom"
    assert slugs.canonicalize_provider_slug_or_keep("custom:custom", dict, _log) == "custom"


def test_custom_endpoint_key_probe_skips_non_custom_configs():
    assert slugs.custom_endpoint_key_probe(lambda: {"model": {"provider": "openrouter"}}, "k") is None
    assert slugs.custom_endpoint_key_probe(lambda: {"model": {"provider": "custom"}}, "k") is None

    def boom():
        raise RuntimeError("bad profile")

    assert slugs.custom_endpoint_key_probe(boom, "k") is None


@pytest.mark.parametrize(("status", "ok"), [(200, True), (429, True), (401, False), (500, False)])
def test_custom_endpoint_key_probe_status_contract(monkeypatch, status, ok):
    seen = {}

    class _Resp:
        status_code = status
        is_success = 200 <= status < 300

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, headers=None):
            seen["url"], seen["headers"] = url, headers
            return _Resp()

    monkeypatch.setattr("httpx.Client", _Client)
    cfg = {"model": {"provider": "custom:box", "base_url": "https://box/v1/"}}
    result = slugs.custom_endpoint_key_probe(lambda: cfg, "secret")
    assert result["ok"] is ok
    assert seen["url"] == "https://box/v1/models"
    assert seen["headers"] == {"Authorization": "Bearer secret"}
