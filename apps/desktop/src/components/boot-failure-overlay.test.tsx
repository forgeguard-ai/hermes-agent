import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { $desktopBoot } from '@/store/boot'
import { $desktopOnboarding } from '@/store/onboarding'

import { BootFailureOverlay } from './boot-failure-overlay'

// Remote-backend users hit a hard boot failure that isn't OAuth reauth (token
// auth, wrong URL, unreachable host). The recovery screen must let them fix the
// remote connection in place — the "Connection settings" action swaps the card
// to an in-line connect form — instead of stranding them (the old bug forced a
// hand-edit of connection.json).

function failBoot() {
  $desktopBoot.set({
    error: 'Could not connect to Hermes gateway',
    fakeMode: false,
    message: 'boot failed',
    phase: 'renderer.error',
    progress: 40,
    running: false,
    timestamp: Date.now(),
    visible: true
  })
}

function stubDesktop(config: Record<string, unknown>) {
  const original = window.hermesDesktop
  Object.defineProperty(window, 'hermesDesktop', {
    configurable: true,
    value: { getRecentLogs: async () => ({ lines: [] }), getConnectionConfig: async () => config }
  })

  return () => Object.defineProperty(window, 'hermesDesktop', { configurable: true, value: original })
}

const remoteToken = {
  envOverride: false,
  mode: 'remote',
  profile: null,
  remoteAuthMode: 'token',
  remoteOauthConnected: false,
  remoteTokenPreview: null,
  remoteTokenSet: true,
  remoteUrl: 'http://100.116.104.53:9191',
  cloudOrg: ''
}

beforeEach(() => {
  $desktopOnboarding.set({
    configured: true,
    flow: { status: 'idle' },
    mode: 'oauth',
    providers: null,
    reason: null,
    requested: false,
    firstRunSkipped: false,
    manual: false,
    localEndpoint: false
  })
  failBoot()
})

afterEach(cleanup)

describe('BootFailureOverlay', () => {
  it('swaps to the in-place gateway settings view (no route nav) and back', async () => {
    render(<BootFailureOverlay />)

    fireEvent.click(screen.getByRole('button', { name: /gateway settings/i }))
    // Recovery actions give way to the embedded panel (behind a Back control).
    expect(await screen.findByRole('button', { name: /back/i })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /retry/i })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /back/i }))
    expect(screen.getByRole('button', { name: /retry/i })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /back/i })).toBeNull()
  })

  it('drops local-only Repair and Use-local-gateway on a local failure', () => {
    render(<BootFailureOverlay />)
    // No connection config stub → treated as a local failure.
    expect(screen.getByRole('button', { name: /retry/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /repair/i })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /use local gateway/i })).toBeNull()
  })

  it('leads with Gateway settings and drops Repair for a remote (token) failure', async () => {
    const restore = stubDesktop(remoteToken)

    try {
      render(<BootFailureOverlay />)
      await waitFor(() => expect(screen.queryByRole('button', { name: /repair/i })).toBeNull())
      expect(screen.getByRole('button', { name: /gateway settings/i })).toBeTruthy()
      expect(screen.getByRole('button', { name: /use local gateway/i })).toBeTruthy()
      // Token-mode remotes have no OAuth session to renew: no sign-in offered.
      expect(screen.queryByRole('button', { name: /sign in/i })).toBeNull()
    } finally {
      restore()
    }
  })

  // ForgeGuard fork: after the agent container is recreated, the ws-ticket
  // refresh fails with a message that need not classify as auth-shaped
  // (status lost, or a 503 while the provider registry re-seeds), and the
  // stale native token keeps Settings → Gateway on "Signed in". The generic
  // remote-failure surface must still offer a sign-in — otherwise every button
  // re-tries the same dead credential and the only way out is wiping app data.
  const remoteOauthStale = {
    ...remoteToken,
    remoteAuthMode: 'oauth',
    remoteOauthConnected: true, // a stale native token still on disk reads as "connected"
    remoteTokenSet: false
  }

  it('routes the ticket-refresh failure to the sign-in surface even while "connected"', async () => {
    const restore = stubDesktop(remoteOauthStale)
    $desktopBoot.set({
      ...$desktopBoot.get(),
      error: 'Could not reach the remote Hermes gateway while refreshing its WebSocket ticket. Try reconnecting.'
    })

    try {
      render(<BootFailureOverlay />)
      await waitFor(() => expect(screen.getByRole('button', { name: /sign in/i })).toBeTruthy())
      expect(screen.getByRole('heading', { name: /sign-in required/i })).toBeTruthy()
    } finally {
      restore()
    }
  })

  it('still offers Sign in on a generic remote (oauth) failure', async () => {
    const restore = stubDesktop(remoteOauthStale)
    $desktopBoot.set({ ...$desktopBoot.get(), error: 'socket timed out' })

    try {
      render(<BootFailureOverlay />)
      await waitFor(() => expect(screen.getByRole('button', { name: /sign in/i })).toBeTruthy())
      expect(screen.getByRole('button', { name: /gateway settings/i })).toBeTruthy()
      expect(screen.getByRole('button', { name: /retry/i })).toBeTruthy()
    } finally {
      restore()
    }
  })
})
