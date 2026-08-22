// /api/audio/speak-stream session outcomes: a provider failure must resolve
// the session (fallback before audio, done after audio) instead of leaving
// voice mode in silence — mirrors gateway/streaming_tts_consumer.py's rule.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/hermes', () => ({
  getApiRequestProfile: vi.fn(() => null),
  speakText: vi.fn()
}))
vi.mock('@hermes/shared', () => ({
  resolveGatewayWsUrl: vi.fn(async () => 'ws://127.0.0.1:1/api/ws')
}))

import { $voicePlayback } from '@/store/voice-playback'

import { startSpeechStream, stopVoicePlayback } from './voice-playback'

type FrameHandler = ((event: { data: ArrayBuffer | string }) => void) | null

class FakeWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  static last: FakeWebSocket | null = null

  binaryType = 'blob'
  readyState = FakeWebSocket.CONNECTING
  url: string
  onopen: (() => void) | null = null
  onmessage: FrameHandler = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  send = vi.fn()
  close = vi.fn(() => {
    this.readyState = FakeWebSocket.CLOSED
  })

  constructor(url: string) {
    this.url = url
    FakeWebSocket.last = this
  }

  open() {
    this.readyState = FakeWebSocket.OPEN
    this.onopen?.()
  }

  json(frame: object) {
    this.onmessage?.({ data: JSON.stringify(frame) })
  }

  pcm(samples: number[]) {
    this.onmessage?.({ data: new Int16Array(samples).buffer })
  }
}

const scheduled: Array<{ connect: ReturnType<typeof vi.fn>; start: ReturnType<typeof vi.fn> }> = []

class FakeAudioContext {
  currentTime = 0
  destination = {}
  state = 'running'
  close = vi.fn(async () => undefined)
  resume = vi.fn(async () => undefined)

  createBuffer(_channels: number, length: number, rate: number) {
    return { duration: length / rate, getChannelData: () => new Float32Array(length) }
  }

  createBufferSource() {
    const source = { buffer: null as unknown, connect: vi.fn(), start: vi.fn() }

    scheduled.push(source)

    return source
  }
}

async function openSession() {
  const session = await startSpeechStream({ source: 'voice-conversation' })

  expect(session).not.toBeNull()

  const ws = FakeWebSocket.last

  expect(ws).not.toBeNull()
  expect(ws!.url).toBe('ws://127.0.0.1:1/api/audio/speak-stream')
  ws!.open()
  ws!.json({ channels: 1, sample_rate: 24_000, type: 'start' })

  return { session: session!, ws: ws! }
}

describe('speak-stream session outcomes', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    scheduled.length = 0
    FakeWebSocket.last = null
    vi.stubGlobal('WebSocket', FakeWebSocket)
    vi.stubGlobal('AudioContext', FakeAudioContext)
    vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    window.hermesDesktop = {
      getConnection: vi.fn(async () => ({}))
    } as unknown as Window['hermesDesktop']
  })

  afterEach(() => {
    stopVoicePlayback()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('resolves fallback when the provider fails before any audio', async () => {
    const { session, ws } = await openSession()

    ws.json({ message: 'HTTP 400 bad voice', type: 'error' })

    await expect(session.done).resolves.toBe('fallback')
    expect(console.warn).toHaveBeenCalledWith('speak-stream failed:', 'HTTP 400 bad voice')
    expect(scheduled).toHaveLength(0)
    expect(ws.close).toHaveBeenCalled()
  })

  it('resolves done when the provider fails after audio already played', async () => {
    const { session, ws } = await openSession()

    ws.pcm([1, 2, 3, 4])
    expect(scheduled).toHaveLength(1)
    expect($voicePlayback.get().status).toBe('speaking')

    ws.json({ message: 'connection reset', type: 'error' })

    let outcome: null | string = null

    void session.done.then(value => {
      outcome = value
    })
    await Promise.resolve()
    // Not settled yet: what was scheduled is allowed to drain first.
    expect(outcome).toBeNull()

    vi.advanceTimersByTime(1_000)
    await expect(session.done).resolves.toBe('done')
    expect($voicePlayback.get().status).toBe('idle')
  })

  it('resolves done on a normal end frame', async () => {
    const { session, ws } = await openSession()

    ws.pcm([5, 6])
    ws.json({ type: 'end' })
    vi.advanceTimersByTime(1_000)

    await expect(session.done).resolves.toBe('done')
  })

  it('ignores unknown frame types', async () => {
    const { session, ws } = await openSession()

    ws.json({ type: 'heartbeat' })
    ws.json({ type: 'end' })
    vi.advanceTimersByTime(1_000)

    await expect(session.done).resolves.toBe('done')
  })
})
