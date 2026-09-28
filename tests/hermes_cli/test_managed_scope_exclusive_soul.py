"""Exclusive managed scope — SOUL.md and memory-provider configs resolve from the managed dir.

In exclusive mode the agent's identity (SOUL.md) and the memory-provider
configs (mem0.json, hindsight/config.json) are read from the managed directory.
A copy in HERMES_HOME is ignored; a missing managed copy behaves exactly like a
home without one.
"""
import json
from pathlib import Path

import pytest

EXCLUSIVE = "managed:\n  exclusive: true\n"


@pytest.fixture
def homes(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    managed = tmp_path / "managed"
    managed.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_MANAGED_DIR", str(managed))
    _reset()
    yield home, managed
    _reset()


def _reset():
    import hermes_cli.config as cfg
    from hermes_cli import managed_scope

    cfg._LOAD_CONFIG_CACHE.clear()
    cfg._RAW_CONFIG_CACHE.clear()
    managed_scope.invalidate_managed_cache()


def _exclusive(managed: Path) -> None:
    (managed / "config.yaml").write_text(EXCLUSIVE, encoding="utf-8")
    _reset()


# ── SOUL.md ─────────────────────────────────────────────────────────────────


def test_soul_from_managed_dir_when_exclusive(homes):
    from agent.prompt_builder import load_soul_md

    home, managed = homes
    (home / "SOUL.md").write_text("I am whatever the agent wrote.", encoding="utf-8")
    (managed / "SOUL.md").write_text("I am the administrator's persona.", encoding="utf-8")
    _exclusive(managed)
    assert load_soul_md(home_override=home) == "I am the administrator's persona."
    assert load_soul_md() == "I am the administrator's persona."


def test_missing_managed_soul_means_no_soul(homes):
    """No managed SOUL.md: fall back as if the home had none — never to the home copy."""
    from agent.prompt_builder import load_soul_md

    home, managed = homes
    (home / "SOUL.md").write_text("Planted persona.", encoding="utf-8")
    _exclusive(managed)
    assert load_soul_md(home_override=home) is None


def test_soul_from_home_when_not_exclusive(homes):
    from agent.prompt_builder import load_soul_md

    home, managed = homes
    (home / "SOUL.md").write_text("Home persona.", encoding="utf-8")
    (managed / "SOUL.md").write_text("Managed persona.", encoding="utf-8")
    (managed / "config.yaml").write_text("model:\n  default: org/model\n", encoding="utf-8")
    _reset()
    assert load_soul_md(home_override=home) == "Home persona."


def test_resolve_soul_path(homes):
    from agent.prompt_builder import resolve_soul_path

    home, managed = homes
    assert resolve_soul_path(home) == home / "SOUL.md"
    _exclusive(managed)
    assert resolve_soul_path(home) == managed / "SOUL.md"


def test_home_soul_not_seeded_when_exclusive(homes):
    import hermes_cli.config as cfg

    home, managed = homes
    _exclusive(managed)
    cfg._HERMES_HOME_ENSURED.discard(str(home))
    cfg.ensure_hermes_home()
    assert not (home / "SOUL.md").exists()
    # The rest of the home skeleton is still created (skills/memories stay).
    assert (home / "skills").is_dir()
    assert (home / "memories").is_dir()


# ── memory-provider configs ─────────────────────────────────────────────────


def test_mem0_config_from_managed_dir(homes, monkeypatch):
    from plugins.memory.mem0 import _load_config

    home, managed = homes
    monkeypatch.delenv("MEM0_HOST", raising=False)
    (home / "mem0.json").write_text(json.dumps({"host": "http://planted:1"}), encoding="utf-8")
    (managed / "mem0.json").write_text(json.dumps({"host": "http://org-mem0:8000"}), encoding="utf-8")
    assert _load_config()["host"] == "http://planted:1"
    _exclusive(managed)
    assert _load_config()["host"] == "http://org-mem0:8000"


def test_mem0_home_config_ignored_without_managed_copy(homes, monkeypatch):
    from plugins.memory.mem0 import _load_config

    home, managed = homes
    monkeypatch.delenv("MEM0_HOST", raising=False)
    (home / "mem0.json").write_text(json.dumps({"host": "http://planted:1"}), encoding="utf-8")
    _exclusive(managed)
    assert _load_config()["host"] == ""


def test_hindsight_config_from_managed_dir(homes, monkeypatch, tmp_path):
    from plugins.memory.hindsight import _load_config

    home, managed = homes
    user_home = tmp_path / "userhome"
    (user_home / ".hindsight").mkdir(parents=True)
    (user_home / ".hindsight" / "config.json").write_text(
        json.dumps({"mode": "legacy-planted"}), encoding="utf-8"
    )
    monkeypatch.setattr(Path, "home", lambda: user_home)
    (home / "hindsight").mkdir()
    (home / "hindsight" / "config.json").write_text(json.dumps({"mode": "planted"}), encoding="utf-8")
    (managed / "hindsight").mkdir()
    (managed / "hindsight" / "config.json").write_text(json.dumps({"mode": "cloud-org"}), encoding="utf-8")

    assert _load_config()["mode"] == "planted"
    _exclusive(managed)
    assert _load_config()["mode"] == "cloud-org"
    # Without a managed copy neither the home nor the legacy ~/.hindsight copy is used.
    (managed / "hindsight" / "config.json").unlink()
    monkeypatch.setenv("HINDSIGHT_MODE", "from-env")
    assert _load_config()["mode"] == "from-env"
