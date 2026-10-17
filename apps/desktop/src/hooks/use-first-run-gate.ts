// First-run local-vs-remote gate for the desktop boot (ForgeGuard fork).
//
// On a fresh install (no prior choice, no explicit remote target, no existing
// local install) main defers starting a backend until the user picks local vs
// external Hermes. The renderer must then show the blocking chooser instead of
// booting: no boot-progress subscription, no gateway, no getConnection() — any
// of which would drive the connecting splash and race the chooser.
//
// Kept out of app/gateway/hooks/use-gateway-boot.ts on purpose: that file is
// upstream-owned and large. The fork hooks in there with three small seams (an
// early return, a guard at the top of boot()'s catch, and the effect deps)
// instead of wrapping and re-indenting the upstream effect body, so upstream
// syncs stay clean. This module lives under src/hooks so its import sorts into
// a quiet spot of that file's import list.
import { useCallback, useEffect, useState } from 'react'

import { suspendDesktopBootForChoice } from '@/store/boot'
import { openFirstRunConnectionChoice } from '@/store/connection-mode'
import { setSessionsLoading } from '@/store/session'

// Error text main uses when a backend call is made while the choice is still
// pending (see electron main's first-run handling).
export const FIRST_RUN_CHOICE_REQUIRED = 'FIRST_RUN_CHOICE_REQUIRED'

export type FirstRunGateState = 'pending' | 'ready' | 'required'

export interface FirstRunGate {
  // True once the gate has cleared and the gateway boot may run.
  firstRunReady: boolean
  // Park on the chooser after boot already started (first-run sentinel seen).
  // Flipping the gate re-runs the boot effect's cleanup, which tears down the
  // gateway machinery before the chooser opens. Stable across renders.
  requireFirstRunChoice: () => void
}

// Show the blocking first-run chooser and park the boot splash.
export function enterFirstRunChoice() {
  suspendDesktopBootForChoice()
  openFirstRunConnectionChoice()
  setSessionsLoading(false)
}

// A backend call rejected with main's first-run sentinel: treat it as "show the
// chooser", not a boot failure.
export function isFirstRunChoiceRequiredError(err: unknown): boolean {
  const message = err instanceof Error ? err.message : String(err)

  return message.includes(FIRST_RUN_CHOICE_REQUIRED)
}

// Best-effort: no bridge, an older main without the IPC, or an IPC that throws
// all mean "not required", so the app proceeds to connect as before the gate.
export async function firstRunChoiceRequired(desktop = window.hermesDesktop): Promise<boolean> {
  try {
    const fr = desktop?.firstRunChoice ? await desktop.firstRunChoice.get() : null

    return Boolean(fr?.required)
  } catch {
    return false
  }
}

export function useFirstRunGate(): FirstRunGate {
  // No bridge, or a main without the first-run IPC: nothing to ask, so the
  // boot effect runs on mount exactly as it would without the gate.
  const [state, setState] = useState<FirstRunGateState>(() =>
    window.hermesDesktop?.firstRunChoice ? 'pending' : 'ready'
  )

  useEffect(() => {
    if (state !== 'pending') {
      return
    }

    let cancelled = false

    void firstRunChoiceRequired().then(required => {
      if (!cancelled) {
        setState(required ? 'required' : 'ready')
      }
    })

    return () => {
      cancelled = true
    }
  }, [state])

  // Runs after React has applied every cleanup of the same commit, so on the
  // sentinel path the gateway teardown has finished before the chooser opens.
  useEffect(() => {
    if (state === 'required') {
      enterFirstRunChoice()
    }
  }, [state])

  const requireFirstRunChoice = useCallback(() => setState('required'), [])

  return { firstRunReady: state === 'ready', requireFirstRunChoice }
}
