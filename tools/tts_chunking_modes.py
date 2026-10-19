"""Fork-owned TTS chunking modes for :class:`tools.tts_streaming.SentenceChunker`.

Config ``tts.streaming.chunking`` picks how streamed speech is cut:

* ``"punctuation"`` (default) — cut per sentence (upstream's
  ``SENTENCE_BOUNDARY_RE``, the chunker's own default).
* ``"paragraphs"`` — cut on every line-break run (``\\n+`` — each markdown
  bullet/line is its own chunk).
* ``"none"`` — ``feed()`` only buffers; the whole reply is one utterance,
  drained by ``flush()``.

Both cutting modes keep the chunker's *min_len* merge, so "Ha!" rides along
with the chunk after it, and ``<think>`` blocks are stripped in every mode
(the chunker does that before it looks for a boundary).

How it hooks in: ``SentenceChunker.feed`` reads an optional per-instance
``boundary`` attribute (any object with a ``re.Pattern``-style
``search(text, pos)``) and falls back to ``SENTENCE_BOUNDARY_RE`` when it is
absent or ``None``. This
module sets that attribute; it is the only fork line inside the chunker.
Call sites build their chunker with :func:`chunker_for_config` (or
:func:`apply_chunking_mode` when they already hold a resolved mode).

At an upstream sync: if the chunker gained a ``from_config`` constructor,
:func:`chunker_for_config` already prefers it, so the call sites can keep
the fork's one-line call.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# Paragraph boundary: every line-break run is a cut.
PARAGRAPH_BOUNDARY_RE = re.compile(r"\n+")

# Canonical values are ``punctuation`` | ``paragraphs`` | ``none``; a few
# obvious synonyms normalize instead of silently falling back to the default.
_CHUNKING_ALIASES = {
    "sentence": "punctuation", "punctuation": "punctuation",
    "paragraph": "paragraphs", "paragraphs": "paragraphs",
    "none": "none", "whole": "none", "off": "none",
}

DEFAULT_CHUNKING_MODE = "punctuation"


class _NoBoundary:
    """Boundary that never matches: ``feed()`` buffers, ``flush()`` drains."""

    @staticmethod
    def search(_text: str, _pos: int = 0) -> None:
        return None


NO_BOUNDARY = _NoBoundary()


def resolve_chunking_mode(tts_config: Dict) -> str:
    """tts.streaming.chunking → 'punctuation' | 'paragraphs' | 'none' (default punctuation)."""
    streaming = tts_config.get("streaming") or {}
    if not isinstance(streaming, dict):  # tolerate a malformed section
        streaming = {}
    raw = str(streaming.get("chunking") or "").lower().strip()
    return _CHUNKING_ALIASES.get(raw, DEFAULT_CHUNKING_MODE)


def boundary_for_mode(mode: str) -> Optional[Any]:
    """The boundary matcher for *mode*; ``None`` means the chunker's default."""
    if mode == "paragraphs":
        return PARAGRAPH_BOUNDARY_RE
    if mode == "none":
        return NO_BOUNDARY
    return None


def apply_chunking_mode(chunker: Any, mode: str) -> Any:
    """Set *mode* on an existing chunker and return it.

    ``chunker.mode`` records the mode for callers that branch on it (the
    speak-stream idle flush skips ``none``); ``chunker.boundary`` is what
    ``feed()`` cuts on (``None`` in punctuation mode, so the chunker's own
    sentence regex applies).
    """
    chunker.mode = mode
    chunker.boundary = boundary_for_mode(mode)
    return chunker


def chunker_for_config(tts_config: Dict) -> Any:
    """A ``SentenceChunker`` honouring ``tts.streaming.chunking``.

    Uses ``SentenceChunker.from_config(tts_config)`` when the chunker has one
    (upstream's config-aware constructor), else the default constructor.
    """
    from tools.tts_streaming import SentenceChunker

    from_config = getattr(SentenceChunker, "from_config", None)
    chunker = from_config(tts_config) if callable(from_config) else SentenceChunker()
    return apply_chunking_mode(chunker, resolve_chunking_mode(tts_config))


def chunker_for_mode(mode: str) -> Any:
    """A default ``SentenceChunker`` cutting in an already-resolved *mode*."""
    from tools.tts_streaming import SentenceChunker

    return apply_chunking_mode(SentenceChunker(), mode)
