# 2026-08-17 — The compressor's output reservation must match the wire (v0.20.3)

Status: implemented on `fix/compaction-output-reservation`; PR → `forgeguard-ai/hermes-agent:main` (never upstream).

## Problem

A deployed lab agent (vLLM, provider `custom`, `context_length: 200000`, no
`model.max_tokens`) never compacted proactively and instead ran into the provider's
HTTP 400 ("requested 65536 output tokens and your prompt contains at least 134465
input tokens"), whereupon the emergency compaction shed 210 messages down to 13 and
the agent re-ran work it no longer remembered.

Cause: two different answers to "how many output tokens are reserved".
- The chat-completions transport reserves the provider profile's default when the
  user set none — `CustomProfile.default_max_tokens = 65536`
  (`plugins/model-providers/custom/__init__.py`, used at
  `agent/transports/chat_completions.py` `build_kwargs`).
- The `ContextCompressor` was only ever handed `agent.max_tokens` (the user tier,
  `agent/agent_init.py`), i.e. `None`, so its #43547 guard
  `effective_window = context_length - (max_tokens or 0)` armed the trigger at
  0.8 × 200000 = 160000 — above the 134464 the session could ever reach.

## Change

- [x] `agent/output_reservation.py` — `resolve_output_reservation(provider, model,
      user_max_tokens)` (user > profile default > None), the agent-shaped wrapper, and
      `reservation_kwargs(engine, n)` which only emits `max_tokens=` when the engine's
      `update_model` accepts it (third-party `ContextEngine`s don't).
- [x] `agent/agent_init.py` — the compressor is constructed with the resolved
      reservation; `agent.max_tokens` is left alone (it still means "the user set it").
- [x] Provider-changing `update_model` sites re-derive it: restore-primary and `/model`
      switch (`agent/agent_runtime_helpers.py`), fallback activation
      (`agent/chat_completion_helpers.py`).
- [x] Tests: `tests/agent/test_output_reservation.py` (resolver table, kwargs guard,
      threshold arithmetic, real `AIAgent` on a custom endpoint with and without
      `model.max_tokens`).
- [x] Version 0.20.3 / 2026.8.17 (`hermes_cli/__init__.py`, `pyproject.toml`,
      `apps/desktop/package.json`, `uv.lock`).

Deliberately not changed: `CustomProfile.default_max_tokens` (Ollama's `num_predict`
rationale stands) and the 400-recovery ephemeral (it is window − input − 64, not a
reservation). Operators who want a smaller reservation set `model.max_tokens`.
