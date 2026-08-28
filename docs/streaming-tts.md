# Streaming TTS

Hermes can stream TTS audio as it arrives from the provider, instead of waiting
for the full audio before playing. This is used by voice mode (CLI/TUI live
conversation), the dashboard speak-stream WebSocket, and — via the gateway
`StreamingTTSConsumer` — any platform adapter that opts into streaming audio.
Voice replies start speaking after the first clause instead of after full
generation + synthesis.

## Architecture

The streaming pipeline has four parts:

1. **Producer** — the LLM emits text deltas as it generates a response
2. **Sentence chunker** — `tools.tts_streaming.SentenceChunker` accumulates
   deltas, strips `<think>` blocks (even split across deltas), and flushes
   complete sentences
3. **TTS provider** — a registered `StreamingTTSProvider` turns each sentence
   into raw PCM chunks (int16 mono at the provider's declared `sample_rate`)
4. **Audio sink** — `sounddevice.OutputStream` for local playback
   (`tools.tts_tool.stream_tts_to_speaker`), or a gateway platform adapter's
   `write_streaming_tts` seam (`gateway/streaming_tts_consumer.py`)

Providers with no chunked API still get per-*sentence* playback via the proven
sync `text_to_speech_tool` path, so edge (the default) is conversational too.
All spoken text is cleaned by `tools.tts_text_normalize.prepare_spoken_text`
(one cleaner, all paths).

## How to pick a provider

By default the dispatcher streams with the provider you already configured
(`tts.provider`) when that provider has a chunked API — it never silently
swaps your voice for a different provider just to get streaming.

To override, set `tts.streaming.provider` in your `config.yaml`:

- a provider name (`elevenlabs`, `gemini`, `openai`, `xai`) pins that streamer
- `auto` walks the priority list `elevenlabs → gemini → openai → xai` and uses
  the first one whose credentials resolve — an explicit opt-in to "best
  chunked voice available"

```yaml
tts:
  provider: gemini
  streaming:
    provider: gemini      # or "auto"
  gemini:
    model: gemini-2.5-flash-preview-tts
    voice: Kore
```

## Chunking granularity

`tts.streaming.chunking` controls how reply text is cut into utterances.
The canonical values are:

- `punctuation` (default) — cut per sentence; each sentence is synthesized
  and streamed the moment it completes. The pre-existing behavior.
- `paragraphs` — cut on every line-break run (`\n+`), so each
  markdown bullet/line is its own utterance.
- `none` — buffer the whole reply and synthesize it as ONE utterance once
  the reply completes. The audio still streams as PCM over the same
  WebSocket after the reply is done, so barge-in keeps working — synthesis
  is late, not disabled.

```yaml
tts:
  streaming:
    chunking: punctuation   # punctuation | paragraphs | none
```

Every surface that speaks honors it, because the cut happens server-side in
`SentenceChunker`: the desktop speak-stream WebSocket (voice mode and
read-aloud), the CLI/TUI speaker pipeline (`stream_tts_to_speaker`), and the
gateway `StreamingTTSConsumer`.

Do not confuse it with `tts.streaming.provider`: that key pins WHICH
streamer is used, and `none` **there** disables streaming entirely (dropping
to the whole-file POST path). `chunking` chooses how the text is cut when
streaming is on.

## Capability matrix

| Provider    | Transport                             | Chunked PCM | Credentials |
|-------------|---------------------------------------|-------------|-------------|
| elevenlabs  | chunked HTTP (`pcm_24000`)            | yes         | `ELEVENLABS_API_KEY` / `tts.elevenlabs` |
| openai      | chunked HTTP (`with_streaming_response`, `pcm`) | yes | `tts.openai.api_key` → `VOICE_TOOLS_OPENAI_KEY` / `OPENAI_API_KEY`; endpoint from `tts.openai.base_url` (never `OPENAI_BASE_URL`) |
| gemini      | SSE (`streamGenerateContent?alt=sse`) | yes         | `GEMINI_API_KEY` / `GOOGLE_API_KEY` |
| xai         | WebSocket (`wss://api.x.ai/v1/tts`)   | yes         | xAI OAuth or `XAI_API_KEY` |
| edge, piper, kitten, neutts, mistral, minimax, deepinfra, … | — | no (per-sentence sync fallback) | as usual |

All credential lookups go through `resolve_provider_secret()`
(config > env/.env > credential pool) — never bare env reads. Streamed bodies
are capped at 16 MiB per sentence, mirroring the sync providers' bounded
upstream-body invariant.

## Local OpenAI-compatible servers (Kokoro-FastAPI and derivatives)

The `openai` streamer is a plain OpenAI-compatible client, so any server that
implements `POST /v1/audio/speech` with `response_format: pcm` streams too —
[Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI) and its
derivatives are the common case. What matters:

- **`tts.openai.base_url` is required** (e.g. `https://kokoro.example/v1`). It
  is the only endpoint knob on both the whole-file and streaming paths;
  `OPENAI_BASE_URL` (the LLM custom-endpoint override) is never consulted.
- **`tts.openai.api_key` must be a non-empty string** even when the server
  has no auth — `"no-key"` works (the streamer gate is "a key resolves", and
  Hermes already treats `no-key` as a placeholder). An empty key silently
  disables streaming.
- **`model` must be one the server accepts.** Kokoro answers `kokoro`,
  `tts-1`, `tts-1-hd` and `gpt-4o-mini-tts`; anything else is HTTP 400.
  **Voice names are the server's** (`af_heart`, …), not OpenAI's.
- Streaming requests `response_format=pcm` and plays it at **24 kHz mono
  int16** (`OpenAIStreamer.sample_rate` is fixed; Kokoro's pcm is 24 kHz).
- `tts.speed` / `tts.openai.speed` and `tts.openai.language` (`lang_code`)
  are honoured on **both** the streaming and whole-file paths.
- `tts.openai.max_text_length` lifts the 4096-character OpenAI cap for a
  server that accepts longer input.
- **Failure contract:** if the provider raises mid-session (unknown voice,
  server down) the speak-stream WebSocket sends `{"type":"error","message":…}`
  instead of `end`. The desktop falls back to `POST /api/audio/speak` when no
  audio was emitted yet, otherwise finishes what played — never silence.
- `hermes doctor --live` probes `<base_url>/models` with `tts.openai.api_key`
  (falling back to `VOICE_TOOLS_OPENAI_KEY` / `OPENAI_API_KEY`) and reports
  `TTS (openai @ <base_url>) (HTTP <code>)`.

```yaml
tts:
  provider: openai
  speed: 1.0
  openai:
    base_url: https://kokoro.example/v1
    api_key: no-key
    model: tts-1
    voice: af_heart
    max_text_length: 8192
```

## Adding a new streaming provider

1. Subclass `StreamingTTSProvider` in `tools/tts_streaming.py`
2. Set `sample_rate` (and `channels` / `sample_width` if not int16 mono)
3. Implement `available()` (a pure probe — never install anything) and
   `stream(self, text) -> Iterator[bytes]` yielding raw PCM chunks
4. Decorate with `@register("yourname")`
5. Add tests in `tests/tools/test_tts_streaming.py`

The ABC enforces the contract; the registry makes the provider discoverable;
the dispatcher (`stream_tts_to_speaker`) and the gateway consumer handle the
sentence buffer, stop events, and audio sink for free.

## Gateway streaming (platform adapters)

`gateway/streaming_tts_consumer.py` bridges agent deltas to an adapter's
streaming-audio seam. Adapters opt in by overriding, on
`BasePlatformAdapter`:

- `supports_streaming_tts(chat_id, audio_format) -> bool`
- `begin_streaming_tts / write_streaming_tts / finish_streaming_tts /
  abort_streaming_tts`

All default to unsupported/no-op, so existing adapters are untouched. When a
turn's streaming audio completes, the whole-file auto-TTS reply for that turn
is suppressed (no double playback); when streaming fails before any audio was
audible, the gateway falls back to the legacy whole-file voice reply.
