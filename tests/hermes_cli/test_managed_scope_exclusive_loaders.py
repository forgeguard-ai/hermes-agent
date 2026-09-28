"""Exclusive managed scope — config.yaml and .env loaders read only the managed copies.

With ``managed: {exclusive: true}`` in the managed config.yaml, the user's
``$HERMES_HOME/config.yaml`` and ``$HERMES_HOME/.env`` are never read: the
managed config.yaml (plus defaults) is the whole config, and the managed .env
(plus the process environment) is the whole env-file layer.
"""
import json
import os

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
    _reset_caches()
    yield home, managed
    _reset_caches()


def _reset_caches():
    import hermes_cli.config as cfg
    from hermes_cli import managed_scope

    cfg._LOAD_CONFIG_CACHE.clear()
    cfg._RAW_CONFIG_CACHE.clear()
    cfg.invalidate_env_cache()
    managed_scope.invalidate_managed_cache()


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _reset_caches()


# ── config.yaml ─────────────────────────────────────────────────────────────


def test_load_config_ignores_user_config_when_exclusive(homes):
    from hermes_cli.config import DEFAULT_CONFIG, load_config

    home, managed = homes
    _write(
        home / "config.yaml",
        "model:\n  default: user/model\ndisplay:\n  skin: user_skin\nagent_planted: 1\n",
    )
    _write(managed / "config.yaml", EXCLUSIVE + "model:\n  default: org/model\n")

    cfg = load_config()
    assert cfg["model"]["default"] == "org/model"
    # A user-only key is gone: the user file is not merged at all.
    assert "agent_planted" not in cfg
    assert cfg["display"]["skin"] == DEFAULT_CONFIG["display"]["skin"]
    # Defaults are still applied to the managed file.
    assert set(DEFAULT_CONFIG) <= set(cfg)


def test_load_config_merges_user_config_when_not_exclusive(homes):
    from hermes_cli.config import load_config

    home, managed = homes
    _write(home / "config.yaml", "display:\n  skin: user_skin\n")
    _write(managed / "config.yaml", "model:\n  default: org/model\n")

    cfg = load_config()
    assert cfg["model"]["default"] == "org/model"
    assert cfg["display"]["skin"] == "user_skin"


def test_exclusive_works_without_any_user_config(homes):
    from hermes_cli.config import load_config, read_raw_config

    _home, managed = homes
    _write(managed / "config.yaml", EXCLUSIVE + "display:\n  skin: org_skin\n")
    assert load_config()["display"]["skin"] == "org_skin"
    assert read_raw_config()["display"]["skin"] == "org_skin"


def test_raw_primitives_read_managed_file(homes):
    from hermes_cli.config import (
        read_raw_config,
        read_raw_config_readonly,
        read_user_config_raw,
    )

    home, managed = homes
    _write(home / "config.yaml", "display:\n  skin: user_skin\n")
    _write(managed / "config.yaml", EXCLUSIVE + "display:\n  skin: org_skin\n")

    assert read_raw_config()["display"]["skin"] == "org_skin"
    assert read_raw_config_readonly()["display"]["skin"] == "org_skin"
    assert read_user_config_raw()["display"]["skin"] == "org_skin"
    # An explicit user path (gateway home, another profile) is redirected too.
    other = home / "profiles" / "work" / "config.yaml"
    _write(other, "display:\n  skin: work_skin\n")
    assert read_user_config_raw(other)["display"]["skin"] == "org_skin"


def test_cli_loader_ignores_user_config_when_exclusive(homes):
    import cli

    home, managed = homes
    _write(home / "config.yaml", "display:\n  skin: user_skin\nagent_planted: 1\n")
    _write(managed / "config.yaml", EXCLUSIVE + "display:\n  skin: org_skin\n")

    cli._hermes_home = home
    cfg = cli.load_cli_config()
    assert (cfg.get("display") or {}).get("skin") == "org_skin"
    assert "agent_planted" not in cfg


def test_gateway_loader_ignores_user_config_and_gateway_json(homes, monkeypatch):
    from gateway.config import load_gateway_config

    home, managed = homes
    # A user-planted legacy gateway.json and config.yaml must both be ignored.
    _write(home / "gateway.json", json.dumps({"session_reset": {"mode": "none"}}))
    _write(home / "config.yaml", "session_reset:\n  mode: none\n")
    _write(managed / "config.yaml", EXCLUSIVE + "session_reset:\n  mode: idle\n  idle_minutes: 7\n")

    cfg = load_gateway_config()
    policy = cfg.default_reset_policy
    assert policy.mode == "idle"
    assert policy.idle_minutes == 7


def test_gateway_runtime_config_reads_managed(homes, monkeypatch):
    import gateway.run as gw_run

    home, managed = homes
    _write(home / "config.yaml", "display:\n  skin: user_skin\n")
    _write(managed / "config.yaml", EXCLUSIVE + "display:\n  skin: org_skin\n")
    monkeypatch.setattr(gw_run, "_hermes_home", home)
    cfg = gw_run._load_gateway_config()
    assert (cfg.get("display") or {}).get("skin") == "org_skin"


# ── .env ────────────────────────────────────────────────────────────────────


def test_dotenv_ignores_user_and_project_env_when_exclusive(homes, monkeypatch, tmp_path):
    from hermes_cli.env_loader import load_hermes_dotenv

    home, managed = homes
    for key in ("XMS_USER_ONLY", "XMS_PROJECT_ONLY", "XMS_MANAGED", "XMS_PROCESS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("XMS_PROCESS", "from_process")
    project_env = tmp_path / "project.env"
    project_env.write_text("XMS_PROJECT_ONLY=project\n", encoding="utf-8")
    _write(home / ".env", "XMS_USER_ONLY=user\nXMS_PROCESS=user_override\n")
    _write(managed / ".env", "XMS_MANAGED=managed\n")
    _write(managed / "config.yaml", EXCLUSIVE)

    try:
        loaded = load_hermes_dotenv(hermes_home=str(home), project_env=str(project_env))
        assert "XMS_USER_ONLY" not in os.environ
        assert "XMS_PROJECT_ONLY" not in os.environ
        assert os.environ["XMS_MANAGED"] == "managed"
        # The process environment is still a source and is not clobbered by
        # the (ignored) user .env.
        assert os.environ["XMS_PROCESS"] == "from_process"
        assert home / ".env" not in loaded
        assert managed / ".env" in loaded
    finally:
        for key in ("XMS_USER_ONLY", "XMS_PROJECT_ONLY", "XMS_MANAGED"):
            os.environ.pop(key, None)


def test_dotenv_still_reads_user_env_when_not_exclusive(homes, monkeypatch):
    from hermes_cli.env_loader import load_hermes_dotenv

    home, _managed = homes
    monkeypatch.delenv("XMS_USER_ONLY", raising=False)
    _write(home / ".env", "XMS_USER_ONLY=user\n")
    try:
        load_hermes_dotenv(hermes_home=str(home))
        assert os.environ["XMS_USER_ONLY"] == "user"
    finally:
        os.environ.pop("XMS_USER_ONLY", None)


def test_load_env_and_get_env_value_read_managed_env(homes, monkeypatch):
    from hermes_cli.config import get_env_value, load_env

    home, managed = homes
    monkeypatch.delenv("XMS_KEY", raising=False)
    _write(home / ".env", "XMS_KEY=user\n")
    _write(managed / ".env", "XMS_KEY=managed\n")
    _write(managed / "config.yaml", EXCLUSIVE)
    assert load_env() == {"XMS_KEY": "managed"}
    assert get_env_value("XMS_KEY") == "managed"


def test_reload_env_keeps_process_env_keys_when_exclusive(homes, monkeypatch):
    from hermes_cli.config import OPTIONAL_ENV_VARS, reload_env

    home, managed = homes
    known = next(iter(OPTIONAL_ENV_VARS))
    monkeypatch.setenv(known, "from-deployment")
    _write(managed / ".env", "")
    _write(managed / "config.yaml", EXCLUSIVE)
    reload_env()
    assert os.environ.get(known) == "from-deployment"


def test_profile_secret_scope_reads_managed_env(homes):
    from agent.secret_scope import build_profile_secret_scope

    home, managed = homes
    _write(home / ".env", "OPENAI_API_KEY=user-key\n")
    _write(managed / ".env", "OPENAI_API_KEY=managed-key\n")
    _write(managed / "config.yaml", EXCLUSIVE)
    scope = build_profile_secret_scope(home)
    assert scope.get("OPENAI_API_KEY") == "managed-key"
