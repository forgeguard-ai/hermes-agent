---
title: "Desktop Font Size — Design Notes (implementation deferred)"
status: deferred
date: 2026-07-02
type: feature-design
target_repo: ForgeGuard/hermes-agent
origin: Phase 5 of docs/agent-plans/2026-07-02-forgeguard-fork-consolidation-plan.md
---

# Desktop Font Size — Design Notes

This branch (`feature/desktop-font-size`) intentionally contains **no
implementation yet**. It exists to hold the design direction below so a
future session (any agent) can pick it up cold. Keep this branch — and
`feat/devcontainer` — indefinitely as candidates for a future upstream PR to
`NousResearch/hermes-agent`; do not open that PR without explicit human
direction (see `AGENTS.md`'s Fork PR Policy).

## Problem

Users have asked for an explicit "font size" / text-scale control in the
desktop app's Settings. There is no dedicated font-scale system today.

## Key finding: don't build a parallel system — expose what already exists

`apps/desktop/electron/main.cjs` already implements full-window Chromium zoom
(`Cmd/Ctrl` + `+`/`-`/`0`), which visually scales *everything* (text, icons,
spacing) together — effectively font size in the way users actually
experience it. It is not exposed anywhere in the Settings UI. Building a
separate CSS `font-size` variable/scale system alongside this would create
two independent, possibly-conflicting scale mechanisms for one user-facing
concept. **Do not do that.** Surface the existing zoom mechanism instead.

### Existing zoom mechanism (as of the `v2026.7.1` sync)

- `apps/desktop/electron/main.cjs` (~line 4107 onward):
  - `ZOOM_STORAGE_KEY = 'hermes:desktop:zoomLevel'` — persisted in the
    renderer's own `localStorage` (per-origin, survives reloads/restarts).
  - `clampZoomLevel(value)` — clamps to `[-9, 9]` (Chromium's
    `webContents.setZoomLevel` range).
  - `setAndPersistZoomLevel(window, zoomLevel)` — the single entry point:
    calls `window.webContents.setZoomLevel(next)`, then mirrors `next` into
    `localStorage` via `executeJavaScript`.
  - `restorePersistedZoomLevel(window)` — reads the persisted value back on
    `did-finish-load` and re-applies it.
  - `installZoomShortcuts(window)` — intercepts `Cmd/Ctrl +`/`-`/`0` at 0.1
    steps (half Chromium's default 0.2, for finer control) and calls
    `setAndPersistZoomLevel`.
  - The zoom level is **main-process-owned**: the renderer never calls
    `setZoomLevel` directly, and there is currently no IPC channel for the
    renderer to *request* a zoom change or *read* the live value — it only
    exists in `localStorage` (written by main) and in `webContents`' own
    internal state (main-only).

### Existing pattern to mirror: `translucency` (renderer-owned setting + IPC)

`translucency` is the closest existing precedent for a Settings-UI-driven,
persisted, main-process-applied visual setting — mirror its shape, **not**
its ownership direction (translucency is renderer-owned; zoom today is
main-owned, see below):

- `apps/desktop/src/store/translucency.ts` — a small nanostore (`$translucency`)
  that reads its initial value from `localStorage` via `storedString`/`persistString`
  (`@/lib/storage`), and on every `.subscribe()` change: (1) persists to
  `localStorage`, (2) calls `window.hermesDesktop?.setTranslucency?.({ intensity })`.
- `apps/desktop/electron/preload.cjs` (line ~78): exposes
  `setTranslucency: payload => ipcRenderer.send('hermes:translucency', payload)`
  on `window.hermesDesktop`.
- `apps/desktop/electron/main.cjs` (line ~6921): `ipcMain.on('hermes:translucency', (_event, payload) => { ... })`
  applies the change to every open window.
- `apps/desktop/src/app/settings/appearance-settings.tsx` (line ~394): a
  `ListRow` with a range `<input>` slider as its `action`, wired to
  `translucency`/`setTranslucency` from the store, `useStore($translucency)`
  for the live value.

## Proposed shape (for the future implementation)

1. **New `apps/desktop/src/store/zoom.ts`** nanostore (`$zoomLevel`):
   - Initial value: read the *existing* `hermes:desktop:zoomLevel` localStorage
     key directly (already being written by main — no format change needed,
     no migration).
   - `setZoomLevel(level: number)`: clamp `[-9, 9]` (match main's existing
     `clampZoomLevel`), update the atom, and on subscribe: send a **new** IPC
     message (e.g. `hermes:setZoomLevel`) with the requested level — do NOT
     write directly to `localStorage` from the renderer store on this path,
     since main's `setAndPersistZoomLevel` already owns that write (avoid two
     writers to one key).
   - Also listen for external changes (keyboard-shortcut-driven zoom, which
     bypasses the store entirely today) so the Settings slider stays in sync
     if the user zooms via `Cmd/Ctrl +/-` while Settings is open — likely via
     a small `hermes:zoomLevelChanged` push event from main
     (`webContents.on('zoom-changed', ...)` or wrapping the shortcut handler)
     that the store subscribes to via a new preload-exposed listener, mirroring
     how other push-style events reach the renderer elsewhere in this codebase.
2. **New IPC channel in `main.cjs`**: `ipcMain.on('hermes:setZoomLevel', (_event, payload) => { ... call the EXISTING setAndPersistZoomLevel(window, payload.level) for the sending window's BrowserWindow ... })`.
   Reuse `setAndPersistZoomLevel` as-is — it already does the clamp + apply +
   persist. Don't duplicate that logic in the new handler.
3. **New `preload.cjs` entry**: `setZoomLevel: payload => ipcRenderer.send('hermes:setZoomLevel', payload)`.
4. **New `ListRow` in `appearance-settings.tsx`**, placed near the existing
   translucency row, mirroring its exact shape: a range `<input>` (map the
   `-9..9` internal zoom-level range to a friendlier displayed `%`, e.g.
   `Math.round(100 * 1.2 ** zoomLevel)` — Chromium's own zoom-to-percent
   curve — the same way Chrome's own zoom UI displays it) plus a numeric
   readout, and a "reset to 100%" affordance (mirrors `Cmd/Ctrl+0`).

## Explicitly out of scope for this feature

- A separate CSS font-scale/rem-multiplier system — the whole point is *not*
  building this.
- Per-element or per-pane zoom (this is a whole-window setting, matching the
  existing keyboard shortcut's scope).
- Windows/Linux-specific carve-outs — Chromium zoom is cross-platform, no
  known platform gap here (unlike `translucency`, which is genuinely
  macOS/Windows-only).

## Open questions for the implementer

- Confirm whether `zoom-changed` fires for keyboard-shortcut-driven zoom in
  the Electron version pinned here (`electron: 40.10.2` as of this note) —
  if not, the shortcut handlers (`installZoomShortcuts`) will need to
  explicitly push the new value to renderer(s) after calling
  `setAndPersistZoomLevel`, rather than relying on a webContents event.
- Decide whether the Settings slider should live-update as `Cmd/Ctrl +/-` is
  pressed while Settings is open, or only reflect the value on next open —
  the `translucency` precedent doesn't have this cross-source-of-truth problem
  (it has exactly one writer: the Settings UI itself), so there's no existing
  pattern to copy verbatim here.
