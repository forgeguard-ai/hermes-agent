"""The compressor's output reservation must equal what the transport sends.

Live failure (2026-08-17): a vLLM box (provider ``custom``, 200k window, no
``model.max_tokens``) never compacted proactively. The transport reserved the
custom profile's ``default_max_tokens`` (65536) on every request, capping input
at 134464, while the compressor was handed ``agent.max_tokens`` = None and armed
its trigger at 0.8 × 200000 = 160000 — unreachable. The session ran into the
provider's HTTP 400 instead, and the emergency compaction that followed shed
210 messages down to 13.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import pytest

from agent.context_compressor import ContextCompressor
from agent.output_reservation import (
    reservation_kwargs,
    resolve_agent_output_reservation,
    resolve_output_reservation,
)


class TestResolveOutputReservation:
    def test_user_max_tokens_wins(self):
        assert resolve_output_reservation("custom", "ornith-1.0-35b", 32768) == 32768

    def test_custom_profile_default_when_user_unset(self):
        # CustomProfile.default_max_tokens — the value the transport falls back to.
        assert resolve_output_reservation("custom", "ornith-1.0-35b", None) == 65536

    def test_custom_aliases_resolve_to_the_same_default(self):
        assert resolve_output_reservation("vllm", "m", None) == 65536
        assert resolve_output_reservation("ollama", "m", None) == 65536

    def test_unknown_provider_yields_none(self):
        assert resolve_output_reservation("definitely-not-a-provider", "m", None) is None
        assert resolve_output_reservation("", "m", None) is None
        assert resolve_output_reservation(None, "m", None) is None

    def test_invalid_user_values_fall_through_to_profile(self):
        assert resolve_output_reservation("custom", "m", 0) == 65536
        assert resolve_output_reservation("custom", "m", -1) == 65536
        assert resolve_output_reservation("custom", "m", "nope") == 65536
        assert resolve_output_reservation("custom", "m", True) == 65536

    def test_agent_shaped_object(self):
        class A:
            provider = "custom"
            model = "ornith-1.0-35b"
            max_tokens = None

        assert resolve_agent_output_reservation(A()) == 65536
        A.max_tokens = 4096
        assert resolve_agent_output_reservation(A()) == 4096


class TestReservationKwargs:
    def test_compressor_accepts_max_tokens(self):
        cc = ContextCompressor(model="m", quiet_mode=True)
        assert reservation_kwargs(cc, 65536) == {"max_tokens": 65536}

    def test_none_reservation_is_dropped(self):
        cc = ContextCompressor(model="m", quiet_mode=True)
        assert reservation_kwargs(cc, None) == {}

    def test_engine_without_the_keyword_gets_nothing(self):
        """A third-party ContextEngine whose update_model() has no max_tokens
        must not be handed one — that would turn a /model switch into a
        TypeError."""

        class Engine:
            def update_model(self, model, context_length, base_url="", api_key="",
                             provider="", api_mode=""):
                pass

        assert reservation_kwargs(Engine(), 65536) == {}

    def test_var_kwargs_engine_is_allowed(self):
        class Engine:
            def update_model(self, model, context_length, **kw):
                pass

        assert reservation_kwargs(Engine(), 65536) == {"max_tokens": 65536}


class TestCompressorThresholdWithReservation:
    """The arithmetic from the live box, end to end through ContextCompressor."""

    def test_reservation_lowers_the_trigger_below_the_input_ceiling(self):
        with_res = ContextCompressor(
            model="ornith-1.0-35b", quiet_mode=True, threshold_percent=0.80,
            config_context_length=200_000, provider="custom", max_tokens=65536,
        )
        without = ContextCompressor(
            model="ornith-1.0-35b", quiet_mode=True, threshold_percent=0.80,
            config_context_length=200_000, provider="custom", max_tokens=None,
        )
        input_ceiling = 200_000 - 65536
        assert without.threshold_tokens == 160_000       # unreachable: > 134464
        assert with_res.threshold_tokens == int(0.80 * input_ceiling)
        assert with_res.threshold_tokens < input_ceiling

    def test_update_model_refreshes_reservation_via_kwargs_helper(self):
        cc = ContextCompressor(
            model="m", quiet_mode=True, threshold_percent=0.80,
            config_context_length=200_000, provider="custom", max_tokens=None,
        )
        assert cc.max_tokens is None
        cc.update_model(
            model="m", context_length=200_000, provider="custom",
            **reservation_kwargs(cc, resolve_output_reservation("custom", "m", None)),
        )
        assert cc.max_tokens == 65536
        assert cc.threshold_tokens == int(0.80 * (200_000 - 65536))


def _config() -> dict:
    return {
        "model": {"context_length": 200_000},
        "compression": {
            "enabled": True,
            "threshold": 0.80,
            "target_ratio": 0.60,
            "protect_first_n": 2,
            "protect_last_n": 12,
        },
        "prompt_caching": {"cache_ttl": "5m"},
        "sessions": {},
        "bedrock": {},
    }


def _make_custom_agent(monkeypatch, tmp_path: Path, *, max_tokens=None):
    """A real AIAgent against a vLLM-shaped custom endpoint (no network)."""
    from hermes_cli import config as config_mod
    from hermes_state import SessionDB
    from run_agent import AIAgent

    cfg = _config()
    if max_tokens is not None:
        cfg["model"]["max_tokens"] = max_tokens
    monkeypatch.setattr(config_mod, "load_config", lambda: cfg)
    monkeypatch.setattr(config_mod, "load_config_readonly", lambda: cfg)
    db = SessionDB(db_path=tmp_path / "state.db")
    with contextlib.redirect_stdout(io.StringIO()):
        return AIAgent(
            base_url="https://vllm.example.internal/v1",
            api_key="test-key",
            provider="custom",
            model="ornith-1.0-35b",
            enabled_toolsets=[],
            disabled_toolsets=[],
            quiet_mode=True,
            skip_memory=True,
            session_db=db,
            session_id="output-reservation-test",
        )


class TestAgentInitWiresTheReservation:
    def test_custom_agent_without_model_max_tokens(self, monkeypatch, tmp_path):
        agent = _make_custom_agent(monkeypatch, tmp_path)
        cc = agent.context_compressor
        # agent.max_tokens keeps meaning "the user set it" — still None here …
        assert agent.max_tokens is None
        # … while the compressor knows the wire reservation.
        assert cc.max_tokens == 65536
        assert cc.context_length == 200_000
        assert cc.threshold_tokens < 200_000 - 65536
        assert cc.threshold_tokens == int(cc.threshold_percent * (200_000 - 65536))

    def test_explicit_model_max_tokens_wins(self, monkeypatch, tmp_path):
        agent = _make_custom_agent(monkeypatch, tmp_path, max_tokens=32768)
        cc = agent.context_compressor
        assert agent.max_tokens == 32768
        assert cc.max_tokens == 32768
        assert cc.threshold_tokens == int(cc.threshold_percent * (200_000 - 32768))
