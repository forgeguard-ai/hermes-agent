#!/usr/bin/env node
/**
 * forgeguard-dist.mjs — the fork's packaging entry point.
 *
 * Runs electron-builder with `--config electron-builder.forgeguard.cjs`: the
 * upstream base config (electron-builder.config.cjs when present, else
 * package.json's "build" block) with the fork's overlay applied. All
 * arguments are passed through to electron-builder, e.g.
 *
 *   node scripts/forgeguard-dist.mjs --linux AppImage deb rpm
 *   node scripts/forgeguard-dist.mjs --win
 *   node scripts/forgeguard-dist.mjs --mac
 *   node scripts/forgeguard-dist.mjs --print-config   (resolved config as JSON, no build)
 *
 * It calls electron-builder directly instead of going through
 * scripts/run-electron-builder.mjs, because upstream's wrapper (0.22 and
 * later) only admits dmg, zip, msix, AppImage, deb and rpm and always passes
 * its own --config. What it keeps from that wrapper and the `builder` npm
 * script it replaces:
 *   - --publish never, always;
 *   - -c.electronDist=<installed electron>/dist when that binary exists
 *     (#38673, #47917), else electron-builder downloads electronVersion;
 *   - a 16 GiB V8 heap for the asar/blockmap pass;
 *   - the macOS electron-builder binary patch (scripts/patch-electron-builder-mac-binary.mjs),
 *     which the `prebuilder` npm hook runs for `npm run builder`.
 *
 * It does not run the renderer/main build; run `npm run build` first.
 */

import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)

export const DESKTOP_DIR = path.resolve(import.meta.dirname, '..')
export const FORGEGUARD_CONFIG = 'electron-builder.forgeguard.cjs'
const HEAP_FLAG = '--max-old-space-size=16384'

/** @returns {string | null} the installed electron's dist directory */
function electronDistDir() {
  try {
    return path.join(path.dirname(require.resolve('electron/package.json')), 'dist')
  } catch {
    return null
  }
}

/** @param {string} dist @param {NodeJS.Platform} [platform] */
function distBinary(dist, platform = process.platform) {
  if (platform === 'darwin') {
    return path.join(dist, 'Electron.app', 'Contents', 'MacOS', 'Electron')
  }
  if (platform === 'win32') {
    return path.join(dist, 'electron.exe')
  }
  return path.join(dist, 'electron')
}

/** @returns {string | null} electronDist to pass, when a usable local binary exists */
export function localElectronDist() {
  const dist = electronDistDir()
  return dist && fs.existsSync(distBinary(dist)) ? dist : null
}

/**
 * The electron-builder argv (after the CLI path).
 * @param {string[]} argv user arguments
 * @param {{ electronDist?: string | null }} [options]
 * @returns {string[]}
 */
export function builderArgs(argv, { electronDist = null } = {}) {
  const args = ['--config', FORGEGUARD_CONFIG, '--publish', 'never']
  if (electronDist) {
    args.push(`-c.electronDist=${electronDist}`)
  }
  return [...args, ...argv]
}

/**
 * NODE_OPTIONS for the electron-builder child: inherited options plus the heap
 * flag, unless a heap size is already set.
 * @param {string} [inherited]
 */
export function builderNodeOptions(inherited = process.env.NODE_OPTIONS ?? '') {
  return inherited.includes('--max-old-space-size') ? inherited : `${inherited} ${HEAP_FLAG}`.trim()
}

function electronBuilderCli() {
  const pkgJson = require.resolve('electron-builder/package.json')
  const bin = require(pkgJson).bin
  const rel = typeof bin === 'string' ? bin : bin['electron-builder']
  return path.join(path.dirname(pkgJson), rel)
}

/** JSON-safe view of the resolved config (functions shown by name). */
function printableConfig(config) {
  return JSON.stringify(
    config,
    (_key, value) => (typeof value === 'function' ? `[Function ${value.name || 'anonymous'}]` : value),
    2
  )
}

/** @param {string[]} argv @returns {number} exit status */
export function main(argv) {
  if (argv.includes('--print-config')) {
    const { loadBaseConfig, resolveForgeguardConfig } = require(path.join(DESKTOP_DIR, FORGEGUARD_CONFIG))
    console.error(`[forgeguard-dist] base config: ${loadBaseConfig(DESKTOP_DIR).source}`)
    console.log(printableConfig(resolveForgeguardConfig(DESKTOP_DIR)))
    return 0
  }

  const env = { ...process.env, NODE_OPTIONS: builderNodeOptions() }

  const patch = path.join(import.meta.dirname, 'patch-electron-builder-mac-binary.mjs')
  if (process.platform === 'darwin' && fs.existsSync(patch)) {
    const patched = spawnSync(process.execPath, [patch], { cwd: DESKTOP_DIR, stdio: 'inherit', env: process.env })
    if (patched.error || patched.status !== 0) {
      console.error(`[forgeguard-dist] ${path.basename(patch)} failed`)
      return patched.status || 1
    }
  }

  const electronDist = localElectronDist()
  if (!electronDist) {
    console.warn(
      '[forgeguard-dist] no local electron dist; electron-builder will fetch ' +
        'via @electron/get (electronVersion + ELECTRON_MIRROR).'
    )
  }

  const result = spawnSync(process.execPath, [electronBuilderCli(), ...builderArgs(argv, { electronDist })], {
    cwd: DESKTOP_DIR,
    stdio: 'inherit',
    env
  })
  if (result.error) {
    console.error(`[forgeguard-dist] spawn failed: ${result.error.message}`)
    return 1
  }
  return result.status == null ? 1 : result.status
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exit(main(process.argv.slice(2)))
}
