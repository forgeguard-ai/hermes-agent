"""Native offline / privacy-mode gate.

The ForgeGuard deployment manager writes a set of ``HERMES_OFFLINE_*`` env vars
into ``$HERMES_HOME/.env`` (see write_env_file in the manager script) when a
profile enables offline mode. This module lets the agent honor them
**natively**, so the same profile toggle works on sealed managed images (where
the legacy reversible source *patch* is skipped). All six network call sites the
patch covered are now gated natively — remote model-catalog fetches
(``hermes_cli/model_catalog.py``), models.dev metadata (``agent/models_dev.py``),
OpenRouter model metadata (``agent/model_metadata.py``), update-availability
checks (``hermes_cli/banner.py``), and the Nous Portal account/usage/billing
calls (``hermes_cli/nous_account.py``, ``agent/account_usage.py``,
``hermes_cli/nous_billing.py``) — so the source patch is no longer required for
offline mode to hold on a sealed image.

These ``HERMES_OFFLINE_*`` env vars are a deliberate cross-repo interface shared
with the ForgeGuard deployment manager (its ``write_env_file``), NOT general
behavioral config. The AGENTS.md "non-secret config belongs in config.yaml, not
new HERMES_* env vars" rule has a documented exception for this offline/privacy
gate precisely because the flag set is owned jointly with the deployment
manager; see AGENTS.md.

Every helper is a pure ``os.environ`` read with no side effects, so it is cheap
to call on hot paths and trivially testable via ``monkeypatch.setenv``.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}
_NOT_DISABLED = {"0", "false", "no", "off"}


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def _disable_flag(name: str) -> bool:
    """Resolve a per-site ``DISABLE_*`` gate with patch-compatible defaults.

    When offline mode is on, an UNSET ``DISABLE_*`` flag defaults to *disabled*
    — matching the legacy source patch's ``os.getenv(flag, "1")`` semantics: the
    site is skipped unless the value is explicitly falsey ({"0","false","no",
    "off"}). Returns False whenever offline mode is off.
    """
    if not offline_enabled():
        return False
    return os.environ.get(name, "1").strip().lower() not in _NOT_DISABLED


def offline_enabled() -> bool:
    """Master switch — HERMES_OFFLINE_MODE. All other gates require this."""
    return _flag("HERMES_OFFLINE_MODE")


def remote_catalog_disabled() -> bool:
    """Skip remote model-catalog fetches (fall back to the bundled snapshot)."""
    return _disable_flag("HERMES_OFFLINE_DISABLE_REMOTE_CATALOG")


def remote_metadata_disabled() -> bool:
    """Skip remote model-metadata (models.dev) fetches; use cache/snapshot."""
    return _disable_flag("HERMES_OFFLINE_DISABLE_REMOTE_METADATA")


def update_checks_disabled() -> bool:
    """Skip update-availability checks (git ls-remote / PyPI)."""
    return _disable_flag("HERMES_OFFLINE_DISABLE_UPDATE_CHECKS")


def portal_checks_disabled() -> bool:
    """Skip Nous Portal account/entitlement/registration calls."""
    return _disable_flag("HERMES_OFFLINE_DISABLE_PORTAL_CHECKS")
