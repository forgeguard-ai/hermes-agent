"""Fork identity: which upstream release this ForgeGuard fork tracks.

The startup banner (``hermes_cli.banner.format_banner_version_label``, which
``--version`` also prints) names the fork and its upstream base, so a fork
build never reads as a plain upstream release. Kept out of ``banner.py`` so
an upstream rewrite of the label only needs the one-line call re-applied.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

FORK_NAME = "ForgeGuard fork"


def fork_upstream_base() -> Optional[str]:
    """Upstream release tag this ForgeGuard fork tracks, read from the repo-root
    ``FORK_UPSTREAM_BASE`` marker (baked into fork images via ``COPY . .``).

    Read from the package root rather than ``_resolve_repo_dir()`` so it still
    works on sealed images that ship no ``.git``. Returns ``None`` on a plain
    upstream checkout with no marker, so the banner degrades to upstream labels.
    """
    try:
        marker = Path(__file__).resolve().parent.parent / "FORK_UPSTREAM_BASE"
        return marker.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def with_fork_identity(label: str, fork_base: Optional[str]) -> str:
    """Append the fork element to a version label when *fork_base* is known."""
    if fork_base:
        return f"{label} · {FORK_NAME} (tracks {fork_base})"
    return label
