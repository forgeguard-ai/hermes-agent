"""Exclusive managed scope — the resolver primitives in hermes_cli.managed_scope.

Exclusive mode is enabled by ``managed: {exclusive: true}`` in the managed
config.yaml. These tests cover the flag itself and the path helpers every
loader and writer routes through.
"""
from pathlib import Path

import pytest


@pytest.fixture
def scope(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    managed = tmp_path / "managed"
    managed.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_MANAGED_DIR", str(managed))
    from hermes_cli import managed_scope

    managed_scope.invalidate_managed_cache()
    yield home, managed
    managed_scope.invalidate_managed_cache()


def _write_managed_config(managed: Path, text: str) -> None:
    from hermes_cli import managed_scope

    (managed / "config.yaml").write_text(text, encoding="utf-8")
    managed_scope.invalidate_managed_cache()


def _exclusive(managed: Path, extra: str = "") -> None:
    _write_managed_config(managed, "managed:\n  exclusive: true\n" + extra)


# ── the flag ────────────────────────────────────────────────────────────────


def test_not_exclusive_without_managed_dir(tmp_path, monkeypatch):
    from hermes_cli import managed_scope

    monkeypatch.delenv("HERMES_MANAGED_DIR", raising=False)
    managed_scope.invalidate_managed_cache()
    assert managed_scope.is_exclusive() is False
    assert managed_scope.exclusive_dir() is None


def test_not_exclusive_without_flag(scope):
    from hermes_cli import managed_scope

    _home, managed = scope
    _write_managed_config(managed, "model:\n  default: org/model\n")
    assert managed_scope.is_exclusive() is False


@pytest.mark.parametrize("value", ["false", "'true'", "1", "{}"])
def test_only_boolean_true_enables(scope, value):
    from hermes_cli import managed_scope

    _home, managed = scope
    _write_managed_config(managed, f"managed:\n  exclusive: {value}\n")
    assert managed_scope.is_exclusive() is False


def test_exclusive_true(scope):
    from hermes_cli import managed_scope

    _home, managed = scope
    _exclusive(managed)
    assert managed_scope.is_exclusive() is True
    assert managed_scope.exclusive_dir() == managed


def test_malformed_managed_config_is_not_exclusive(scope):
    from hermes_cli import managed_scope

    _home, managed = scope
    _write_managed_config(managed, "managed: [exclusive: true\n")
    assert managed_scope.is_exclusive() is False


def test_flag_follows_file_edits(scope):
    from hermes_cli import managed_scope

    _home, managed = scope
    _exclusive(managed)
    assert managed_scope.is_exclusive() is True
    # Different size -> new cache signature, no explicit invalidation needed.
    (managed / "config.yaml").write_text("managed:\n  exclusive: false\n", encoding="utf-8")
    assert managed_scope.is_exclusive() is False


# ── path resolution ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "rel",
    ["config.yaml", ".env", "SOUL.md", "mem0.json", "hindsight/config.json", "gateway.json"],
)
def test_resolve_home_path_uses_managed_dir_when_exclusive(scope, rel):
    from hermes_cli import managed_scope

    home, managed = scope
    assert managed_scope.resolve_home_path(home, rel) == home / rel
    _exclusive(managed)
    assert managed_scope.resolve_home_path(home, rel) == managed / rel


@pytest.mark.parametrize("rel", ["skills", "memories/MEMORY.md", "memories/USER.md", "auth.json"])
def test_agent_state_stays_in_home_when_exclusive(scope, rel):
    from hermes_cli import managed_scope

    home, managed = scope
    _exclusive(managed)
    assert managed_scope.resolve_home_path(home, rel) == home / rel
    assert managed_scope.protected_entry(home / rel) is None


def test_hooks_and_plugins_dirs_resolve_to_managed(scope):
    from hermes_cli import managed_scope

    home, managed = scope
    _exclusive(managed)
    assert managed_scope.resolve_home_path(home, "hooks") == managed / "hooks"
    assert managed_scope.resolve_home_path(home, "plugins") == managed / "plugins"
    assert (
        managed_scope.resolve_home_path(home, "plugins/model-providers")
        == managed / "plugins" / "model-providers"
    )


def test_config_and_env_read_paths(scope):
    from hermes_cli import managed_scope

    home, managed = scope
    other_profile = home / "profiles" / "work" / "config.yaml"
    assert managed_scope.config_read_path(home / "config.yaml") == home / "config.yaml"
    assert managed_scope.env_read_path(home / ".env") == home / ".env"
    _exclusive(managed)
    assert managed_scope.config_read_path(home / "config.yaml") == managed / "config.yaml"
    assert managed_scope.config_read_path(other_profile) == managed / "config.yaml"
    assert managed_scope.env_read_path(home / ".env") == managed / ".env"
    assert managed_scope.env_read_path(home / ".op.env") == managed / ".op.env"
    # Unrelated files are never redirected.
    assert managed_scope.config_read_path(home / "skins.yaml") == home / "skins.yaml"


# ── write protection ────────────────────────────────────────────────────────


def test_protected_entries_only_in_exclusive_mode(scope):
    from hermes_cli import managed_scope

    home, managed = scope
    assert managed_scope.protected_entry(home / "config.yaml") is None
    managed_scope.check_write_allowed(home / "config.yaml")  # no raise
    _exclusive(managed)
    assert managed_scope.protected_entry(home / "config.yaml") == "config.yaml"
    assert managed_scope.protected_entry(home / "SOUL.md") == "SOUL.md"
    assert managed_scope.protected_entry(home / "hooks" / "x" / "handler.py") == "hooks"
    assert managed_scope.protected_entry(home / "plugins" / "p" / "__init__.py") == "plugins"
    assert managed_scope.protected_entry(home / "profiles" / "w" / "config.yaml") == "config.yaml"
    assert managed_scope.protected_entry(managed / "SOUL.md") == "managed"


def test_check_write_allowed_raises_managed_message(scope):
    from hermes_cli import managed_scope

    home, managed = scope
    _exclusive(managed)
    with pytest.raises(managed_scope.ManagedScopeReadOnlyError) as exc:
        managed_scope.check_write_allowed(home / "config.yaml")
    msg = str(exc.value)
    assert "managed by your administrator" in msg
    assert str(managed) in msg
    assert isinstance(exc.value, PermissionError)


def test_translate_write_error(scope):
    import errno

    from hermes_cli import managed_scope

    home, managed = scope
    erofs = OSError(errno.EROFS, "Read-only file system")
    # Not exclusive: unchanged.
    assert managed_scope.translate_write_error(erofs, managed / "SOUL.md") is erofs
    _exclusive(managed)
    translated = managed_scope.translate_write_error(erofs, managed / "SOUL.md")
    assert isinstance(translated, managed_scope.ManagedScopeReadOnlyError)
    assert "managed by your administrator" in str(translated)
    # A path outside the managed dir keeps its original error.
    assert managed_scope.translate_write_error(erofs, home / "x") is erofs
    # Unrelated errnos keep theirs.
    enospc = OSError(errno.ENOSPC, "No space left on device")
    assert managed_scope.translate_write_error(enospc, managed / "SOUL.md") is enospc
