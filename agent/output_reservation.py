"""Resolve the output-token reservation a request will actually carry.

The chat-completions transport picks ``max_tokens`` for the wire in this
order (``agent/transports/chat_completions.py`` — ``build_kwargs``):

    ephemeral (one-shot 400 recovery) > user (``model.max_tokens``) >
    provider-profile default (``ProviderProfile.get_max_tokens``)

The context compressor sizes its compaction trigger from the *usable input
budget* — ``context_length - max_tokens`` (#43547) — but it was only ever
handed ``agent.max_tokens``, i.e. the USER tier. When that is unset, the
transport still reserves the profile default (65536 for the ``custom``
profile, so a 200k vLLM window has a 134k input ceiling) while the
compressor believed the whole window was usable and armed its trigger at
0.8 × 200k = 160k — above anything the session could reach. The result was
no proactive compaction ever, an HTTP 400 at the ceiling, and an emergency
compaction that shed all but the last few messages (2026-08-17, live).

This module is the single place that answers "what will the transport
reserve?", so the compressor and the transport agree from the first turn.
It deliberately does NOT write to ``agent.max_tokens``: a non-None value
there reads as "the user set it" downstream (session init snapshot,
model-switch restore, gateway resolution) and must keep meaning that.
"""

from __future__ import annotations

from typing import Any, Optional


def _positive_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def resolve_output_reservation(
    provider: Optional[str],
    model: Optional[str],
    user_max_tokens: Any = None,
) -> Optional[int]:
    """Return the output-token reservation the transport will send, or None.

    ``user_max_tokens`` is the explicit ``model.max_tokens`` tier and wins
    outright. Otherwise the registered provider profile's per-model default
    is used — exactly what ``build_kwargs`` falls back to. ``None`` means the
    transport will omit ``max_tokens`` (no profile, or a profile with no
    default), in which case the compressor correctly assumes the full window.
    """
    explicit = _positive_int(user_max_tokens)
    if explicit is not None:
        return explicit
    if not provider:
        return None
    try:
        from providers import get_provider_profile

        profile = get_provider_profile(provider)
    except Exception:
        return None
    if profile is None:
        return None
    try:
        return _positive_int(profile.get_max_tokens(model or ""))
    except Exception:
        return None


def resolve_agent_output_reservation(agent: Any) -> Optional[int]:
    """``resolve_output_reservation`` read off a live agent's fields."""
    return resolve_output_reservation(
        getattr(agent, "provider", None),
        getattr(agent, "model", None),
        getattr(agent, "max_tokens", None),
    )


def reservation_kwargs(engine: Any, max_tokens: Optional[int]) -> dict:
    """``{"max_tokens": N}`` for ``engine.update_model(...)`` when that engine
    accepts the keyword, else ``{}``.

    ``ContextCompressor.update_model`` takes ``max_tokens``; the base
    ``ContextEngine.update_model`` and third-party engines that override it
    do not, and passing an unexpected keyword there would turn a model switch
    into a TypeError. A ``None`` reservation is dropped too — the compressor
    reads None as "keep the current value", so passing it is a no-op anyway.
    """
    if max_tokens is None:
        return {}
    update = getattr(engine, "update_model", None)
    if update is None:
        return {}
    try:
        import inspect

        params = inspect.signature(update).parameters
    except (TypeError, ValueError):
        return {}
    if "max_tokens" in params or any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
    ):
        return {"max_tokens": max_tokens}
    return {}
