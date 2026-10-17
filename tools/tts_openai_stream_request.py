"""Fork-owned request shaping for the OpenAI streaming-TTS provider.

``tools.tts_streaming.OpenAIStreamer.stream`` asks :func:`openai_stream_request`
for the endpoint and the ``audio.speech`` create kwargs, so the fork's
hardening lives here rather than inside the upstream provider class:

* Endpoint: ``tts.openai.base_url``, else the public API. ``OPENAI_BASE_URL``
  is the *LLM* custom-endpoint override (``hermes_cli/providers.py``, the
  model setup flows) and the sync path (``_generate_openai_tts``) never reads
  it, so neither does the streamer — a voice request must not land on the
  chat server. Passing the explicit default also keeps the SDK from reading
  that env var itself (its constructor falls back to it when ``base_url`` is
  ``None``).
* Same knobs as the whole-file path (``tools.tts_tool._generate_openai_tts``):
  ``tts.openai.speed`` > ``tts.speed``, clamped to the API's [0.25, 4.0] and
  only sent when non-default; ``tts.openai.language`` rides as ``lang_code``
  for OpenAI-compatible servers (Kokoro) that support it.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


def openai_stream_request(section: Dict[str, Any], tts_config: Dict[str, Any],
                          text: str) -> Tuple[str, Dict[str, Any]]:
    """Return ``(base_url, create_kwargs)`` for one streamed OpenAI speech request."""
    from tools.tts_tool import DEFAULT_OPENAI_BASE_URL

    base_url = section.get("base_url") or DEFAULT_OPENAI_BASE_URL
    create_kwargs: Dict[str, Any] = {
        "model": section.get("model", "gpt-4o-mini-tts"),
        "voice": section.get("voice", "alloy"),
        "input": text,
        "response_format": "pcm",
    }
    try:
        speed = float(section.get("speed", tts_config.get("speed", 1.0)))
    except (TypeError, ValueError):
        speed = 1.0
    if speed != 1.0:
        create_kwargs["speed"] = max(0.25, min(4.0, speed))
    language = section.get("language")
    if language:
        create_kwargs["extra_body"] = {"lang_code": language}
    return base_url, create_kwargs
