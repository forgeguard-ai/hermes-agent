import { afterEach, describe, expect, it, vi } from 'vitest'

// ForgeGuard fork: with update checks off (the shipped default in
// src/lib/fork-config), the client must never raise the "Update ready" toast —
// not from the poller (which never starts) and not from a manual check path
// that reaches maybeNotifyUpdateAvailable with a status that says an update
// exists. updates.test.ts pins the switch ON to validate upstream's logic; this
// file uses the real constant.

const notifySpy = vi.fn()

vi.mock('@/store/notifications', () => ({
  notify: (...args: unknown[]) => notifySpy(...args),
  dismissNotification: () => undefined
}))

afterEach(() => {
  notifySpy.mockReset()
})

describe('update checks off (fork default)', () => {
  it('is the shipped default', async () => {
    const { FORK_UPDATE_CHECKS_ENABLED } = await import('@/lib/fork-config')
    expect(FORK_UPDATE_CHECKS_ENABLED).toBe(false)
  })

  it('never shows the update toast, even for a status that reports an update', async () => {
    const { maybeNotifyUpdateAvailable } = await import('@/store/updates')

    maybeNotifyUpdateAvailable({
      supported: true,
      updateAvailable: true,
      behind: 12,
      branch: 'main',
      currentSha: 'abcdef0',
      targetSha: '1234567'
    } as never)

    expect(notifySpy).not.toHaveBeenCalled()
  })
})
