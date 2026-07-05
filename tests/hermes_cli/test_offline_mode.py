"""Tests for the native offline / privacy-mode gate (hermes_cli.offline).

These tests assert the gate at each of the six network call sites the ForgeGuard
deployment manager's source patch covers. The key property: with the relevant
gate on, the underlying **network function is never called**. Each test spies on
that function with a MagicMock and asserts ``assert_not_called()`` so it FAILS if
the gate is removed — a swallowed exception (``fetch_models_dev`` wraps its fetch
in ``except Exception``) would otherwise hide a broken gate.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hermes_cli import offline


def _set(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)


# ---------------------------------------------------------------------------
# Flag resolution
# ---------------------------------------------------------------------------


def test_gates_require_master_switch(monkeypatch):
    # Feature flag set but master switch off → gate stays closed.
    monkeypatch.delenv("HERMES_OFFLINE_MODE", raising=False)
    _set(monkeypatch, HERMES_OFFLINE_DISABLE_REMOTE_CATALOG="1")
    assert offline.offline_enabled() is False
    assert offline.remote_catalog_disabled() is False


def test_each_gate_resolves(monkeypatch):
    _set(
        monkeypatch,
        HERMES_OFFLINE_MODE="1",
        HERMES_OFFLINE_DISABLE_REMOTE_CATALOG="1",
        HERMES_OFFLINE_DISABLE_REMOTE_METADATA="true",
        HERMES_OFFLINE_DISABLE_UPDATE_CHECKS="yes",
        HERMES_OFFLINE_DISABLE_PORTAL_CHECKS="on",
    )
    assert offline.offline_enabled() is True
    assert offline.remote_catalog_disabled() is True
    assert offline.remote_metadata_disabled() is True
    assert offline.update_checks_disabled() is True
    assert offline.portal_checks_disabled() is True


def test_falsey_values(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="0")
    assert offline.offline_enabled() is False
    _set(monkeypatch, HERMES_OFFLINE_MODE="false")
    assert offline.offline_enabled() is False
    monkeypatch.delenv("HERMES_OFFLINE_MODE", raising=False)
    assert offline.offline_enabled() is False


def test_unset_disable_flags_default_to_disabled_when_offline(monkeypatch):
    # H2: with only the master switch on and every DISABLE_* flag UNSET, all four
    # per-site gates default to disabled (matching the source patch's
    # os.getenv(flag, "1") behavior).
    _set(monkeypatch, HERMES_OFFLINE_MODE="1")
    for name in (
        "HERMES_OFFLINE_DISABLE_REMOTE_CATALOG",
        "HERMES_OFFLINE_DISABLE_REMOTE_METADATA",
        "HERMES_OFFLINE_DISABLE_UPDATE_CHECKS",
        "HERMES_OFFLINE_DISABLE_PORTAL_CHECKS",
    ):
        monkeypatch.delenv(name, raising=False)
    assert offline.remote_catalog_disabled() is True
    assert offline.remote_metadata_disabled() is True
    assert offline.update_checks_disabled() is True
    assert offline.portal_checks_disabled() is True


def test_explicit_falsey_disable_flag_reenables_site(monkeypatch):
    # An explicit falsey DISABLE_* value opts a single site back in even while
    # offline mode is on.
    _set(
        monkeypatch,
        HERMES_OFFLINE_MODE="1",
        HERMES_OFFLINE_DISABLE_REMOTE_CATALOG="0",
    )
    assert offline.remote_catalog_disabled() is False
    # Other unset sites still default to disabled.
    monkeypatch.delenv("HERMES_OFFLINE_DISABLE_PORTAL_CHECKS", raising=False)
    assert offline.portal_checks_disabled() is True


# ---------------------------------------------------------------------------
# Call-site gates — the network function must never be reached when gated
# ---------------------------------------------------------------------------


def test_update_check_short_circuits(monkeypatch):
    # banner.check_for_updates() must return None immediately when the gate is
    # set, before reaching any git/PyPI/home-dir work.
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_UPDATE_CHECKS="1")
    from hermes_cli import banner

    # Everything the function would touch *after* the gate.
    spies = {
        "_check_via_rev": MagicMock(return_value=0),
        "_check_via_local_git": MagicMock(return_value=0),
        "check_via_pypi": MagicMock(return_value=0),
        "get_hermes_home": MagicMock(side_effect=AssertionError("home reached")),
    }
    for name, spy in spies.items():
        monkeypatch.setattr(banner, name, spy, raising=False)

    assert banner.check_for_updates() is None
    for spy in spies.values():
        spy.assert_not_called()


def test_models_dev_skips_network_when_offline(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_REMOTE_METADATA="1")
    from agent import models_dev

    # Force stages 1/2 empty so only the network path could produce data.
    monkeypatch.setattr(models_dev, "_models_dev_cache", {}, raising=False)
    monkeypatch.setattr(models_dev, "_load_disk_cache", lambda: {}, raising=False)

    # Spy on the network layer. fetch_models_dev swallows exceptions, so a raising
    # mock would hide a broken gate — assert the call simply never happens.
    get_spy = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(models_dev.requests, "get", get_spy, raising=False)

    assert models_dev.fetch_models_dev() == {}
    get_spy.assert_not_called()


def test_model_catalog_fallback_skips_network_when_offline(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_REMOTE_CATALOG="1")
    from hermes_cli import model_catalog

    fetch_spy = MagicMock(return_value={"version": 1, "providers": {}})
    monkeypatch.setattr(model_catalog, "_fetch_manifest", fetch_spy, raising=False)

    assert model_catalog._fetch_manifest_with_fallback("https://x/catalog.json", 1.0) is None
    fetch_spy.assert_not_called()


def test_model_catalog_provider_override_skips_network_when_offline(monkeypatch):
    # _fetch_provider_override calls _fetch_manifest directly, bypassing the gate
    # in _fetch_manifest_with_fallback — assert its own gate holds.
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_REMOTE_CATALOG="1")
    from hermes_cli import model_catalog

    # An enabled config with a provider override URL — without the gate this
    # would trigger a live _fetch_manifest call.
    monkeypatch.setattr(
        model_catalog,
        "_load_catalog_config",
        lambda: {
            "enabled": True,
            "url": "https://x/catalog.json",
            "ttl_hours": 1.0,
            "providers": {"openrouter": {"url": "https://x/openrouter.json"}},
        },
        raising=False,
    )
    fetch_spy = MagicMock(return_value={"version": 1, "providers": {}})
    monkeypatch.setattr(model_catalog, "_fetch_manifest", fetch_spy, raising=False)

    assert model_catalog._fetch_provider_override("openrouter") is None
    fetch_spy.assert_not_called()


def test_model_metadata_skips_network_when_offline(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_REMOTE_METADATA="1")
    from agent import model_metadata

    monkeypatch.setattr(model_metadata, "_model_metadata_cache", {}, raising=False)
    monkeypatch.setattr(
        model_metadata, "_load_model_metadata_disk_cache", lambda: {}, raising=False
    )
    get_spy = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(model_metadata.requests, "get", get_spy, raising=False)

    assert model_metadata.fetch_model_metadata() == {}
    get_spy.assert_not_called()


def test_portal_account_info_skips_network_when_offline(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_PORTAL_CHECKS="1")
    from hermes_cli import nous_account

    fetch_spy = MagicMock(return_value={"user": {}})
    monkeypatch.setattr(nous_account, "_fetch_nous_account_info", fetch_spy, raising=False)

    info = nous_account.get_nous_portal_account_info()
    fetch_spy.assert_not_called()
    # Offline snapshot shape (patch parity): source "none", not fresh, tagged.
    assert info.source == "none"
    assert info.fresh is False
    assert info.error == "offline_mode"


def test_portal_usage_lines_skip_network_when_offline(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_PORTAL_CHECKS="1")
    from agent import account_usage
    from hermes_cli import auth, nous_account

    # A logged-in token so the non-gated path *would* fetch the portal account.
    monkeypatch.setattr(
        auth, "get_provider_auth_state", lambda provider: {"access_token": "tok"}, raising=False
    )
    account_spy = MagicMock(return_value=None)
    monkeypatch.setattr(
        nous_account, "get_nous_portal_account_info", account_spy, raising=False
    )

    assert account_usage.nous_credits_lines() == []
    account_spy.assert_not_called()


def test_billing_request_raises_offline_when_offline(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_PORTAL_CHECKS="1")
    from hermes_cli import nous_billing

    resolve_spy = MagicMock(return_value=("tok", "https://portal.example"))
    monkeypatch.setattr(
        nous_billing, "_resolve_token_and_base", resolve_spy, raising=False
    )

    with pytest.raises(nous_billing.BillingError) as excinfo:
        nous_billing.get_billing_state()
    assert excinfo.value.error == "offline_mode"
    resolve_spy.assert_not_called()
