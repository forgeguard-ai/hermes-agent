"""Tests for the native offline / privacy-mode gate (hermes_cli.offline)."""

from __future__ import annotations

import pytest

from hermes_cli import offline


def _set(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)


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
    st = offline.status()
    assert st["offline"] and st["remoteCatalogDisabled"] and st["portalChecksDisabled"]


def test_falsey_values(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="0")
    assert offline.offline_enabled() is False
    _set(monkeypatch, HERMES_OFFLINE_MODE="false")
    assert offline.offline_enabled() is False
    monkeypatch.delenv("HERMES_OFFLINE_MODE", raising=False)
    assert offline.offline_enabled() is False


def test_update_check_short_circuits(monkeypatch):
    # check_for_updates() must return None immediately when the gate is set,
    # without touching git/PyPI.
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_UPDATE_CHECKS="1")
    from hermes_cli import banner

    assert banner.check_for_updates() is None


def test_models_dev_skips_network_when_offline(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_REMOTE_METADATA="1")
    from agent import models_dev

    # Force stages 1/2 empty and make any network attempt fail loudly.
    monkeypatch.setattr(models_dev, "_models_dev_cache", {}, raising=False)
    monkeypatch.setattr(models_dev, "_load_disk_cache", lambda: {}, raising=False)

    def _boom(*a, **k):  # pragma: no cover - must never be reached
        raise AssertionError("network fetch attempted while offline")

    monkeypatch.setattr(models_dev.requests, "get", _boom, raising=False)
    assert models_dev.fetch_models_dev() == {}


def test_model_catalog_skips_network_when_offline(monkeypatch):
    _set(monkeypatch, HERMES_OFFLINE_MODE="1", HERMES_OFFLINE_DISABLE_REMOTE_CATALOG="1")
    from hermes_cli import model_catalog

    def _boom(*a, **k):  # pragma: no cover - must never be reached
        raise AssertionError("catalog fetch attempted while offline")

    monkeypatch.setattr(model_catalog, "_fetch_manifest", _boom, raising=False)
    assert model_catalog._fetch_manifest_with_fallback("https://x/catalog.json", 1.0) is None
