/**
 * The quit state machine, kept pure so it can be tested without Electron.
 *
 * Electron's `before-quit` fires once per `app.quit()`. Async teardown (backend
 * children, SSH tunnels) needs the first pass to `preventDefault()` and re-issue
 * `app.quit()` when done. Upstream's handler did that but never `return`ed, so
 * the destructive synchronous body (overlays, HUD, quick entry, PTYs) ran on the
 * cancelled pass, the async continuation was the only thing re-issuing quit,
 * and `window-all-closed` deliberately keeps the darwin process alive — the
 * result on macOS was Cmd+Q once: a half-torn-down app still in the Dock;
 * Cmd+Q twice: gone. Now the passes are explicit:
 *
 *   first pass with async work outstanding → 'defer'   (start it ONCE, quit again after)
 *   a pass while that work is still running → 'wait'    (swallow the extra Cmd+Q)
 *   async work done (or none)                → 'proceed' (sync teardown, then exit)
 */
export interface QuitPassState {
  /** Async teardown (backend / SSH) already started by an earlier pass. */
  teardownStarted: boolean
  /** Async teardown finished — the re-issued quit is this pass. */
  teardownDone: boolean
  /** There is async work to do at all (children, tunnels, bootstraps). */
  hasAsyncWork: boolean
}

export type QuitPassDecision = 'defer' | 'wait' | 'proceed'

export function decideQuitPass(state: QuitPassState): QuitPassDecision {
  if (state.teardownDone) {
    return 'proceed'
  }

  if (state.teardownStarted) {
    return 'wait'
  }

  return state.hasAsyncWork ? 'defer' : 'proceed'
}

/**
 * Whether `window-all-closed` should end the process on darwin. The macOS
 * convention (stay in the Dock) holds only outside a quit: once the user asked
 * to quit, or an updater/uninstaller handoff needs the process gone, the last
 * window closing must not leave a zombie in the Dock.
 */
export function shouldQuitOnAllWindowsClosed(input: {
  platform: NodeJS.Platform
  quittingForHandoff: boolean
  userQuitInProgress: boolean
}): boolean {
  return input.platform !== 'darwin' || input.quittingForHandoff || input.userQuitInProgress
}
