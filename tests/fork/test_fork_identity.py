"""Fork-owned tests: ``hermes_cli/fork_identity.py`` and its banner hook."""

from pathlib import Path
from unittest.mock import patch

from hermes_cli import fork_identity


def test_with_fork_identity_appends_the_fork_element():
    assert (
        fork_identity.with_fork_identity("Hermes Agent v1 (d)", "v2026.8.31")
        == "Hermes Agent v1 (d) · ForgeGuard fork (tracks v2026.8.31)"
    )


def test_with_fork_identity_without_base_is_unchanged():
    assert fork_identity.with_fork_identity("label", None) == "label"
    assert fork_identity.with_fork_identity("label", "") == "label"


def test_fork_upstream_base_reads_the_repo_root_marker():
    marker = Path(fork_identity.__file__).resolve().parent.parent / "FORK_UPSTREAM_BASE"
    expected = (marker.read_text(encoding="utf-8").strip() or None) if marker.exists() else None
    assert fork_identity.fork_upstream_base() == expected


def test_fork_upstream_base_missing_marker_is_none():
    with patch.object(Path, "read_text", side_effect=OSError("missing")):
        assert fork_identity.fork_upstream_base() is None


def test_banner_label_goes_through_the_banner_level_name():
    """``banner._fork_upstream_base`` stays patchable: the label looks it up
    in the banner module at call time."""
    from hermes_cli import banner

    with patch.object(banner, "get_git_banner_state", return_value=None), \
         patch.object(banner, "_fork_upstream_base", return_value="v9.9.9"):
        label = banner.format_banner_version_label()
    assert label.endswith(" · ForgeGuard fork (tracks v9.9.9)")
