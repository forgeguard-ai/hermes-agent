import { act, cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { $desktopBoot } from '@/store/boot'
import { $connectionModeDialog } from '@/store/connection-mode'
import { $gatewayState } from '@/store/session'

import { useGatewayBoot } from './use-gateway-boot'

// End-to-end-ish repro of the "remote VPS → stuck on CONNECTING, no Settings"
// bug that drives the REAL useGatewayBoot hook + REAL HermesGateway through a
// fake WebSocket we fully control. No Docker / no real port: from the desktop's
// point of view a "remote VPS" is just a WebSocket that opens once and later
// refuses to reopen, so that is exactly (and only) what we fake.
//
// The previous test (gateway-connecting-overlay.test.tsx) hand-set the stores
// and asserted the overlays; this one proves the HOOK actually PRODUCES that
// stuck store combo — closing the "inferred by reading code" gap on the
// post-boot reconnect loop.

type Listener = (ev: unknown) => void

// Minimal WebSocket stand-in implementing only what json-rpc-gateway.connect()
// touches: readyState, add/removeEventListener('open'|'error'|'close'), close().
class FakeWebSocket {
  static OPEN = 1
  static CLOSED = 3
  // Flipped by the test: 'open' = next socket connects; 'fail' = next socket
  // errors (a dead remote). Mirrors a VPS going away after the first connect.
  static mode: 'open' | 'fail' = 'open'
  static instances: FakeWebSocket[] = []

  readyState = 0
  // Frames written by the client (heartbeat pings land here).
  sent: string[] = []
  private listeners: Record<string, Set<Listener>> = {}

  constructor(public url: string) {
    FakeWebSocket.instances.push(this)
    const willOpen = FakeWebSocket.mode === 'open'
    // Resolve on the next microtask/macrotask so connect()'s promise wiring is
    // in place before open/error fires (matches real async socket handshake).
    setTimeout(() => {
      if (willOpen) {
        this.readyState = FakeWebSocket.OPEN
        this.emit('open', {})
      } else {
        this.readyState = FakeWebSocket.CLOSED
        this.emit('error', {})
      }
    }, 0)
  }

  addEventListener(type: string, fn: Listener) {
    ;(this.listeners[type] ??= new Set()).add(fn)
  }

  removeEventListener(type: string, fn: Listener) {
    this.listeners[type]?.delete(fn)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.readyState = FakeWebSocket.CLOSED
    this.emit('close', {})
  }

  // Force-drop an open socket, as a sleeping laptop / restarted remote would.
  drop() {
    this.readyState = FakeWebSocket.CLOSED
    this.emit('close', {})
  }

  private emit(type: string, ev: unknown) {
    for (const fn of this.listeners[type] ?? []) {
      fn(ev)
    }
  }
}

function fakeDesktop() {
  const conn = {
    authMode: 'token' as const,
    baseUrl: 'https://vps.example.com',
    profile: 'default',
    token: 't',
    wsUrl: 'wss://vps.example.com/api/ws?token=t'
  }

  return {
    getConnection: vi.fn(async () => conn),
    getGatewayWsUrl: vi.fn(async () => conn.wsUrl),
    getBootProgress: vi.fn(async () => ({
      error: null,
      fakeMode: false,
      message: '',
      phase: 'init',
      progress: 0,
      running: true,
      timestamp: Date.now()
    })),
    onBootProgress: vi.fn(() => () => undefined),
    onBackendExit: vi.fn(() => () => undefined),
    onPowerResume: vi.fn(() => () => undefined),
    onWindowStateChanged: vi.fn(() => () => undefined),
    touchBackend: vi.fn(async () => undefined),
    profile: { get: vi.fn(async () => ({ profile: 'default' })) }
  }
}

function Harness() {
  useGatewayBoot({
    handleGatewayEvent: () => undefined,
    onConnectionReady: () => undefined,
    onGatewayReady: () => undefined,
    refreshHermesConfig: async () => undefined,
    refreshSessions: async () => undefined
  })

  return null
}

const originalWebSocket = globalThis.WebSocket

beforeEach(() => {
  vi.useFakeTimers()
  FakeWebSocket.mode = 'open'
  FakeWebSocket.instances = []
  ;(globalThis as { WebSocket: unknown }).WebSocket = FakeWebSocket
  ;(window as { hermesDesktop?: unknown }).hermesDesktop = fakeDesktop()
  $gatewayState.set('idle')
  $connectionModeDialog.set({ open: false, prefill: null, firstRun: false })
  $desktopBoot.set({
    error: null,
    fakeMode: false,
    message: '',
    phase: 'init',
    progress: 0,
    running: true,
    timestamp: Date.now(),
    visible: true
  })
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  ;(globalThis as { WebSocket: unknown }).WebSocket = originalWebSocket
  delete (window as { hermesDesktop?: unknown }).hermesDesktop
})

// Let pending microtasks (awaits) AND the queued 0ms socket open/error fire.
// Advances a few fake ms (not 0): a 0ms timer scheduled DURING a previous
// advance window lands just past its boundary and never fires on a 0ms
// advance — observed with the retry chain's delay → dial → socket-event hops.
async function flushAsync() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(50)
  })
}

// Drive the exponential backoff forward by its full cap so the next scheduled
// reconnect attempt actually runs (1s,2s,4s,8s,15s,15s…). Returns after the
// attempt's async work settles.
async function advanceBackoff() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(15_000)
  })
}

describe('useGatewayBoot remote reconnect loop (real hook, fake socket)', () => {
  it('INITIAL boot against a dead VPS: getConnection hangs (waitForHermes) → app sits in the connecting combo, then fails', async () => {
    // The report's actual path: a fresh launch pointed at an unreachable VPS.
    // startHermes()'s remote branch awaits waitForHermes() for 45s before it
    // throws, so the renderer's `await desktop.getConnection()` stays pending
    // that whole window. During it: gatewayState is still 'idle' (connect was
    // never reached) and boot.error is null → connecting=true → the fullscreen
    // CONNECTING overlay, latched, blocking Settings.
    let rejectConn: (e: Error) => void = () => undefined
    const desktop = fakeDesktop()
    desktop.getConnection = vi.fn(
      () =>
        new Promise((_resolve, reject) => {
          rejectConn = reject
        })
    )
    ;(window as { hermesDesktop?: unknown }).hermesDesktop = desktop

    render(<Harness />)
    await flushAsync()

    // getConnection is still pending — the dead-VPS wait. No socket was ever
    // created, gatewayState never left idle, boot.error is null.
    expect(FakeWebSocket.instances).toHaveLength(0)
    expect($gatewayState.get()).not.toBe('open')
    expect($desktopBoot.get().error).toBeNull()
    // ^ connecting === true here → fullscreen CONNECTING, no Settings.

    // After ~45s waitForHermes gives up and getConnection rejects → boot()
    // catch → failDesktopBoot → the BootFailureOverlay recovery surface.
    await act(async () => {
      rejectConn(new Error('Hermes backend did not become ready: timeout'))
      await vi.advanceTimersByTimeAsync(0)
    })

    expect($desktopBoot.get().error).toBeTruthy()
  })

  it('FIX: a WS-stage failure on INITIAL boot retries with backoff and connects when the gateway comes back', async () => {
    // The HTTP probe passed (getConnection resolves) but the WS dial fails —
    // e.g. the gateway restarting between probe and dial. Previously a single
    // failed attempt dropped straight to the failure overlay.
    FakeWebSocket.mode = 'fail'

    render(<Harness />)
    await flushAsync()

    // First attempt failed, but boot is still retrying — no failure overlay.
    expect(FakeWebSocket.instances).toHaveLength(1)
    expect($desktopBoot.get().error).toBeNull()

    // The gateway comes back before the retries run out.
    FakeWebSocket.mode = 'open'
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000)
    })
    await flushAsync()

    expect($gatewayState.get()).toBe('open')
    expect($desktopBoot.get().error).toBeNull()
    expect(FakeWebSocket.instances).toHaveLength(2)
  })

  it('a persistently dead WS on INITIAL boot exhausts the bounded retries, then fails', async () => {
    FakeWebSocket.mode = 'fail'

    render(<Harness />)
    await flushAsync()

    // Walk through the 1s, 2s, 4s waits between the four attempts.
    for (const delay of [1_000, 2_000, 4_000]) {
      expect($desktopBoot.get().error).toBeNull()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(delay)
      })
      await flushAsync()
    }

    expect(FakeWebSocket.instances).toHaveLength(4)
    expect($desktopBoot.get().error).toBeTruthy()
  })

  it('FIX: a silent half-dead socket is heartbeat-detected and force-closed into the reconnect loop', async () => {
    render(<Harness />)
    await flushAsync()
    expect($gatewayState.get()).toBe('open')
    const socket = FakeWebSocket.instances[0]

    // First heartbeat tick: the ping goes out on the wire.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(socket.sent.some(frame => frame.includes('gateway.ping'))).toBe(true)

    // No reply ever arrives (the socket is half-dead — open at the TCP layer,
    // delivering nothing). After the reply timeout the hook force-closes it,
    // handing off to the reconnect loop, which mints a fresh socket.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(socket.readyState).toBe(FakeWebSocket.CLOSED)

    await advanceBackoff()
    expect($gatewayState.get()).toBe('open')
    expect(FakeWebSocket.instances.length).toBeGreaterThan(1)
  })

  it('a remote that drops post-boot keeps looping with NO boot.error (the dead-end CONNECTING combo)', async () => {
    render(<Harness />)
    await flushAsync()

    // Initial boot connected.
    expect($gatewayState.get()).toBe('open')
    expect($desktopBoot.get().error).toBeNull()
    expect(FakeWebSocket.instances).toHaveLength(1)

    // The remote VPS goes away: drop the live socket, and make every reopen
    // fail from here on.
    FakeWebSocket.mode = 'fail'
    act(() => FakeWebSocket.instances[0].drop())
    await flushAsync()

    // Burn a couple backoff cycles BEFORE the escalation threshold (<6 attempts,
    // ~the first ~15s). This is the window where stock and fixed behave the
    // same: socket down, hook retrying, gatewayState non-open, boot.error still
    // null → CONNECTING covers the screen with no recovery surface. (Past ~45s
    // the fix raises boot.error; that's asserted in the next test.)
    await advanceBackoff()

    expect($gatewayState.get()).not.toBe('open')
    expect($desktopBoot.get().error).toBeNull()
    // It is actively retrying, not idle — more sockets were minted.
    expect(FakeWebSocket.instances.length).toBeGreaterThan(1)
  })

  it('FIX: after the prolonged drop the hook raises a recoverable boot error (the escape hatch)', async () => {
    render(<Harness />)
    await flushAsync()
    expect($desktopBoot.get().error).toBeNull()

    FakeWebSocket.mode = 'fail'
    act(() => FakeWebSocket.instances[0].drop())
    await flushAsync()

    // Walk the backoff past the >=6 attempt threshold (~45s of failures).
    for (let i = 0; i < 8; i += 1) {
      await advanceBackoff()
    }

    // The hook surfaced the recoverable error → BootFailureOverlay (Use local
    // gateway / Sign in / Retry) becomes reachable instead of CONNECTING.
    expect($desktopBoot.get().error).toBeTruthy()
  })

  it('first-run required: defers connecting and opens the blocking chooser instead', async () => {
    const desktop = fakeDesktop() as ReturnType<typeof fakeDesktop> & {
      firstRunChoice?: { get: ReturnType<typeof vi.fn>; complete: ReturnType<typeof vi.fn> }
    }

    desktop.firstRunChoice = {
      get: vi.fn(async () => ({ required: true })),
      complete: vi.fn(async () => ({ ok: true, required: false }))
    }
    ;(window as { hermesDesktop?: unknown }).hermesDesktop = desktop

    render(<Harness />)
    await flushAsync()

    // No backend is dialed while the user still has to choose.
    expect(desktop.getConnection).not.toHaveBeenCalled()
    expect(FakeWebSocket.instances).toHaveLength(0)
    // The blocking first-run chooser is up, and the boot splash stood down.
    expect($connectionModeDialog.get().open).toBe(true)
    expect($connectionModeDialog.get().firstRun).toBe(true)
    expect($desktopBoot.get().visible).toBe(false)
    expect($desktopBoot.get().running).toBe(false)
    // The gateway machinery never subscribed to boot progress either — the whole
    // init was deferred behind the gate, not just the getConnection call.
    expect(desktop.onBootProgress).not.toHaveBeenCalled()
  })

  it('first-run check is best-effort: a rejecting get() still boots normally', async () => {
    const desktop = fakeDesktop() as ReturnType<typeof fakeDesktop> & {
      firstRunChoice?: { get: ReturnType<typeof vi.fn> }
    }

    // An older/erroring main (IPC throws) must not wedge the app on the splash:
    // we fall through to the normal connect path exactly as before the gate.
    desktop.firstRunChoice = { get: vi.fn(async () => Promise.reject(new Error('no ipc'))) }
    ;(window as { hermesDesktop?: unknown }).hermesDesktop = desktop

    render(<Harness />)
    await flushAsync()

    expect(desktop.getConnection).toHaveBeenCalled()
    expect($connectionModeDialog.get().open).toBe(false)
    expect($gatewayState.get()).toBe('open')
  })

  it('FIX: a successful reconnect clears the recoverable error', async () => {
    render(<Harness />)
    await flushAsync()

    FakeWebSocket.mode = 'fail'
    act(() => FakeWebSocket.instances[0].drop())
    await flushAsync()

    for (let i = 0; i < 8; i += 1) {
      await advanceBackoff()
    }

    expect($desktopBoot.get().error).toBeTruthy()

    // The remote comes back: next reconnect attempt opens.
    FakeWebSocket.mode = 'open'
    await advanceBackoff()

    expect($gatewayState.get()).toBe('open')
    expect($desktopBoot.get().error).toBeNull()
  })
})
