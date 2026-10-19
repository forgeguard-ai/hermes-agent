"""Fork-owned tests: the startup banner names the ForgeGuard fork.

Covers the fork patch in ``hermes_cli/banner.py``: ``_fork_upstream_base()``
reads the repo-root ``FORK_UPSTREAM_BASE`` marker, and
``format_banner_version_label()`` inserts "ForgeGuard fork (tracks <tag>)"
between the version base and the git upstream/local suffix (see
``docs/maintainers/upstream-sync/patch-inventory.md``).

These cases were copied from ``tests/hermes_cli/test_banner_git_state.py``,
which upstream deleted when it rebuilt the banner label around a build-time
install stamp. The duplication is intentional until the next upstream sync:
the sync accepts upstream's deletion of that file, and from then on this file
is the only home for these cases.

At that sync the fork-identity element has to be re-applied to upstream's
rebuilt ``format_banner_version_label()``, and these cases re-ported with it:
the rebuilt label no longer uses ``banner.VERSION``, and it can return early
(desktop install stamp, non-main update channel) before the git suffix.
"""

from unittest.mock import patch


def test_format_banner_version_label_without_git_state():
    from hermes_cli import banner

    # Isolate the no-git-state base label from the fork-identity element (which
    # is driven by the repo-root FORK_UPSTREAM_BASE marker, present in this repo).
    with patch.object(banner, "get_git_banner_state", return_value=None), \
         patch.object(banner, "_fork_upstream_base", return_value=None):
        value = banner.format_banner_version_label()

    assert value == f"Hermes Agent v{banner.VERSION} ({banner.RELEASE_DATE})"


def test_format_banner_version_label_includes_fork_identity():
    from hermes_cli import banner

    with patch.object(banner, "get_git_banner_state", return_value=None), \
         patch.object(banner, "_fork_upstream_base", return_value="v2026.7.1"):
        value = banner.format_banner_version_label()

    assert value == (
        f"Hermes Agent v{banner.VERSION} ({banner.RELEASE_DATE})"
        " · ForgeGuard fork (tracks v2026.7.1)"
    )


def test_format_banner_version_label_fork_identity_before_git_suffix():
    """The fork element sits between the base and the git upstream/local suffix."""
    from hermes_cli import banner

    with patch.object(
        banner,
        "get_git_banner_state",
        return_value={"upstream": "b2f477a3", "local": "b2f477a3", "ahead": 0},
    ), patch.object(banner, "_fork_upstream_base", return_value="v2026.7.1"):
        value = banner.format_banner_version_label()

    assert "· ForgeGuard fork (tracks v2026.7.1) · upstream b2f477a3" in value
