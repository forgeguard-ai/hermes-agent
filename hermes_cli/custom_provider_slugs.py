"""Fork-owned handling of ``custom:<name>`` provider slugs.

The pickers and the desktop settings namespace every provider row as
``custom:<name>``. For endpoints declared under ``providers:`` or
``custom_providers:`` those resolve to a durable id, but the BARE custom
endpoint (``model.provider: custom`` + ``base_url``, the shape deployment
managers write) declares no entry, so its UI row slug (``custom:custom``)
resolves to nothing. Persisting such a slug verbatim bricks agent init with
"Unknown provider 'custom:custom'". The helpers here keep every write path
and the credential probe consistent; the upstream files carry one-line calls.

Related one-line patches that stay in upstream files (they cannot be hooks):

* ``hermes_cli/auth.py::resolve_provider`` resolves ``custom:custom`` to
  ``custom``. It names the bare endpoint, so resolving it to the bare
  provider is exact, not a guess. Deliberately NOT a
  ``startswith("custom:")`` prefix match: a namespaced slug for a DECLARED
  entry (``custom:mimo-v2.5-pro``) must keep raising there, because three
  call sites in ``runtime_provider.py`` use
  ``resolve_provider(x) == "custom"`` as the signal to collapse
  ``requested_norm`` to bare ``custom``; resolving a named slug would
  destroy the entry identity they exist to recover (the legacy-row healing
  path in ``tests/tui_gateway/test_custom_provider_session_persistence.py``
  then drops back to placeholder ``no-key-required`` credentials instead of
  the entry's real key). Their ``except AuthError: pass`` is load-bearing.
  Equality also sidesteps ``.startswith`` on a non-str ``normalized`` (YAML
  ``provider: 123``, or a mock), which returns a truthy object and swallowed
  every provider into the custom branch.
* ``hermes_cli/auth.py::_PLACEHOLDER_SECRET_VALUES`` includes ``"no-key"``.
  Deployment managers ship ``no-key`` as the profile default for an endpoint
  with no credential. Treating it as usable let it pass the env-var provider
  checks and route a request to an aggregator with no real credential
  attached (OpenRouter's "HTTP 401: Missing Authentication header").
  ``"no-key-required"`` stays OUT of that set on purpose: the credential
  resolver substitutes it as the deliberate non-empty bearer for no-auth
  endpoints, and the AuthError guard in ``resolve_provider_credentials``
  relies on it passing.
* ``tui_gateway/server.py::_stored_session_runtime_overrides`` keeps a NAMED
  custom slug that healing could not map to a registered entry verbatim: the
  fork's agent init resolves ``custom:<name>`` (with the stored base_url when
  present) through :func:`canonicalize_provider_slug` / ``resolve_provider``,
  so dropping it there would lose the user's pinned endpoint identity on
  resume.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, Optional, Tuple

from hermes_cli.providers import resolve_custom_provider, resolve_user_provider

BARE_CUSTOM_ROW_SLUG = "custom:custom"


def canonicalize_provider_slug(provider: str, config: Optional[Dict[str, Any]] = None) -> str:
    """Collapse a UI provider slug into an id the credential resolver can load.

    The pickers and the desktop settings hand around namespaced slugs
    (``custom:<name>``). For endpoints declared under ``providers:`` or
    ``custom_providers:`` those resolve to a durable id — but the BARE custom
    endpoint (``model.provider: custom`` + base_url, the shape deployment
    managers write) declares no entry, so its UI row slug (``custom:custom``)
    resolves to nothing. Persisting that string verbatim bricks agent init
    with "Unknown provider 'custom:custom'"; every write path must collapse
    it to ``custom`` instead. Anything that is not a ``custom:*`` slug is
    returned unchanged — this is a slug repair, not a general resolver.
    """
    raw = (provider or "").strip()
    if not raw.lower().startswith("custom:"):
        return raw

    cfg = config if isinstance(config, dict) else {}
    user_providers = cfg.get("providers")
    if isinstance(user_providers, dict):
        pdef = resolve_user_provider(raw.lower(), user_providers)
        if pdef is not None:
            return pdef.id
    try:
        from hermes_cli.config import get_compatible_custom_providers

        pdef = resolve_custom_provider(raw, get_compatible_custom_providers(cfg))
        if pdef is not None:
            return pdef.id
    except Exception:
        pass
    return "custom"


def canonicalize_provider_slug_or_keep(provider: str, load_cfg: Callable[[], Dict[str, Any]],
                                       log: logging.Logger) -> str:
    """:func:`canonicalize_provider_slug` against ``load_cfg()``, keeping
    *provider* when that yields nothing or fails (failure logged at debug).

    For persisting a model pick (``model.provider``): a composer/menu pick
    hands over the UI slug, and a ``--global`` pick must never write a
    provider that bricks the next agent init with "Unknown provider"."""
    try:
        return canonicalize_provider_slug(provider, load_cfg()) or provider
    except Exception:
        log.debug("provider slug canonicalization failed", exc_info=True)
        return provider


def is_custom_class(provider: str) -> bool:
    """Bare ``custom`` and any ``custom:<name>`` slug — one endpoint class."""
    p = (provider or "").strip().lower()
    return p == "custom" or p.startswith("custom:")


def collapse_unresolved_custom_slug(canonical: str, prov_in: str, cfg: Any,
                                    log: logging.Logger) -> Optional[str]:
    """The provider id to persist for a ``custom:*`` slug that resolved to no
    declared entry, or ``None`` to fall through to upstream's handling.

    * ``custom:custom`` (the bare endpoint's UI row) always collapses back to
      the bare provider id. A named ``custom:<name>`` that missed resolution
      keeps its durable slug by default (upstream behavior): preserving the
      name keeps the config actionable — the resolver's AuthError/healing
      path reports the missing entry by name instead of silently rebinding
      the model to the bare endpoint.
    * A named ``custom:<name>`` that resolves to NO entry (the deployment
      manager rewrote config.yaml and dropped it, or the desktop's cached row
      outlived it) must not be persisted verbatim when the bare endpoint is
      ROUTABLE — ``model.base_url`` is set — because agent init then dies
      with "Unknown provider 'custom:<name>'" for every new session while the
      URL it should use sits right there. Collapse it to ``custom`` and let
      the log carry the name. With no base_url there is nothing to route to,
      so the slug stays.
    """
    if canonical == BARE_CUSTOM_ROW_SLUG:
        return canonicalize_provider_slug(prov_in, cfg if isinstance(cfg, dict) else {})
    if canonical.startswith("custom:"):
        model_block = cfg.get("model") if isinstance(cfg, dict) else None
        routable = isinstance(model_block, dict) and bool(str(model_block.get("base_url") or "").strip())
        if routable:
            collapsed = canonicalize_provider_slug(prov_in, cfg if isinstance(cfg, dict) else {})
            if collapsed != canonical:
                log.warning(
                    "model.provider %r names no configured custom endpoint; storing %r "
                    "(model.base_url routes the bare endpoint)",
                    canonical, collapsed,
                )
            return collapsed
    return None


def same_custom_endpoint(prev_provider: str, new_provider: str, prev_base_url: str,
                         base_url: str) -> bool:
    """Bare ``custom`` and ``custom:<name>`` are the SAME endpoint when they
    name the same base_url — the desktop's Model settings goes bare-custom →
    named row for the URL it already had (its first Apply auto-registers the
    entry, the second selects it). Treating that as a provider switch cleared
    ``model.api_key`` and the next request went out with a placeholder bearer
    (HTTP 401). Same endpoint ⇒ same credentials.

    *prev_base_url* is the stored ``model.base_url`` already stripped of
    whitespace and trailing ``/``."""
    return (
        is_custom_class(prev_provider)
        and is_custom_class(new_provider)
        and bool(prev_base_url)
        and (base_url.strip().rstrip("/") or prev_base_url) == prev_base_url
    )


def user_provider_entry(providers_cfg: Any, provider: str) -> Any:
    """The ``providers:`` entry for *provider*. Entries are keyed by bare
    name; the slug the UI hands back is ``custom:<name>``, so look both up."""
    provider_entry = None
    if isinstance(providers_cfg, dict):
        provider_entry = providers_cfg.get(provider)
        if provider_entry is None and provider.lower().startswith("custom:"):
            provider_entry = providers_cfg.get(provider.split(":", 1)[1])
    return provider_entry


def model_endpoint_credential_for_entry() -> Tuple[str, str]:
    """(api_key, key_env) a ``custom_providers`` entry auto-registered for the
    CURRENT ``model.*`` endpoint should carry. Reads the RAW config so a
    ``${HERMES_LLM_API_KEY}``-style reference (the shape deployment managers
    write) is preserved as ``key_env`` rather than expanded and written to
    config.yaml as a literal secret.

    The desktop never sends the endpoint key (secrets do not cross the
    settings wire), so auto-registration used to write a KEYLESS entry for an
    endpoint that requires auth — selecting that row next was HTTP 401 on
    every request. A ``${VAR}`` reference becomes the entry's ``key_env``
    (never the literal); a literal key is copied."""
    try:
        from hermes_cli.config import _env_ref_var_name, read_raw_config_readonly

        raw_model = read_raw_config_readonly().get("model")
        raw_key = ""
        if isinstance(raw_model, dict):
            raw_key = str(raw_model.get("api_key") or raw_model.get("api") or "").strip()
        if not raw_key:
            return "", ""
        ref = re.fullmatch(r"\$\{([^}]+)\}", raw_key)
        if ref:
            var = _env_ref_var_name(ref.group(1))
            return ("", var) if var else ("", "")
        return raw_key, ""
    except Exception:
        return "", ""


def custom_endpoint_key_probe(load_cfg: Callable[[], Any], value: str) -> Optional[Dict[str, Any]]:
    """Validate ``OPENAI_API_KEY`` against the configured CUSTOM endpoint.

    On a config whose model provider is custom (a vLLM / llama.cpp / any
    self-hosted OpenAI-compatible server), the key authenticates against
    ``model.base_url``, not api.openai.com. The fixed-table probe would send
    that key to OpenAI and report its 401 as "That API key was rejected" — a
    false rejection of a perfectly good key. Probe the configured endpoint
    instead, with the same response contract. Returns ``None`` when the
    config has no custom endpoint (the caller falls through to its table).
    """
    import httpx

    custom_base = ""
    try:
        cfg = load_cfg()
        model_cfg = cfg.get("model", {}) if isinstance(cfg, dict) else {}
        prov = str(model_cfg.get("provider", "") or "").strip().lower()
        if prov == "custom" or prov.startswith("custom:"):
            custom_base = str(model_cfg.get("base_url", "") or "").strip()
    except Exception:
        custom_base = ""
    if not custom_base:
        return None
    url = custom_base.rstrip("/") + "/models"
    try:
        with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
            resp = client.get(url, headers={"Authorization": f"Bearer {value}"})
    except Exception:
        return {"ok": False, "reachable": False, "message": f"Could not reach {url}."}
    if resp.status_code in (401, 403):
        return {"ok": False, "reachable": True, "message": "That API key was rejected. Double-check it and try again."}
    if resp.status_code == 429 or resp.is_success:
        return {"ok": True, "reachable": True, "message": ""}
    return {"ok": False, "reachable": True, "message": f"Provider returned HTTP {resp.status_code} for this key."}
