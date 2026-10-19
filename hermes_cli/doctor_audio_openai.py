"""Fork-owned OpenAI target resolution for ``hermes doctor --live`` audio probes.

The live TTS/STT probe asks :func:`audio_probe_target` which URL and key to
probe. For the ``openai`` provider the fork probes what the voice path will
actually use: an OpenAI-compatible server configured via
``tts.openai.base_url`` is probed at ``<base_url>/models`` with
``tts.openai.api_key``, else the shared audio key chain
(:func:`openai_audio_key`), instead of api.openai.com with
``OPENAI_API_KEY``. Other providers keep their fixed env var.
"""

from __future__ import annotations

import os
from typing import Callable, Optional, Tuple

OPENAI_KEY_HINT = "tts.openai.api_key / VOICE_TOOLS_OPENAI_KEY / OPENAI_API_KEY"


def openai_audio_key() -> str:
    """OpenAI key for the TTS probe when ``tts.openai.api_key`` is unset.

    ``tts.openai.api_key`` is checked by the caller; this resolves
    ``VOICE_TOOLS_OPENAI_KEY`` > ``OPENAI_API_KEY`` via the shared audio
    resolver (env/.env/credential pool) — the same chain the openai TTS
    provider and streamer authenticate with, so the probe tests the key the
    voice path will actually use. Lazy import: ``tools.tool_backend_helpers``
    is light; ``tools.tts_tool`` / ``tools.tts_streaming`` are not.
    """
    try:
        from tools.tool_backend_helpers import resolve_openai_audio_api_key

        return resolve_openai_audio_api_key() or ""
    except Exception:
        return (os.getenv("VOICE_TOOLS_OPENAI_KEY")
                or os.getenv("OPENAI_API_KEY") or "").strip()


def audio_probe_target(provider: str, url: str, env_var: str, openai_cfg: Optional[dict],
                       openai_key: Callable[[], str]) -> Tuple[str, str, str, str]:
    """``(url, key, key_hint, base_url)`` for one audio provider probe.

    *url* / *env_var* are the provider's fixed probe entry; *openai_cfg* is
    the ``tts.openai`` section (``None``/``{}`` for STT); *openai_key* is the
    fallback key lookup (the caller passes its patchable seam). ``base_url``
    is non-empty only when a configured OpenAI-compatible endpoint replaced
    the fixed URL, so the caller can name it in the result.
    """
    openai_cfg = openai_cfg or {}
    base_url = ""
    if provider == "openai":
        base_url = str(openai_cfg.get("base_url") or "").rstrip("/")
        if base_url:
            url = f"{base_url}/models"
        key_hint = OPENAI_KEY_HINT
        key = (str(openai_cfg.get("api_key") or "").strip()
               or openai_key())
    else:
        key_hint = env_var
        key = os.getenv(env_var, "").strip()
    return url, key, key_hint, base_url
