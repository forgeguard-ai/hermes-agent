/**
 * Desktop text size (whole-window Chromium zoom).
 *
 * "Text size" as users actually experience it: the main process owns
 * `webContents` zoom — also driven by ⌘/Ctrl +/−/0 — which scales text, icons,
 * and spacing together. Rather than build a parallel CSS font-scale system,
 * this store surfaces that existing zoom over IPC so a Settings slider can
 * drive it (see docs/agent-plans/2026-07-02-desktop-font-size-design-notes.md).
 *
 * Ownership: the zoom level is main-process-owned. Main persists it to
 * localStorage (`hermes:desktop:zoomLevel`) via `setAndPersistZoomLevel` and
 * re-applies it on load. This store reads that same key for its initial value
 * and *sends* level changes to main (which owns the write) — it never writes the
 * key itself, so there is exactly one writer. It also syncs back when zoom
 * changes from another source (the keyboard shortcuts) so the slider stays live
 * while Settings is open.
 */

import { atom } from 'nanostores'

// The key main writes/reads (apps/desktop/electron/main.cjs ZOOM_STORAGE_KEY).
// Read it directly for the initial value; do NOT persist here — main owns that.
const KEY = 'hermes:desktop:zoomLevel'

// Matches main's clampZoomLevel (the webContents.setZoomLevel range).
const clamp = (n: number): number => (Number.isFinite(n) ? Math.min(9, Math.max(-9, n)) : 0)

const read = (): number => {
  try {
    return clamp(Number(window.localStorage.getItem(KEY)))
  } catch {
    return 0
  }
}

export const $zoomLevel = atom<number>(typeof window === 'undefined' ? 0 : read())

// Suppress the outbound IPC when the change originated in main (a keyboard
// shortcut pushing the new level back) so we don't loop set→send→apply→push→set.
let applyingExternal = false

/** User-driven change from the Settings slider. */
export function setZoomLevel(level: number): void {
  $zoomLevel.set(clamp(level))
}

if (typeof window !== 'undefined') {
  $zoomLevel.subscribe(level => {
    if (applyingExternal) return
    window.hermesDesktop?.setZoomLevel?.({ level })
  })

  // Stay in sync when zoom changes from the keyboard shortcuts: main pushes the
  // new level and we set the atom under the guard, moving the slider without
  // echoing an IPC message back to main.
  window.hermesDesktop?.onZoomLevelChanged?.(level => {
    const next = clamp(level)
    if (next === $zoomLevel.get()) return
    applyingExternal = true
    try {
      $zoomLevel.set(next)
    } finally {
      applyingExternal = false
    }
  })
}
