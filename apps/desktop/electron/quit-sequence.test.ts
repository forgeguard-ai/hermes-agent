import { describe, expect, it } from 'vitest'

import { decideQuitPass, shouldQuitOnAllWindowsClosed } from './quit-sequence'

describe('decideQuitPass', () => {
  it('defers the first pass when async teardown is outstanding', () => {
    expect(decideQuitPass({ teardownStarted: false, teardownDone: false, hasAsyncWork: true })).toBe('defer')
  })

  it('swallows a repeated Cmd+Q while teardown runs', () => {
    expect(decideQuitPass({ teardownStarted: true, teardownDone: false, hasAsyncWork: true })).toBe('wait')
  })

  it('proceeds on the re-issued quit once teardown finished', () => {
    expect(decideQuitPass({ teardownStarted: true, teardownDone: true, hasAsyncWork: true })).toBe('proceed')
  })

  it('proceeds straight away with nothing async to do (pure client mode, no tunnels)', () => {
    expect(decideQuitPass({ teardownStarted: false, teardownDone: false, hasAsyncWork: false })).toBe('proceed')
  })
})

describe('shouldQuitOnAllWindowsClosed', () => {
  it('keeps the darwin process alive outside a quit (Dock convention)', () => {
    expect(shouldQuitOnAllWindowsClosed({ platform: 'darwin', quittingForHandoff: false, userQuitInProgress: false })).toBe(false)
  })

  it('ends the process during a user quit or an updater handoff on darwin', () => {
    expect(shouldQuitOnAllWindowsClosed({ platform: 'darwin', quittingForHandoff: false, userQuitInProgress: true })).toBe(true)
    expect(shouldQuitOnAllWindowsClosed({ platform: 'darwin', quittingForHandoff: true, userQuitInProgress: false })).toBe(true)
  })

  it('always ends the process elsewhere', () => {
    expect(shouldQuitOnAllWindowsClosed({ platform: 'linux', quittingForHandoff: false, userQuitInProgress: false })).toBe(true)
    expect(shouldQuitOnAllWindowsClosed({ platform: 'win32', quittingForHandoff: false, userQuitInProgress: false })).toBe(true)
  })
})
