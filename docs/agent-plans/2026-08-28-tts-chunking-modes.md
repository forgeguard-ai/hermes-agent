# 2026-08-28 — TTS chunking modes (fork v0.20.8)

Status: implemented on `feat/tts-chunking-modes` (branched from `dev` @ `fa62ddd29`, v0.20.7).

## Why

The v0.20.7 streaming TTS work functions, but sentence-by-sentence delivery reads badly (choppy
prosody, especially on short replies) — streaming is currently pinned off deployment-side via
`tts.streaming.provider: none` (agent-command PR #48). The fix is a dropdown of preset split
granularities — the same three a chat UI conventionally offers, which the operator surveyed before
choosing (2026-08-28): canonical config values `punctuation` | `paragraphs` | `none`, default
`punctuation`, paragraphs split on EVERY line break (`\n+`). The modes are implemented from
scratch against Hermes' own incremental chunker (its pre-existing `SENTENCE_BOUNDARY_RE` and
`min_len` merge), not ported from any other project. Hermes implements all three **server-side in `SentenceChunker`**, so every voice surface
(desktop voice mode + read-aloud, CLI/TUI voice, gateway streaming) inherits them. `none` still
streams PCM over the WS after the reply completes, so barge-in keeps working — strictly better
than the current provider pin, which drops to the POST path.

Config key: `tts.streaming.chunking` (sibling of the existing `tts.streaming.provider` streamer
pin — that key's `none` disables streaming entirely; `chunking` chooses how text is cut when
streaming is on). UI labels: "On punctuation" / "By paragraph" / "Whole reply". Part B (the
durable `endpoints.tts.chunking` agent-command profile field + console dropdown) is a separate
change in the agent-command repo; this plan is the hermes half only.

## A1 — modes in `tools/tts_streaming.py` + call sites

- [x] `PARAGRAPH_BOUNDARY_RE = re.compile(r"\n+")` next to `SENTENCE_BOUNDARY_RE`
- [x] `SentenceChunker(min_len=20, mode="punctuation")` — boundary picked by mode
      (`paragraphs` → `PARAGRAPH_BOUNDARY_RE`, else `SENTENCE_BOUNDARY_RE`); `none` buffers only
      (`feed()` returns `[]` after think-stripping + open-think guard); `flush()` unchanged;
      min_len merge-forward kept for both cutting modes; docstring covers the three modes
- [x] `resolve_chunking_mode(tts_config)` + `_CHUNKING_ALIASES`
      (`sentence|punctuation`→punctuation, `paragraph|paragraphs`→paragraphs,
      `none|whole|off`→none, unknown/absent→punctuation; non-dict `streaming` tolerated)
- [x] `hermes_cli/web_server.py::speak_stream_ws` — `_resolve()` also returns the profile-scoped
      mode; `_produce` builds `SentenceChunker(mode=mode)`; `none` skips the idle flush (only
      `done` → flush)
- [x] `tools/tts_tool.py::stream_tts_to_speaker` — `SentenceChunker(mode=resolve_chunking_mode(tts_config))`
- [x] `gateway/streaming_tts_consumer.py` — same
- [x] `hermes_cli/config_defaults.py` tts block — `"streaming": {"chunking": "punctuation"}` with
      the three-values comment (puts the key in CONFIG_SCHEMA so the desktop field renders)

## A2 — desktop dropdown (`apps/desktop/src/app/settings/`)

- [x] `constants.ts`: voice section key after `'voice.auto_tts'`; `ENUM_OPTIONS` entry
      `['punctuation', 'paragraphs', 'none']`; `TTS_CHUNKING_LABELS` display map; `FIELD_LABELS`
      `tts.streaming.chunking` = 'Speech Chunking'; `FIELD_DESCRIPTIONS` entry; NOT in
      `FREE_INPUT_KEYS`
- [x] `config-settings.tsx`: `voiceFieldVisible` early `tts.streaming.` return (provider regex
      would hide it); `optionLabels` passes `TTS_CHUNKING_LABELS` for the key
- [x] `voice-provider-fields.tsx`: confirmed no change — `voiceProviderKeys` filters by
      `tts.<provider>.` prefix against the curated voice keys; 'streaming' is not a provider the
      Capabilities picker offers, and the pathological custom-provider-named-'streaming' case is
      accepted as out of scope

## A3 — tests

- [x] `tests/tools/test_tts_streaming.py`: `TestSentenceChunkerModes` (paragraphs per line-break
      run incl. min_len merge-forward; none buffers until flush; think-block stripped across
      deltas in both modes) + `TestResolveChunkingMode` (default, aliases, garbage, non-dict
      streaming section)
- [x] `tests/hermes_cli/test_web_server_speak_stream.py`: paragraphs config → one `stream()` per
      line; none config → zero calls before `done`, exactly one after, containing all the text;
      existing tests unchanged
- [x] `apps/desktop/src/app/settings/voice-field-visible.test.ts`: `tts.streaming.chunking`
      always visible; `voice-provider-fields.test.ts` stays green unchanged

## A4 — docs / fork bookkeeping

- [x] `docs/streaming-tts.md` — "Chunking granularity" section
- [x] `website/docs/user-guide/features/tts.md` — short paragraph near the streaming material
- [x] `docs/site/fork/forgeguard-changes.md` — `v0.20.8:` sentence chained onto the version paragraph
- [x] `docs/site/fork/compatibility.md` — v0.20.8 rows
- [x] `docs/maintainers/upstream-sync/patch-inventory.md` — new carried-patch entry
- [x] Version bump 0.20.7 → 0.20.8 (pyproject.toml, hermes_cli/__init__.py + release date,
      uv.lock hermes-agent entry, apps/desktop/package.json, package-lock.json desktop entry)

## Verification

- [x] `scripts/run_tests.sh tests/tools/test_tts_streaming.py tests/hermes_cli/test_web_server_speak_stream.py tests/tools/test_tts_speed.py tests/hermes_cli/test_doctor_live.py`
- [x] `.venv/bin/ruff check` on the touched Python files
- [x] `cd apps/desktop && npm run typecheck`, then `npx vitest run --project ui src/app/settings/`,
      then `npx vitest run --project electron` — sequentially (3 GB devcontainer)

Single commit on `feat/tts-chunking-modes`; no push, no PR (operator merges; release tag v0.20.8
builds the runtime image). Never stage `contributors/emails/agent@agents-Mac-mini.local`.
