"""Fork-owned per-session model pin for the TUI gateway.

A stored session row remembers which model the chat ran on. The fork makes
that memory say *who chose it*, so a resume only restores a model the user
actually picked for this chat:

* ``model_config["model_source"] = "user"`` — an explicit composer/menu pick
  or a pinning ``/model`` switch. Restored verbatim on resume.
* ``model_config["model_source"] = "default"`` — the global default stamped
  when the row was created because the chat made no pick. Such a row must
  NOT read as a pin on resume, or a later config.yaml model change (a
  renamed vLLM served model, say) never reaches the chat again and it 404s
  forever on the retired name.
* Rows written before ``model_source`` existed are treated as default when
  they point at the SAME endpoint config does (the rename case) and as a pin
  when they name a different endpoint: re-pinning a legacy chat is one
  ``/model`` away; a chat that 404s forever is not.

A resumed chat that moves on to config's current model parks a one-line
notice (``session["pending_model_notice"]``) that the first turn emits.

``tui_gateway/server.py`` keeps thin wrappers (``_stored_model_is_pinned``,
``_stored_model_adoption_notice``) that pass in its config readers, so tests
patching ``server._load_cfg`` / ``server._config_model_target`` keep working.
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

PENDING_NOTICE_KEY = "pending_model_notice"


def row_model_source(override: dict) -> str:
    """``model_source`` for a freshly created row: ``user`` when the chat named
    a model override, else ``default``."""
    return "user" if str(override.get("model") or "").strip() else "default"


def provider_class(provider: str) -> str:
    """The billing/routing class of a provider slug: ``custom:<name>`` and
    ``custom`` are one class (a named custom endpoint), everything else is
    itself."""
    p = (provider or "").strip().lower()
    if p == "custom" or p.startswith("custom:"):
        return "custom"
    return p


def stored_model_is_pinned(model_config: dict, model: str, provider: str, base_url: str,
                           *, load_cfg: Callable[[], dict]) -> bool:
    """Whether a stored session row's model should be restored as a session
    override. ``model_config.model_source`` is authoritative when present
    (``user`` = pin, ``default`` = follow config). A legacy row without it
    keeps the historical pin EXCEPT in the one case that pin is known to be
    harmful: the row names a different model than config.yaml's current
    default while pointing at the SAME endpoint — the served-model rename,
    where restoring the old name 404s on every turn until the operator
    re-picks. A legacy row on a different endpoint is a real pin and stays.

    ``load_cfg`` is only called for a legacy row."""
    source = str((model_config or {}).get("model_source") or "").strip().lower()
    if source == "user":
        return True
    if source == "default":
        return False
    cfg_model = load_cfg().get("model")
    cfg_default = ""
    cfg_provider = ""
    cfg_base_url = ""
    if isinstance(cfg_model, dict):
        cfg_default = str(cfg_model.get("default") or "").strip()
        cfg_provider = str(cfg_model.get("provider") or "").strip()
        cfg_base_url = str(cfg_model.get("base_url") or "").strip()
    elif isinstance(cfg_model, str):
        cfg_default = cfg_model.strip()
    if not cfg_default or not model or model == cfg_default:
        # Same model (or nothing to compare against): the pin is harmless.
        return True
    stored_url = (base_url or "").rstrip("/")
    config_url = cfg_base_url.rstrip("/")
    if stored_url and config_url:
        return stored_url != config_url
    if provider and cfg_provider:
        return provider_class(provider) != provider_class(cfg_provider)
    # A different model and no endpoint evidence either way: config's model
    # is what the operator maintains; the chat follows it.
    return False


def adoption_notice(row: dict | None, overrides: dict,
                    *, config_model_target: Callable[[], Tuple[str, str]]) -> Optional[str]:
    """A one-line status for a resumed chat whose stored model was NOT pinned
    and differs from config.yaml's current model — so the operator learns the
    chat moved on rather than wondering why the footer changed."""
    if not row or overrides.get("model_override"):
        return None
    stored = str(row.get("model") or "").strip()
    if not stored:
        return None
    current, _ = config_model_target()
    if not current or current == stored:
        return None
    return (
        f"This chat was last on {stored}, which is no longer the configured "
        f"default; continuing on {current}. Use the model picker to pin a model to this chat."
    )
