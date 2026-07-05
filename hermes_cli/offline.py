"""Native offline / privacy-mode gate.

The ForgeGuard deployment manager writes a set of ``HERMES_OFFLINE_*`` env vars
into ``$HERMES_HOME/.env`` (see write_env_file in the manager script) when a
profile enables offline mode. Historically those flags were only honored by a
reversible source *patch* injected into the checkout; this module lets the agent
honor them **natively**, so the same profile toggle works on sealed managed
images (where the patch is skipped) and reduces the patch surface over time.

Every helper is a pure ``os.environ`` read with no side effects, so it is cheap
to call on hot paths and trivially testable via ``monkeypatch.setenv``.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def offline_enabled() -> bool:
    """Master switch — HERMES_OFFLINE_MODE. All other gates require this."""
    return _flag("HERMES_OFFLINE_MODE")


def remote_catalog_disabled() -> bool:
    """Skip remote model-catalog fetches (fall back to the bundled snapshot)."""
    return offline_enabled() and _flag("HERMES_OFFLINE_DISABLE_REMOTE_CATALOG")


def remote_metadata_disabled() -> bool:
    """Skip remote model-metadata (models.dev) fetches; use cache/snapshot."""
    return offline_enabled() and _flag("HERMES_OFFLINE_DISABLE_REMOTE_METADATA")


def update_checks_disabled() -> bool:
    """Skip update-availability checks (git ls-remote / PyPI)."""
    return offline_enabled() and _flag("HERMES_OFFLINE_DISABLE_UPDATE_CHECKS")


def portal_checks_disabled() -> bool:
    """Skip Nous Portal account/entitlement/registration calls."""
    return offline_enabled() and _flag("HERMES_OFFLINE_DISABLE_PORTAL_CHECKS")


def status() -> dict[str, bool]:
    """A snapshot of the resolved gate for diagnostics / status reporting."""
    return {
        "offline": offline_enabled(),
        "remoteCatalogDisabled": remote_catalog_disabled(),
        "remoteMetadataDisabled": remote_metadata_disabled(),
        "updateChecksDisabled": update_checks_disabled(),
        "portalChecksDisabled": portal_checks_disabled(),
    }
