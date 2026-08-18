"""A stored session's model is a PIN only when the user chose it.

Live failure (2026-08-18): the vLLM shared service behind a deployment was
switched from ``qwen3.8-27b`` to ``nemotron-3.5-lightning`` and config.yaml
followed — but every older desktop chat kept asking for ``qwen3.8-27b`` and
404'd on each turn. ``_ensure_session_db_row`` stamps the then-current global
model into every row (``or _resolve_model()``), ``_stored_session_runtime_
overrides`` restored any non-empty row model as a ``model_override``, and
``_sync_agent_model_with_config`` short-circuits on ``model_override`` — so
every resumed chat looked like a deliberate ``/model`` pin and the config
adoption sync never ran.

Now the row records ``model_config.model_source`` (``user`` | ``default``) and
only ``user`` rows are restored as an override. Legacy rows (no source) keep
their pin unless they name a different model on the SAME endpoint config
points at — the rename case.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tui_gateway import server


def _cfg(default: str, provider: str = "custom", base_url: str = "https://vllm.lab.internal/v1") -> dict:
    return {"model": {"default": default, "provider": provider, "base_url": base_url}}


def _row(model: str, *, source: str | None = None, provider: str | None = None, base_url: str | None = None) -> dict:
    mc: dict = {"model": model}
    if source is not None:
        mc["model_source"] = source
    if provider:
        mc["provider"] = provider
    if base_url:
        mc["base_url"] = base_url
    return {"model": model, "model_config": json.dumps(mc)}


class TestStoredOverridesHonourTheSource:
    def test_user_pin_is_restored(self):
        with patch.object(server, "_load_cfg", return_value=_cfg("nemotron-3.5-lightning")):
            ov = server._stored_session_runtime_overrides(
                _row("qwen3.8-27b", source="user", provider="custom:vllm.lab.internal", base_url="https://vllm.lab.internal/v1")
            )
        assert ov["model_override"]["model"] == "qwen3.8-27b"
        assert ov["provider_override"] == "custom:vllm.lab.internal"

    def test_default_sourced_row_follows_config(self):
        with patch.object(server, "_load_cfg", return_value=_cfg("nemotron-3.5-lightning")):
            ov = server._stored_session_runtime_overrides(
                _row("qwen3.8-27b", source="default", provider="custom:vllm.lab.internal", base_url="https://vllm.lab.internal/v1")
            )
        assert "model_override" not in ov
        assert "provider_override" not in ov

    def test_default_sourced_row_keeps_reasoning_and_tier(self):
        row = _row("qwen3.8-27b", source="default")
        mc = json.loads(row["model_config"])
        mc["reasoning_config"] = {"enabled": True, "effort": "low"}
        mc["service_tier"] = "normal"
        row["model_config"] = json.dumps(mc)
        with patch.object(server, "_load_cfg", return_value=_cfg("nemotron-3.5-lightning")):
            ov = server._stored_session_runtime_overrides(row)
        assert "model_override" not in ov
        assert ov["reasoning_config_override"] == {"enabled": True, "effort": "low"}
        assert ov["service_tier_override"] == ""


class TestLegacyRowsWithoutASource:
    """Rows written before model_source existed."""

    def test_same_endpoint_different_model_heals(self):
        # The rename: config moved to nemotron on the same vLLM URL.
        with patch.object(server, "_load_cfg", return_value=_cfg("nemotron-3.5-lightning")):
            ov = server._stored_session_runtime_overrides(
                _row("qwen3.8-27b", provider="custom:vllm.lab.internal", base_url="https://vllm.lab.internal/v1")
            )
        assert "model_override" not in ov

    def test_same_model_keeps_its_harmless_pin(self):
        with patch.object(server, "_load_cfg", return_value=_cfg("qwen3.8-27b")):
            ov = server._stored_session_runtime_overrides(
                _row("qwen3.8-27b", provider="custom:vllm.lab.internal", base_url="https://vllm.lab.internal/v1")
            )
        assert ov["model_override"]["model"] == "qwen3.8-27b"

    def test_different_endpoint_is_a_real_pin(self):
        with patch.object(server, "_load_cfg", return_value=_cfg("nemotron-3.5-lightning")):
            ov = server._stored_session_runtime_overrides(
                _row("claude-sonnet-4-5", provider="anthropic", base_url="https://api.anthropic.com")
            )
        assert ov["model_override"]["model"] == "claude-sonnet-4-5"
        assert ov["provider_override"] == "anthropic"

    def test_provider_class_decides_when_no_urls(self):
        # No stored/config base_url: custom vs custom:<name> is one class → heal;
        # anthropic vs custom → pin.
        with patch.object(server, "_load_cfg", return_value={"model": {"default": "nemotron", "provider": "custom"}}):
            same = server._stored_session_runtime_overrides(_row("qwen", provider="custom:vllm.lab.internal"))
            other = server._stored_session_runtime_overrides(_row("claude", provider="anthropic"))
        assert "model_override" not in same
        assert other["model_override"]["model"] == "claude"

    def test_no_config_default_keeps_the_pin(self):
        with patch.object(server, "_load_cfg", return_value={"model": {"provider": "custom"}}):
            ov = server._stored_session_runtime_overrides(_row("qwen", provider="custom:x"))
        assert ov["model_override"]["model"] == "qwen"


class TestAdoptionNotice:
    def test_notice_when_stored_model_was_not_restored_and_differs(self):
        row = _row("qwen3.8-27b", source="default")
        with patch.object(server, "_load_cfg", return_value=_cfg("nemotron-3.5-lightning")):
            ov = server._stored_session_runtime_overrides(row)
            note = server._stored_model_adoption_notice(row, ov)
        assert note and "qwen3.8-27b" in note and "nemotron-3.5-lightning" in note

    def test_no_notice_for_a_pin_or_an_unchanged_model(self):
        with patch.object(server, "_load_cfg", return_value=_cfg("nemotron-3.5-lightning")):
            pinned = _row("qwen3.8-27b", source="user")
            assert server._stored_model_adoption_notice(pinned, server._stored_session_runtime_overrides(pinned)) is None
            same = _row("nemotron-3.5-lightning", source="default")
            assert server._stored_model_adoption_notice(same, server._stored_session_runtime_overrides(same)) is None

    def test_sync_emits_the_parked_notice_once(self):
        emitted: list = []
        session = {"agent": MagicMock(model="nemotron", provider="custom"), "pending_model_notice": "moved on"}
        with (
            patch.object(server, "_emit", lambda kind, sid, payload: emitted.append((kind, payload))),
            patch.object(server, "_config_model_target", return_value=("nemotron", "custom")),
        ):
            server._sync_agent_model_with_config("sid", session)
            server._sync_agent_model_with_config("sid", session)
        assert emitted == [("status.update", {"kind": "process", "text": "moved on"})]
        assert "pending_model_notice" not in session


class TestFirstRowRecordsTheSource:
    @pytest.mark.parametrize(
        "override,expected",
        [({}, "default"), ({"model": "picked-model"}, "user")],
    )
    def test_ensure_session_db_row_stamps_model_source(self, override, expected, monkeypatch):
        db = MagicMock()
        session = {"model_override": override, "session_key": "k1"}
        monkeypatch.setattr(server, "_resolve_model", lambda: "cfg-default")
        monkeypatch.setattr(server, "_get_db", lambda: db)
        try:
            server._ensure_session_db_row(session)
        except Exception:
            # The helper does more than the row (title, hidden…); the create
            # call is what this pins.
            pass
        assert db.create_session.called, "create_session was not reached"
        kwargs = db.create_session.call_args.kwargs
        assert kwargs["model_config"]["model_source"] == expected
        assert kwargs["model"] == (override.get("model") or "cfg-default")


class TestPersistMarksUserPins:
    def test_model_source_written_only_when_asked(self):
        agent = MagicMock(model="m", provider="anthropic", base_url="", api_mode="", reasoning_config=None, service_tier=None)
        db = MagicMock()
        db.get_session.return_value = {"model_config": json.dumps({"model_source": "default"})}
        agent._session_db = db
        session = {"agent": agent, "session_key": "k"}
        server._persist_live_session_runtime(session)
        cfg = json.loads(db.update_session_meta.call_args.args[1])
        assert cfg["model_source"] == "default"
        server._persist_live_session_runtime(session, model_source="user")
        cfg = json.loads(db.update_session_meta.call_args.args[1])
        assert cfg["model_source"] == "user"
