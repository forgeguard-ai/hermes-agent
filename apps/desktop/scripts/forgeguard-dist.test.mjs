// ForgeGuard fork: the packaging overlay (electron-builder.forgeguard.cjs),
// its entry point (forgeguard-dist.mjs) and its afterPack hook. No packaging
// run: these check the resolved config, electron-builder's own loading and
// schema validation of it, and the argv the entry point would hand over.
import assert from 'node:assert/strict'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { afterEach, describe, test } from 'vitest'

import { adhocSignMacBundle, forgeguardAfterPack } from './forgeguard-after-pack.mjs'
import { builderArgs, builderNodeOptions, FORGEGUARD_CONFIG } from './forgeguard-dist.mjs'

const require = createRequire(import.meta.url)
const DESKTOP_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const overlay = require(join(DESKTOP_ROOT, FORGEGUARD_CONFIG))
const pkg = JSON.parse(readFileSync(join(DESKTOP_ROOT, 'package.json'), 'utf8'))

// The installer set and names the fork's releases ship. Changing any of these
// changes what users download; update the docs and release notes with them.
const EXPECTED = {
  artifactName: 'hermes-desktop-client-${version}-${os}-${arch}.${ext}',
  nsisArtifactName: 'hermes-desktop-client-${version}-win-${arch}-setup.${ext}',
  portableArtifactName: 'hermes-desktop-client-${version}-win-${arch}-portable.${ext}',
  linuxTargets: ['AppImage', 'deb', 'rpm'],
  winTargets: ['nsis', 'portable'],
  macTargets: ['dmg', 'zip'],
  homepage: 'https://github.com/forgeguard-ai/hermes-agent#readme'
}

function assertForkSettings(config) {
  assert.equal(config.artifactName, EXPECTED.artifactName)
  assert.equal(config.publish, null)
  assert.equal(config.afterPack, 'scripts/forgeguard-after-pack.mjs')
  assert.equal(config.extraMetadata?.homepage, EXPECTED.homepage)

  assert.deepEqual(config.mac.target, EXPECTED.macTargets)

  assert.deepEqual(config.win.target, EXPECTED.winTargets)
  assert.equal(config.win.signAndEditExecutable, false)

  assert.deepEqual(config.nsis, {
    ...config.nsis,
    artifactName: EXPECTED.nsisArtifactName,
    oneClick: false,
    allowToChangeInstallationDirectory: true,
    perMachine: false,
    shortcutName: 'Hermes',
    uninstallDisplayName: 'Hermes',
    warningsAsErrors: false
  })
  assert.equal(config.portable.artifactName, EXPECTED.portableArtifactName)

  assert.deepEqual(config.linux.target, EXPECTED.linuxTargets)
  assert.equal(config.linux.icon, 'assets/icons')
}

describe('resolved fork config on the current base', () => {
  test('the base is package.json#build until upstream ships electron-builder.config.cjs', () => {
    const { source } = overlay.loadBaseConfig(DESKTOP_ROOT)
    assert.equal(source, 'package.json#build')
  })

  test('carries every fork setting', () => {
    assertForkSettings(overlay.resolveForgeguardConfig(DESKTOP_ROOT))
  })

  test('electronVersion is the exact electron devDependency pin', () => {
    const config = overlay.resolveForgeguardConfig(DESKTOP_ROOT)
    assert.equal(config.electronVersion, pkg.devDependencies.electron)
  })

  test('keeps the upstream base settings it does not own', () => {
    const base = pkg.build
    const config = overlay.resolveForgeguardConfig(DESKTOP_ROOT)
    for (const key of [
      'appId',
      'productName',
      'executableName',
      'icon',
      'files',
      'asarUnpack',
      'beforePack',
      'afterSign',
      'dmg'
    ]) {
      assert.deepEqual(config[key], base[key], key)
    }
    assert.deepEqual(config.mac.extendInfo, base.mac.extendInfo)
    assert.equal(config.linux.maintainer, base.linux.maintainer)
  })

  test('electron-builder loads it as --config and its schema accepts it', async () => {
    const { getConfig, validateConfiguration } = require('app-builder-lib/out/util/config/config.js')
    const loaded = await getConfig(DESKTOP_ROOT, FORGEGUARD_CONFIG, null)
    assertForkSettings(loaded)
    await validateConfiguration(loaded, { isEnabled: false, add() {} })
  })
})

describe('overlay on an upstream 0.22-shaped base', () => {
  // The shape of upstream's electron-builder.config.cjs that the overlay has
  // to override: MSIX/AppImage-only targets, an update feed, a function-valued
  // mac signer, and its own extraMetadata.
  function upstreamShapedBase() {
    return {
      appId: 'com.nousresearch.hermes',
      artifactName: 'Hermes-${version}-${os}-${arch}.${ext}',
      publish: [{ provider: 'github', owner: 'NousResearch', repo: 'hermes-agent', channel: 'latest' }],
      extraMetadata: { name: 'Hermes', desktopName: 'com.nousresearch.hermes' },
      afterPack: 'scripts/after-pack.mjs',
      mac: {
        target: ['dmg', 'zip'],
        publish: [{ provider: 'generic', url: 'https://example.invalid/', channel: 'stable' }],
        sign: function upstreamSigner() {}
      },
      win: { target: ['msix'], legalTrademarks: 'Hermes' },
      msix: { identityName: 'Example' },
      linux: { category: 'Development', target: ['AppImage'] }
    }
  }

  test('restores the fork installer set, names and publish policy', () => {
    assertForkSettings(overlay.applyForgeguardOverlay(upstreamShapedBase()))
  })

  test('nulls platform-level publish and keeps upstream-only keys', () => {
    const config = overlay.applyForgeguardOverlay(upstreamShapedBase())
    assert.equal(config.mac.publish, null)
    assert.equal(config.mac.sign.name, 'upstreamSigner')
    assert.equal(config.win.legalTrademarks, 'Hermes')
    assert.deepEqual(config.msix, { identityName: 'Example' })
    assert.equal(config.extraMetadata.desktopName, 'com.nousresearch.hermes')
    assert.equal(config.linux.category, 'Development')
  })

  test('does not modify the base object', () => {
    const base = upstreamShapedBase()
    const before = JSON.stringify(base)
    overlay.applyForgeguardOverlay(base, { electronVersion: '1.2.3' })
    assert.equal(JSON.stringify(base), before)
  })
})

describe('loadBaseConfig prefers electron-builder.config.cjs', () => {
  let dir
  afterEach(() => dir && rmSync(dir, { recursive: true, force: true }))

  test('reads the upstream config file when it exists', () => {
    dir = mkdtempSync(join(tmpdir(), 'forgeguard-overlay-'))
    writeFileSync(
      join(dir, 'package.json'),
      JSON.stringify({ devDependencies: { electron: '40.10.6' }, build: { appId: 'from.package.json' } })
    )
    assert.equal(overlay.loadBaseConfig(dir).source, 'package.json#build')

    writeFileSync(
      join(dir, 'electron-builder.config.cjs'),
      "module.exports = { appId: 'from.config.cjs', win: { target: ['msix'] } }\n"
    )
    const { source, config } = overlay.loadBaseConfig(dir)
    assert.equal(source, 'electron-builder.config.cjs')
    assert.equal(config.appId, 'from.config.cjs')

    const resolved = overlay.resolveForgeguardConfig(dir)
    assert.equal(resolved.appId, 'from.config.cjs')
    assert.equal(resolved.electronVersion, '40.10.6')
    assert.deepEqual(resolved.win.target, EXPECTED.winTargets)
  })
})

describe('forgeguard-dist argv', () => {
  test('always passes the overlay config and --publish never, then the caller args', () => {
    assert.deepEqual(builderArgs(['--linux', 'AppImage', 'deb', 'rpm']), [
      '--config',
      'electron-builder.forgeguard.cjs',
      '--publish',
      'never',
      '--linux',
      'AppImage',
      'deb',
      'rpm'
    ])
  })

  test('reuses a local electron dist when there is one', () => {
    assert.deepEqual(builderArgs(['--win'], { electronDist: '/x/electron/dist' }), [
      '--config',
      'electron-builder.forgeguard.cjs',
      '--publish',
      'never',
      '-c.electronDist=/x/electron/dist',
      '--win'
    ])
  })

  test('sets the builder heap without dropping inherited NODE_OPTIONS', () => {
    assert.equal(builderNodeOptions(''), '--max-old-space-size=16384')
    assert.equal(builderNodeOptions('--require ./x.cjs'), '--require ./x.cjs --max-old-space-size=16384')
    assert.equal(builderNodeOptions('--max-old-space-size=4096'), '--max-old-space-size=4096')
  })

  test('every npm packaging script goes through forgeguard-dist', () => {
    assert.match(pkg.scripts.builder, /node scripts\/forgeguard-dist\.mjs$/)
    for (const [name, script] of Object.entries(pkg.scripts)) {
      if (name === 'pack' || name.startsWith('dist')) {
        assert.match(script, /npm run builder\b/, `${name} must package through the builder script`)
      }
    }
  })
})

describe('forgeguard-after-pack', () => {
  const context = platform => ({
    electronPlatformName: platform,
    appOutDir: '/out/mac-arm64',
    packager: { appInfo: { productFilename: 'Hermes' } }
  })

  test('runs the upstream hook, then ad-hoc signs on macOS', async () => {
    const calls = []
    await forgeguardAfterPack(context('darwin'), {
      upstream: () => calls.push('upstream'),
      sign: () => calls.push('sign')
    })
    assert.deepEqual(calls, ['upstream', 'sign'])
  })

  test('only runs the upstream hook elsewhere', async () => {
    for (const platform of ['win32', 'linux']) {
      const calls = []
      await forgeguardAfterPack(context(platform), {
        upstream: () => calls.push('upstream'),
        sign: () => calls.push('sign')
      })
      assert.deepEqual(calls, ['upstream'], platform)
    }
  })

  test('signs the bundle ad-hoc and verifies it', () => {
    const runs = []
    const app = adhocSignMacBundle(context('darwin'), (cmd, args) => runs.push([cmd, ...args]))
    assert.equal(app, '/out/mac-arm64/Hermes.app')
    assert.deepEqual(runs, [
      ['codesign', '--force', '--deep', '--sign', '-', app],
      ['codesign', '--verify', '--deep', '--strict', app]
    ])
  })
})
