# 2026-08-22 — Fork release v0.20.7: OpenAI streaming-TTS hardening (Kokoro via the built-in `openai` provider)

Status: implemented on branch `fix/openai-streaming-tts-hardening` (from `dev` @ `34d035fab`, v0.20.6)
· Base unchanged: upstream `v2026.8.16.2` · Companion: Agent Command PR "streaming TTS via the built-in
`openai` provider" (the deploy manager now writes `tts.provider: openai` + `tts.openai.base_url` pointing
at the lab's Kokoro-FastAPI derivative instead of a `command` curl helper).

## Why

Desktop voice mode only streams speech (WS `/api/audio/speak-stream` → `SentenceChunker` → per-sentence
PCM) when `tts.provider` is a registered chunked streamer. Pointing the built-in `openai` streamer at a
local OpenAI-compatible server (Kokoro) turns streaming on everywhere at once, but the streaming path had
four rough edges the sync path does not:

1. `OpenAIStreamer.stream` fell back to `OPENAI_BASE_URL` — the **LLM** custom-endpoint override
   (`hermes_cli/providers.py`, model setup flows) — so an agent whose LLM lives on a custom endpoint would
   have its *voice* requests sent to the LLM server whenever `tts.openai.base_url` was unset. The sync
   path (`_generate_openai_tts`) never reads that variable.
2. `tts.speed` / `tts.openai.speed` and `tts.openai.language` (`lang_code`) were honoured on the
   whole-file path only; the streamer ignored them.
3. `hermes doctor --live` probed `https://api.openai.com/v1/models` with `OPENAI_API_KEY` regardless of
   `tts.openai.base_url` / `tts.openai.api_key` — against a local server it reports a bogus warn/fail.
4. A provider failure mid-session (e.g. HTTP 400 for a voice the server does not know) logged a warning
   and then sent `{"type":"end"}` — the desktop heard **silence** and treated it as a successful reply.
   The gateway consumer already has the right rule (no audio yet → whole-file fallback; audio played →
   finish what played).

## Change

- [x] **A.** `tools/tts_streaming.py` `OpenAIStreamer.stream`: `base_url = tts.openai.base_url or
      DEFAULT_OPENAI_BASE_URL` (no `OPENAI_BASE_URL`); `create_kwargs` parity with
      `_generate_openai_tts` (`speed` clamped `[0.25, 4.0]`, sent only when `!= 1.0`; `language` →
      `extra_body={"lang_code": …}`). Tests: `tests/tools/test_tts_streaming.py` (shared fake OpenAI
      client helper; config base_url + dummy key; `OPENAI_BASE_URL` ignored; speed/lang_code parity).
- [x] **B.** `hermes_cli/doctor_live.py`: `_audio_provider_probe(..., openai_cfg=)` — for `openai`,
      URL `<tts.openai.base_url>/models` when set, key `tts.openai.api_key` or the shared audio resolver
      (`_openai_audio_key()` seam → `VOICE_TOOLS_OPENAI_KEY` > `OPENAI_API_KEY`); detail prefixed
      `@ <base_url>`. TTS only. Tests: `tests/hermes_cli/test_doctor_live.py`.
- [x] **C.** Silence → fallback: `hermes_cli/web_server.py` `speak_stream_ws` sends
      `{"type":"error","message":…}` instead of `end` when the producer raised;
      `apps/desktop/src/lib/voice-playback.ts` handles `error` (`started ? finishWhenDrained() :
      settle('fallback')`). Tests: `tests/hermes_cli/test_web_server_speak_stream.py`,
      new `apps/desktop/src/lib/voice-playback.test.ts`.
- [x] **D.** Docs: `docs/streaming-tts.md` (openai credentials row + "Local OpenAI-compatible servers"
      section), `website/docs/user-guide/features/tts.md` (two small notes),
      `docs/site/fork/forgeguard-changes.md` (`v0.20.7:` sentence), `docs/site/fork/compatibility.md`
      (row), `docs/maintainers/upstream-sync/patch-inventory.md` (carried runtime patch entry).
- [x] Version 0.20.6 → 0.20.7 / release date 2026.8.22 (`pyproject.toml`, `hermes_cli/__init__.py`,
      `uv.lock`, `apps/desktop/package.json`, `package-lock.json`).

## Manual test (lab)

- Agent deployed with `tts.provider: openai`, `tts.openai.base_url: https://kokoro.<zone>/v1`,
  `api_key: no-key`: a desktop voice reply starts speaking after the first sentence; DevTools WS on
  `/api/audio/speak-stream` shows `{"type":"start","sample_rate":24000}`, not `fallback`.
- `tts.speed: 1.5` audibly speeds up the streamed reply; `tts.openai.language: es` selects the Spanish
  phonemizer on Kokoro for streamed sentences too.
- `hermes doctor --live` shows `TTS (openai @ https://kokoro.<zone>/v1) (HTTP 200)`.
- Set `tts.openai.voice: nonexistent` → the desktop falls back to the POST path (toast on failure), not
  silence; with a real voice and a mid-reply server restart, what played is kept and the session ends.
- `OPENAI_BASE_URL` set in `.env` (LLM custom endpoint) with `tts.openai.base_url` unset → voice requests
  go to `https://api.openai.com/v1`, not the LLM server.

## Verification

- `scripts/run_tests.sh tests/tools/test_tts_streaming.py tests/tools/test_tts_speed.py
  tests/tools/test_tts_openai_config.py tests/hermes_cli/test_web_server_speak_stream.py
  tests/hermes_cli/test_doctor_live.py`
- `ruff check tools/tts_streaming.py hermes_cli/web_server.py hermes_cli/doctor_live.py
  tests/tools/test_tts_streaming.py tests/hermes_cli/test_doctor_live.py
  tests/hermes_cli/test_web_server_speak_stream.py`
- `cd apps/desktop && npm run typecheck && npm run lint && npx vitest run --project ui
  src/lib/voice-playback.test.ts src/app/chat/composer/hooks/`

Results (2026-08-22, devcontainer): `run_tests.sh` subset — 5 files, 86 passed, 0 failed;
`ruff check` — all checks passed; desktop `npm run typecheck` — exit 0; `npm run lint` — 0 errors
(pre-existing warnings only); `vitest --project ui src/lib/voice-playback.test.ts
src/app/chat/composer/hooks/` — 16 files, 92 passed.
