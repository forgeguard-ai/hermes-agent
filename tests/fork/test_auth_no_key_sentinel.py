"""Fork-owned tests: the "no-key" deploy sentinel is not a usable secret.

Covers the fork patch in ``hermes_cli/auth.py`` that adds ``"no-key"`` to the
placeholder-secret set while ``"no-key-required"`` stays usable (see
``docs/maintainers/upstream-sync/patch-inventory.md``).

These cases were copied from ``tests/hermes_cli/test_auth_usable_secret.py``,
which upstream has deleted. The duplication is intentional until the next
upstream sync: the sync accepts upstream's deletion of that file, and from then
on this file is the only home for these cases. The two upstream baseline cases
are carried too, so this file still proves the placeholder check works at all
(rejects documentation placeholders, accepts generated keys) once the upstream
file is gone.
"""

from hermes_cli.auth import has_usable_secret


def test_has_usable_secret_rejects_documented_placeholder_key() -> None:
    """Network-exposed API server key must reject static documentation placeholders."""
    assert not has_usable_secret("your_api_key_here", min_length=8)


def test_has_usable_secret_accepts_generated_key() -> None:
    """Random-looking keys should still be accepted."""
    assert has_usable_secret("b4d59f7fe8b857d0b367ef0f5710b6a4", min_length=8)


def test_has_usable_secret_rejects_deploy_no_key_sentinel() -> None:
    """"no-key" is a deployment default, not a credential.

    A deployment manager seeds endpoints.llm.apiKey with "no-key" when a profile has
    no credential. Treating it as usable let provider auto-detection see a
    "configured" OPENAI_API_KEY and route the request to an aggregator with
    no real credential — OpenRouter's "HTTP 401: Missing Authentication
    header" (2026-08-10, live fleet).
    """
    assert not has_usable_secret("no-key")
    assert not has_usable_secret("NO-KEY")


def test_has_usable_secret_still_accepts_no_key_required() -> None:
    """The resolver's own no-auth placeholder must stay usable.

    "no-key-required" is deliberately substituted for no-auth endpoints (LM
    Studio path) and the AuthError guard in credential resolution relies on
    it passing — see runtime_provider.resolve_provider_credentials.
    """
    assert has_usable_secret("no-key-required")
