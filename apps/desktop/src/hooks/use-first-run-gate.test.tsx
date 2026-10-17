import { act, cleanup, renderHook } from '@testing-library/react'
import { useEffect } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { $desktopBoot } from '@/store/boot'
import { $connectionModeDialog } from '@/store/connection-mode'
import { $sessionsLoading } from '@/store/session'

import {
  enterFirstRunChoice,
  FIRST_RUN_CHOICE_REQUIRED,
  firstRunChoiceRequired,
  isFirstRunChoiceRequiredError,
  useFirstRunGate
} from './use-first-run-gate'

type FirstRunBridge = { firstRunChoice?: { get: () => Promise<{ required: boolean }> } }

function installBridge(bridge: FirstRunBridge | undefined) {
  ;(window as { hermesDesktop?: unknown }).hermesDesktop = bridge
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(r => (resolve = r))

  return { promise, resolve }
}

const originalBridge = (window as { hermesDesktop?: unknown }).hermesDesktop

beforeEach(() => {
  $connectionModeDialog.set({ open: false, prefill: null, firstRun: false })
  $sessionsLoading.set(true)
  $desktopBoot.set({
    error: null,
    phase: 'renderer.boot',
    progress: 10,
    running: true,
    timestamp: 0,
    visible: true
  } as ReturnType<typeof $desktopBoot.get>)
})

afterEach(() => {
  cleanup()
  installBridge(originalBridge as FirstRunBridge | undefined)
})

function expectChooserOpen() {
  expect($connectionModeDialog.get()).toMatchObject({ firstRun: true, open: true })
  expect($desktopBoot.get()).toMatchObject({ phase: 'renderer.first-run', running: false, visible: false })
  expect($sessionsLoading.get()).toBe(false)
}

function expectChooserClosed() {
  expect($connectionModeDialog.get().open).toBe(false)
  expect($desktopBoot.get().visible).toBe(true)
}

describe('isFirstRunChoiceRequiredError', () => {
  it('matches main’s sentinel, bare or wrapped by an IPC invoke', () => {
    expect(isFirstRunChoiceRequiredError(new Error(`${FIRST_RUN_CHOICE_REQUIRED}: waiting`))).toBe(true)
    expect(
      isFirstRunChoiceRequiredError(
        new Error(`Error invoking remote method 'hermes:connection': Error: ${FIRST_RUN_CHOICE_REQUIRED}: waiting`)
      )
    ).toBe(true)
    expect(isFirstRunChoiceRequiredError(FIRST_RUN_CHOICE_REQUIRED)).toBe(true)
  })

  it('ignores every other failure', () => {
    expect(isFirstRunChoiceRequiredError(new Error('Timed out connecting to Hermes backend'))).toBe(false)
    expect(isFirstRunChoiceRequiredError(undefined)).toBe(false)
    expect(isFirstRunChoiceRequiredError(null)).toBe(false)
  })
})

describe('firstRunChoiceRequired', () => {
  it('is false without a bridge or without the first-run IPC', async () => {
    await expect(firstRunChoiceRequired(undefined)).resolves.toBe(false)
    await expect(firstRunChoiceRequired({} as Window['hermesDesktop'])).resolves.toBe(false)
  })

  it('reports main’s answer and treats a throwing IPC as not required', async () => {
    const bridge = (required: boolean | Error) =>
      ({
        firstRunChoice: {
          get: vi.fn(async () => {
            if (required instanceof Error) {
              throw required
            }

            return { required }
          })
        }
      }) as unknown as Window['hermesDesktop']

    await expect(firstRunChoiceRequired(bridge(true))).resolves.toBe(true)
    await expect(firstRunChoiceRequired(bridge(false))).resolves.toBe(false)
    await expect(firstRunChoiceRequired(bridge(new Error('no ipc')))).resolves.toBe(false)
  })
})

describe('enterFirstRunChoice', () => {
  it('opens the blocking chooser, parks the boot splash and stops the sessions spinner', () => {
    enterFirstRunChoice()

    expectChooserOpen()
  })
})

describe('useFirstRunGate', () => {
  it('is ready on the first render when there is no bridge', () => {
    installBridge(undefined)

    const { result } = renderHook(() => useFirstRunGate())

    expect(result.current.firstRunReady).toBe(true)
    expectChooserClosed()
  })

  it('is ready on the first render when main has no first-run IPC', () => {
    installBridge({})

    const { result } = renderHook(() => useFirstRunGate())

    expect(result.current.firstRunReady).toBe(true)
    expectChooserClosed()
  })

  it('holds the boot until main answers, then opens when no choice is needed', async () => {
    const answer = deferred<{ required: boolean }>()
    installBridge({ firstRunChoice: { get: () => answer.promise } })

    const { result } = renderHook(() => useFirstRunGate())

    expect(result.current.firstRunReady).toBe(false)

    await act(async () => {
      answer.resolve({ required: false })
      await answer.promise
    })

    expect(result.current.firstRunReady).toBe(true)
    expectChooserClosed()
  })

  it('stays closed and opens the chooser when main needs the first-run choice', async () => {
    installBridge({ firstRunChoice: { get: async () => ({ required: true }) } })

    const { result } = renderHook(() => useFirstRunGate())

    await act(async () => undefined)

    expect(result.current.firstRunReady).toBe(false)
    expectChooserOpen()
  })

  it('opens (best-effort) when the first-run IPC rejects', async () => {
    installBridge({ firstRunChoice: { get: async () => Promise.reject(new Error('no ipc')) } })

    const { result } = renderHook(() => useFirstRunGate())

    await act(async () => undefined)

    expect(result.current.firstRunReady).toBe(true)
    expectChooserClosed()
  })

  it('ignores an answer that lands after unmount', async () => {
    const answer = deferred<{ required: boolean }>()
    installBridge({ firstRunChoice: { get: () => answer.promise } })

    const { unmount } = renderHook(() => useFirstRunGate())

    unmount()

    await act(async () => {
      answer.resolve({ required: true })
      await answer.promise
    })

    expectChooserClosed()
  })

  it('requireFirstRunChoice closes an open gate and opens the chooser; the callback is stable', async () => {
    installBridge(undefined)

    const { rerender, result } = renderHook(() => useFirstRunGate())
    const require = result.current.requireFirstRunChoice

    expect(result.current.firstRunReady).toBe(true)

    rerender()
    expect(result.current.requireFirstRunChoice).toBe(require)

    act(() => {
      require()
    })

    expect(result.current.firstRunReady).toBe(false)
    expect(result.current.requireFirstRunChoice).toBe(require)
    expectChooserOpen()
  })

  it('a consumer effect keyed on the gate is cleaned up before the chooser opens', () => {
    installBridge(undefined)

    const order: string[] = []

    const unsubscribe = $connectionModeDialog.listen(state => {
      if (state.open) {
        order.push('chooser')
      }
    })

    const { result } = renderHook(() => {
      const gate = useFirstRunGate()

      // Stands in for useGatewayBoot's effect, which is keyed on firstRunReady.
      useEffect(() => {
        if (!gate.firstRunReady) {
          return
        }

        order.push('boot')

        return () => {
          order.push('teardown')
        }
      }, [gate.firstRunReady])

      return gate
    })

    act(() => {
      result.current.requireFirstRunChoice()
    })

    unsubscribe()
    expect(order).toEqual(['boot', 'teardown', 'chooser'])
  })
})
